"""
Monitoring Dashboard - Real-time visualization of Federated Learning progress
Shows loss convergence, node participation, and model metrics
"""

import json
import os
import time
import argparse
from datetime import datetime
from typing import List, Dict
from kafka import KafkaConsumer
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_GLOBAL_MODEL,
    TOPIC_MODEL_WEIGHTS,
    LOG_DIR
)


class ConsoleDashboard:
    """Simple console-based dashboard for monitoring FL progress"""

    def __init__(self, kafka_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.kafka_servers = kafka_servers
        self.rounds: List[Dict] = []
        self.node_stats: Dict[int, Dict] = {}

    def clear_screen(self):
        """Clear console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """Print dashboard header"""
        print("=" * 70)
        print("       FEDERATED LEARNING MONITORING DASHBOARD")
        print("       Kafka + Spark | FedAvg Aggregation")
        print("=" * 70)
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

    def print_loss_chart(self, losses: List[float], width: int = 50):
        """Print ASCII chart of loss convergence"""
        if not losses:
            print("  No data yet...")
            return

        print("\n  LOSS CONVERGENCE")
        print("  " + "-" * (width + 10))

        # Normalize losses for display
        min_loss = min(losses) if losses else 0
        max_loss = max(losses) if losses else 1
        range_loss = max_loss - min_loss if max_loss != min_loss else 1

        # Show last N rounds
        display_losses = losses[-20:]
        for i, loss in enumerate(display_losses):
            round_num = len(losses) - len(display_losses) + i + 1
            normalized = (loss - min_loss) / range_loss
            bar_length = int(normalized * width)
            bar = "#" * bar_length + "-" * (width - bar_length)
            print(f"  R{round_num:3d} |{bar}| {loss:.6f}")

        print("  " + "-" * (width + 10))
        print(f"  Min Loss: {min_loss:.6f}  |  Max Loss: {max_loss:.6f}  |  Latest: {losses[-1]:.6f}")

    def print_node_stats(self):
        """Print statistics per node"""
        print("\n  NODE STATISTICS")
        print("  " + "-" * 60)
        print(f"  {'Node':<10} {'Samples':<12} {'Last Loss':<12} {'Contributions':<15}")
        print("  " + "-" * 60)

        for node_id, stats in sorted(self.node_stats.items()):
            print(f"  Node {node_id:<4} {stats.get('total_samples', 0):<12} "
                  f"{stats.get('last_loss', 0):<12.6f} {stats.get('contributions', 0):<15}")

        print("  " + "-" * 60)

    def print_summary(self):
        """Print current training summary"""
        if not self.rounds:
            print("\n  Waiting for aggregation rounds...")
            return

        latest = self.rounds[-1]
        print("\n  CURRENT GLOBAL MODEL")
        print("  " + "-" * 60)
        print(f"  Round:              {latest.get('round', 'N/A')}")
        print(f"  Timestamp:          {latest.get('timestamp', 'N/A')}")
        print(f"  Participating Nodes: {latest.get('participating_nodes', [])}")
        print(f"  Total Samples:      {latest.get('aggregation_info', {}).get('total_samples', 'N/A')}")
        print(f"  Weighted Loss:      {latest.get('aggregation_info', {}).get('weighted_loss', 'N/A'):.6f}")
        print("  " + "-" * 60)

    def update_from_message(self, message: Dict):
        """Update dashboard state from a Kafka message"""
        self.rounds.append(message)

        # Update node stats
        participating = message.get("participating_nodes", [])
        aggregation_info = message.get("aggregation_info", {})

        for node_id in participating:
            if node_id not in self.node_stats:
                self.node_stats[node_id] = {"total_samples": 0, "contributions": 0}

            self.node_stats[node_id]["contributions"] += 1
            self.node_stats[node_id]["total_samples"] = aggregation_info.get("total_samples", 0) // len(participating)
            self.node_stats[node_id]["last_loss"] = aggregation_info.get("weighted_loss", 0)

    def render(self):
        """Render the full dashboard"""
        self.clear_screen()
        self.print_header()

        losses = [r.get("aggregation_info", {}).get("weighted_loss", 0) for r in self.rounds]
        self.print_loss_chart(losses)

        self.print_node_stats()
        self.print_summary()

        print("\n  Press Ctrl+C to exit")

    def run(self):
        """Run the monitoring dashboard"""
        print("Starting Federated Learning Dashboard...")
        print(f"Connecting to Kafka at {self.kafka_servers}...")

        consumer = KafkaConsumer(
            TOPIC_GLOBAL_MODEL,
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='dashboard_consumer'
        )

        print("Connected! Waiting for aggregation events...")

        try:
            for message in consumer:
                self.update_from_message(message.value)
                self.render()
        except KeyboardInterrupt:
            print("\n\nDashboard stopped.")
        finally:
            consumer.close()


class LogFileDashboard:
    """Dashboard that reads from log file (for offline analysis)"""

    def __init__(self, log_file: str = None):
        self.log_file = log_file or os.path.join(LOG_DIR, "aggregation_log.jsonl")
        self.rounds = []

    def load_logs(self):
        """Load aggregation logs from file"""
        if not os.path.exists(self.log_file):
            print(f"Log file not found: {self.log_file}")
            return

        self.rounds = []
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    self.rounds.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

    def print_summary(self):
        """Print training summary from logs"""
        if not self.rounds:
            print("No training data found in logs.")
            return

        print("=" * 70)
        print("       FEDERATED LEARNING TRAINING SUMMARY")
        print("=" * 70)

        print(f"\n  Total Rounds: {len(self.rounds)}")
        print(f"  First Round:  {self.rounds[0].get('timestamp', 'N/A')}")
        print(f"  Last Round:   {self.rounds[-1].get('timestamp', 'N/A')}")

        losses = [r.get('weighted_loss', 0) for r in self.rounds]
        print(f"\n  Initial Loss: {losses[0]:.6f}")
        print(f"  Final Loss:   {losses[-1]:.6f}")
        print(f"  Improvement:  {((losses[0] - losses[-1]) / losses[0] * 100):.2f}%")

        print("\n  Loss per Round:")
        print("  " + "-" * 50)
        for r in self.rounds:
            round_num = r.get('round', '?')
            loss = r.get('weighted_loss', 0)
            nodes = r.get('participating_nodes', [])
            samples = r.get('total_samples', 0)
            bar = "#" * int(loss * 50)
            print(f"  R{round_num:3d}: {loss:.6f} | Nodes: {nodes} | Samples: {samples}")
        print("  " + "-" * 50)

    def run(self):
        """Run offline analysis"""
        self.load_logs()
        self.print_summary()


def main():
    parser = argparse.ArgumentParser(description='Federated Learning Monitoring Dashboard')
    parser.add_argument('--mode', type=str, choices=['live', 'offline'], default='live',
                        help='Dashboard mode: live (Kafka) or offline (log file)')
    parser.add_argument('--kafka-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                        help='Kafka bootstrap servers (for live mode)')
    parser.add_argument('--log-file', type=str, default=None,
                        help='Log file path (for offline mode)')

    args = parser.parse_args()

    if args.mode == 'live':
        dashboard = ConsoleDashboard(args.kafka_servers)
    else:
        dashboard = LogFileDashboard(args.log_file)

    dashboard.run()


if __name__ == "__main__":
    main()
