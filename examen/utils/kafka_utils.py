"""Utilitaires Kafka pour gérer la communication entre composants"""

import json
import logging
from typing import Any, Dict, Optional
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import time

logger = logging.getLogger(__name__)


class KafkaProducerWrapper:
    """Wrapper pour KafkaProducer avec gestion d'erreurs"""

    def __init__(self, bootstrap_servers: list, max_retries: int = 3):
        self.bootstrap_servers = bootstrap_servers
        self.max_retries = max_retries
        self.producer = None
        self._connect()

    def _connect(self):
        """Établit la connexion au broker Kafka avec retry"""
        for attempt in range(self.max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',
                    retries=3,
                    max_in_flight_requests_per_connection=1
                )
                logger.info("✓ Connexion Kafka Producer établie")
                return
            except KafkaError as e:
                logger.warning(f"Tentative {attempt + 1}/{self.max_retries} échouée: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def send_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None) -> bool:
        """Envoie un message sur un topic Kafka"""
        try:
            future = self.producer.send(topic, value=message, key=key)
            future.get(timeout=10)
            return True
        except Exception as e:
            logger.error(f"Erreur envoi message sur {topic}: {e}")
            return False

    def close(self):
        """Ferme proprement le producer"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Producer Kafka fermé")


class KafkaConsumerWrapper:
    """Wrapper pour KafkaConsumer avec gestion d'erreurs"""

    def __init__(self, topics: list, bootstrap_servers: list,
                 group_id: str, auto_offset_reset: str = 'earliest',
                 max_retries: int = 3):
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.max_retries = max_retries
        self.consumer = None
        self._connect()

    def _connect(self):
        """Établit la connexion au broker Kafka avec retry"""
        for attempt in range(self.max_retries):
            try:
                self.consumer = KafkaConsumer(
                    *self.topics,
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    group_id=self.group_id,
                    auto_offset_reset=self.auto_offset_reset,
                    enable_auto_commit=True,
                    max_poll_interval_ms=300000
                )
                logger.info(f"✓ Connexion Kafka Consumer établie (group: {self.group_id})")
                return
            except KafkaError as e:
                logger.warning(f"Tentative {attempt + 1}/{self.max_retries} échouée: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def consume(self):
        """Générateur de messages depuis Kafka"""
        try:
            for message in self.consumer:
                yield message.value
        except Exception as e:
            logger.error(f"Erreur consommation Kafka: {e}")
            raise

    def close(self):
        """Ferme proprement le consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer Kafka fermé")


def create_topics_if_not_exist(bootstrap_servers: list, topics: list):
    """Crée les topics Kafka s'ils n'existent pas (avec admin client)"""
    from kafka.admin import KafkaAdminClient, NewTopic

    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='topic_creator'
        )

        existing_topics = admin_client.list_topics()
        topics_to_create = [
            NewTopic(name=topic, num_partitions=3, replication_factor=1)
            for topic in topics if topic not in existing_topics
        ]

        if topics_to_create:
            admin_client.create_topics(new_topics=topics_to_create, validate_only=False)
            logger.info(f"✓ Topics créés: {[t.name for t in topics_to_create]}")
        else:
            logger.info("✓ Tous les topics existent déjà")

        admin_client.close()
    except Exception as e:
        logger.warning(f"Impossible de créer les topics: {e}")
