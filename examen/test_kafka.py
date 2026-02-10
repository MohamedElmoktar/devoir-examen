"""
Script de test pour vérifier la connexion Kafka
Usage: python test_kafka.py
"""

import sys
from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient
import config

def test_kafka_connection():
    """Teste la connexion à Kafka"""
    print("🔧 Test de connexion Kafka...")

    try:
        # Test Admin Client
        print("\n1️⃣  Test Admin Client...")
        admin = KafkaAdminClient(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            client_id='test_admin'
        )
        topics = admin.list_topics()
        print(f"   ✓ Connexion établie")
        print(f"   ✓ Topics existants : {topics}")
        admin.close()

        # Test Producer
        print("\n2️⃣  Test Producer...")
        producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: str(v).encode('utf-8')
        )
        test_topic = 'test_topic'
        producer.send(test_topic, value='test_message')
        producer.flush()
        print(f"   ✓ Message envoyé sur '{test_topic}'")
        producer.close()

        # Test Consumer
        print("\n3️⃣  Test Consumer...")
        consumer = KafkaConsumer(
            test_topic,
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000
        )
        messages = list(consumer)
        print(f"   ✓ {len(messages)} message(s) reçu(s)")
        consumer.close()

        print("\n✅ Tous les tests Kafka sont passés !")
        return True

    except Exception as e:
        print(f"\n❌ Erreur de connexion Kafka : {e}")
        print("\nVérifiez que Kafka est démarré :")
        print("  docker compose up -d")
        return False


if __name__ == '__main__':
    success = test_kafka_connection()
    sys.exit(0 if success else 1)
