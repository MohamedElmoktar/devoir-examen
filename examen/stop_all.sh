#!/bin/bash
# Script d'arrêt de tous les composants
# Usage: ./stop_all.sh

echo "🛑 Arrêt de tous les composants..."

# Tuer tous les processus Python liés au projet
pkill -f "simulator.py"
pkill -f "edge_node.py"
pkill -f "cloud_fedavg.py"
pkill -f "dashboard_app.py"

# Tuer Spark
pkill -f "fog_aggregator_spark.py"
pkill -f "SparkSubmit"

# Arrêter Kafka
docker compose down

echo "✅ Tous les composants ont été arrêtés"
