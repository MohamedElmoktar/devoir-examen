"""
Fog Node - Spark Structured Streaming application for local model training
Implements Stochastic Gradient Descent (SGD) for anomaly detection
"""

import json
import argparse
import numpy as np
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, udf, struct, to_json
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    IntegerType, TimestampType, ArrayType
)
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_SENSOR_NODE_1,
    TOPIC_SENSOR_NODE_2,
    TOPIC_MODEL_WEIGHTS,
    TOPIC_GLOBAL_MODEL,
    NUM_FEATURES,
    LEARNING_RATE,
    BATCH_SIZE,
    LOCAL_EPOCHS,
    WEIGHT_PUBLISH_INTERVAL_SECONDS,
    SPARK_APP_NAME_FOG,
    SPARK_MASTER
)


class SGDModel:
    """Simple logistic regression model with SGD optimizer for anomaly detection"""

    def __init__(self, num_features: int = NUM_FEATURES, learning_rate: float = LEARNING_RATE):
        self.num_features = num_features
        self.learning_rate = learning_rate
        # Initialize weights randomly
        self.weights = np.random.randn(num_features) * 0.01
        self.bias = 0.0
        self.num_samples_trained = 0
        self.training_loss_history = []

    def sigmoid(self, z: np.ndarray) -> np.ndarray:
        """Sigmoid activation function"""
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probability of anomaly"""
        z = np.dot(X, self.weights) + self.bias
        return self.sigmoid(z)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class (0 or 1)"""
        return (self.predict_proba(X) >= 0.5).astype(int)

    def compute_loss(self, X: np.ndarray, y: np.ndarray) -> float:
        """Compute binary cross-entropy loss"""
        epsilon = 1e-15
        y_pred = self.predict_proba(X)
        y_pred = np.clip(y_pred, epsilon, 1 - epsilon)
        loss = -np.mean(y * np.log(y_pred) + (1 - y) * np.log(1 - y_pred))
        return loss

    def train_batch(self, X: np.ndarray, y: np.ndarray) -> float:
        """Train on a batch of data using SGD"""
        if len(X) == 0:
            return 0.0

        # Forward pass
        y_pred = self.predict_proba(X)

        # Compute gradients
        error = y_pred - y
        grad_weights = np.dot(X.T, error) / len(X)
        grad_bias = np.mean(error)

        # Update parameters
        self.weights -= self.learning_rate * grad_weights
        self.bias -= self.learning_rate * grad_bias

        # Compute loss
        loss = self.compute_loss(X, y)
        self.training_loss_history.append(loss)
        self.num_samples_trained += len(X)

        return loss

    def get_weights(self) -> Dict:
        """Get model weights as dictionary"""
        return {
            "weights": self.weights.tolist(),
            "bias": float(self.bias),
            "num_samples": self.num_samples_trained
        }

    def set_weights(self, weights: List[float], bias: float):
        """Set model weights from global model"""
        self.weights = np.array(weights)
        self.bias = bias

    def get_latest_loss(self) -> float:
        """Get the most recent training loss"""
        if self.training_loss_history:
            return self.training_loss_history[-1]
        return float('inf')


class FogNode:
    """Fog node that processes sensor data and trains local model"""

    def __init__(self, node_id: int, kafka_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.node_id = node_id
        self.kafka_servers = kafka_servers
        self.topic = TOPIC_SENSOR_NODE_1 if node_id == 1 else TOPIC_SENSOR_NODE_2
        self.model = SGDModel()
        self.data_buffer = []
        self.buffer_lock = threading.Lock()
        self.running = True

        # Kafka producer for publishing weights
        self.weight_producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )

        # Initialize Spark session
        self.spark = SparkSession.builder \
            .appName(f"{SPARK_APP_NAME_FOG}_{node_id}") \
            .master(SPARK_MASTER) \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.sql.streaming.checkpointLocation", f"/tmp/checkpoint_fog_{node_id}") \
            .config("spark.driver.memory", "2g") \
            .config("spark.executor.memory", "2g") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

        print(f"[Fog Node {node_id}] Initialized with Spark session")
        print(f"[Fog Node {node_id}] Listening to topic: {self.topic}")

    def _define_schema(self) -> StructType:
        """Define schema for sensor data"""
        return StructType([
            StructField("timestamp", StringType(), True),
            StructField("node_id", IntegerType(), True),
            StructField("sensor_id", StringType(), True),
            StructField("features", StructType([
                StructField("vibration_x", DoubleType(), True),
                StructField("vibration_y", DoubleType(), True),
                StructField("vibration_z", DoubleType(), True),
                StructField("temperature", DoubleType(), True),
                StructField("pressure", DoubleType(), True)
            ]), True),
            StructField("label", IntegerType(), True)
        ])

    def extract_features(self, row) -> tuple:
        """Extract feature vector and label from a row"""
        features = np.array([
            row.features.vibration_x,
            row.features.vibration_y,
            row.features.vibration_z,
            row.features.temperature,
            row.features.pressure
        ])
        # Normalize features
        features = (features - np.array([0.5, 0.5, 0.5, 65, 100])) / np.array([1, 1, 1, 20, 30])
        label = row.label
        return features, label

    def process_batch(self, batch_df, batch_id):
        """Process a micro-batch of data"""
        if batch_df.isEmpty():
            return

        # Collect data and train locally
        rows = batch_df.collect()

        X_batch = []
        y_batch = []

        for row in rows:
            try:
                features, label = self.extract_features(row)
                X_batch.append(features)
                y_batch.append(label)
            except Exception as e:
                print(f"[Fog Node {self.node_id}] Error extracting features: {e}")
                continue

        if len(X_batch) > 0:
            X = np.array(X_batch)
            y = np.array(y_batch)

            # Train on batch
            loss = self.model.train_batch(X, y)
            accuracy = np.mean(self.model.predict(X) == y)

            print(f"[Fog Node {self.node_id}] Batch {batch_id}: "
                  f"samples={len(X)}, loss={loss:.4f}, accuracy={accuracy:.4f}, "
                  f"total_trained={self.model.num_samples_trained}")

    def publish_weights(self):
        """Publish model weights to Kafka"""
        weights_data = {
            "node_id": self.node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model_weights": self.model.get_weights(),
            "loss": self.model.get_latest_loss()
        }

        try:
            future = self.weight_producer.send(
                TOPIC_MODEL_WEIGHTS,
                key=f"fog_node_{self.node_id}",
                value=weights_data
            )
            future.get(timeout=10)
            print(f"[Fog Node {self.node_id}] Published weights: "
                  f"samples={self.model.num_samples_trained}, loss={self.model.get_latest_loss():.4f}")
        except KafkaError as e:
            print(f"[Fog Node {self.node_id}] Error publishing weights: {e}")

    def subscribe_to_global_model(self):
        """Subscribe to global model updates in a separate thread"""
        def listen_for_updates():
            consumer = KafkaConsumer(
                TOPIC_GLOBAL_MODEL,
                bootstrap_servers=self.kafka_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id=f'fog_node_{self.node_id}_consumer'
            )

            print(f"[Fog Node {self.node_id}] Listening for global model updates...")

            for message in consumer:
                if not self.running:
                    break
                try:
                    global_model = message.value
                    weights = global_model["aggregated_weights"]["weights"]
                    bias = global_model["aggregated_weights"]["bias"]
                    round_num = global_model.get("round", "?")

                    self.model.set_weights(weights, bias)
                    print(f"[Fog Node {self.node_id}] Received global model (round {round_num}), "
                          f"updated local weights")
                except Exception as e:
                    print(f"[Fog Node {self.node_id}] Error processing global model: {e}")

            consumer.close()

        thread = threading.Thread(target=listen_for_updates, daemon=True)
        thread.start()
        return thread

    def weight_publisher_thread(self):
        """Background thread that publishes weights periodically"""
        def publish_loop():
            while self.running:
                time.sleep(WEIGHT_PUBLISH_INTERVAL_SECONDS)
                if self.model.num_samples_trained > 0:
                    self.publish_weights()

        thread = threading.Thread(target=publish_loop, daemon=True)
        thread.start()
        return thread

    def run(self):
        """Run the fog node streaming application"""
        print(f"[Fog Node {self.node_id}] Starting Spark Structured Streaming...")

        # Start background threads
        self.subscribe_to_global_model()
        self.weight_publisher_thread()

        schema = self._define_schema()

        # Read from Kafka
        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_servers) \
            .option("subscribe", self.topic) \
            .option("startingOffsets", "latest") \
            .load()

        # Parse JSON data
        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data")
        ).select("data.*")

        # Process stream with foreachBatch
        query = parsed_df \
            .writeStream \
            .foreachBatch(self.process_batch) \
            .outputMode("append") \
            .trigger(processingTime="5 seconds") \
            .start()

        try:
            query.awaitTermination()
        except KeyboardInterrupt:
            print(f"\n[Fog Node {self.node_id}] Shutting down...")
            self.running = False
            query.stop()
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.weight_producer.flush()
        self.weight_producer.close()
        self.spark.stop()
        print(f"[Fog Node {self.node_id}] Cleaned up resources")


def main():
    parser = argparse.ArgumentParser(description='Fog Node for Federated Learning')
    parser.add_argument('--node-id', type=int, required=True, choices=[1, 2],
                        help='Node ID (1 or 2)')
    parser.add_argument('--kafka-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                        help='Kafka bootstrap servers')

    args = parser.parse_args()

    fog_node = FogNode(args.node_id, args.kafka_servers)
    fog_node.run()


if __name__ == "__main__":
    main()
