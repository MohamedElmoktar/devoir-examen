# Federated Learning with Kafka and Spark

A distributed machine learning system that implements Federated Learning (FL) for anomaly detection using Apache Kafka for message transport and Apache Spark for analytical processing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLOUD LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Cloud Aggregator (FedAvg)                     │    │
│  │  - Collects model weights from Fog nodes                        │    │
│  │  - Applies Federated Averaging: w_{t+1} = Σ(n_k/n) * w_k        │    │
│  │  - Broadcasts global model to all nodes                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ▲                    │                      │
│                              │ model-weights      │ global-model         │
│                              │                    ▼                      │
└─────────────────────────────────────────────────────────────────────────┘
                               │                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                           KAFKA BROKER                                   │
│  Topics: sensor-data-node-1, sensor-data-node-2, model-weights,         │
│          global-model                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                               │                    │
        ┌──────────────────────┴────────────────────┴──────────────────────┐
        │                                                                   │
        ▼                                                                   ▼
┌───────────────────────────┐                       ┌───────────────────────────┐
│      FOG NODE 1           │                       │      FOG NODE 2           │
│  (Spark Streaming)        │                       │  (Spark Streaming)        │
│  ┌─────────────────────┐  │                       │  ┌─────────────────────┐  │
│  │ - Read sensor data  │  │                       │  │ - Read sensor data  │  │
│  │ - Local SGD training│  │                       │  │ - Local SGD training│  │
│  │ - Publish weights   │  │                       │  │ - Publish weights   │  │
│  └─────────────────────┘  │                       │  └─────────────────────┘  │
└───────────────────────────┘                       └───────────────────────────┘
        ▲                                                   ▲
        │ sensor-data-node-1                               │ sensor-data-node-2
        │                                                   │
┌───────────────────────────┐                       ┌───────────────────────────┐
│   DEVICE LAYER            │                       │   DEVICE LAYER            │
│   Sensor Simulator 1      │                       │   Sensor Simulator 2      │
│   (vibration, temp, etc.) │                       │   (vibration, temp, etc.) │
└───────────────────────────┘                       └───────────────────────────┘
```

## Project Structure

```
federated-learning-kafka-spark/
├── docker-compose.yml          # Kafka, Zookeeper, Spark cluster
├── requirements.txt            # Python dependencies
├── config/
│   └── settings.py             # Configuration parameters
├── producers/
│   └── sensor_producer.py      # IoT sensor simulators
├── fog_nodes/
│   └── fog_node.py             # Spark Streaming + local SGD
├── cloud_aggregator/
│   └── aggregator.py           # FedAvg implementation
├── monitor/
│   └── dashboard.py            # Loss convergence visualization
└── logs/
    └── aggregation_log.jsonl   # Training history
```

## Quick Start

### 1. Start Infrastructure

```bash
# Start Kafka, Zookeeper, and Spark
docker-compose up -d

# Wait for services to be ready (check topics created)
docker logs kafka-init
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the System (in separate terminals)

```bash
# Terminal 1: Start Cloud Aggregator
python cloud_aggregator/aggregator.py --mode batch

# Terminal 2: Start Fog Node 1
python fog_nodes/fog_node.py --node-id 1

# Terminal 3: Start Fog Node 2
python fog_nodes/fog_node.py --node-id 2

# Terminal 4: Start Sensor Producer 1
python producers/sensor_producer.py --node-id 1

# Terminal 5: Start Sensor Producer 2
python producers/sensor_producer.py --node-id 2

# Terminal 6: Monitor Dashboard
python monitor/dashboard.py --mode live
```

### 4. View Results

```bash
# Live monitoring
python monitor/dashboard.py --mode live

# Offline analysis from logs
python monitor/dashboard.py --mode offline
```

## Components

### Sensor Producer
Simulates industrial IoT sensors generating:
- Vibration data (x, y, z axes)
- Temperature readings
- Pressure measurements
- Anomaly labels (10% anomaly rate)

### Fog Node (Spark Streaming)
- Receives sensor data via Kafka
- Preprocesses and normalizes features
- Trains local logistic regression model using SGD
- Publishes model weights every N seconds

### Cloud Aggregator (FedAvg)
Implements the Federated Averaging algorithm:

```
w_{t+1} = Σ_{k=1}^{K} (n_k / n) * w_k^t
```

Where:
- `w_{t+1}` = new global model weights
- `n_k` = number of samples on node k
- `n` = total samples across all nodes
- `w_k^t` = weights from node k at round t

## Fog Node Failure Handling

The system is designed to handle fog node failures gracefully:

### 1. **Partial Participation**
- The aggregator doesn't require all nodes to participate in every round
- `MIN_NODES_FOR_AGGREGATION` parameter controls minimum required nodes
- If only 1 of 2 nodes is available, aggregation proceeds with available data

### 2. **Asynchronous Updates**
- Fog nodes publish weights independently
- Late arrivals are included in the next aggregation round
- No strict synchronization required

### 3. **Automatic Recovery**
- When a failed node recovers, it:
  - Subscribes to `global-model` topic
  - Receives latest global model
  - Resumes local training with updated weights
  - Continues participating in future rounds

### 4. **Weight Staleness Handling**
- Aggregator uses latest weights from each node
- Old weights are replaced when new ones arrive
- Timeout mechanism can be added to discard stale weights

### 5. **Fault Tolerance Mechanisms**
```python
# In aggregator.py
MIN_NODES_FOR_AGGREGATION = 1  # Proceed with single node if needed

# Weight validity check
if current_time - weight_timestamp > MAX_WEIGHT_AGE:
    discard_stale_weights()
```

### 6. **Graceful Degradation**
- System continues functioning with reduced nodes
- Global model quality may degrade temporarily
- Full recovery when nodes rejoin

## Configuration

Edit `config/settings.py` to customize:

```python
# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = "localhost:29092"

# Training parameters
LEARNING_RATE = 0.01
BATCH_SIZE = 32
LOCAL_EPOCHS = 1

# Federated Learning
AGGREGATION_INTERVAL_SECONDS = 30
MIN_NODES_FOR_AGGREGATION = 1
WEIGHT_PUBLISH_INTERVAL_SECONDS = 10
```

## Monitoring

The dashboard shows:
- Real-time loss convergence chart
- Per-node statistics
- Aggregation round details
- Participation history

## Technologies

- **Apache Kafka**: Message broker for data streaming
- **Apache Spark**: Distributed processing with Structured Streaming
- **PySpark MLlib**: Machine learning utilities
- **Python**: Kafka clients, orchestration
- **Docker Compose**: Infrastructure orchestration

## Troubleshooting

### Kafka Connection Issues
```bash
# Check if Kafka is running
docker ps | grep kafka

# View Kafka logs
docker logs kafka

# List topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Spark Issues
```bash
# Check Spark UI
open http://localhost:8080

# Increase memory if needed
export SPARK_DRIVER_MEMORY=4g
```

### No Data Flowing
```bash
# Test producer manually
python producers/sensor_producer.py --node-id 1 --max-messages 10

# Check consumer
kafka-console-consumer --bootstrap-server localhost:29092 --topic sensor-data-node-1
```

## License

MIT License
