# 📚 Index de la Documentation

Bienvenue dans le projet **Federated Learning Edge-Fog-Cloud** !

Ce fichier vous guide vers la bonne documentation selon votre besoin.

## 🆕 Je débute

1. **[QUICKSTART.md](QUICKSTART.md)** - Démarrage rapide en 5 minutes
   - Installation
   - Premier lancement
   - Vérification que tout fonctionne

2. **[README.md](README.md)** - Documentation complète
   - Vue d'ensemble du projet
   - Instructions détaillées
   - Troubleshooting

## 🏗️ Je veux comprendre l'architecture

3. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture détaillée
   - Composants du système
   - Flux de données
   - Algorithme FedAvg expliqué
   - Privacy & sécurité

4. **[STRUCTURE.txt](STRUCTURE.txt)** - Structure du projet
   - Arborescence des fichiers
   - Description de chaque composant

## ⚙️ Je veux configurer/personnaliser

5. **[CONFIGURATION.md](CONFIGURATION.md)** - Guide de configuration
   - Paramètres ajustables
   - Configurations recommandées (dev/prod)
   - Tuning des performances

6. **[config.py](config.py)** - Fichier de configuration
   - Variables centralisées
   - À modifier selon vos besoins

## 🔧 Je veux comprendre le code

### Scripts principaux

7. **[simulator.py](simulator.py)** - Simulateur de capteurs
   - Génération de données électriques
   - Injection d'anomalies

8. **[edge_node.py](edge_node.py)** - Noeud Edge
   - Entraînement local SGDClassifier
   - Publication des poids

9. **[fog_aggregator_spark.py](fog_aggregator_spark.py)** - Agrégateur Fog
   - Spark Structured Streaming
   - Agrégation régionale

10. **[cloud_fedavg.py](cloud_fedavg.py)** - Serveur Cloud
    - Algorithme FedAvg
    - Génération modèle global

11. **[dashboard_app.py](dashboard_app.py)** - Dashboard
    - Visualisation Streamlit
    - Métriques temps réel

### Utilitaires

12. **[utils/kafka_utils.py](utils/kafka_utils.py)** - Wrappers Kafka
    - Producer/Consumer avec retry
    - Gestion d'erreurs

13. **[utils/model_utils.py](utils/model_utils.py)** - Utilitaires ML
    - FedAvg
    - Sérialisation modèles
    - Normalisation

## 🧪 Je veux tester

14. **[test_components.py](test_components.py)** - Tests unitaires
    - Tests des fonctions principales
    - Validation de FedAvg

15. **[test_kafka.py](test_kafka.py)** - Test Kafka
    - Vérification connexion Kafka
    - Test Producer/Consumer

16. **[run_tests.sh](run_tests.sh)** - Lancer les tests
    - Exécution automatique des tests
    - Rapport de couverture

## 🚀 Je veux déployer/lancer

17. **[setup.sh](setup.sh)** - Installation
    - Configuration automatique
    - Création venv
    - Installation dépendances

18. **[start_all.sh](start_all.sh)** - Lancement automatique
    - Démarre tous les composants
    - Mode background

19. **[stop_all.sh](stop_all.sh)** - Arrêt
    - Arrête tous les composants
    - Nettoyage propre

20. **[docker-compose.yml](docker-compose.yml)** - Docker Compose
    - Kafka + Zookeeper
    - Kafka UI

## 📊 Je veux un résumé

21. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Résumé complet
    - Vue d'ensemble
    - Livrables
    - Technologies
    - Résultats attendus

## 📚 Préparation examen

22. **[EXAM_PREPARATION.md](EXAM_PREPARATION.md)** - Guide complet Q&A ⭐
    - 8 parties avec questions-réponses détaillées
    - Concepts fondamentaux
    - Architecture technique
    - Technologies utilisées
    - Cas d'usage
    - Implémentation
    - Questions approfondies
    - Dépannage
    - Questions de synthèse

23. **[CHEAT_SHEET.md](CHEAT_SHEET.md)** - Aide-mémoire 1 page 🎯
    - Définitions clés
    - Formules importantes
    - Schémas essentiels
    - Commandes utiles
    - Révision rapide

24. **[EXERCISES.md](EXERCISES.md)** - Exercices pratiques 📝
    - 8 exercices avec solutions complètes
    - Calculs FedAvg
    - Normalisation
    - Bande passante
    - Latence
    - Debugging
    - Optimisation
    - Scalabilité

25. **[SYSTEM_STATUS.md](SYSTEM_STATUS.md)** - État système actuel
    - Composants actifs
    - Métriques temps réel
    - Logs disponibles
    - Commandes de gestion

## 🗺️ Parcours recommandés

### Pour un débutant complet
```
1. QUICKSTART.md
2. README.md
3. Lancer le projet
4. ARCHITECTURE.md
```

### Pour un développeur
```
1. PROJECT_SUMMARY.md
2. ARCHITECTURE.md
3. Lire config.py
4. Lire les scripts principaux
5. CONFIGURATION.md pour tuning
```

### Pour un data scientist
```
1. ARCHITECTURE.md (section FedAvg)
2. utils/model_utils.py
3. edge_node.py
4. cloud_fedavg.py
5. Expérimenter avec config.py
```

### Pour un DevOps
```
1. docker-compose.yml
2. setup.sh / start_all.sh
3. CONFIGURATION.md
4. test_kafka.py
```

### Pour préparer un examen 🎓
```
1. EXAM_PREPARATION.md (guide complet 8 parties)
2. CHEAT_SHEET.md (révision rapide)
3. EXERCISES.md (8 exercices pratiques)
4. ARCHITECTURE.md (théorie approfondie)
5. Pratiquer avec le système réel
6. Refaire les exercices sans regarder les solutions
```

## 📞 Support

- **Problèmes Kafka** : voir README.md section "Troubleshooting"
- **Problèmes Spark** : voir README.md section "Troubleshooting"
- **Configuration** : voir CONFIGURATION.md
- **Architecture** : voir ARCHITECTURE.md

---

**Bon apprentissage ! 🚀**

Pour démarrer immédiatement : `./setup.sh` puis `./start_all.sh`
