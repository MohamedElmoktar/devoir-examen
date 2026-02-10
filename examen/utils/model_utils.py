"""Utilitaires pour la gestion des modèles et FedAvg"""

import numpy as np
from typing import Dict, List, Tuple
from sklearn.linear_model import SGDClassifier


def serialize_model_weights(model: SGDClassifier) -> Dict:
    """Sérialise les poids d'un modèle SGDClassifier"""
    return {
        'coef': model.coef_.tolist() if hasattr(model, 'coef_') else None,
        'intercept': model.intercept_.tolist() if hasattr(model, 'intercept_') else None,
        'classes': model.classes_.tolist() if hasattr(model, 'classes_') else None
    }


def deserialize_model_weights(weights_dict: Dict) -> Tuple:
    """Désérialise les poids d'un modèle"""
    coef = np.array(weights_dict['coef']) if weights_dict.get('coef') else None
    intercept = np.array(weights_dict['intercept']) if weights_dict.get('intercept') else None
    classes = np.array(weights_dict['classes']) if weights_dict.get('classes') else None
    return coef, intercept, classes


def federated_averaging(updates: List[Dict]) -> Dict:
    """
    Implémente l'algorithme FedAvg (Federated Averaging)

    FedAvg: moyenne pondérée des poids locaux par le nombre d'échantillons

    Args:
        updates: Liste de dicts contenant {weights, n_samples}

    Returns:
        Dict contenant les poids agrégés
    """
    if not updates:
        return None

    total_samples = sum(u['n_samples'] for u in updates)

    # Initialisation avec zéros
    first_weights = updates[0]['weights']
    coef_shape = np.array(first_weights['coef']).shape
    intercept_shape = np.array(first_weights['intercept']).shape

    avg_coef = np.zeros(coef_shape)
    avg_intercept = np.zeros(intercept_shape)

    # Moyenne pondérée
    for update in updates:
        weight = update['n_samples'] / total_samples
        coef, intercept, _ = deserialize_model_weights(update['weights'])
        avg_coef += weight * coef
        avg_intercept += weight * intercept

    return {
        'coef': avg_coef.tolist(),
        'intercept': avg_intercept.tolist(),
        'classes': first_weights['classes']  # Classes communes
    }


def apply_global_model_to_local(local_model: SGDClassifier, global_weights: Dict):
    """Applique les poids globaux à un modèle local"""
    coef, intercept, classes = deserialize_model_weights(global_weights)

    if coef is not None:
        local_model.coef_ = coef
    if intercept is not None:
        local_model.intercept_ = intercept
    if classes is not None:
        local_model.classes_ = classes


def normalize_features(voltage: float, current: float,
                       v_mean: float = 230.0, v_std: float = 5.0,
                       i_mean: float = 10.0, i_std: float = 2.0) -> np.ndarray:
    """Normalise les features (Z-score normalization)"""
    v_norm = (voltage - v_mean) / v_std
    i_norm = (current - i_mean) / i_std
    power = voltage * current
    p_norm = (power - (v_mean * i_mean)) / (v_std * i_std)

    return np.array([[v_norm, i_norm, p_norm]])


def detect_anomaly(model: SGDClassifier, features: np.ndarray, threshold: float = 0.5) -> bool:
    """Détecte une anomalie avec le modèle"""
    if not hasattr(model, 'coef_'):
        return False

    try:
        proba = model.predict_proba(features)
        return proba[0][1] > threshold  # Probabilité classe anomalie
    except:
        prediction = model.predict(features)
        return prediction[0] == 1
