# 🏗️ Architecture détaillée

## Vue d'ensemble

Le système implémente une architecture **Edge-Fog-Cloud** pour le Federated Learning avec trois couches distinctes :

```
┌──────────────────────────────────────────────────────────┐
│                      CLOUD LAYER                         │
│  • Agrégation FedAvg globale                             │
│  • Gestion des rounds                                    │
│  • Publication modèle global                             │
└──────────────────────────────────────────────────────────┘
                          ▲
                          │ Poids agrégés par région
                          │
┌──────────────────────────────────────────────────────────┐
│                       FOG LAYER                          │
│  • Pré-agrégation régionale (Spark)                      │
│  • Réduction du trafic vers Cloud                        │
│  • Fenêtres temporelles (30s)                            │
└──────────────────────────────────────────────────────────┘
                          ▲
                          │ Poids des modèles locaux
                          │
┌──────────────────────────────────────────────────────────┐
│                      EDGE LAYER                          │
│  • Capteurs distribués (4 villages)                      │
│  • Entraînement local (SGDClassifier)                    │
│  • Détection d'anomalies en temps réel                   │
└──────────────────────────────────────────────────────────┘
```

## Composants détaillés

### 1. Simulator (`simulator.py`)

**Rôle** : Génération de données synthétiques de capteurs électriques

**Fonctionnement** :
- Génère des lectures de tension (V) et courant (I) pour chaque village
- Injecte aléatoirement des anomalies (10% par défaut)
- Publie sur le topic Kafka `sensor_data`

**Types d'anomalies** :
- `overvoltage` : tension × 1.3
- `undervoltage` : tension × 0.7
- `overcurrent` : courant × 2.0
- `power_surge` : tension × 1.2 + courant × 1.5

**Format de message** :
```json
{
  "edge_id": "village_1",
  "timestamp": "2026-02-06T10:30:00.123Z",
  "voltage": 235.4,
  "current": 12.3,
  "power": 2895.42,
  "label": 0,
  "type": "normal"
}
```

### 2. Edge Nodes (`edge_node.py`)

**Rôle** : Entraînement local du modèle de détection

**Algorithme** :
- **Modèle** : `SGDClassifier` (sklearn) avec `warm_start=True`
- **Entraînement incrémental** : `partial_fit()` toutes les N lectures
- **Features** : [V_norm, I_norm, P_norm] (normalisation Z-score)

**Workflow** :
1. Consomme `sensor_data` pour son `edge_id`
2. Accumule dans un buffer (max 1000 échantillons)
3. Entraîne toutes les 50 lectures (configurable)
4. Publie **uniquement les poids** (pas les données)

**Format de publication** :
```json
{
  "edge_id": "village_1",
  "region": "north",
  "round": 5,
  "n_samples": 50,
  "weights": {
    "coef": [[0.12, -0.34, 0.56]],
    "intercept": [0.02],
    "classes": [0, 1]
  },
  "metrics": {
    "local_accuracy": 0.94,
    "total_samples": 250,
    "anomalies_detected": 12
  }
}
```

### 3. Fog Aggregator (`fog_aggregator_spark.py`)

**Rôle** : Pré-agrégation régionale avec Spark Structured Streaming

**Pourquoi le Fog ?**
- Réduit le trafic vers le Cloud
- Agrège plusieurs Edge nodes d'une même région
- Traitement en streaming temps réel

**Configuration Spark** :
- Fenêtre temporelle : 30 secondes
- Watermark : 10 secondes (gestion du retard)
- Agrégation par `region`

**Transformations** :
1. Lecture depuis Kafka (`edge_weights`)
2. Groupement par `region` et fenêtre temporelle
3. Agrégation : collect_list(weights), sum(n_samples), avg(accuracy)
4. Écriture vers `fog_agg`

**Format de sortie** :
```json
{
  "region": "north",
  "window_start": "2026-02-06T10:30:00Z",
  "window_end": "2026-02-06T10:30:30Z",
  "contributing_edges": ["village_1", "village_2"],
  "all_weights": [...],
  "total_n_samples": 100,
  "avg_accuracy": 0.92,
  "total_anomalies": 8
}
```

### 4. Cloud FedAvg (`cloud_fedavg.py`)

**Rôle** : Agrégation globale avec algorithme FedAvg

**Algorithme FedAvg** (McMahan et al., 2017) :

```
Pour chaque round r:
  1. Attendre updates de K régions/edges
  2. Pour chaque update i:
     - wi : poids du modèle local
     - ni : nombre d'échantillons
  3. Calculer modèle global:
     w_global = Σ(ni * wi) / Σ(ni)
  4. Publier w_global
```

**Implémentation** :
```python
def federated_averaging(updates):
    total_samples = sum(u['n_samples'] for u in updates)

    avg_weights = 0
    for update in updates:
        weight = update['n_samples'] / total_samples
        avg_weights += weight * update['weights']

    return avg_weights
```

**Gestion des rounds** :
- Buffer d'updates par round
- Agrégation quand :
  - Au moins 2 régions ont contribué OU
  - Timeout de 60 secondes dépassé

**Publications** :
- `global_model` : modèle global pour redistribution aux Edge
- `global_metrics` : métriques pour le dashboard

### 5. Dashboard (`dashboard_app.py`)

**Rôle** : Visualisation temps réel

**Composants** :
- **Métriques principales** : round actuel, anomalies totales, dernière MAJ
- **Graphique anomalies** : bar chart par village et région
- **Timeline rounds** : évolution échantillons et anomalies
- **Statistiques détaillées** : dernier round, config Edge

**Rafraîchissement** : toutes les 2 secondes (non-bloquant)

## Communication Kafka

### Topics et flux de données

```
simulator.py
    │
    ├─> sensor_data ──> edge_node.py (×4)
                            │
                            ├─> edge_weights ──> fog_aggregator_spark.py
                                                      │
                                                      ├─> fog_agg ──> cloud_fedavg.py
                                                                          │
                                                                          ├─> global_model ──> (edge_node.py)
                                                                          │
                                                                          └─> global_metrics ──> dashboard_app.py
```

### Partitionnement

- **sensor_data** : partitionné par `edge_id` (clé)
- **edge_weights** : partitionné par `edge_id`
- **fog_agg** : partitionné par `region`
- **global_model** : clé = `round_X`

### Consumer Groups

- `edge_node_{edge_id}` : un groupe par village
- `fog_aggregator` : groupe Spark Streaming
- `cloud_fedavg` : groupe Cloud
- `dashboard` : groupe Dashboard

## Privacy et Sécurité

### Privacy-Preserving Features

✅ **Pas de données brutes transmises**
- Les Edge ne publient QUE les poids du modèle
- Les capteurs bruts restent locaux

✅ **Agrégation progressive**
- Fog pré-agrège avant Cloud
- Limite l'exposition d'informations spécifiques

✅ **Modèle global partagé**
- Tous les Edge bénéficient du modèle global
- Pas de biais vers un Edge particulier

### Limitations (hors scope MVP)

❌ Chiffrement des poids (à ajouter avec homomorphic encryption)
❌ Differential Privacy (ajout de bruit)
❌ Secure Aggregation (agrégation cryptographique)

## Scalabilité

### Edge Layer
- **Scalabilité horizontale** : ajout facile de nouveaux villages
- **Indépendance** : chaque Edge tourne indépendamment
- **Résilience** : la panne d'un Edge n'affecte pas les autres

### Fog Layer
- **Spark Streaming** : scalabilité native (ajout de workers)
- **Fenêtres temporelles** : gestion de flux importants
- **Watermark** : tolérance au retard des messages

### Cloud Layer
- **Agrégation légère** : simple moyenne pondérée (rapide)
- **Stateless** : peut être répliqué facilement

## Monitoring et Observabilité

### Logs
- **Format structuré** : timestamps, niveaux, contexte
- **Logs par composant** : dans `logs/` avec lancement automatique

### Métriques clés
- **Edge** : samples traités, anomalies détectées, précision locale
- **Fog** : updates agrégées, régions participantes
- **Cloud** : rounds complétés, modèles publiés

### Dashboard temps réel
- Visualisation instantanée
- Détection de problèmes (manque d'updates, anomalies anormales)

## Extensions possibles

### Court terme
1. **Alerting** : topic `alerts` pour anomalies critiques
2. **Persistance** : stockage des rounds dans une DB (PostgreSQL)
3. **API REST** : exposition des métriques

### Moyen terme
1. **Modèles plus complexes** : CNN, LSTM avec PyTorch/TensorFlow
2. **Differential Privacy** : ajout de bruit pour privacy renforcée
3. **Compression** : compression des poids pour réduire trafic
4. **Multi-tenancy** : plusieurs réseaux électriques isolés

### Long terme
1. **Blockchain** : traçabilité des updates et modèles
2. **Federated Transfer Learning** : adaptation de modèles pré-entraînés
3. **AutoML fédéré** : optimisation hyper-paramètres distribuée
