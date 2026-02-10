"""
Cloud Aggregator - Implements Federated Averaging (FedAvg) algorithm
Collects model weights from Fog nodes and computes global model
"""

import json
import argparse
import numpy as np
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, ArrayType
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_MODEL_WEIGHTS,
    TOPIC_GLOBAL_MODEL,
    NUM_FEATURES,
    NUM_FOG_NODES,
    AGGREGATION_INTERVAL_SECONDS,
    MIN_NODES_FOR_AGGREGATION,
    SPARK_APP_NAME_CLOUD,
    SPARK_MASTER,
    LOG_DIR
)


class FedAvgAggregator:
    """Implements Federated Averaging algorithm"""

    def __init__(self, num_features: int = NUM_FEATURES):
        self.num_features = num_features
        self.global_weights = np.zeros(num_features)
        self.global_bias = 0.0
        self.round_number = 0
        self.loss_history = []
        self.node_contributions = defaultdict(list)

    def aggregate(self, node_weights: Dict[int, Dict]) -> Dict:
        """
        Apply FedAvg: w_{t+1} = sum_{k=1}^{K} (n_k / n) * w_k^t

        Args:
            node_weights: Dictionary mapping node_id to weight info
                         {node_id: {"weights": [...], "bias": float, "num_samples": int, "loss": float}}

        Returns:
            Dictionary with aggregated weights
        """
        if not node_weights:
            return None

        # Calculate total samples across all nodes
        total_samples = sum(w["num_samples"] for w in node_weights.values())

        if total_samples == 0:
            print("[Aggregator] No samples to aggregate")
            return None

        # Initialize aggregated weights
        aggregated_weights = np.zeros(self.num_features)
        aggregated_bias = 0.0
        weighted_loss = 0.0

        # Apply FedAvg formula
        for node_id, weight_info in node_weights.items():
            n_k = weight_info["num_samples"]
            w_k = np.array(weight_info["weights"])
            b_k = weight_info["bias"]
            loss_k = weight_info.get("loss", 0)

            # Weight by proportion of samples
            weight_factor = n_k / total_samples

            aggregated_weights += weight_factor * w_k
            aggregated_bias += weight_factor * b_k
            weighted_loss += weight_factor * loss_k

            # Track contributions
            self.node_contributions[node_id].append({
                "round": self.round_number + 1,
                "samples": n_k,
                "weight_factor": weight_factor,
                "loss": loss_k
            })

        # Update global model
        self.global_weights = aggregated_weights
        self.global_bias = aggregated_bias
        self.round_number += 1
        self.loss_history.append(weighted_loss)

        return {
            "weights": aggregated_weights.tolist(),
            "bias": float(aggregated_bias),
            "total_samples": total_samples,
            "weighted_loss": weighted_loss
        }

    def get_global_model(self) -> Dict:
        """Get current global model state"""
        return {
            "round": self.round_number,
            "aggregated_weights": {
                "weights": self.global_weights.tolist(),
                "bias": float(self.global_bias)
            },
            "loss_history": self.loss_history,
            "timestamp": datetime.utcnow().isoformat()
        }


class CloudAggregator:
    """Cloud node that aggregates models from Fog nodes"""

    def __init__(self, kafka_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.kafka_servers = kafka_servers
        self.aggregator = FedAvgAggregator()
        self.latest_weights = {}  # node_id -> latest weight info
        self.running = True

        # Kafka producer for publishing global model
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )

        # Initialize Spark session
        self.spark = SparkSession.builder \
            .appName(SPARK_APP_NAME_CLOUD) \
            .master(SPARK_MASTER) \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoint_cloud") \
            .config("spark.driver.memory", "2g") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

        print("[Cloud Aggregator] Initialized")
        print(f"[Cloud Aggregator] Listening to topic: {TOPIC_MODEL_WEIGHTS}")
        print(f"[Cloud Aggregator] Publishing to topic: {TOPIC_GLOBAL_MODEL}")

    def _define_weights_schema(self) -> StructType:
        """Define schema for model weights messages"""
        return StructType([
            StructField("node_id", IntegerType(), True),
            StructField("timestamp", StringType(), True),
            StructField("model_weights", StructType([
                StructField("weights", ArrayType(DoubleType()), True),
                StructField("bias", DoubleType(), True),
                StructField("num_samples", IntegerType(), True)
            ]), True),
            StructField("loss", DoubleType(), True)
        ])

    def publish_global_model(self, aggregated: Dict):
        """Publish the aggregated global model to Kafka"""
        global_model = self.aggregator.get_global_model()
        global_model["participating_nodes"] = list(self.latest_weights.keys())
        global_model["aggregation_info"] = aggregated

        try:
            future = self.producer.send(
                TOPIC_GLOBAL_MODEL,
                key="global_model",
                value=global_model
            )
            future.get(timeout=10)

            print(f"\n{'='*60}")
            print(f"[Cloud Aggregator] Round {self.aggregator.round_number} completed")
            print(f"  Participating nodes: {global_model['participating_nodes']}")
            print(f"  Total samples: {aggregated['total_samples']}")
            print(f"  Weighted loss: {aggregated['weighted_loss']:.6f}")
            print(f"  Global weights: {np.array(aggregated['weights'])[:3]}...")  # Show first 3
            print(f"  Global bias: {aggregated['bias']:.6f}")
            print(f"{'='*60}\n")

            # Log to file
            self._log_round(global_model, aggregated)

        except KafkaError as e:
            print(f"[Cloud Aggregator] Error publishing global model: {e}")

    def _log_round(self, global_model: Dict, aggregated: Dict):
        """Log aggregation round to file"""
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, "aggregation_log.jsonl")

        log_entry = {
            "round": self.aggregator.round_number,
            "timestamp": datetime.utcnow().isoformat(),
            "weighted_loss": aggregated["weighted_loss"],
            "total_samples": aggregated["total_samples"],
            "participating_nodes": global_model["participating_nodes"],
            "weights_norm": float(np.linalg.norm(aggregated["weights"]))
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def run_batch_mode(self, aggregation_interval: int = AGGREGATION_INTERVAL_SECONDS):
        """Run aggregator in batch mode - periodically aggregate available weights"""
        print("[Cloud Aggregator] Running in batch mode...")
        print(f"[Cloud Aggregator] Aggregation interval: {aggregation_interval}s")
        print(f"[Cloud Aggregator] Minimum nodes required: {MIN_NODES_FOR_AGGREGATION}")

        # Kafka consumer for weights
        consumer = KafkaConsumer(
            TOPIC_MODEL_WEIGHTS,
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='cloud_aggregator',
            consumer_timeout_ms=1000  # 1 second timeout for polling
        )

        last_aggregation_time = time.time()

        try:
            while self.running:
                # Poll for new weight updates
                messages = consumer.poll(timeout_ms=1000)

                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            weight_data = record.value
                            node_id = weight_data["node_id"]
                            model_weights = weight_data["model_weights"]
                            loss = weight_data.get("loss", 0)

                            self.latest_weights[node_id] = {
                                "weights": model_weights["weights"],
                                "bias": model_weights["bias"],
                                "num_samples": model_weights["num_samples"],
                                "loss": loss,
                                "timestamp": weight_data["timestamp"]
                            }

                            print(f"[Cloud Aggregator] Received weights from Node {node_id}: "
                                  f"samples={model_weights['num_samples']}, loss={loss:.4f}")

                        except Exception as e:
                            print(f"[Cloud Aggregator] Error processing weight message: {e}")

                # Check if it's time to aggregate
                current_time = time.time()
                if current_time - last_aggregation_time >= aggregation_interval:
                    if len(self.latest_weights) >= MIN_NODES_FOR_AGGREGATION:
                        # Perform aggregation
                        aggregated = self.aggregator.aggregate(self.latest_weights)
                        if aggregated:
                            self.publish_global_model(aggregated)
                            # Clear weights for next round
                            self.latest_weights.clear()
                    else:
                        print(f"[Cloud Aggregator] Waiting for more nodes... "
                              f"({len(self.latest_weights)}/{MIN_NODES_FOR_AGGREGATION})")

                    last_aggregation_time = current_time

        except KeyboardInterrupt:
            print("\n[Cloud Aggregator] Shutting down...")
        finally:
            consumer.close()
            self.cleanup()

    def run_streaming_mode(self, aggregation_interval: int = AGGREGATION_INTERVAL_SECONDS):
        """Run aggregator using Spark Structured Streaming"""
        print("[Cloud Aggregator] Running in streaming mode...")

        schema = self._define_weights_schema()

        # Read from Kafka
        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_servers) \
            .option("subscribe", TOPIC_MODEL_WEIGHTS) \
            .option("startingOffsets", "latest") \
            .load()

        # Parse JSON
        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data"),
            col("timestamp").alias("kafka_timestamp")
        ).select("data.*", "kafka_timestamp")

        def process_weights_batch(batch_df, batch_id):
            """Process a batch of weight updates"""
            if batch_df.isEmpty():
                return

            rows = batch_df.collect()

            for row in rows:
                try:
                    node_id = row.node_id
                    model_weights = row.model_weights
                    loss = row.loss or 0

                    self.latest_weights[node_id] = {
                        "weights": list(model_weights.weights),
                        "bias": float(model_weights.bias),
                        "num_samples": int(model_weights.num_samples),
                        "loss": float(loss),
                        "timestamp": row.timestamp
                    }

                    print(f"[Cloud Aggregator] Received weights from Node {node_id}: "
                          f"samples={model_weights.num_samples}")

                except Exception as e:
                    print(f"[Cloud Aggregator] Error processing row: {e}")

            # Check if we have enough nodes to aggregate
            if len(self.latest_weights) >= MIN_NODES_FOR_AGGREGATION:
                aggregated = self.aggregator.aggregate(self.latest_weights)
                if aggregated:
                    self.publish_global_model(aggregated)
                    self.latest_weights.clear()

        # Process stream
        query = parsed_df \
            .writeStream \
            .foreachBatch(process_weights_batch) \
            .trigger(processingTime=f"{aggregation_interval} seconds") \
            .start()

        try:
            query.awaitTermination()
        except KeyboardInterrupt:
            print("\n[Cloud Aggregator] Shutting down...")
            query.stop()
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.producer.flush()
        self.producer.close()

        # Print final summary
        print("\n" + "="*60)
        print("[Cloud Aggregator] Final Summary")
        print(f"  Total rounds completed: {self.aggregator.round_number}")
        if self.aggregator.loss_history:
            print(f"  Final weighted loss: {self.aggregator.loss_history[-1]:.6f}")
            print(f"  Loss history: {[f'{l:.4f}' for l in self.aggregator.loss_history[-10:]]}")
        print("="*60)

        self.spark.stop()
        print("[Cloud Aggregator] Cleaned up resources")


def main():
    parser = argparse.ArgumentParser(description='Cloud Aggregator for Federated Learning')
    parser.add_argument('--kafka-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                        help='Kafka bootstrap servers')
    parser.add_argument('--mode', type=str, choices=['batch', 'streaming'], default='batch',
                        help='Aggregation mode: batch or streaming')
    parser.add_argument('--interval', type=int, default=AGGREGATION_INTERVAL_SECONDS,
                        help='Aggregation interval in seconds')

    args = parser.parse_args()

    aggregator = CloudAggregator(args.kafka_servers)

    if args.mode == 'batch':
        aggregator.run_batch_mode(aggregation_interval=args.interval)
    else:
        aggregator.run_streaming_mode(aggregation_interval=args.interval)


if __name__ == "__main__":
    main()
