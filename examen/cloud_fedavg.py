"""
Cloud FedAvg: Agrégation globale avec algorithme Federated Averaging
Consomme les agrégations Fog, applique FedAvg, publie le modèle global
"""

import logging
import time
from datetime import datetime, timezone
from collections import defaultdict
from utils.kafka_utils import KafkaProducerWrapper, KafkaConsumerWrapper
from utils.model_utils import federated_averaging
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CloudFedAvg:
    """Serveur Cloud pour agrégation FedAvg globale"""

    def __init__(self):
        self.current_round = 0
        self.global_weights = None

        # Buffer pour accumulation des updates par round
        self.round_updates = defaultdict(list)

        # Métriques globales
        self.global_metrics = {
            'total_samples': 0,
            'total_anomalies': 0,
            'participating_regions': set()
        }

        # Kafka
        self.producer = None
        self.consumer = None

    def connect(self):
        """Initialise les connexions Kafka"""
        self.producer = KafkaProducerWrapper(config.KAFKA_BOOTSTRAP_SERVERS)

        self.consumer = KafkaConsumerWrapper(
            topics=[config.KAFKA_TOPICS['fog_agg']],
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id='cloud_fedavg',
            auto_offset_reset='latest'
        )
        logger.info("✓ Cloud FedAvg connecté")

    def process_fog_update(self, message: dict) -> bool:
        """Traite une update du Fog"""
        region = message.get('region')
        all_weights = message.get('all_weights', [])
        total_n_samples = message.get('total_n_samples', 0)
        avg_accuracy = message.get('avg_accuracy', 0.0)
        total_anomalies = message.get('total_anomalies', 0)

        if not all_weights:
            logger.warning(f"Update Fog vide pour région {region}")
            return False

        # Prépare les updates pour FedAvg
        for weights in all_weights:
            self.round_updates[self.current_round].append({
                'region': region,
                'weights': weights,
                'n_samples': total_n_samples // len(all_weights)  # Distribution équitable
            })

        # Métriques
        self.global_metrics['total_samples'] += total_n_samples
        self.global_metrics['total_anomalies'] += total_anomalies
        self.global_metrics['participating_regions'].add(region)

        logger.info(
            f"📥 Fog update reçue: région={region}, "
            f"edges={len(all_weights)}, samples={total_n_samples}, "
            f"acc={avg_accuracy:.3f}, anomalies={total_anomalies}"
        )

        return True

    def should_aggregate(self) -> bool:
        """Détermine si on doit agréger (assez d'updates reçues)"""
        updates = self.round_updates[self.current_round]
        regions = set(u['region'] for u in updates)

        # Attend au minimum updates de X régions différentes
        if len(regions) >= config.FEDAVG_AGGREGATION_THRESHOLD:
            return True

        return False

    def perform_fedavg(self):
        """Applique l'algorithme FedAvg et publie le modèle global"""
        updates = self.round_updates[self.current_round]

        if not updates:
            logger.warning("Aucune update à agréger")
            return

        logger.info(f"🧮 FedAvg Round {self.current_round}: agrégation de {len(updates)} updates")

        # Application de FedAvg
        self.global_weights = federated_averaging(updates)

        if not self.global_weights:
            logger.error("Échec FedAvg")
            return

        # Calcul métriques
        total_samples = sum(u['n_samples'] for u in updates)
        participating_regions = list(set(u['region'] for u in updates))

        # Publication modèle global
        global_model_message = {
            'round': self.current_round,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'global_weights': self.global_weights,
            'participating_regions': participating_regions,
            'total_samples': total_samples
        }

        self.producer.send_message(
            config.KAFKA_TOPICS['global_model'],
            global_model_message,
            key=f"round_{self.current_round}"
        )

        # Publication métriques globales
        metrics_message = {
            'round': self.current_round,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_samples': total_samples,
            'participating_regions': participating_regions,
            'num_updates': len(updates),
            'anomalies_detected': self.global_metrics['total_anomalies']
        }

        self.producer.send_message(
            config.KAFKA_TOPICS['global_metrics'],
            metrics_message,
            key=f"round_{self.current_round}"
        )

        logger.info(
            f"✅ Round {self.current_round} terminé: "
            f"{len(participating_regions)} régions, {total_samples} samples, "
            f"{self.global_metrics['total_anomalies']} anomalies"
        )

        # Réinitialisation pour prochain round
        self.current_round += 1
        self.global_metrics = {
            'total_samples': 0,
            'total_anomalies': 0,
            'participating_regions': set()
        }

    def run(self):
        """Boucle principale Cloud FedAvg"""
        logger.info("🚀 Démarrage Cloud FedAvg Server")
        logger.info(f"   Seuil agrégation: {config.FEDAVG_AGGREGATION_THRESHOLD} régions")

        last_aggregation_time = time.time()

        try:
            for message in self.consumer.consume():
                self.process_fog_update(message)

                # Agrégation si conditions remplies
                current_time = time.time()
                time_elapsed = current_time - last_aggregation_time

                if self.should_aggregate() or time_elapsed > config.FEDAVG_ROUND_TIMEOUT:
                    self.perform_fedavg()
                    last_aggregation_time = current_time

        except KeyboardInterrupt:
            logger.info(f"\n⏹  Arrêt Cloud FedAvg (rounds complétés: {self.current_round})")
            self.producer.close()
            self.consumer.close()
        except Exception as e:
            logger.error(f"Erreur fatale: {e}", exc_info=True)
            if self.producer:
                self.producer.close()
            if self.consumer:
                self.consumer.close()


def main():
    cloud = CloudFedAvg()
    cloud.connect()
    time.sleep(2)
    cloud.run()


if __name__ == '__main__':
    main()
