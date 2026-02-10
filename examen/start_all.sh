#!/bin/bash
# Script de lancement automatique de tous les composants
# Usage: ./start_all.sh

set -e

echo "🚀 Lancement du projet Federated Learning Edge-Fog-Cloud"
echo ""

# Vérifier que Docker tourne
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker n'est pas démarré. Veuillez lancer Docker Desktop."
    exit 1
fi

# Vérifier l'environnement virtuel
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Environnement virtuel non activé. Activation..."
    source venv/bin/activate || {
        echo "❌ Impossible d'activer venv. Créez-le avec: python3 -m venv venv"
        exit 1
    }
fi

# Démarrer Kafka
echo "1️⃣  Démarrage de Kafka..."
docker compose up -d
echo "   ✓ Kafka démarré"

# Créer les topics Kafka
echo "2️⃣  Création des topics Kafka (attente de Kafka)..."
python create_kafka_topics.py
if [ $? -ne 0 ]; then
    echo "   ❌ Erreur création topics"
    exit 1
fi
echo "   ✓ Topics Kafka créés"

# Lancer le simulateur en arrière-plan
echo "3️⃣  Lancement du simulateur..."
python simulator.py > logs/simulator.log 2>&1 &
SIMULATOR_PID=$!
echo "   ✓ Simulateur démarré (PID: $SIMULATOR_PID)"

sleep 2

# Lancer les Edge nodes
echo "4️⃣  Lancement des Edge nodes..."
for village in village_1 village_2 village_3 village_4; do
    python edge_node.py --edge_id $village > logs/edge_$village.log 2>&1 &
    echo "   ✓ Edge node $village démarré (PID: $!)"
    sleep 1
done

sleep 2

# Lancer le Fog aggregator (Spark)
echo "5️⃣  Lancement du Fog aggregator (Spark)..."
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  fog_aggregator_spark.py > logs/fog.log 2>&1 &
FOG_PID=$!
echo "   ✓ Fog aggregator démarré (PID: $FOG_PID)"

sleep 2

# Lancer Cloud FedAvg
echo "6️⃣  Lancement du Cloud FedAvg..."
python cloud_fedavg.py > logs/cloud.log 2>&1 &
CLOUD_PID=$!
echo "   ✓ Cloud FedAvg démarré (PID: $CLOUD_PID)"

sleep 2

# Lancer le dashboard
echo "7️⃣  Lancement du Dashboard Streamlit..."
streamlit run dashboard_app.py > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo "   ✓ Dashboard démarré (PID: $DASHBOARD_PID)"

echo ""
echo "✅ Tous les composants sont démarrés !"
echo ""
echo "📊 Dashboard disponible sur : http://localhost:8501"
echo "🔧 Kafka UI disponible sur : http://localhost:8080"
echo ""
echo "📋 PIDs des processus :"
echo "   Simulator: $SIMULATOR_PID"
echo "   Fog: $FOG_PID"
echo "   Cloud: $CLOUD_PID"
echo "   Dashboard: $DASHBOARD_PID"
echo ""
echo "Pour arrêter tous les composants : ./stop_all.sh"
echo "Pour voir les logs : tail -f logs/*.log"
