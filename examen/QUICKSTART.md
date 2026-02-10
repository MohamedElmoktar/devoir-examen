# 🚀 Quick Start Guide

Guide de démarrage rapide en 5 minutes.

## Installation rapide

```bash
# 1. Installer et configurer
./setup.sh

# 2. Activer l'environnement
source venv/bin/activate

# 3. Démarrer Kafka
docker compose up -d

# 4. Attendre que Kafka soit prêt (30 secondes)
sleep 30

# 5. Tester la connexion
python test_kafka.py
```

## Lancement manuel (recommandé pour débuter)

Ouvrez **6 terminaux** dans le dossier du projet :

### Terminal 1 : Simulator
```bash
source venv/bin/activate
python simulator.py
```

### Terminal 2-5 : Edge Nodes
```bash
# Terminal 2
source venv/bin/activate
python edge_node.py --edge_id village_1

# Terminal 3
python edge_node.py --edge_id village_2

# Terminal 4
python edge_node.py --edge_id village_3

# Terminal 5
python edge_node.py --edge_id village_4
```

### Terminal 6 : Fog Aggregator
```bash
source venv/bin/activate
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 fog_aggregator_spark.py
```

### Terminal 7 : Cloud FedAvg
```bash
source venv/bin/activate
python cloud_fedavg.py
```

### Terminal 8 : Dashboard
```bash
source venv/bin/activate
streamlit run dashboard_app.py
```

## Lancement automatique (alternative)

```bash
source venv/bin/activate
./start_all.sh
```

**Note** : Le lancement automatique démarre tout en arrière-plan. Les logs sont dans `logs/*.log`.

## Visualisation

- **Dashboard** : http://localhost:8501
- **Kafka UI** : http://localhost:8080

## Arrêt

```bash
# Ctrl+C dans chaque terminal (mode manuel)

# Ou
./stop_all.sh  # Mode automatique

# Arrêter Kafka
docker compose down
```

## Vérifier que tout fonctionne

1. **Simulator** : doit afficher des messages `✓ [village_X]` et `🔴 ANOMALY`
2. **Edge nodes** : doivent afficher `📊 Round X: Précision=...`
3. **Fog** : affiche un tableau avec les agrégations
4. **Cloud** : affiche `✅ Round X terminé`
5. **Dashboard** : graphiques qui se mettent à jour toutes les 2 secondes

## Problèmes courants

### "Connection refused" Kafka
```bash
docker compose down -v
docker compose up -d
sleep 30
```

### Spark ne trouve pas le package
Vérifiez que vous utilisez bien :
```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 fog_aggregator_spark.py
```

### Edge node ne reçoit pas de données
Assurez-vous que le simulator tourne et que `--edge_id` est correct.

## Prochaines étapes

Consultez `README.md` pour :
- Architecture détaillée
- Configuration avancée
- Explication de FedAvg
- Troubleshooting complet
