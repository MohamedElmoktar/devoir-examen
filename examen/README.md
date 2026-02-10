# Federated Learning: Architecture Edge-Fog-Cloud

**MVP Complet** pour la détection d'anomalies dans un réseau électrique rural utilisant le Federated Learning (FedAvg).

## 🎯 Objectif

Simuler un système distribué où :
- **Edge nodes** (villages) détectent des anomalies électriques localement
- **Fog layer** agrège les modèles par région
- **Cloud layer** applique FedAvg pour créer un modèle global
- **Aucune donnée brute** n'est transmise (privacy-preserving)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLOUD LAYER                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  cloud_fedavg.py                                     │   │
│  │  • Agrégation FedAvg globale                         │   │
│  │  • Moyenne pondérée par n_samples                    │   │
│  │  • Publie modèle global                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ (weights only)
                              │
┌─────────────────────────────────────────────────────────────┐
│                          FOG LAYER                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  fog_aggregator_spark.py (Spark Streaming)           │   │
│  │  • Agrégation régionale (fenêtres 30s)               │   │
│  │  • Pré-agrégation avant Cloud                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ (weights only)
                              │
┌─────────────────────────────────────────────────────────────┐
│                         EDGE LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ edge_node.py │  │ edge_node.py │  │ edge_node.py │ ...  │
│  │ (village_1)  │  │ (village_2)  │  │ (village_3)  │      │
│  │              │  │              │  │              │      │
│  │ • Capteurs   │  │ • Capteurs   │  │ • Capteurs   │      │
│  │ • Training   │  │ • Training   │  │ • Training   │      │
│  │   local      │  │   local      │  │   local      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ (sensor data)
                              │
┌─────────────────────────────────────────────────────────────┐
│                       simulator.py                          │
│  Génère données capteurs (V, I) + anomalies                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Flux de données

1. **Simulator** → Topic `sensor_data` : données capteurs {edge_id, V, I, label}
2. **Edge nodes** → Topic `edge_weights` : poids modèles {weights, n_samples, metrics}
3. **Fog** → Topic `fog_agg` : agrégation régionale
4. **Cloud** → Topic `global_model` : modèle global FedAvg
5. **Cloud** → Topic `global_metrics` : métriques pour dashboard

## 📋 Prérequis

- **Python 3.10+**
- **Docker & Docker Compose**
- **Java 8+** (pour Spark)

## ⚙️ Installation

### 1. Cloner/Créer le projet

```bash
cd federated-edge-fog-cloud
```

### 2. Créer l'environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Démarrer Kafka

```bash
docker compose up -d
```

Vérifier que Kafka est prêt :
```bash
docker compose ps
```

Interface Kafka UI disponible : http://localhost:8080

## 🚀 Lancement de la solution

### Ordre de démarrage recommandé

Ouvrez **6 terminaux** (tous avec venv activé) :

#### Terminal 1: Simulator
```bash
python simulator.py
```
✓ Génère des données de capteurs pour 4 villages
✓ Injecte 10% d'anomalies aléatoires

#### Terminal 2-5: Edge Nodes (4 villages)
```bash
# Terminal 2
python edge_node.py --edge_id village_1

# Terminal 3
python edge_node.py --edge_id village_2

# Terminal 4
python edge_node.py --edge_id village_3

# Terminal 5
python edge_node.py --edge_id village_4
```
✓ Chaque node entraîne localement un SGDClassifier
✓ Publie uniquement les poids (pas les données)

#### Terminal 6: Fog Aggregator (Spark)
```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  fog_aggregator_spark.py
```
✓ Agrège par région toutes les 30 secondes
✓ Streaming temps réel avec Spark

#### Terminal 7: Cloud FedAvg
```bash
python cloud_fedavg.py
```
✓ Applique FedAvg (moyenne pondérée)
✓ Publie modèle global à chaque round

#### Terminal 8: Dashboard Streamlit
```bash
streamlit run dashboard_app.py
```
✓ Interface web : http://localhost:8501
✓ Visualisation temps réel

## 📊 Dashboard

Le dashboard Streamlit affiche :

- **Round actuel** et timestamp
- **Anomalies détectées** par village
- **Graphiques temps réel** :
  - Distribution anomalies par village et région
  - Évolution des métriques par round
  - Échantillons traités
- **Statistiques détaillées** du dernier round

## 🧠 Logique Federated Learning

### Principe FedAvg

Le **Federated Averaging** (McMahan et al., 2017) permet d'entraîner un modèle global sans centraliser les données :

```python
# Chaque Edge node i entraîne localement sur ni échantillons
# et obtient des poids wi

# Le Cloud agrège avec moyenne pondérée :
w_global = Σ(ni * wi) / Σ(ni)
```

### Rôles des couches

| Couche | Responsabilité | Données reçues | Données émises |
|--------|---------------|----------------|----------------|
| **Edge** | Entraînement local | Capteurs bruts | Poids modèle |
| **Fog** | Pré-agrégation régionale | Poids Edge | Poids agrégés |
| **Cloud** | FedAvg global | Poids Fog | Modèle global |

### Privacy-preserving

✅ **Pas de données brutes** transmises aux couches supérieures
✅ **Seuls les poids** du modèle sont partagés
✅ **Agrégation** avant transmission au Cloud
✅ **Préservation** de la confidentialité des données locales

## 📁 Structure du projet

```
federated-edge-fog-cloud/
├── docker-compose.yml          # Kafka + Zookeeper
├── requirements.txt            # Dépendances Python
├── config.py                   # Configuration centralisée
├── simulator.py                # Générateur de données capteurs
├── edge_node.py                # Noeud Edge (entraînement local)
├── fog_aggregator_spark.py     # Agrégateur Fog (Spark)
├── cloud_fedavg.py             # Serveur Cloud (FedAvg)
├── dashboard_app.py            # Dashboard Streamlit
├── utils/
│   ├── __init__.py
│   ├── kafka_utils.py          # Wrappers Kafka
│   └── model_utils.py          # Utilitaires FedAvg
└── README.md
```

## 🔧 Configuration

Modifiez `config.py` pour ajuster :

- **Villages** : nombre et IDs des edge nodes
- **Régions** : mapping village → région
- **Fréquence entraînement** : nombre de messages avant training
- **Probabilité anomalies** : taux d'injection d'anomalies
- **Paramètres FedAvg** : seuil agrégation, timeout
- **Paramètres électriques** : moyennes/écarts-types V, I

## 📈 Topics Kafka

| Topic | Description | Producteur | Consommateur |
|-------|-------------|------------|--------------|
| `sensor_data` | Données capteurs brutes | Simulator | Edge nodes |
| `edge_weights` | Poids modèles Edge | Edge nodes | Fog |
| `fog_agg` | Agrégation régionale | Fog | Cloud |
| `global_model` | Modèle global FedAvg | Cloud | Edge nodes |
| `global_metrics` | Métriques globales | Cloud | Dashboard |
| `alerts` | Alertes anomalies | (optionnel) | Dashboard |

## 🧪 Tester la solution

### 1. Vérifier le flux de données

```bash
# Lister les topics créés
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Consommer un topic pour debug
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic sensor_data \
  --from-beginning
```

### 2. Injecter des anomalies manuelles

Modifiez temporairement dans `config.py` :
```python
ANOMALY_PROBABILITY = 0.5  # 50% d'anomalies
```

### 3. Scaler les Edge nodes

Lancez plus de villages en modifiant `config.py` :
```python
EDGE_IDS = ['village_1', 'village_2', ..., 'village_10']
```

## 🛠️ Troubleshooting

### Kafka ne démarre pas
```bash
docker compose down -v
docker compose up -d
```

### Spark ne trouve pas le package Kafka
Assurez-vous que le package est spécifié :
```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 fog_aggregator_spark.py
```

### Edge node ne reçoit pas de données
Vérifiez que :
1. Le simulator tourne
2. Le `--edge_id` correspond à ceux dans `config.EDGE_IDS`
3. Kafka est bien démarré

### Dashboard ne rafraîchit pas
Le dashboard consomme Kafka en mode `latest`. Si vous le démarrez après les autres composants, il ne verra que les nouveaux messages. Pour voir l'historique, modifiez dans `dashboard_app.py` :
```python
auto_offset_reset='earliest'  # au lieu de 'latest'
```

## 📚 Références

- **FedAvg** : McMahan et al. (2017) - "Communication-Efficient Learning of Deep Networks from Decentralized Data"
- **Edge Computing** : Architecture distribuée pour IoT
- **Kafka** : Messaging distribué temps réel
- **Spark Streaming** : Traitement de flux de données

## 🏆 Fonctionnalités implémentées

✅ Simulation de capteurs multi-villages
✅ Entraînement local Edge (SGDClassifier)
✅ Agrégation Fog (Spark Structured Streaming)
✅ FedAvg Cloud (moyenne pondérée)
✅ Dashboard temps réel (Streamlit)
✅ Gestion d'erreurs et retry Kafka
✅ Logs clairs et structurés
✅ Privacy-preserving (pas de données brutes transmises)
✅ Configuration centralisée
✅ Docker Compose pour Kafka

## 🚦 Arrêt de la solution

```bash
# Ctrl+C dans chaque terminal Python/Spark

# Arrêter Kafka
docker compose down
```

## 📝 Licence

Projet éducatif - MVP Federated Learning

---

**Auteur** : Projet Federated Learning Edge-Fog-Cloud
**Date** : 2026
**Version** : 1.0.0
