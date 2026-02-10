"""
Simple Integration Test for Federated Learning system
Uses simplified (non-Spark) components for faster testing
"""

import subprocess
import time
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import LOG_DIR

def run_test(duration_seconds=45):
    """Run all components for specified duration"""
    processes = []

    print("=" * 60)
    print("FEDERATED LEARNING - SIMPLE INTEGRATION TEST")
    print("=" * 60)

    try:
        # Clean up old logs
        log_file = os.path.join(LOG_DIR, "aggregation_log.jsonl")
        if os.path.exists(log_file):
            os.remove(log_file)
        os.makedirs(LOG_DIR, exist_ok=True)

        # Start Cloud Aggregator (simplified version)
        print("\n[1/5] Starting Cloud Aggregator...")
        agg_proc = subprocess.Popen(
            [sys.executable, "cloud_aggregator/aggregator_simple.py", "--interval", "10"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Aggregator", agg_proc))
        time.sleep(2)

        # Start Fog Node 1 (simplified version)
        print("[2/5] Starting Fog Node 1...")
        fog1_proc = subprocess.Popen(
            [sys.executable, "fog_nodes/fog_node_simple.py", "--node-id", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Fog Node 1", fog1_proc))
        time.sleep(1)

        # Start Fog Node 2 (simplified version)
        print("[3/5] Starting Fog Node 2...")
        fog2_proc = subprocess.Popen(
            [sys.executable, "fog_nodes/fog_node_simple.py", "--node-id", "2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Fog Node 2", fog2_proc))
        time.sleep(1)

        # Start Producer 1
        print("[4/5] Starting Sensor Producer 1...")
        prod1_proc = subprocess.Popen(
            [sys.executable, "producers/sensor_producer.py", "--node-id", "1", "--interval", "0.2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Producer 1", prod1_proc))

        # Start Producer 2
        print("[5/5] Starting Sensor Producer 2...")
        prod2_proc = subprocess.Popen(
            [sys.executable, "producers/sensor_producer.py", "--node-id", "2", "--interval", "0.2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Producer 2", prod2_proc))

        print("\n" + "=" * 60)
        print(f"All components started. Running for {duration_seconds} seconds...")
        print("=" * 60 + "\n")

        # Monitor and print output
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            for name, proc in processes:
                if proc.poll() is None:
                    try:
                        import select
                        if hasattr(select, 'select'):
                            readable, _, _ = select.select([proc.stdout], [], [], 0.1)
                            if readable:
                                line = proc.stdout.readline()
                                if line:
                                    prefix = name[:3].upper()
                                    print(f"[{prefix}] {line.strip()}")
                    except:
                        pass

            # Check for dead processes
            for name, proc in processes:
                if proc.poll() is not None and proc.returncode != 0:
                    # Read remaining output
                    remaining = proc.stdout.read()
                    if remaining:
                        print(f"[{name}] {remaining}")
                    print(f"[WARNING] {name} exited with code {proc.returncode}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nInterrupted...")

    finally:
        print("\n" + "=" * 60)
        print("Shutting down processes...")
        print("=" * 60)

        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            print(f"  - {name} stopped")

        # Print results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        log_file = os.path.join(LOG_DIR, "aggregation_log.jsonl")
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                rounds = [json.loads(line) for line in f if line.strip()]

            if rounds:
                print(f"\nAggregation rounds completed: {len(rounds)}")
                print(f"Initial loss: {rounds[0].get('weighted_loss', 0):.6f}")
                print(f"Final loss: {rounds[-1].get('weighted_loss', 0):.6f}")

                initial = rounds[0].get('weighted_loss', 1)
                final = rounds[-1].get('weighted_loss', 1)
                if initial > 0:
                    change = (initial - final) / initial * 100
                    direction = "improved" if change > 0 else "increased"
                    print(f"Loss {direction} by: {abs(change):.2f}%")

                print("\nPer-round details:")
                for r in rounds:
                    print(f"  Round {r.get('round', '?')}: "
                          f"loss={r.get('weighted_loss', 0):.6f}, "
                          f"samples={r.get('total_samples', 0)}, "
                          f"nodes={r.get('participating_nodes', [])}")

                print("\n" + "=" * 60)
                print("SUCCESS: Federated Learning test completed!")
                print("=" * 60)
                return True
            else:
                print("\n[WARNING] No aggregation rounds completed")
        else:
            print(f"\n[WARNING] No log file found at {log_file}")

        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=45)
    args = parser.parse_args()

    success = run_test(args.duration)
    sys.exit(0 if success else 1)
