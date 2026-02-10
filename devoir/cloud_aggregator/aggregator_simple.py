"""
Simplified Cloud Aggregator - Pure Python version without Spark
Uses Kafka consumers directly for faster testing and demo
"""

import json
import argparse
import numpy as np
import time
import os
from datetime import datetime
from typing import Dict
from collections import defaultdict
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_MODEL_WEIGHTS,
    TOPIC_GLOBAL_MODEL,
    NUM_FEATURES,
    AGGREGATION_INTERVAL_SECONDS,
    MIN_NODES_FOR_AGGREGATION,
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

    def aggregate(self, node_weights: Dict[int, Dict]) -> Dict:
        """
        Apply FedAvg: w_{t+1} = sum_{k=1}^{K} (n_k / n) * w_k^t
        """
        if not node_weights:
            return None

        total_samples = sum(w["num_samples"] for w in node_weights.values())
        if total_samples == 0:
            return None

        aggregated_weights = np.zeros(self.num_features)
        aggregated_bias = 0.0
        weighted_loss = 0.0

        for node_id, weight_info in node_weights.items():
            n_k = weight_info["num_samples"]
            w_k = np.array(weight_info["weights"])
            b_k = weight_info["bias"]
            loss_k = weight_info.get("loss", 0)

            weight_factor = n_k / total_samples
            aggregated_weights += weight_factor * w_k
            aggregated_bias += weight_factor * b_k
            weighted_loss += weight_factor * loss_k

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
        return {
            "round": self.round_number,
            "aggregated_weights": {
                "weights": self.global_weights.tolist(),
                "bias": float(self.global_bias)
            },
            "loss_history": self.loss_history,
            "timestamp": datetime.utcnow().isoformat()
        }


class SimpleCloudAggregator:
    """Simplified cloud aggregator using direct Kafka consumers"""

    def __init__(self, kafka_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.kafka_servers = kafka_servers
        self.aggregator = FedAvgAggregator()
        self.latest_weights = {}
        self.running = True

        self.producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )

        print("[Cloud Aggregator] Initialized")
        print(f"[Cloud Aggregator] Listening to topic: {TOPIC_MODEL_WEIGHTS}")
        print(f"[Cloud Aggregator] Publishing to topic: {TOPIC_GLOBAL_MODEL}")

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
            print(f"  Global weights: {np.array(aggregated['weights'])[:3]}...")
            print(f"{'='*60}\n")

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

    def run(self, aggregation_interval: int = AGGREGATION_INTERVAL_SECONDS):
        """Run the aggregator"""
        print(f"[Cloud Aggregator] Aggregation interval: {aggregation_interval}s")
        print(f"[Cloud Aggregator] Minimum nodes: {MIN_NODES_FOR_AGGREGATION}")

        consumer = KafkaConsumer(
            TOPIC_MODEL_WEIGHTS,
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='cloud_aggregator_simple',
            consumer_timeout_ms=1000
        )

        last_aggregation_time = time.time()

        try:
            while self.running:
                messages = consumer.poll(timeout_ms=1000)

                for tp, records in messages.items():
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
                                "loss": loss
                            }

                            print(f"[Cloud Aggregator] Received weights from Node {node_id}: "
                                  f"samples={model_weights['num_samples']}, loss={loss:.4f}")

                        except Exception as e:
                            print(f"[Cloud Aggregator] Error processing message: {e}")

                # Check if it's time to aggregate
                current_time = time.time()
                if current_time - last_aggregation_time >= aggregation_interval:
                    if len(self.latest_weights) >= MIN_NODES_FOR_AGGREGATION:
                        aggregated = self.aggregator.aggregate(self.latest_weights)
                        if aggregated:
                            self.publish_global_model(aggregated)
                            self.latest_weights.clear()
                    else:
                        print(f"[Cloud Aggregator] Waiting for nodes... "
                              f"({len(self.latest_weights)}/{MIN_NODES_FOR_AGGREGATION})")

                    last_aggregation_time = current_time

        except KeyboardInterrupt:
            print("\n[Cloud Aggregator] Shutting down...")
        finally:
            consumer.close()
            self.producer.flush()
            self.producer.close()

            print("\n" + "="*60)
            print("[Cloud Aggregator] Final Summary")
            print(f"  Total rounds: {self.aggregator.round_number}")
            if self.aggregator.loss_history:
                print(f"  Final loss: {self.aggregator.loss_history[-1]:.6f}")
            print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Simplified Cloud Aggregator')
    parser.add_argument('--kafka-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS)
    parser.add_argument('--interval', type=int, default=AGGREGATION_INTERVAL_SECONDS)

    args = parser.parse_args()

    aggregator = SimpleCloudAggregator(args.kafka_servers)
    aggregator.run(aggregation_interval=args.interval)


if __name__ == "__main__":
    main()
