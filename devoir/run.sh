#!/bin/bash

# Federated Learning with Kafka and Spark - Run Script

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Virtual environment path
VENV_PATH="/Volumes/external/fog-federated-learning/venv"

# Activate virtual environment if it exists
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

case "$1" in
    start-infra)
        print_status "Starting Kafka, Zookeeper, and Spark..."
        docker-compose up -d
        print_status "Waiting for services to initialize..."
        sleep 10
        print_status "Checking topic creation..."
        docker logs kafka-init 2>&1 | tail -5
        print_status "Infrastructure started! Spark UI: http://localhost:8080"
        ;;

    stop-infra)
        print_status "Stopping infrastructure..."
        docker-compose down
        print_status "Infrastructure stopped."
        ;;

    producer)
        NODE_ID=${2:-1}
        print_status "Starting Sensor Producer for Node $NODE_ID..."
        python3 producers/sensor_producer.py --node-id "$NODE_ID"
        ;;

    fog-node)
        NODE_ID=${2:-1}
        print_status "Starting Fog Node $NODE_ID..."
        python3 fog_nodes/fog_node.py --node-id "$NODE_ID"
        ;;

    aggregator)
        MODE=${2:-batch}
        print_status "Starting Cloud Aggregator in $MODE mode..."
        python3 cloud_aggregator/aggregator.py --mode "$MODE"
        ;;

    dashboard)
        MODE=${2:-live}
        print_status "Starting Dashboard in $MODE mode..."
        python3 monitor/dashboard.py --mode "$MODE"
        ;;

    demo)
        print_status "Starting demo (requires tmux)..."
        if ! command -v tmux &> /dev/null; then
            print_error "tmux is required for demo mode. Install it or run components manually."
            exit 1
        fi

        # Start infrastructure first
        print_status "Starting infrastructure..."
        docker-compose up -d
        sleep 15

        # Create tmux session with all components
        ACTIVATE_VENV="source $VENV_PATH/bin/activate"

        tmux new-session -d -s fl_demo -n 'aggregator'
        tmux send-keys -t fl_demo:aggregator "cd $PROJECT_DIR && $ACTIVATE_VENV && python3 cloud_aggregator/aggregator.py --mode batch" Enter

        tmux new-window -t fl_demo -n 'fog1'
        tmux send-keys -t fl_demo:fog1 "cd $PROJECT_DIR && $ACTIVATE_VENV && sleep 5 && python3 fog_nodes/fog_node.py --node-id 1" Enter

        tmux new-window -t fl_demo -n 'fog2'
        tmux send-keys -t fl_demo:fog2 "cd $PROJECT_DIR && $ACTIVATE_VENV && sleep 5 && python3 fog_nodes/fog_node.py --node-id 2" Enter

        tmux new-window -t fl_demo -n 'producer1'
        tmux send-keys -t fl_demo:producer1 "cd $PROJECT_DIR && $ACTIVATE_VENV && sleep 10 && python3 producers/sensor_producer.py --node-id 1" Enter

        tmux new-window -t fl_demo -n 'producer2'
        tmux send-keys -t fl_demo:producer2 "cd $PROJECT_DIR && $ACTIVATE_VENV && sleep 10 && python3 producers/sensor_producer.py --node-id 2" Enter

        tmux new-window -t fl_demo -n 'dashboard'
        tmux send-keys -t fl_demo:dashboard "cd $PROJECT_DIR && $ACTIVATE_VENV && sleep 15 && python3 monitor/dashboard.py --mode live" Enter

        print_status "Demo started in tmux session 'fl_demo'"
        print_status "Attach with: tmux attach -t fl_demo"
        print_status "Switch windows with: Ctrl+b, then 0-5"
        ;;

    stop-demo)
        print_status "Stopping demo..."
        tmux kill-session -t fl_demo 2>/dev/null || true
        docker-compose down
        print_status "Demo stopped."
        ;;

    install)
        print_status "Installing Python dependencies..."
        pip3 install -r requirements.txt
        print_status "Dependencies installed."
        ;;

    clean)
        print_status "Cleaning up..."
        rm -rf /tmp/checkpoint_*
        rm -rf logs/*.jsonl
        docker-compose down -v
        print_status "Cleanup complete."
        ;;

    *)
        echo "Federated Learning with Kafka and Spark"
        echo ""
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  start-infra      Start Kafka, Zookeeper, Spark (Docker)"
        echo "  stop-infra       Stop infrastructure"
        echo "  producer <n>     Start sensor producer for node n (1 or 2)"
        echo "  fog-node <n>     Start fog node n (1 or 2)"
        echo "  aggregator [m]   Start cloud aggregator (mode: batch/streaming)"
        echo "  dashboard [m]    Start monitoring dashboard (mode: live/offline)"
        echo "  demo             Start full demo with tmux"
        echo "  stop-demo        Stop demo and infrastructure"
        echo "  install          Install Python dependencies"
        echo "  clean            Clean checkpoints and logs"
        echo ""
        echo "Example workflow:"
        echo "  $0 install"
        echo "  $0 start-infra"
        echo "  $0 aggregator      # Terminal 1"
        echo "  $0 fog-node 1      # Terminal 2"
        echo "  $0 fog-node 2      # Terminal 3"
        echo "  $0 producer 1      # Terminal 4"
        echo "  $0 producer 2      # Terminal 5"
        echo "  $0 dashboard       # Terminal 6"
        ;;
esac
