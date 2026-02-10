"""
Integration test for Federated Learning system
Runs all components and verifies end-to-end flow
"""

import subprocess
import time
import signal
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import LOG_DIR

def run_integration_test(duration_seconds=60):
    """Run all components for specified duration and verify results"""

    processes = []

    print("=" * 60)
    print("FEDERATED LEARNING INTEGRATION TEST")
    print("=" * 60)

    try:
        # Clean up old logs
        log_file = os.path.join(LOG_DIR, "aggregation_log.jsonl")
        if os.path.exists(log_file):
            os.remove(log_file)
        os.makedirs(LOG_DIR, exist_ok=True)

        # Start Cloud Aggregator
        print("\n[1/5] Starting Cloud Aggregator...")
        aggregator_proc = subprocess.Popen(
            [sys.executable, "cloud_aggregator/aggregator.py", "--mode", "batch", "--interval", "15"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Aggregator", aggregator_proc))
        time.sleep(3)

        # Start Fog Node 1
        print("[2/5] Starting Fog Node 1...")
        fog1_proc = subprocess.Popen(
            [sys.executable, "fog_nodes/fog_node.py", "--node-id", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Fog Node 1", fog1_proc))
        time.sleep(2)

        # Start Fog Node 2
        print("[3/5] Starting Fog Node 2...")
        fog2_proc = subprocess.Popen(
            [sys.executable, "fog_nodes/fog_node.py", "--node-id", "2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Fog Node 2", fog2_proc))
        time.sleep(2)

        # Start Producer 1
        print("[4/5] Starting Sensor Producer 1...")
        prod1_proc = subprocess.Popen(
            [sys.executable, "producers/sensor_producer.py", "--node-id", "1", "--interval", "0.3"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Producer 1", prod1_proc))

        # Start Producer 2
        print("[5/5] Starting Sensor Producer 2...")
        prod2_proc = subprocess.Popen(
            [sys.executable, "producers/sensor_producer.py", "--node-id", "2", "--interval", "0.3"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Producer 2", prod2_proc))

        print("\n" + "=" * 60)
        print(f"All components started. Running for {duration_seconds} seconds...")
        print("=" * 60 + "\n")

        # Monitor output
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            # Print aggregator output
            if aggregator_proc.poll() is None:
                try:
                    line = aggregator_proc.stdout.readline()
                    if line:
                        print(f"[AGG] {line.strip()}")
                except:
                    pass

            time.sleep(0.1)

            # Check if any process died
            for name, proc in processes:
                if proc.poll() is not None and proc.returncode != 0:
                    print(f"WARNING: {name} exited with code {proc.returncode}")

        print("\n" + "=" * 60)
        print("Test duration completed. Shutting down...")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\nInterrupted by user...")

    finally:
        # Cleanup: terminate all processes
        print("\nTerminating processes...")
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                print(f"  - {name} terminated")

        # Analyze results
        print("\n" + "=" * 60)
        print("RESULTS ANALYSIS")
        print("=" * 60)

        log_file = os.path.join(LOG_DIR, "aggregation_log.jsonl")
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                rounds = [json.loads(line) for line in f if line.strip()]

            if rounds:
                print(f"\nTotal aggregation rounds: {len(rounds)}")
                print(f"Initial loss: {rounds[0].get('weighted_loss', 'N/A'):.6f}")
                print(f"Final loss: {rounds[-1].get('weighted_loss', 'N/A'):.6f}")

                initial = rounds[0].get('weighted_loss', 1)
                final = rounds[-1].get('weighted_loss', 1)
                if initial > 0:
                    improvement = (initial - final) / initial * 100
                    print(f"Improvement: {improvement:.2f}%")

                print("\nLoss per round:")
                for r in rounds:
                    print(f"  Round {r.get('round', '?')}: loss={r.get('weighted_loss', 0):.6f}, "
                          f"samples={r.get('total_samples', 0)}, nodes={r.get('participating_nodes', [])}")

                print("\n[SUCCESS] Integration test completed successfully!")
                return True
            else:
                print("\n[WARNING] No aggregation rounds recorded")
                return False
        else:
            print(f"\n[WARNING] Log file not found: {log_file}")
            return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Integration test for FL system')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    args = parser.parse_args()

    success = run_integration_test(args.duration)
    sys.exit(0 if success else 1)
