"""
Tests unitaires pour les composants principaux
Usage: pytest test_components.py
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from utils.model_utils import (
    serialize_model_weights,
    deserialize_model_weights,
    federated_averaging,
    normalize_features,
    detect_anomaly
)
from sklearn.linear_model import SGDClassifier


class TestModelUtils:
    """Tests pour les utilitaires de modèle"""

    def test_normalize_features(self):
        """Test de normalisation des features"""
        features = normalize_features(
            voltage=230.0,
            current=10.0,
            v_mean=230.0,
            v_std=5.0,
            i_mean=10.0,
            i_std=2.0
        )

        assert features.shape == (1, 3)
        # Voltage normalisé : (230 - 230) / 5 = 0
        assert abs(features[0][0]) < 0.01
        # Current normalisé : (10 - 10) / 2 = 0
        assert abs(features[0][1]) < 0.01

    def test_serialize_deserialize_model(self):
        """Test sérialisation/désérialisation des poids"""
        # Créer un modèle simple
        model = SGDClassifier()
        X = np.array([[1, 2, 3], [4, 5, 6]])
        y = np.array([0, 1])
        model.fit(X, y)

        # Sérialiser
        weights_dict = serialize_model_weights(model)

        assert 'coef' in weights_dict
        assert 'intercept' in weights_dict
        assert 'classes' in weights_dict

        # Désérialiser
        coef, intercept, classes = deserialize_model_weights(weights_dict)

        assert coef is not None
        assert intercept is not None
        assert classes is not None
        np.testing.assert_array_equal(coef, model.coef_)

    def test_federated_averaging(self):
        """Test de l'algorithme FedAvg"""
        # Créer des updates simulés
        updates = [
            {
                'n_samples': 100,
                'weights': {
                    'coef': [[1.0, 2.0, 3.0]],
                    'intercept': [0.5],
                    'classes': [0, 1]
                }
            },
            {
                'n_samples': 200,
                'weights': {
                    'coef': [[2.0, 3.0, 4.0]],
                    'intercept': [1.0],
                    'classes': [0, 1]
                }
            }
        ]

        # FedAvg
        avg_weights = federated_averaging(updates)

        # Vérification : moyenne pondérée
        # total_samples = 300
        # avg_coef[0] = (100 * 1.0 + 200 * 2.0) / 300 = 1.666...
        assert avg_weights is not None
        expected_coef = (100 * 1.0 + 200 * 2.0) / 300
        assert abs(avg_weights['coef'][0][0] - expected_coef) < 0.01

    def test_federated_averaging_empty(self):
        """Test FedAvg avec liste vide"""
        result = federated_averaging([])
        assert result is None


class TestSimulatorLogic:
    """Tests pour la logique du simulateur"""

    def test_anomaly_generation(self):
        """Test génération d'anomalies"""
        from simulator import ElectricalSensorSimulator

        sim = ElectricalSensorSimulator()

        # Test anomalie surtension
        anomaly = sim.generate_anomaly_reading('village_1', 'overvoltage')
        assert anomaly['label'] == 1
        assert anomaly['type'] == 'overvoltage'
        assert anomaly['voltage'] > 230.0 * 1.2  # Au-dessus de la normale

        # Test anomalie surintensité
        anomaly = sim.generate_anomaly_reading('village_1', 'overcurrent')
        assert anomaly['label'] == 1
        assert anomaly['current'] > 10.0 * 1.5

    def test_normal_generation(self):
        """Test génération de lectures normales"""
        from simulator import ElectricalSensorSimulator

        sim = ElectricalSensorSimulator()
        normal = sim.generate_normal_reading('village_1')

        assert normal['label'] == 0
        assert normal['type'] == 'normal'
        assert 'voltage' in normal
        assert 'current' in normal
        assert 'power' in normal


class TestEdgeNodeLogic:
    """Tests pour la logique des Edge nodes"""

    def test_preprocess_data(self):
        """Test prétraitement des données"""
        from edge_node import EdgeNode

        edge = EdgeNode('village_1')
        message = {
            'voltage': 235.0,
            'current': 12.0,
            'label': 0
        }

        features, label = edge.preprocess_data(message)

        assert features.shape == (1, 3)
        assert label == 0

    def test_model_initialization(self):
        """Test initialisation du modèle"""
        from edge_node import EdgeNode

        edge = EdgeNode('village_1')

        assert edge.model is not None
        assert not edge.model_initialized

        # Simuler un entraînement
        X = np.array([[0, 0, 0], [1, 1, 1], [0, 0, 0], [1, 1, 1]])
        y = np.array([0, 1, 0, 1])

        edge.model.partial_fit(X, y, classes=[0, 1])
        edge.model_initialized = True

        assert edge.model_initialized


class TestKafkaUtils:
    """Tests pour les utilitaires Kafka"""

    @patch('utils.kafka_utils.KafkaProducer')
    def test_producer_wrapper(self, mock_kafka_producer):
        """Test du wrapper Producer"""
        from utils.kafka_utils import KafkaProducerWrapper

        # Mock le producer
        mock_instance = Mock()
        mock_kafka_producer.return_value = mock_instance

        wrapper = KafkaProducerWrapper(['localhost:9092'])

        # Test envoi message
        message = {'test': 'data'}
        mock_instance.send.return_value.get.return_value = None

        result = wrapper.send_message('test_topic', message, 'key1')

        assert result is True
        mock_instance.send.assert_called_once()


class TestConfigValidation:
    """Tests pour valider la configuration"""

    def test_config_values(self):
        """Vérifie que config.py contient les bonnes valeurs"""
        import config

        assert isinstance(config.KAFKA_BOOTSTRAP_SERVERS, list)
        assert len(config.KAFKA_BOOTSTRAP_SERVERS) > 0

        assert isinstance(config.EDGE_IDS, list)
        assert len(config.EDGE_IDS) > 0

        assert isinstance(config.EDGE_REGIONS, dict)
        assert all(edge_id in config.EDGE_REGIONS for edge_id in config.EDGE_IDS)

        assert config.EDGE_TRAINING_FREQUENCY > 0
        assert 0 <= config.ANOMALY_PROBABILITY <= 1

    def test_kafka_topics(self):
        """Vérifie que tous les topics sont définis"""
        import config

        required_topics = [
            'sensor_data', 'edge_weights', 'fog_agg',
            'global_model', 'global_metrics'
        ]

        for topic in required_topics:
            assert topic in config.KAFKA_TOPICS


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
