# 📝 Exercices Pratiques - Préparation Examen

Exercices avec solutions pour maîtriser le projet

---

## EXERCICE 1 : Calcul FedAvg à la main

**Énoncé :**
3 Edge nodes entraînent localement et obtiennent :
- Edge 1 : 100 samples, coef = [2.0, 3.0], intercept = 0.5
- Edge 2 : 200 samples, coef = [3.0, 4.0], intercept = 1.0
- Edge 3 : 50 samples, coef = [1.0, 2.0], intercept = 0.0

Calculez les poids du modèle global après FedAvg.

**Solution :**
```
Total samples = 100 + 200 + 50 = 350

Poids Edge 1 = 100/350 = 0.286
Poids Edge 2 = 200/350 = 0.571
Poids Edge 3 = 50/350 = 0.143

coef[0] = 0.286 × 2.0 + 0.571 × 3.0 + 0.143 × 1.0
        = 0.572 + 1.713 + 0.143
        = 2.428

coef[1] = 0.286 × 3.0 + 0.571 × 4.0 + 0.143 × 2.0
        = 0.858 + 2.284 + 0.286
        = 3.428

intercept = 0.286 × 0.5 + 0.571 × 1.0 + 0.143 × 0.0
          = 0.143 + 0.571 + 0.0
          = 0.714

RÉPONSE :
coef = [2.428, 3.428]
intercept = 0.714
```

---

## EXERCICE 2 : Normalisation Z-score

**Énoncé :**
Un capteur mesure V=250V et I=15A.
Paramètres normaux : μ_V=230V, σ_V=5V, μ_I=10A, σ_I=2A

Calculez les features normalisées.

**Solution :**
```
V_norm = (V - μ_V) / σ_V
       = (250 - 230) / 5
       = 20 / 5
       = 4.0

I_norm = (I - μ_I) / σ_I
       = (15 - 10) / 2
       = 5 / 2
       = 2.5

P = V × I = 250 × 15 = 3750W
P_norm = (P - μ_P) / σ_P
       = (3750 - 2300) / 1000
       = 1.45

Features = [4.0, 2.5, 1.45]

INTERPRÉTATION :
V_norm = 4.0 → 4 écarts-types au-dessus (ANOMALIE !)
I_norm = 2.5 → 2.5 écarts-types au-dessus (ANOMALIE !)
→ Probable surtension + surintensité
```

---

## EXERCICE 3 : Calcul bande passante

**Énoncé :**
Comparez la bande passante utilisée pour 4 villages sur 1 heure entre :
- A) Approche centralisée (toutes données au Cloud)
- B) Federated Learning (poids seulement)

Données :
- Fréquence : 2 msg/s par village
- Taille message brut : 100 bytes
- Taille poids modèle : 500 bytes
- Fréquence update poids : 1/6s (toutes les 50 lectures)

**Solution :**
```
APPROCHE A (Centralisé) :
Messages/heure = 4 villages × 2 msg/s × 3600s = 28,800 messages
Taille totale = 28,800 × 100 bytes = 2,880,000 bytes = 2.88 MB

APPROCHE B (Federated Learning) :
Updates/heure = 4 villages × (3600s / 6s) = 2,400 updates
Taille totale = 2,400 × 500 bytes = 1,200,000 bytes = 1.2 MB

RÉDUCTION :
(2.88 - 1.2) / 2.88 = 58.3% de réduction

MAIS ATTENTION !
On oublie les données locales Edge → Fog → Cloud
Calcul complet :

Centralisé :
- Edge → Cloud : 2.88 MB

Federated :
- Edge → Fog : 1.2 MB (poids)
- Fog → Cloud : dépend agrégation

Si Fog agrège toutes les 30s :
Fog updates = 120 updates/heure (3600s / 30s)
Par région (2 régions) = 240 updates
Fog → Cloud = 240 × 1000 bytes = 240 KB

Total FL = 1.2 MB + 0.24 MB = 1.44 MB
Réduction = 50%
```

---

## EXERCICE 4 : Latence bout en bout

**Énoncé :**
Calculez la latence totale pour qu'une anomalie détectée par un capteur apparaisse sur le dashboard.

Latences connues :
- Capteur → Kafka : 10ms
- Kafka → Edge : 20ms
- Edge training : 0ms (déjà entraîné)
- Edge inference : 5ms
- Edge → Kafka : 10ms
- Kafka → Fog : 20ms
- Fog aggregation : 30,000ms (fenêtre 30s)
- Fog → Kafka : 10ms
- Kafka → Cloud : 20ms
- Cloud FedAvg : 50ms
- Cloud → Kafka : 10ms
- Kafka → Dashboard : 20ms
- Dashboard render : 100ms

**Solution :**
```
SCÉNARIO 1 : Détection locale (Edge)
Capteur → Kafka : 10ms
Kafka → Edge : 20ms
Edge inference : 5ms
(Edge peut détecter localement, pas besoin d'attendre FedAvg)

TOTAL = 35ms (détection temps réel !)

SCÉNARIO 2 : Métriques sur Dashboard
Capteur → Kafka : 10ms
Kafka → Edge : 20ms
Edge training : 0ms (batch)
Edge → Kafka : 10ms
Kafka → Fog : 20ms
Fog aggregation : 30,000ms (goulot !)
Fog → Kafka : 10ms
Kafka → Cloud : 20ms
Cloud FedAvg : 50ms
Cloud → Kafka : 10ms
Kafka → Dashboard : 20ms
Dashboard render : 100ms

TOTAL = 30,270ms ≈ 30 secondes

OPTIMISATION :
Si on réduit fenêtre Fog à 5s :
TOTAL = 5,270ms ≈ 5 secondes

CONCLUSION :
Détection locale = temps réel (<100ms)
Métriques globales = différé (30s)
```

---

## EXERCICE 5 : Choix architecture

**Énoncé :**
Pour chaque scénario, justifiez si Federated Learning est adapté :

A) Réseau social avec 1 milliard d'utilisateurs, photos personnelles
B) Station météo nationale avec 50 capteurs centralisés
C) Smartphones détectant activité physique (marche/course) pour 10,000 users
D) Serveurs d'une banque analysant transactions frauduleuses

**Solution :**

**A) Réseau social (1B users)**
✅ **ADAPTÉ** - Federated Learning
- Privacy : photos personnelles sensibles
- Scalabilité : impossiblede centraliser 1B users
- Bande passante : photos = gros fichiers
- Exemple : Google Photos utilise FL

**B) Station météo (50 capteurs)**
❌ **NON ADAPTÉ** - Approche centralisée
- Privacy : données météo publiques
- Volume : 50 capteurs = gérable au Cloud
- Latence : pas critique (prévisions à l'heure)
- Complexité : FL serait over-engineering

**C) Smartphones activité (10K users)**
✅ **ADAPTÉ** - Federated Learning
- Privacy : données santé sensibles (RGPD)
- Offline : détection locale nécessaire
- Bande passante : économies importantes
- Exemple : Apple HealthKit utilise FL

**D) Banque transactions (centralisé)**
❌ **NON ADAPTÉ** - Approche centralisée
- Privacy : déjà géré par chiffrement + compliance
- Temps réel : besoin détection <100ms au datacenter
- Régulation : audits nécessitent accès données
- Infrastructure : serveurs bancaires déjà sécurisés

---

## EXERCICE 6 : Debugging

**Énoncé :**
Vous lancez le système mais les Edge nodes ne reçoivent aucune donnée.
Logs observés :
```
[Simulator] INFO - ✓ Kafka Producer connecté
[Simulator] INFO - ✓ [village_1] V=235V, I=10A
[Edge village_1] INFO - ✓ Kafka Consumer connecté
[Edge village_1] WARNING - Aucun message reçu depuis 60s
```

Diagnostiquez le problème et proposez une solution.

**Solution :**

**Diagnostic étape par étape :**

```bash
# 1. Vérifier que Kafka reçoit les messages
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic sensor_data \
  --from-beginning \
  --max-messages 5
```

**Cas 1 : Messages visibles**
→ Problème : Edge consumer mal configuré

Causes possibles :
- Consumer group différent avec offset à la fin
- Filter edge_id incorrect
- Consumer.poll() timeout trop court

Solution :
```python
# edge_node.py
consumer = KafkaConsumer(
    'sensor_data',
    group_id=f'edge_node_{edge_id}',
    auto_offset_reset='earliest',  # Lire depuis début
    consumer_timeout_ms=None  # Pas de timeout
)
```

**Cas 2 : Aucun message visible**
→ Problème : Simulator ne publie pas

Causes possibles :
- Topic pas créé
- Producer mal configuré
- Erreur silencieuse

Solution :
```bash
# Créer topics
python create_kafka_topics.py

# Vérifier topics
docker exec kafka kafka-topics \
  --list --bootstrap-server localhost:9092

# Vérifier logs simulator
tail -f logs/simulator.log
```

**Cas 3 : Topic existe mais vide**
→ Problème : Serialization ou Producer

Solution :
```python
# simulator.py - ajouter logs debug
try:
    future = producer.send('sensor_data', message)
    record_metadata = future.get(timeout=10)
    logger.info(f"Message envoyé : {record_metadata.offset}")
except Exception as e:
    logger.error(f"ERREUR : {e}")
```

---

## EXERCICE 7 : Optimisation

**Énoncé :**
Le système fonctionne mais la précision du modèle plafonne à 60%.
Proposez 3 optimisations pour améliorer la performance.

**Solution :**

**1. Augmenter features**
```python
# Actuellement : [V_norm, I_norm, P_norm]
# Ajouter features dérivées :

def extract_features(history):
    # Features temporelles
    V_mean_5s = np.mean(history[-10:, 0])  # Moyenne 5s
    V_std_5s = np.std(history[-10:, 0])    # Variance
    V_trend = history[-1, 0] - history[-5, 0]  # Tendance

    # Features fréquentielles
    V_fft = np.fft.fft(history[:, 0])
    dominant_freq = np.argmax(np.abs(V_fft))

    return [V_norm, I_norm, P_norm,
            V_mean_5s, V_std_5s, V_trend,
            dominant_freq]
```
Gain attendu : +10-15% précision

**2. Ajuster hyper-paramètres**
```python
# config.py - Tester différentes configs

# Configuration actuelle (sous-optimale ?)
MODEL_PARAMS = {
    'learning_rate': 'constant',
    'eta0': 0.01,  # Trop faible ?
    'alpha': 0.0001  # Régularisation trop forte ?
}

# Configuration optimisée
MODEL_PARAMS = {
    'learning_rate': 'adaptive',  # Ajuste automatiquement
    'eta0': 0.1,  # Plus agressif
    'alpha': 0.00001,  # Moins de régularisation
    'early_stopping': True,
    'validation_fraction': 0.1
}
```
Gain attendu : +5-10% précision

**3. Augmenter données d'entraînement**
```python
# Actuellement : 50 samples par batch
# Problème : pas assez pour apprendre patterns complexes

# config.py
EDGE_TRAINING_FREQUENCY = 200  # Au lieu de 50
EDGE_BATCH_SIZE = 100  # Au lieu de 20

# Plus de données = meilleure généralisation
```
Gain attendu : +5-8% précision

**BONUS : Class imbalance**
```python
# Si 90% normal, 10% anomalie
# Modèle apprend à toujours prédire "normal"

from sklearn.utils import class_weight

# Calculer poids des classes
weights = class_weight.compute_class_weight(
    'balanced',
    classes=np.array([0, 1]),
    y=labels
)

# Appliquer au modèle
model = SGDClassifier(class_weight='balanced')
```
Gain attendu : +10-20% sur détection anomalies

---

## EXERCICE 8 : Scalabilité

**Énoncé :**
Actuellement 4 villages. Le projet doit passer à 100 villages.
Identifiez 3 goulots d'étranglement et proposez des solutions.

**Solution :**

**Goulot 1 : Kafka partitions**
```
Problème :
- 3 partitions pour 100 villages
- Parallelisme limité
- Latence augmente

Solution :
# docker-compose.yml
environment:
  KAFKA_NUM_PARTITIONS: 50  # 50 partitions
  KAFKA_REPLICATION_FACTOR: 3  # Résilience

# Edge nodes
# Kafka distribue automatiquement sur partitions

Gain : 16× parallélisme (50 vs 3)
```

**Goulot 2 : Fog Spark (1 instance)**
```
Problème :
- 1 seul worker Spark
- Agrégation séquentielle
- RAM insuffisante (500 MB → 10+ GB)

Solution :
# Spark cluster
spark-submit \
  --master spark://master:7077 \
  --executor-memory 4g \
  --num-executors 10 \
  --executor-cores 4 \
  fog_aggregator_spark.py

# Ou : Spark on Kubernetes
kubectl apply -f spark-deployment.yaml

Gain : 10× capacité traitement
```

**Goulot 3 : Cloud FedAvg (agrégation séquentielle)**
```
Problème :
- FedAvg séquentiel : O(n)
- 100 villages = 100× plus lent

Solution :
# Agrégation hiérarchique
def hierarchical_fedavg(updates, levels=2):
    # Niveau 1 : 100 villages → 10 groupes
    groups = [updates[i:i+10] for i in range(0, 100, 10)]
    regional = [fedavg(group) for group in groups]

    # Niveau 2 : 10 régions → 1 global
    return fedavg(regional)

# Complexité : O(n/k + k) au lieu de O(n)

Gain : 5× plus rapide si k=10
```

**Monitoring scalabilité :**
```python
# Ajouter métriques
import time

start = time.time()
global_weights = federated_averaging(updates)
duration = time.time() - start

logger.info(f"FedAvg duration: {duration:.2f}s for {len(updates)} updates")

# Alarme si trop lent
if duration > 5.0:
    send_alert("FedAvg trop lent !")
```

---

## ✅ CORRECTION RAPIDE

Vérifiez vos réponses :
- **Ex1** : coef=[2.428, 3.428], intercept=0.714 ✓
- **Ex2** : Features=[4.0, 2.5, 1.45], ANOMALIE ✓
- **Ex3** : Réduction 50% bande passante ✓
- **Ex4** : Local=35ms, Global=30s ✓
- **Ex5** : A=Oui, B=Non, C=Oui, D=Non ✓
- **Ex6** : Vérifier topics + offsets consumer ✓
- **Ex7** : Features + Hyper-params + Data ✓
- **Ex8** : Kafka partitions + Spark cluster + Hiérarchie ✓

**Score 8/8** → Vous maîtrisez ! 🎉

---

## 📚 Pour aller plus loin

Créez vos propres exercices :
1. Calculez la convergence théorique de FedAvg
2. Implémentez Differential Privacy
3. Comparez FedAvg vs FedProx
4. Simulez une attaque Byzantine
5. Optimisez la compression de modèles

Révisez `EXAM_PREPARATION.md` pour théorie complète.
