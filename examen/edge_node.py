"""
Edge Node: Entraînement local du modèle de détection d'anomalies
Consomme les données capteurs, entraîne localement, publie les poids (pas les données)
"""

import argparse
import logging
import time
from collections import deque
from datetime import datetime, timezone
import numpy as np
from sklearn.linear_model import SGDClassifier
from utils.kafka_utils import KafkaProducerWrapper, KafkaConsumerWrapper
from utils.model_utils import (
    serialize_model_weights,
    normalize_features,
    apply_global_model_to_local
)
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EdgeNode:
    """Noeud Edge pour entraînement local Federated Learning"""

    def __init__(self, edge_id: str):
        self.edge_id = edge_id
        self.region = config.EDGE_REGIONS.get(edge_id, 'unknown')
        self.current_round = 0

        # Buffer pour accumulation de données
        self.data_buffer = deque(maxlen=1000)

        # Modèle local
        self.model = SGDClassifier(
            loss=config.MODEL_PARAMS['loss'],
            penalty=config.MODEL_PARAMS['penalty'],
            alpha=config.MODEL_PARAMS['alpha'],
            learning_rate=config.MODEL_PARAMS['learning_rate'],
            eta0=config.MODEL_PARAMS['eta0'],
            max_iter=config.MODEL_PARAMS['max_iter'],
            random_state=config.MODEL_PARAMS['random_state'],
            warm_start=True
        )
        self.model_initialized = False

        # Métriques
        self.total_samples = 0
        self.anomalies_detected = 0

        # Kafka
        self.producer = None
        self.consumer = None

    def connect(self):
        """Initialise les connexions Kafka"""
        self.producer = KafkaProducerWrapper(config.KAFKA_BOOTSTRAP_SERVERS)

        self.consumer = KafkaConsumerWrapper(
            topics=[config.KAFKA_TOPICS['sensor_data'], config.KAFKA_TOPICS['global_model']],
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=f'edge_node_{self.edge_id}',
            auto_offset_reset='latest'
        )
        logger.info(f"✓ Edge Node {self.edge_id} (région: {self.region}) connecté")

    def preprocess_data(self, message: dict) -> tuple:
        """Prétraite les données capteur"""
        features = normalize_features(
            message['voltage'],
            message['current'],
            config.VOLTAGE_MEAN,
            config.VOLTAGE_STD,
            config.CURRENT_MEAN,
            config.CURRENT_STD
        )
        label = message.get('label', 0)
        return features, label

    def train_local_model(self):
        """Entraîne le modèle local sur le buffer"""
        if len(self.data_buffer) < config.EDGE_BATCH_SIZE:
            return

        # Prépare les données
        X = []
        y = []
        for features, label in self.data_buffer:
            X.append(features[0])
            y.append(label)

        X = np.array(X)
        y = np.array(y)

        # Entraînement incrémental
        if not self.model_initialized:
            # Premier entraînement: initialise les classes
            if len(np.unique(y)) > 1:
                self.model.partial_fit(X, y, classes=np.array([0, 1]))
                self.model_initialized = True
                logger.info(f"[{self.edge_id}] 🧠 Modèle initialisé")
        else:
            # Entraînements suivants
            self.model.partial_fit(X, y)

        # Évalue localement
        if self.model_initialized:
            score = self.model.score(X, y)
            logger.info(
                f"[{self.edge_id}] 📊 Round {self.current_round}: "
                f"Précision={score:.3f}, Échantillons={len(y)}"
            )

            return len(y), score
        return 0, 0.0

    def publish_model_update(self, n_samples: int, local_score: float):
        """Publie les poids du modèle (pas les données brutes)"""
        if not self.model_initialized:
            return

        weights = serialize_model_weights(self.model)

        update_message = {
            'edge_id': self.edge_id,
            'region': self.region,
            'round': self.current_round,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'n_samples': n_samples,
            'weights': weights,
            'metrics': {
                'local_accuracy': local_score,
                'total_samples': self.total_samples,
                'anomalies_detected': self.anomalies_detected
            }
        }

        success = self.producer.send_message(
            config.KAFKA_TOPICS['edge_weights'],
            update_message,
            key=self.edge_id
        )

        if success:
            logger.info(
                f"[{self.edge_id}] 📤 Poids publiés: Round {self.current_round}, "
                f"n={n_samples}, acc={local_score:.3f}"
            )
            self.current_round += 1

    def update_from_global_model(self, global_weights: dict):
        """Met à jour le modèle local avec le modèle global"""
        if not self.model_initialized:
            return

        apply_global_model_to_local(self.model, global_weights)
        logger.info(f"[{self.edge_id}] 🔄 Modèle global appliqué (Round {global_weights.get('round', '?')})")

    def run(self):
        """Boucle principale du noeud Edge"""
        logger.info(f"🚀 Démarrage Edge Node {self.edge_id}")

        message_count = 0

        try:
            for message in self.consumer.consume():
                # Gestion des updates de modèle global
                if 'global_weights' in message:
                    self.update_from_global_model(message['global_weights'])
                    continue

                # Gestion des données capteur
                if message.get('edge_id') != self.edge_id:
                    continue  # Ignore les messages des autres edges

                message_count += 1
                self.total_samples += 1

                # Prétraitement
                features, label = self.preprocess_data(message)
                self.data_buffer.append((features, label))

                if label == 1:
                    self.anomalies_detected += 1

                # Entraînement périodique
                if message_count % config.EDGE_TRAINING_FREQUENCY == 0:
                    n_samples, score = self.train_local_model()
                    if n_samples > 0:
                        self.publish_model_update(n_samples, score)
                        self.data_buffer.clear()  # Nettoie le buffer

        except KeyboardInterrupt:
            logger.info(f"\n⏹  Arrêt Edge Node {self.edge_id}")
            self.producer.close()
            self.consumer.close()
        except Exception as e:
            logger.error(f"Erreur fatale: {e}", exc_info=True)
            if self.producer:
                self.producer.close()
            if self.consumer:
                self.consumer.close()


def main():
    parser = argparse.ArgumentParser(description='Edge Node pour Federated Learning')
    parser.add_argument('--edge_id', type=str, required=True,
                        help='Identifiant du noeud Edge (ex: village_1)')
    args = parser.parse_args()

    if args.edge_id not in config.EDGE_IDS:
        logger.error(f"Edge ID invalide: {args.edge_id}. Valeurs possibles: {config.EDGE_IDS}")
        return

    edge_node = EdgeNode(args.edge_id)
    edge_node.connect()
    time.sleep(2)  # Attendre initialisation Kafka
    edge_node.run()


if __name__ == '__main__':
    main()
