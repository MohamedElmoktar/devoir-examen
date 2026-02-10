"""Configuration centrale pour le projet Federated Learning"""

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
KAFKA_TOPICS = {
    'sensor_data': 'sensor_data',
    'edge_weights': 'edge_weights',
    'fog_agg': 'fog_agg',
    'global_model': 'global_model',
    'global_metrics': 'global_metrics',
    'alerts': 'alerts'
}

# Edge Configuration
EDGE_IDS = ['village_1', 'village_2', 'village_3', 'village_4']
EDGE_REGIONS = {
    'village_1': 'north',
    'village_2': 'north',
    'village_3': 'south',
    'village_4': 'south'
}
EDGE_TRAINING_FREQUENCY = 50  # Nombre de messages avant entraînement
EDGE_BATCH_SIZE = 20

# Fog Configuration
FOG_WINDOW_DURATION = '30 seconds'
FOG_WATERMARK_DELAY = '10 seconds'

# Cloud Configuration
FEDAVG_AGGREGATION_THRESHOLD = 2  # Nombre minimum d'updates avant FedAvg
FEDAVG_ROUND_TIMEOUT = 60  # secondes

# Simulator Configuration
SIMULATOR_FREQUENCY = 0.5  # secondes entre messages
ANOMALY_PROBABILITY = 0.1  # 10% d'anomalies

# Electrical parameters (normal ranges)
VOLTAGE_MEAN = 230.0  # Volts
VOLTAGE_STD = 5.0
CURRENT_MEAN = 10.0  # Ampères
CURRENT_STD = 2.0

# Anomaly parameters
ANOMALY_VOLTAGE_FACTOR = 1.3  # Surtension
ANOMALY_CURRENT_FACTOR = 2.0  # Surintensité

# Model Configuration
MODEL_PARAMS = {
    'loss': 'log_loss',
    'penalty': 'l2',
    'alpha': 0.0001,
    'learning_rate': 'constant',
    'eta0': 0.01,
    'max_iter': 1000,
    'random_state': 42
}

# Alert thresholds
ALERT_THRESHOLD = 0.15  # 15% d'anomalies détectées
