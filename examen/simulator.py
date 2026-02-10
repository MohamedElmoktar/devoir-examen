"""
Simulateur de capteurs pour réseau électrique rural
Génère des données de tension/courant avec injection d'anomalies
"""

import time
import random
import logging
from datetime import datetime, timezone
import numpy as np
from utils.kafka_utils import KafkaProducerWrapper, create_topics_if_not_exist
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ElectricalSensorSimulator:
    """Simule des capteurs électriques pour plusieurs villages"""

    def __init__(self):
        self.producer = None
        self.message_count = 0

    def connect(self):
        """Initialise la connexion Kafka"""
        create_topics_if_not_exist(
            config.KAFKA_BOOTSTRAP_SERVERS,
            list(config.KAFKA_TOPICS.values())
        )
        time.sleep(2)  # Attendre création topics

        self.producer = KafkaProducerWrapper(config.KAFKA_BOOTSTRAP_SERVERS)
        logger.info("✓ Simulateur connecté à Kafka")

    def generate_normal_reading(self, edge_id: str) -> dict:
        """Génère une lecture normale"""
        voltage = np.random.normal(config.VOLTAGE_MEAN, config.VOLTAGE_STD)
        current = np.random.normal(config.CURRENT_MEAN, config.CURRENT_STD)

        return {
            'edge_id': edge_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'voltage': round(voltage, 2),
            'current': round(current, 2),
            'power': round(voltage * current, 2),
            'label': 0,  # Normal
            'type': 'normal'
        }

    def generate_anomaly_reading(self, edge_id: str, anomaly_type: str = 'random') -> dict:
        """Génère une lecture anormale"""
        if anomaly_type == 'random':
            anomaly_type = random.choice(['overvoltage', 'overcurrent', 'undervoltage', 'power_surge'])

        if anomaly_type == 'overvoltage':
            voltage = config.VOLTAGE_MEAN * config.ANOMALY_VOLTAGE_FACTOR
            current = np.random.normal(config.CURRENT_MEAN, config.CURRENT_STD)
        elif anomaly_type == 'undervoltage':
            voltage = config.VOLTAGE_MEAN * 0.7
            current = np.random.normal(config.CURRENT_MEAN, config.CURRENT_STD)
        elif anomaly_type == 'overcurrent':
            voltage = np.random.normal(config.VOLTAGE_MEAN, config.VOLTAGE_STD)
            current = config.CURRENT_MEAN * config.ANOMALY_CURRENT_FACTOR
        else:  # power_surge
            voltage = config.VOLTAGE_MEAN * 1.2
            current = config.CURRENT_MEAN * 1.5

        return {
            'edge_id': edge_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'voltage': round(voltage, 2),
            'current': round(current, 2),
            'power': round(voltage * current, 2),
            'label': 1,  # Anomalie
            'type': anomaly_type
        }

    def generate_reading(self, edge_id: str) -> dict:
        """Génère une lecture (normale ou anormale)"""
        if random.random() < config.ANOMALY_PROBABILITY:
            return self.generate_anomaly_reading(edge_id)
        else:
            return self.generate_normal_reading(edge_id)

    def run(self):
        """Boucle principale de simulation"""
        logger.info(f"🚀 Démarrage du simulateur pour {len(config.EDGE_IDS)} villages")
        logger.info(f"   Fréquence: {config.SIMULATOR_FREQUENCY}s")
        logger.info(f"   Probabilité anomalie: {config.ANOMALY_PROBABILITY * 100}%")

        try:
            while True:
                for edge_id in config.EDGE_IDS:
                    reading = self.generate_reading(edge_id)

                    success = self.producer.send_message(
                        config.KAFKA_TOPICS['sensor_data'],
                        reading,
                        key=edge_id
                    )

                    if success:
                        self.message_count += 1
                        status = "🔴 ANOMALY" if reading['label'] == 1 else "✓"
                        logger.info(
                            f"{status} [{edge_id}] V={reading['voltage']}V, "
                            f"I={reading['current']}A, P={reading['power']}W "
                            f"(total: {self.message_count})"
                        )

                time.sleep(config.SIMULATOR_FREQUENCY)

        except KeyboardInterrupt:
            logger.info(f"\n⏹  Arrêt du simulateur (total messages: {self.message_count})")
            self.producer.close()
        except Exception as e:
            logger.error(f"Erreur fatale: {e}", exc_info=True)
            self.producer.close()


def main():
    simulator = ElectricalSensorSimulator()
    simulator.connect()
    simulator.run()


if __name__ == '__main__':
    main()
