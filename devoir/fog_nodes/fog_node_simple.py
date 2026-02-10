"""
Simplified Fog Node - Pure Python version without Spark Streaming
Uses Kafka consumers directly for faster testing and demo
"""

import json
import argparse
import numpy as np
import threading
import time
from datetime import datetime
from typing import Dict
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
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
    WEIGHT_PUBLISH_INTERVAL_SECONDS
)


class SGDModel:
    """Simple logistic regression model with SGD optimizer for anomaly detection"""

    def __init__(self, num_features: int = NUM_FEATURES, learning_rate: float = LEARNING_RATE):
        self.num_features = num_features
        self.learning_rate = learning_rate
        self.weights = np.random.randn(num_features) * 0.01
        self.bias = 0.0
        self.num_samples_trained = 0
        self.training_loss_history = []

    def sigmoid(self, z: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        z = np.dot(X, self.weights) + self.bias
        return self.sigmoid(z)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) >= 0.5).astype(int)

    def compute_loss(self, X: np.ndarray, y: np.ndarray) -> float:
        epsilon = 1e-15
        y_pred = self.predict_proba(X)
        y_pred = np.clip(y_pred, epsilon, 1 - epsilon)
        loss = -np.mean(y * np.log(y_pred) + (1 - y) * np.log(1 - y_pred))
        return loss

    def train_batch(self, X: np.ndarray, y: np.ndarray) -> float:
        if len(X) == 0:
            return 0.0

        y_pred = self.predict_proba(X)
        error = y_pred - y
        grad_weights = np.dot(X.T, error) / len(X)
        grad_bias = np.mean(error)

        self.weights -= self.learning_rate * grad_weights
        self.bias -= self.learning_rate * grad_bias

        loss = self.compute_loss(X, y)
        self.training_loss_history.append(loss)
        self.num_samples_trained += len(X)

        return loss

    def get_weights(self) -> Dict:
        return {
            "weights": self.weights.tolist(),
            "bias": float(self.bias),
            "num_samples": self.num_samples_trained
        }

    def set_weights(self, weights, bias):
        self.weights = np.array(weights)
        self.bias = bias

    def get_latest_loss(self) -> float:
        return self.training_loss_history[-1] if self.training_loss_history else float('inf')


class SimpleFogNode:
    """Simplified fog node using direct Kafka consumers"""

    def __init__(self, node_id: int, kafka_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.node_id = node_id
        self.kafka_servers = kafka_servers
        self.topic = TOPIC_SENSOR_NODE_1 if node_id == 1 else TOPIC_SENSOR_NODE_2
        self.model = SGDModel()
        self.running = True
        self.data_buffer = []

        # Kafka producer for publishing weights
        self.weight_producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )

        print(f"[Fog Node {node_id}] Initialized")
        print(f"[Fog Node {node_id}] Listening to topic: {self.topic}")

    def extract_features(self, data: Dict) -> tuple:
        """Extract feature vector and label from sensor data"""
        features = np.array([
            data['features']['vibration_x'],
            data['features']['vibration_y'],
            data['features']['vibration_z'],
            data['features']['temperature'],
            data['features']['pressure']
        ])
        # Normalize
        features = (features - np.array([0.5, 0.5, 0.5, 65, 100])) / np.array([1, 1, 1, 20, 30])
        return features, data['label']

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

    def global_model_listener(self):
        """Listen for global model updates"""
        consumer = KafkaConsumer(
            TOPIC_GLOBAL_MODEL,
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            group_id=f'fog_node_{self.node_id}_global',
            consumer_timeout_ms=1000
        )

        while self.running:
            try:
                messages = consumer.poll(timeout_ms=1000)
                for tp, records in messages.items():
                    for record in records:
                        global_model = record.value
                        weights = global_model["aggregated_weights"]["weights"]
                        bias = global_model["aggregated_weights"]["bias"]
                        round_num = global_model.get("round", "?")

                        self.model.set_weights(weights, bias)
                        print(f"[Fog Node {self.node_id}] Received global model (round {round_num})")
            except Exception as e:
                if self.running:
                    pass  # Ignore timeout errors
        consumer.close()

    def run(self):
        """Run the fog node"""
        print(f"[Fog Node {self.node_id}] Starting...")

        # Start global model listener thread
        listener_thread = threading.Thread(target=self.global_model_listener, daemon=True)
        listener_thread.start()

        # Sensor data consumer
        consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            group_id=f'fog_node_{self.node_id}_sensor',
            consumer_timeout_ms=1000
        )

        last_publish_time = time.time()
        batch_X = []
        batch_y = []

        try:
            while self.running:
                messages = consumer.poll(timeout_ms=1000)

                for tp, records in messages.items():
                    for record in records:
                        try:
                            features, label = self.extract_features(record.value)
                            batch_X.append(features)
                            batch_y.append(label)
                        except Exception as e:
                            print(f"[Fog Node {self.node_id}] Error processing message: {e}")

                # Train on batch if we have enough samples
                if len(batch_X) >= BATCH_SIZE:
                    X = np.array(batch_X)
                    y = np.array(batch_y)
                    loss = self.model.train_batch(X, y)
                    accuracy = np.mean(self.model.predict(X) == y)
                    print(f"[Fog Node {self.node_id}] Trained batch: samples={len(X)}, "
                          f"loss={loss:.4f}, accuracy={accuracy:.4f}, "
                          f"total={self.model.num_samples_trained}")
                    batch_X = []
                    batch_y = []

                # Publish weights periodically
                current_time = time.time()
                if current_time - last_publish_time >= WEIGHT_PUBLISH_INTERVAL_SECONDS:
                    if self.model.num_samples_trained > 0:
                        self.publish_weights()
                    last_publish_time = current_time

        except KeyboardInterrupt:
            print(f"\n[Fog Node {self.node_id}] Shutting down...")
        finally:
            self.running = False
            consumer.close()
            self.weight_producer.flush()
            self.weight_producer.close()
            print(f"[Fog Node {self.node_id}] Cleaned up")


def main():
    parser = argparse.ArgumentParser(description='Simplified Fog Node for Federated Learning')
    parser.add_argument('--node-id', type=int, required=True, choices=[1, 2],
                        help='Node ID (1 or 2)')
    parser.add_argument('--kafka-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                        help='Kafka bootstrap servers')

    args = parser.parse_args()

    fog_node = SimpleFogNode(args.node_id, args.kafka_servers)
    fog_node.run()


if __name__ == "__main__":
    main()
