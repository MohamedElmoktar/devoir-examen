"""
Configuration settings for Federated Learning with Kafka and Spark
"""

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:29092"
KAFKA_BOOTSTRAP_SERVERS_DOCKER = "kafka:9092"

# Kafka Topics
TOPIC_SENSOR_NODE_1 = "sensor-data-node-1"
TOPIC_SENSOR_NODE_2 = "sensor-data-node-2"
TOPIC_MODEL_WEIGHTS = "model-weights"
TOPIC_GLOBAL_MODEL = "global-model"

# Sensor Simulation Settings
SENSOR_INTERVAL_SECONDS = 0.5  # Time between sensor readings
ANOMALY_PROBABILITY = 0.1  # 10% chance of anomaly

# Model Settings
NUM_FEATURES = 5  # Number of features (vibration_x, vibration_y, vibration_z, temperature, pressure)
LEARNING_RATE = 0.01
BATCH_SIZE = 32
LOCAL_EPOCHS = 1

# Federated Learning Settings
NUM_FOG_NODES = 2
AGGREGATION_INTERVAL_SECONDS = 30  # Aggregate every N seconds
MIN_NODES_FOR_AGGREGATION = 1  # Minimum fog nodes required for aggregation
WEIGHT_PUBLISH_INTERVAL_SECONDS = 10  # Fog nodes publish weights every N seconds

# Spark Settings
SPARK_APP_NAME_FOG = "FogNode"
SPARK_APP_NAME_CLOUD = "CloudAggregator"
SPARK_MASTER = "local[*]"

# Logging
LOG_DIR = "logs"
LOG_LEVEL = "INFO"
