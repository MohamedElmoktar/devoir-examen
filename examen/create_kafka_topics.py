"""
Script pour créer les topics Kafka au démarrage
"""

import time
import logging
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_kafka(bootstrap_servers, max_retries=30, delay=2):
    """Attend que Kafka soit prêt"""
    for i in range(max_retries):
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id='topic_creator',
                request_timeout_ms=10000
            )
            admin.close()
            logger.info("✓ Kafka est prêt")
            return True
        except Exception as e:
            logger.info(f"Tentative {i+1}/{max_retries}: Kafka pas encore prêt...")
            time.sleep(delay)

    logger.error("❌ Impossible de se connecter à Kafka")
    return False


def create_topics():
    """Crée tous les topics nécessaires"""
    logger.info("🔧 Création des topics Kafka...")

    # Attendre que Kafka soit prêt
    if not wait_for_kafka(config.KAFKA_BOOTSTRAP_SERVERS):
        return False

    try:
        admin = KafkaAdminClient(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            client_id='topic_creator'
        )

        # Liste des topics à créer
        topics = [
            NewTopic(
                name=topic_name,
                num_partitions=3,
                replication_factor=1
            )
            for topic_name in config.KAFKA_TOPICS.values()
        ]

        # Créer les topics
        try:
            admin.create_topics(new_topics=topics, validate_only=False)
            logger.info(f"✓ {len(topics)} topics créés avec succès")
        except TopicAlreadyExistsError:
            logger.info("✓ Topics existent déjà")

        # Vérifier que les topics existent
        existing_topics = admin.list_topics()
        for topic_name in config.KAFKA_TOPICS.values():
            if topic_name in existing_topics:
                logger.info(f"  ✓ {topic_name}")
            else:
                logger.warning(f"  ⚠️  {topic_name} n'existe pas")

        admin.close()
        return True

    except Exception as e:
        logger.error(f"❌ Erreur création topics: {e}")
        return False


if __name__ == '__main__':
    success = create_topics()
    exit(0 if success else 1)
