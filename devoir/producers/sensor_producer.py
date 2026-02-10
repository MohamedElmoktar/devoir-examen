"""
Sensor Data Producer - Simulates industrial IoT sensors
Sends vibration, temperature, and pressure data to Kafka topics
"""

import json
import time
import random
import argparse
import numpy as np
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_SENSOR_NODE_1,
    TOPIC_SENSOR_NODE_2,
    SENSOR_INTERVAL_SECONDS,
    ANOMALY_PROBABILITY
)


class SensorSimulator:
    """Simulates industrial sensor data with occasional anomalies"""

    def __init__(self, node_id: int, seed: int = None):
        self.node_id = node_id
        if seed:
            np.random.seed(seed)
            random.seed(seed)

        # Normal operating parameters
        self.base_temperature = 65.0 + random.uniform(-5, 5)  # Base temp varies by node
        self.base_pressure = 100.0 + random.uniform(-10, 10)
        self.base_vibration = 0.5

    def generate_reading(self, inject_anomaly: bool = False) -> dict:
        """Generate a single sensor reading"""
        timestamp = datetime.utcnow().isoformat()

        if inject_anomaly or random.random() < ANOMALY_PROBABILITY:
            # Anomaly: significant deviation from normal
            vibration_x = self.base_vibration + np.random.normal(3.0, 0.5)
            vibration_y = self.base_vibration + np.random.normal(2.5, 0.5)
            vibration_z = self.base_vibration + np.random.normal(2.0, 0.5)
            temperature = self.base_temperature + np.random.normal(25, 5)
            pressure = self.base_pressure + np.random.normal(30, 10)
            is_anomaly = 1
        else:
            # Normal operation: small fluctuations
            vibration_x = self.base_vibration + np.random.normal(0, 0.1)
            vibration_y = self.base_vibration + np.random.normal(0, 0.1)
            vibration_z = self.base_vibration + np.random.normal(0, 0.1)
            temperature = self.base_temperature + np.random.normal(0, 2)
            pressure = self.base_pressure + np.random.normal(0, 3)
            is_anomaly = 0

        return {
            "timestamp": timestamp,
            "node_id": self.node_id,
            "sensor_id": f"sensor_{self.node_id}_{random.randint(1, 5)}",
            "features": {
                "vibration_x": round(vibration_x, 4),
                "vibration_y": round(vibration_y, 4),
                "vibration_z": round(vibration_z, 4),
                "temperature": round(temperature, 2),
                "pressure": round(pressure, 2)
            },
            "label": is_anomaly  # Ground truth for training
        }


class SensorProducer:
    """Kafka producer for sensor data"""

    def __init__(self, node_id: int, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.node_id = node_id
        self.topic = TOPIC_SENSOR_NODE_1 if node_id == 1 else TOPIC_SENSOR_NODE_2
        self.simulator = SensorSimulator(node_id)

        print(f"[Node {node_id}] Connecting to Kafka at {bootstrap_servers}...")
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3
        )
        print(f"[Node {node_id}] Connected! Publishing to topic: {self.topic}")

    def send_reading(self) -> dict:
        """Send a single sensor reading to Kafka"""
        reading = self.simulator.generate_reading()
        key = f"node_{self.node_id}"

        future = self.producer.send(self.topic, key=key, value=reading)
        try:
            record_metadata = future.get(timeout=10)
            return reading
        except KafkaError as e:
            print(f"[Node {self.node_id}] Error sending message: {e}")
            return None

    def run(self, interval: float = SENSOR_INTERVAL_SECONDS, max_messages: int = None):
        """Continuously send sensor readings"""
        print(f"[Node {self.node_id}] Starting sensor simulation...")
        print(f"[Node {self.node_id}] Interval: {interval}s, Anomaly probability: {ANOMALY_PROBABILITY*100}%")

        count = 0
        try:
            while max_messages is None or count < max_messages:
                reading = self.send_reading()
                if reading:
                    status = "ANOMALY" if reading["label"] == 1 else "NORMAL"
                    print(f"[Node {self.node_id}] Sent #{count+1}: {status} - "
                          f"Temp={reading['features']['temperature']}°C, "
                          f"Vib_x={reading['features']['vibration_x']}")
                count += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n[Node {self.node_id}] Shutting down...")
        finally:
            self.producer.flush()
            self.producer.close()
            print(f"[Node {self.node_id}] Producer closed. Total messages sent: {count}")

    def close(self):
        """Close the producer"""
        self.producer.flush()
        self.producer.close()


def main():
    parser = argparse.ArgumentParser(description='Sensor Data Producer for Federated Learning')
    parser.add_argument('--node-id', type=int, required=True, choices=[1, 2],
                        help='Node ID (1 or 2)')
    parser.add_argument('--interval', type=float, default=SENSOR_INTERVAL_SECONDS,
                        help='Interval between readings in seconds')
    parser.add_argument('--max-messages', type=int, default=None,
                        help='Maximum number of messages to send (default: unlimited)')
    parser.add_argument('--kafka-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                        help='Kafka bootstrap servers')

    args = parser.parse_args()

    producer = SensorProducer(args.node_id, args.kafka_servers)
    producer.run(interval=args.interval, max_messages=args.max_messages)


if __name__ == "__main__":
    main()
