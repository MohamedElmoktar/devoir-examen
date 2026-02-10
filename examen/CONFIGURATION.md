# ⚙️ Guide de Configuration

## Fichier config.py

Toute la configuration du système est centralisée dans `config.py`.

### Configuration Kafka

```python
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
```

**Production** : utilisez plusieurs brokers pour haute disponibilité
```python
KAFKA_BOOTSTRAP_SERVERS = ['kafka1:9092', 'kafka2:9092', 'kafka3:9092']
```

### Topics Kafka

```python
KAFKA_TOPICS = {
    'sensor_data': 'sensor_data',
    'edge_weights': 'edge_weights',
    'fog_agg': 'fog_agg',
    'global_model': 'global_model',
    'global_metrics': 'global_metrics',
    'alerts': 'alerts'
}
```

**Environnements multiples** : utilisez des préfixes
```python
ENV = 'dev'  # ou 'staging', 'prod'
KAFKA_TOPICS = {
    'sensor_data': f'{ENV}_sensor_data',
    # ...
}
```

### Configuration Edge

#### Nombre de villages

```python
EDGE_IDS = ['village_1', 'village_2', 'village_3', 'village_4']
```

**Scaler à 10 villages** :
```python
EDGE_IDS = [f'village_{i}' for i in range(1, 11)]
```

#### Mapping régions

```python
EDGE_REGIONS = {
    'village_1': 'north',
    'village_2': 'north',
    'village_3': 'south',
    'village_4': 'south'
}
```

**Génération automatique** :
```python
EDGE_REGIONS = {
    edge_id: 'north' if int(edge_id.split('_')[1]) <= 5 else 'south'
    for edge_id in EDGE_IDS
}
```

#### Fréquence d'entraînement

```python
EDGE_TRAINING_FREQUENCY = 50  # Entraîne toutes les 50 lectures
```

- **Plus faible** (ex: 20) : entraînement plus fréquent, convergence rapide
- **Plus élevé** (ex: 100) : moins de trafic Kafka, convergence lente

#### Taille de batch

```python
EDGE_BATCH_SIZE = 20  # Minimum 20 échantillons pour entraîner
```

### Configuration Fog (Spark)

```python
FOG_WINDOW_DURATION = '30 seconds'  # Fenêtre d'agrégation
FOG_WATERMARK_DELAY = '10 seconds'  # Tolérance au retard
```

**Ajustements** :
- **Temps réel strict** : fenêtre courte (10s), watermark court (2s)
- **Tolérance au retard** : fenêtre longue (60s), watermark long (30s)

### Configuration Cloud FedAvg

```python
FEDAVG_AGGREGATION_THRESHOLD = 2  # Min 2 régions avant FedAvg
FEDAVG_ROUND_TIMEOUT = 60  # secondes
```

**Scénarios** :
- **Convergence rapide** : threshold bas (2), timeout court (30s)
- **Stabilité** : threshold haut (4), timeout long (120s)

### Configuration Simulator

```python
SIMULATOR_FREQUENCY = 0.5  # 0.5s entre messages (2 msg/s par village)
ANOMALY_PROBABILITY = 0.1  # 10% d'anomalies
```

**Stress test** :
```python
SIMULATOR_FREQUENCY = 0.1  # 10 msg/s par village
ANOMALY_PROBABILITY = 0.3  # 30% d'anomalies
```

**Test normal** :
```python
SIMULATOR_FREQUENCY = 2.0  # 1 msg tous les 2s
ANOMALY_PROBABILITY = 0.05  # 5% d'anomalies
```

### Paramètres électriques

```python
# Valeurs normales
VOLTAGE_MEAN = 230.0  # Volts (EU standard)
VOLTAGE_STD = 5.0
CURRENT_MEAN = 10.0  # Ampères
CURRENT_STD = 2.0

# Facteurs d'anomalie
ANOMALY_VOLTAGE_FACTOR = 1.3  # +30% surtension
ANOMALY_CURRENT_FACTOR = 2.0  # +100% surintensité
```

**Adapter au contexte** :
- **US voltage** : 120V
- **Industrial** : courant moyen plus élevé

### Paramètres du modèle

```python
MODEL_PARAMS = {
    'loss': 'log_loss',        # Classification binaire
    'penalty': 'l2',           # Régularisation L2
    'alpha': 0.0001,           # Force de régularisation
    'learning_rate': 'constant',
    'eta0': 0.01,              # Taux d'apprentissage
    'max_iter': 1000,
    'random_state': 42
}
```

**Tuning** :
- **Overfitting** : augmenter `alpha` (ex: 0.001)
- **Underfitting** : augmenter `eta0` (ex: 0.1) ou diminuer `alpha`
- **Convergence lente** : augmenter `eta0`

### Seuils d'alerte

```python
ALERT_THRESHOLD = 0.15  # 15% d'anomalies = alerte
```

## Variables d'environnement

Créez un fichier `.env` pour override :

```bash
# .env
KAFKA_BOOTSTRAP_SERVERS=kafka.prod.example.com:9092
EDGE_TRAINING_FREQUENCY=100
ANOMALY_PROBABILITY=0.05
```

Chargez avec `python-dotenv` :
```python
# config.py
from dotenv import load_dotenv
import os

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = [
    os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
]
```

## Configurations recommandées

### Développement

```python
EDGE_IDS = ['village_1', 'village_2']  # 2 villages seulement
SIMULATOR_FREQUENCY = 1.0  # Lent
EDGE_TRAINING_FREQUENCY = 20  # Rapide pour voir résultats
FOG_WINDOW_DURATION = '10 seconds'  # Court pour debug
```

### Test / Staging

```python
EDGE_IDS = ['village_1', 'village_2', 'village_3', 'village_4']
SIMULATOR_FREQUENCY = 0.5
EDGE_TRAINING_FREQUENCY = 50
FOG_WINDOW_DURATION = '30 seconds'
```

### Production (hypothétique)

```python
EDGE_IDS = [f'village_{i}' for i in range(1, 21)]  # 20 villages
SIMULATOR_FREQUENCY = 2.0  # Données réelles, pas de simulation
EDGE_TRAINING_FREQUENCY = 100
EDGE_BATCH_SIZE = 50
FOG_WINDOW_DURATION = '60 seconds'
FEDAVG_AGGREGATION_THRESHOLD = 4
```

## Monitoring des performances

### Métriques à surveiller

1. **Latence Kafka** : temps entre production et consommation
2. **Throughput** : messages/seconde par topic
3. **Précision modèle** : accuracy locale vs globale
4. **Convergence** : évolution de la loss par round

### Ajuster selon les observations

**Si trop de retard au Fog :**
- Augmenter `FOG_WATERMARK_DELAY`
- Diminuer `FOG_WINDOW_DURATION`

**Si le Cloud ne reçoit jamais assez d'updates :**
- Diminuer `FEDAVG_AGGREGATION_THRESHOLD`
- Augmenter `FEDAVG_ROUND_TIMEOUT`

**Si les Edge ne convergent pas :**
- Augmenter `EDGE_TRAINING_FREQUENCY` (plus de données)
- Augmenter `eta0` (learning rate)
- Diminuer `alpha` (moins de régularisation)

## Configuration Spark

Éditez `fog_aggregator_spark.py` pour ajuster :

```python
spark = SparkSession.builder \
    .appName("FogAggregator") \
    .config("spark.sql.shuffle.partitions", "8")  # Ajuster selon charge
    .config("spark.executor.memory", "2g")  # Mémoire par executor
    .config("spark.driver.memory", "1g")  # Mémoire driver
    .getOrCreate()
```

## Logging

Ajustez le niveau de log dans chaque script :

```python
logging.basicConfig(level=logging.INFO)  # INFO, DEBUG, WARNING, ERROR
```

**Debug intensif** :
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
```
