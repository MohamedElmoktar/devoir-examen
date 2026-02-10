# 📚 Préparation Examen - Federated Learning Edge-Fog-Cloud

Guide complet de questions-réponses pour maîtriser le projet.

---

## 🎯 PARTIE 1 : CONCEPTS FONDAMENTAUX

### Q1.1 : Qu'est-ce que le Federated Learning ?

**Réponse :**
Le Federated Learning (apprentissage fédéré) est une technique de machine learning où :
- **L'entraînement se fait localement** sur plusieurs appareils (Edge nodes)
- **Seuls les paramètres du modèle** sont partagés (pas les données brutes)
- **Un modèle global** est créé par agrégation des modèles locaux
- **Les données restent privées** sur chaque appareil

**Avantages :**
- ✅ Préservation de la confidentialité (privacy-preserving)
- ✅ Réduction de la bande passante (pas de transfert de données brutes)
- ✅ Distribution de la charge de calcul
- ✅ Apprentissage sur données décentralisées

---

### Q1.2 : Qu'est-ce que l'architecture Edge-Fog-Cloud ?

**Réponse :**

**3 couches hiérarchiques :**

1. **Edge Layer (Couche périphérique)**
   - Appareils IoT, capteurs, smartphones
   - Proche des utilisateurs/sources de données
   - Ressources limitées mais faible latence
   - **Notre projet** : 4 villages avec capteurs électriques

2. **Fog Layer (Couche intermédiaire)**
   - Serveurs intermédiaires régionaux
   - Pré-traitement et agrégation
   - Réduction du trafic vers le Cloud
   - **Notre projet** : Spark Streaming (agrégation par région)

3. **Cloud Layer (Couche centrale)**
   - Serveurs puissants centralisés
   - Ressources quasi-illimitées
   - Latence plus élevée
   - **Notre projet** : FedAvg global

**Pourquoi cette architecture ?**
- Réduit la latence (traitement Edge)
- Économise la bande passante (agrégation Fog)
- Optimise les ressources (calcul distribué)

---

### Q1.3 : Qu'est-ce que l'algorithme FedAvg ?

**Réponse :**

**FedAvg = Federated Averaging** (McMahan et al., 2017)

**Principe :**
Moyenne pondérée des poids des modèles locaux par le nombre d'échantillons.

**Formule mathématique :**
```
w_global = Σ(n_i × w_i) / Σ(n_i)

où :
- w_i : poids du modèle local i
- n_i : nombre d'échantillons du client i
- w_global : poids du modèle global agrégé
```

**Algorithme étape par étape :**
```
1. Initialiser w_global aléatoirement
2. Pour chaque round t = 1, 2, 3, ...
   a. Distribuer w_global à tous les clients
   b. Chaque client i :
      - Entraîne localement sur ses données
      - Obtient w_i (nouveau poids local)
      - Envoie (w_i, n_i) au serveur
   c. Serveur calcule :
      w_global = Σ(n_i × w_i) / Σ(n_i)
3. Retourner w_global final
```

**Pourquoi pondérer par n_i ?**
- Les clients avec plus de données ont plus d'influence
- Évite le biais vers les petits datasets
- Meilleure convergence

---

## 🏗️ PARTIE 2 : ARCHITECTURE DU PROJET

### Q2.1 : Décrivez l'architecture complète du projet

**Réponse :**

```
┌─────────────────────────────────────────┐
│           CLOUD LAYER                    │
│  cloud_fedavg.py                        │
│  • Reçoit updates du Fog                │
│  • Applique FedAvg                      │
│  • Publie modèle global                 │
│  Topics: fog_agg → global_model         │
└─────────────────────────────────────────┘
                ▲
                │ (poids agrégés par région)
                │
┌─────────────────────────────────────────┐
│            FOG LAYER                     │
│  fog_aggregator_spark.py                │
│  • Spark Structured Streaming           │
│  • Agrégation régionale (30s windows)   │
│  • 2 régions: North, South              │
│  Topics: edge_weights → fog_agg         │
└─────────────────────────────────────────┘
                ▲
                │ (poids des modèles locaux)
                │
┌─────────────────────────────────────────┐
│            EDGE LAYER                    │
│  4× edge_node.py (villages 1-4)        │
│  • Consomme données capteurs            │
│  • Entraîne SGDClassifier localement    │
│  • Publie poids (pas données)           │
│  Topics: sensor_data → edge_weights     │
└─────────────────────────────────────────┘
                ▲
                │ (données capteurs brutes)
                │
┌─────────────────────────────────────────┐
│         DATA SOURCE                      │
│  simulator.py                           │
│  • Génère données V, I                  │
│  • Injecte anomalies (10%)              │
│  Topics: → sensor_data                  │
└─────────────────────────────────────────┘
```

**Composants additionnels :**
- **Kafka** : Bus de messages distribué
- **Dashboard Streamlit** : Visualisation temps réel
- **Docker Compose** : Orchestration Kafka/Zookeeper

---

### Q2.2 : Quels sont les topics Kafka et leur rôle ?

**Réponse :**

| Topic | Producteur | Consommateur | Contenu | Rôle |
|-------|-----------|--------------|---------|------|
| `sensor_data` | Simulator | Edge nodes | {V, I, P, label} | Données capteurs brutes |
| `edge_weights` | Edge nodes | Fog | {weights, n_samples, metrics} | Poids modèles locaux |
| `fog_agg` | Fog | Cloud | {région, weights agrégés} | Agrégation régionale |
| `global_model` | Cloud | Edge nodes | {global_weights, round} | Modèle global FedAvg |
| `global_metrics` | Cloud | Dashboard | {round, samples, anomalies} | Métriques globales |
| `alerts` | (optionnel) | Dashboard | {anomalies critiques} | Alertes |

**Partitionnement :**
- Chaque topic a **3 partitions** pour parallélisme
- **Replication factor = 1** (développement, production = 3+)

---

### Q2.3 : Pourquoi utiliser Kafka ? Quelles alternatives ?

**Réponse :**

**Pourquoi Kafka ?**
- ✅ **Streaming temps réel** : latence <10ms
- ✅ **Scalabilité horizontale** : partitions + consumers groups
- ✅ **Durabilité** : messages persistés sur disque
- ✅ **Découplage** : producteurs/consommateurs indépendants
- ✅ **Rejouabilité** : relire messages historiques

**Alternatives :**
| Technologie | Avantages | Inconvénients |
|------------|-----------|---------------|
| **RabbitMQ** | Simple, protocoles multiples | Moins performant en streaming |
| **Apache Pulsar** | Multi-tenancy, geo-replication | Plus complexe |
| **Redis Streams** | Très rapide, simple | Moins de fonctionnalités |
| **AWS Kinesis** | Managed, scalable | Cloud-only, coût |
| **MQTT** | IoT optimisé, léger | Pas de persistance |

**Choix Kafka justifié :**
- Architecture Edge-Fog-Cloud nécessite streaming temps réel
- Volume de messages élevé (8 msg/s × scaling)
- Besoin de rejouabilité pour tests/debug

---

## 💻 PARTIE 3 : TECHNOLOGIES UTILISÉES

### Q3.1 : Pourquoi utiliser Spark Structured Streaming au Fog ?

**Réponse :**

**Raisons :**

1. **Streaming temps réel**
   - API déclarative (DataFrame/SQL)
   - Fenêtres temporelles (windows)
   - Gestion du retard (watermarks)

2. **Scalabilité**
   - Distribué sur plusieurs workers
   - Traitement parallèle automatique
   - Tolère les pannes (checkpointing)

3. **Intégration Kafka native**
   - Connector Kafka intégré
   - Gestion offsets automatique
   - Exactly-once semantics

**Notre implémentation :**
```python
# Fenêtre de 30 secondes
aggregated = df.groupBy(
    window(col("timestamp"), "30 seconds"),
    col("region")
).agg(...)
```

**Alternatives considérées :**
- **Flink** : plus complexe, overkill pour notre cas
- **Python pur** : pas de distribution, limite scalabilité
- **Kafka Streams** : nécessiterait Java/Scala

---

### Q3.2 : Pourquoi scikit-learn SGDClassifier pour l'Edge ?

**Réponse :**

**Raisons du choix :**

1. **Entraînement incrémental**
   ```python
   model.partial_fit(X, y)  # Pas besoin de tout recharger
   ```
   - Crucial pour Edge avec mémoire limitée
   - Mise à jour continue sans réinitialiser

2. **Léger et rapide**
   - Pas de dépendances lourdes (TensorFlow, PyTorch)
   - CPU-only (pas besoin GPU sur Edge)
   - Footprint mémoire faible

3. **Compatible FedAvg**
   - Poids linéaires simples (coef + intercept)
   - Sérialisation facile (JSON)
   - Agrégation mathématique directe

**Formule SGDClassifier (logistic regression) :**
```
y = sigmoid(w·x + b)

où :
- w : coefficients (poids)
- x : features [V_norm, I_norm, P_norm]
- b : intercept (biais)
```

**Alternatives possibles :**
- **TensorFlow Lite** : pour modèles plus complexes (CNN)
- **PyTorch Mobile** : si on voulait deep learning
- **Random Forest** : pas d'entraînement incrémental
- **Neural Network** : trop lourd pour Edge simple

---

### Q3.3 : Expliquez le rôle de Streamlit

**Réponse :**

**Streamlit = Dashboard interactif Python**

**Avantages :**
- ✅ **Rapide à développer** : Python pur, pas de HTML/CSS/JS
- ✅ **Temps réel** : rafraîchissement auto toutes les 2s
- ✅ **Visualisation riche** : intégration Plotly
- ✅ **Consommation Kafka** : lit global_metrics en live

**Notre dashboard affiche :**
1. **Métriques principales** (cartes)
   - Round actuel
   - Anomalies totales
   - Dernière mise à jour
   - Échantillons traités

2. **Graphiques**
   - Bar chart : anomalies par village/région
   - Line chart : évolution rounds (samples + anomalies)

3. **Détails**
   - Dernier round (JSON)
   - Configuration Edge nodes
   - Architecture système

**Code simplifié :**
```python
# Consommation Kafka non-bloquante
consumer.poll(timeout_ms=100)

# Affichage
st.metric("Round actuel", round_number)
fig = px.bar(df, x='village', y='anomalies')
st.plotly_chart(fig)
```

---

## 📊 PARTIE 4 : CAS D'USAGE

### Q4.1 : Décrivez le cas d'usage détection d'anomalies électriques

**Réponse :**

**Contexte :**
- **Réseau électrique rural** avec 4 villages
- **Capteurs** mesurant tension (V) et courant (I)
- **Problème** : détecter anomalies (surcharges, pannes) en temps réel

**Types d'anomalies détectées :**

| Type | Caractéristique | Cause possible |
|------|----------------|----------------|
| **Surtension** | V × 1.3 | Foudre, équipement défaillant |
| **Sous-tension** | V × 0.7 | Surcharge réseau, panne |
| **Surintensité** | I × 2.0 | Court-circuit, surcharge |
| **Power surge** | V × 1.2 + I × 1.5 | Démarrage moteurs |

**Données capteurs :**
```json
{
  "edge_id": "village_1",
  "timestamp": "2026-02-07T10:30:00Z",
  "voltage": 235.4,      // Volts
  "current": 12.3,       // Ampères
  "power": 2895.42,      // Watts = V × I
  "label": 0             // 0=normal, 1=anomalie
}
```

**Features pour ML :**
```python
V_norm = (V - 230) / 5       # Z-score normalisation
I_norm = (I - 10) / 2
P_norm = (P - 2300) / 1000
X = [V_norm, I_norm, P_norm]  # Vecteur features
```

**Pourquoi Federated Learning ici ?**
- ✅ **Privacy** : données électriques sensibles (consommation des foyers)
- ✅ **Bande passante** : villages ruraux = connexion limitée
- ✅ **Données locales** : chaque village a caractéristiques propres
- ✅ **Temps réel** : détection rapide sans aller-retour Cloud

---

### Q4.2 : Pourquoi ne pas tout faire au Cloud directement ?

**Réponse :**

**Limitations approche centralisée (tout au Cloud) :**

1. **Privacy / RGPD**
   ❌ Transfert données brutes = violation confidentialité
   ❌ Données électriques = données personnelles sensibles

2. **Bande passante**
   ❌ 4 villages × 2 msg/s × 24h = 691,200 messages/jour
   ❌ Connexion rurale limitée (< 1 Mbps)
   ❌ Coût transfert données élevé

3. **Latence**
   ❌ Round-trip Edge → Cloud → Edge = 500-1000ms
   ❌ Détection anomalie critique retardée
   ❌ Actions correctives trop lentes

4. **Dépendance réseau**
   ❌ Panne réseau = plus de détection
   ❌ Cloud down = système complet arrêté

**Avantages Federated Learning :**
- ✅ **Poids modèle << données brutes** (1 KB vs 100 KB)
- ✅ **Détection locale** = latence <100ms
- ✅ **Fonctionne offline** (modèle local)
- ✅ **Privacy-preserving** automatique

---

## ⚙️ PARTIE 5 : IMPLÉMENTATION TECHNIQUE

### Q5.1 : Comment fonctionne l'entraînement local (Edge) ?

**Réponse :**

**Workflow complet :**

```python
# 1. INITIALISATION
model = SGDClassifier(warm_start=True)
buffer = deque(maxlen=1000)

# 2. CONSOMMATION DONNÉES
for message in consumer:
    # Prétraitement
    V, I = message['voltage'], message['current']
    features = normalize([V, I, V*I])
    label = message['label']

    # Accumulation dans buffer
    buffer.append((features, label))

    # 3. ENTRAÎNEMENT (tous les 50 messages)
    if len(buffer) >= 50:
        X = np.array([f for f, l in buffer])
        y = np.array([l for f, l in buffer])

        # Entraînement incrémental
        model.partial_fit(X, y, classes=[0, 1])

        # 4. PUBLICATION POIDS (pas données!)
        weights = {
            'coef': model.coef_.tolist(),
            'intercept': model.intercept_.tolist()
        }

        producer.send('edge_weights', {
            'edge_id': 'village_1',
            'round': current_round,
            'n_samples': 50,
            'weights': weights,
            'metrics': {'accuracy': score}
        })

        buffer.clear()
        current_round += 1
```

**Points clés :**
- ✅ `warm_start=True` : garde l'état entre appels
- ✅ `partial_fit()` : entraînement incrémental
- ✅ Sérialisation poids en JSON (pas pickle pour sécurité)
- ✅ Métrique locale calculée (accuracy)

---

### Q5.2 : Comment Spark agrège au Fog ?

**Réponse :**

**Code Spark Structured Streaming :**

```python
# 1. LECTURE KAFKA
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "edge_weights") \
    .load()

# 2. PARSING JSON
edge_weights_df = kafka_df \
    .selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*", current_timestamp().alias("event_time"))

# 3. AGRÉGATION PAR RÉGION + FENÊTRE
aggregated = edge_weights_df \
    .withWatermark("event_time", "10 seconds") \
    .groupBy(
        window(col("event_time"), "30 seconds"),
        col("region")
    ) \
    .agg(
        collect_list("weights").alias("all_weights"),
        sum("n_samples").alias("total_n_samples"),
        avg("metrics.local_accuracy").alias("avg_accuracy")
    )

# 4. ÉCRITURE KAFKA
aggregated.writeStream \
    .format("kafka") \
    .option("topic", "fog_agg") \
    .start()
```

**Concepts Spark importants :**

1. **Fenêtres temporelles**
   - `window("30 seconds")` = agrège par blocs de 30s
   - Évite surcharge Cloud (pas un message par Edge)

2. **Watermarks**
   - `withWatermark("10 seconds")` = tolère 10s de retard
   - Messages tardifs encore inclus si <10s

3. **collect_list()**
   - Collecte tous les poids d'une fenêtre
   - Permet agrégation ultérieure (FedAvg)

---

### Q5.3 : Comment FedAvg est implémenté au Cloud ?

**Réponse :**

**Implémentation mathématique :**

```python
def federated_averaging(updates):
    """
    FedAvg: moyenne pondérée par n_samples

    Args:
        updates: [{
            'n_samples': 100,
            'weights': {'coef': [[...]], 'intercept': [...]}
        }, ...]

    Returns:
        {'coef': [[...]], 'intercept': [...]}
    """
    # 1. Calcul total échantillons
    total_samples = sum(u['n_samples'] for u in updates)

    # 2. Initialisation avec zéros
    coef_shape = np.array(updates[0]['weights']['coef']).shape
    avg_coef = np.zeros(coef_shape)
    avg_intercept = np.zeros(...)

    # 3. Moyenne pondérée
    for update in updates:
        weight = update['n_samples'] / total_samples
        coef = np.array(update['weights']['coef'])
        intercept = np.array(update['weights']['intercept'])

        avg_coef += weight * coef
        avg_intercept += weight * intercept

    return {
        'coef': avg_coef.tolist(),
        'intercept': avg_intercept.tolist()
    }
```

**Exemple numérique :**

```
Edge 1: n=100, coef=[1.0, 2.0]
Edge 2: n=200, coef=[2.0, 3.0]

Total samples = 300

Poids Edge 1 = 100/300 = 0.33
Poids Edge 2 = 200/300 = 0.67

avg_coef[0] = 0.33 × 1.0 + 0.67 × 2.0 = 1.67
avg_coef[1] = 0.33 × 2.0 + 0.67 × 3.0 = 2.67

Résultat: [1.67, 2.67]
```

**Workflow Cloud complet :**

```python
# 1. Buffer updates par round
round_updates = defaultdict(list)

# 2. Consommation fog_agg
for message in consumer:
    round_updates[current_round].append({
        'n_samples': message['total_n_samples'],
        'weights': message['all_weights']
    })

    # 3. Déclenchement FedAvg si assez d'updates
    if should_aggregate():
        # Appliquer FedAvg
        global_weights = federated_averaging(
            round_updates[current_round]
        )

        # 4. Publication modèle global
        producer.send('global_model', {
            'round': current_round,
            'global_weights': global_weights
        })

        # Métriques
        producer.send('global_metrics', {
            'round': current_round,
            'total_samples': sum(n_samples),
            'anomalies': sum(anomalies)
        })

        current_round += 1
```

---

## 🔍 PARTIE 6 : QUESTIONS APPROFONDIES

### Q6.1 : Comment garantir la privacy dans le système ?

**Réponse :**

**Mécanismes de préservation de la confidentialité :**

1. **Pas de données brutes transmises**
   - ❌ **Ne transite PAS** : valeurs V, I, consommation
   - ✅ **Transite** : poids modèle (coef, intercept)
   - **Ratio** : ~1 KB (poids) vs ~100 KB (données)

2. **Agrégation progressive**
   - Edge → Fog : par village
   - Fog → Cloud : par région
   - **Dilution** : impossible d'isoler un village

3. **Poids ≠ Données**
   - Poids = résumé statistique de millions de points
   - **Pas d'inversion** : retrouver données depuis poids = très difficile

**Limitations (hors scope MVP) :**

❌ **Pas implémenté :**
- **Differential Privacy** : ajout de bruit pour protection
- **Secure Aggregation** : chiffrement homomorphique
- **Byzantine robustness** : protection contre nodes malicieux

✅ **Améliorations futures :**
```python
# Differential Privacy (exemple)
def add_noise(weights, epsilon=0.1):
    noise = np.random.laplace(0, 1/epsilon, weights.shape)
    return weights + noise

# Utilisation
noisy_weights = add_noise(model.coef_, epsilon=0.1)
```

**Attaques possibles (théoriques) :**
1. **Model inversion** : retrouver données depuis poids
   - Nécessite accès multiple rounds + attaque sophistiquée
   - Mitigé par agrégation

2. **Membership inference** : savoir si donnée était dans training
   - Possible mais limité par bruit naturel

---

### Q6.2 : Comment le système gère les pannes ?

**Réponse :**

**Résilience à différents niveaux :**

**1. Niveau Kafka**
- ✅ **Persistance** : messages sur disque
- ✅ **Replication** : (production : factor=3)
- ✅ **Consumer groups** : offset tracking
- ⚠️ **Limitation MVP** : replication=1 (perte si broker down)

**2. Niveau Edge**
```python
# Retry automatique sur erreur Kafka
for attempt in range(max_retries):
    try:
        producer.send(topic, message)
        break
    except KafkaError:
        time.sleep(2 ** attempt)  # Exponential backoff
```
- ✅ **Warm start** : modèle persiste en mémoire
- ✅ **Buffer local** : continue à entraîner si Kafka down
- ❌ **Pas de persistance disque** : perte si crash (amélioration possible)

**3. Niveau Fog (Spark)**
```python
.option("checkpointLocation", "/tmp/spark-checkpoint")
```
- ✅ **Checkpointing** : état sauvegardé
- ✅ **Rejouabilité** : relit depuis dernier offset
- ✅ **Exactly-once semantics**

**4. Niveau Cloud**
- ✅ **Stateless** : pas d'état persistant nécessaire
- ✅ **Redémarrage rapide** : relit fog_agg depuis offset
- ⚠️ **Round reset** : si crash, repart à 0 (amélioration: sauver état)

**Scénarios de panne :**

| Panne | Impact | Récupération |
|-------|--------|--------------|
| Edge node down | ❌ Pas d'updates ce village | ✅ Autres continuent, FedAvg adapte |
| Fog down | ❌ Pas d'agrégation régionale | ✅ Rejoue depuis checkpoint |
| Cloud down | ❌ Pas de FedAvg global | ✅ Redémarre, relit fog_agg |
| Kafka down | ❌ Tout s'arrête | ⚠️ Replication pour éviter |

---

### Q6.3 : Quelles sont les métriques de performance ?

**Réponse :**

**Métriques système (SLA) :**

1. **Latence**
   ```
   Simulator → Edge    : < 100ms   (local Kafka)
   Edge → Fog          : < 500ms   (batch + réseau)
   Fog → Cloud         : < 1s      (fenêtre 30s)
   Cloud → Dashboard   : < 2s      (total E2E)
   ```

2. **Throughput**
   ```
   Simulator     : 8 msg/s (2 msg/s × 4 villages)
   Edge training : 1 round / 6s (50 messages)
   Fog agg       : 1 batch / 30s
   Cloud FedAvg  : 1 round / 30-60s
   ```

3. **Utilisation ressources**
   ```
   Edge node     : ~20 MB RAM, <5% CPU
   Fog (Spark)   : ~500 MB RAM, 10-20% CPU
   Cloud         : ~20 MB RAM, <5% CPU
   Kafka         : ~512 MB RAM, 5-10% CPU
   ```

**Métriques ML (qualité) :**

1. **Précision locale (Edge)**
   ```
   Round 0: ~52% (modèle aléatoire)
   Round 1: ~54%
   Round 5: ~75% (convergence)
   Round 10: ~85% (plateau)
   ```

2. **Précision globale (après FedAvg)**
   - Généralement **5-10% supérieure** aux modèles locaux
   - Bénéficie de la diversité des données

3. **Détection anomalies**
   ```
   True Positives  : anomalies correctement détectées
   False Positives : fausses alertes
   Recall          : ~80% (détecte 8/10 anomalies)
   Precision       : ~70% (7/10 alertes sont vraies)
   ```

**Commandes monitoring :**
```bash
# Latence Kafka
docker exec kafka kafka-run-class kafka.tools.JmxTool \
  --object-name kafka.network:type=RequestMetrics,name=TotalTimeMs

# Utilisation CPU/RAM
docker stats

# Logs latence
grep "latency" logs/*.log
```

---

## 🛠️ PARTIE 7 : DÉPANNAGE

### Q7.1 : Que faire si Kafka ne démarre pas ?

**Réponse :**

**Diagnostic étape par étape :**

```bash
# 1. Vérifier Docker
docker ps
# Si vide → Docker Desktop pas lancé

# 2. Vérifier logs
docker compose logs kafka
# Chercher erreurs

# 3. Vérifier ports
lsof -i :9092
# Si occupé → autre processus utilise le port

# 4. Nettoyer et redémarrer
docker compose down -v   # -v supprime volumes
docker compose up -d
sleep 30  # Attendre démarrage complet

# 5. Tester connexion
python test_kafka.py
```

**Erreurs courantes :**

| Erreur | Cause | Solution |
|--------|-------|----------|
| `Connection refused` | Kafka pas démarré | Attendre 30s supplémentaires |
| `BrokenPipeError` | Kafka encore en init | Normal, retry automatique |
| `Address already in use` | Port 9092 occupé | `lsof -i :9092` puis `kill` |
| `No space left on device` | Disque plein | Nettoyer `/var/lib/docker` |

---

### Q7.2 : Pourquoi les Edge nodes ne reçoivent rien ?

**Réponse :**

**Checklist de diagnostic :**

```bash
# 1. Simulator tourne ?
ps aux | grep simulator
# Si non → python simulator.py

# 2. Topics créés ?
python create_kafka_topics.py
# Doit afficher 6 topics OK

# 3. Messages dans sensor_data ?
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic sensor_data \
  --from-beginning \
  --max-messages 10
# Doit afficher messages JSON

# 4. Edge connecté au bon topic ?
grep "sensor_data" logs/edge_village_1.log
# Doit montrer subscription

# 5. Consumer group assigné ?
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group edge_node_village_1
# Doit montrer partitions assignées
```

**Causes fréquentes :**
- ✅ **Simulator pas lancé** → `python simulator.py`
- ✅ **Topic pas créé** → `create_kafka_topics.py`
- ✅ **Mauvais edge_id** → Vérifier `config.EDGE_IDS`
- ✅ **Kafka pas prêt** → Attendre 30s après `docker compose up`

---

### Q7.3 : Dashboard inaccessible, pourquoi ?

**Réponse :**

**Diagnostic :**

```bash
# 1. Streamlit lancé ?
ps aux | grep streamlit
# Si non → relancer

# 2. Port 8501 libre ?
lsof -i :8501
# Si occupé → tuer process

# 3. Logs Streamlit
tail -f logs/dashboard.log
# Chercher erreurs

# 4. Tester localement
curl http://localhost:8501
# Doit retourner HTML
```

**Solutions :**

```bash
# Redémarrage propre
pkill -f streamlit
source venv/bin/activate
STREAMLIT_SERVER_HEADLESS=true \
  streamlit run dashboard_app.py \
  --server.port 8501 \
  > logs/dashboard.log 2>&1 &

# Vérifier après 5s
sleep 5
curl -I http://localhost:8501
# HTTP/1.1 200 OK
```

**Configuration alternative :**
```python
# Si problème persist, modifier dashboard_app.py
if __name__ == '__main__':
    st.set_page_config(page_title="FL Dashboard")
    # Désactiver auto-refresh pour debug
    st.legacy_caching.clear_cache()
```

---

## 📝 PARTIE 8 : QUESTIONS DE SYNTHÈSE

### Q8.1 : Expliquez le flux complet d'un message de bout en bout

**Réponse :**

**Timeline complète (exemple) :**

```
T=0s : Simulator génère
───────────────────────────────────
{
  "edge_id": "village_1",
  "voltage": 235.4,
  "current": 12.3,
  "label": 0
}
→ Kafka topic: sensor_data

T=0.05s : Edge village_1 consomme
───────────────────────────────────
1. Prétraitement
   features = normalize([235.4, 12.3, 2895.42])
   = [1.08, 1.15, 0.60]  # Z-score

2. Accumulation buffer
   buffer.append((features, label=0))

3. Si len(buffer) >= 50:
   → Entraînement local
   model.partial_fit(X, y)
   accuracy = 0.52

T=6s : Edge publie poids
───────────────────────────────────
{
  "edge_id": "village_1",
  "region": "north",
  "round": 0,
  "n_samples": 50,
  "weights": {
    "coef": [[0.12, -0.34, 0.56]],
    "intercept": [0.02]
  },
  "metrics": {"accuracy": 0.52}
}
→ Kafka topic: edge_weights

T=30s : Fog agrège (fenêtre 30s)
───────────────────────────────────
Spark Structured Streaming:
- Collecte 2 updates (village_1, village_2)
- Calcule moyenne régionale
- Agrège par region="north"

{
  "region": "north",
  "all_weights": [weights_v1, weights_v2],
  "total_n_samples": 100,
  "avg_accuracy": 0.51
}
→ Kafka topic: fog_agg

T=31s : Cloud applique FedAvg
───────────────────────────────────
1. Reçoit fog_agg (north + south)
2. FedAvg:
   w_global = (100 × w_north + 100 × w_south) / 200

3. Publie modèle global:
{
  "round": 0,
  "global_weights": {
    "coef": [[0.15, -0.30, 0.50]],
    "intercept": [0.03]
  }
}
→ Kafka topics: global_model, global_metrics

T=32s : Edge reçoit modèle global
───────────────────────────────────
1. Consomme global_model
2. Met à jour modèle local:
   model.coef_ = global_weights.coef
3. Continue entraînement avec nouveau modèle

T=33s : Dashboard affiche
───────────────────────────────────
1. Consomme global_metrics
2. Update graphiques:
   - Round 0 complété
   - 100 samples
   - 10 anomalies
3. Rafraîchit UI
```

**Flux de données (taille) :**
```
Données brutes : 100 bytes × 50 = 5 KB
Poids modèle   : ~500 bytes
Réduction      : 90% (5 KB → 500 B)
```

---

### Q8.2 : Comparez cette approche à l'apprentissage centralisé classique

**Réponse :**

| Critère | **Centralisé** | **Federated Learning** (notre projet) |
|---------|---------------|----------------------------------------|
| **Données** | Toutes au Cloud | Restent locales (Edge) |
| **Privacy** | ❌ Faible (données exposées) | ✅ Forte (seuls poids partagés) |
| **Bande passante** | ❌ Élevée (toutes données transférées) | ✅ Faible (poids << données) |
| **Latence** | ❌ Haute (round-trip Cloud) | ✅ Basse (détection locale) |
| **Scalabilité** | ❌ Cloud goulot d'étranglement | ✅ Distribution calcul |
| **Offline capability** | ❌ Non (besoin Cloud) | ✅ Oui (modèle local) |
| **Convergence** | ✅ Plus rapide | ⚠️ Plus lente (communication) |
| **Complexité** | ✅ Simple | ❌ Plus complexe (orchestration) |
| **Coût** | ❌ Élevé (Cloud compute + storage) | ✅ Distribué (Edge + Cloud léger) |

**Exemple numérique (1 jour) :**

```
CENTRALISÉ:
- 4 villages × 2 msg/s × 86,400s = 691,200 messages/jour
- Taille message : 100 bytes
- Bande passante : 69 MB/jour ↑ (upload)
- Coût Cloud : compute + storage

FEDERATED LEARNING:
- Edge → Fog : 4 villages × 144 rounds/jour = 576 updates
- Taille update : 500 bytes
- Bande passante : 288 KB/jour ↑ (upload)
- Réduction : 99.6% !
- Coût Cloud : agrégation seule (léger)
```

---

### Q8.3 : Quelles améliorations pourrait-on apporter ?

**Réponse :**

**Court terme (semaines) :**

1. **Differential Privacy**
   ```python
   def privatize_weights(weights, epsilon=0.1):
       noise = np.random.laplace(0, sensitivity/epsilon)
       return weights + noise
   ```
   - Ajoute bruit mathématique pour privacy formelle

2. **Persistance modèles**
   ```python
   # Sauver modèle localement
   import joblib
   joblib.dump(model, f'models/{edge_id}_round_{round}.pkl')
   ```
   - Survit aux redémarrages

3. **Alertes temps réel**
   ```python
   if anomaly_rate > threshold:
       producer.send('alerts', {
           'edge_id': edge_id,
           'severity': 'HIGH',
           'anomaly_rate': 0.25
       })
   ```

**Moyen terme (mois) :**

4. **Modèles deep learning**
   - Remplacer SGDClassifier par LSTM/CNN
   - Détection patterns temporels complexes
   - Nécessite TensorFlow/PyTorch

5. **Compression de modèles**
   ```python
   # Quantization
   weights_int8 = (weights * 255).astype(np.int8)
   # Réduction : float32 → int8 = 4× plus petit
   ```

6. **Byzantine robustness**
   - Détecter Edge nodes malicieux
   - Rejeter updates aberrants
   - Algorithmes : Krum, Trimmed mean

**Long terme (années) :**

7. **Blockchain pour traçabilité**
   - Chaque update signée cryptographiquement
   - Audit trail immuable
   - Smart contracts pour rewards

8. **Federated Transfer Learning**
   - Pré-entraîner sur dataset public
   - Fine-tuner localement
   - Convergence plus rapide

9. **AutoML fédéré**
   - Optimisation hyper-paramètres distribuée
   - Sélection features automatique
   - Architecture search

10. **Multi-tenancy**
    - Plusieurs réseaux électriques isolés
    - Namespaces Kafka
    - FedAvg séparé par tenant

**Production-ready checklist :**
```
□ Monitoring (Prometheus + Grafana)
□ Alerting (PagerDuty)
□ CI/CD pipeline
□ Tests intégration
□ Documentation API
□ Disaster recovery plan
□ Load testing (K6/Locust)
□ Security audit
□ RGPD compliance
□ SLA définition
```

---

## 🎓 QUESTIONS BONUS (NIVEAU EXPERT)

### QB.1 : Démontrez mathématiquement la convergence de FedAvg

**Réponse :**

**Théorème (McMahan et al., 2017) :**

Sous certaines conditions, FedAvg converge vers le minimum global.

**Conditions :**
1. Fonction loss convexe : `f(αx + (1-α)y) ≤ αf(x) + (1-α)f(y)`
2. Lipschitz continuous : `|∇f(x) - ∇f(y)| ≤ L||x - y||`
3. Strong convexity : `f(y) ≥ f(x) + ∇f(x)·(y-x) + (μ/2)||y-x||²`

**Démonstration simplifiée :**

```
Soit:
- K clients
- n_k échantillons au client k
- f_k(w) loss locale du client k
- f(w) = Σ(n_k/n) f_k(w) loss globale

FedAvg à l'itération t:
w^(t+1) = Σ(n_k/n) w_k^(t+1)

où w_k^(t+1) = w_k^(t) - η∇f_k(w_k^(t))

Borne d'erreur:
E[f(w^(t))] - f(w*) ≤ C / t

où C dépend de L, μ, η

→ Convergence linéaire vers optimum !
```

**Intuition :**
- Chaque client descend localement (SGD)
- Moyenne pondérée = descente globale approximée
- Convergence garantie si learning rate bien choisi

---

### QB.2 : Comment adapter le système pour 1000 villages ?

**Réponse :**

**Modifications nécessaires :**

**1. Architecture Kafka**
```yaml
# docker-compose.yml (production)
kafka:
  replicas: 3  # 3 brokers
  environment:
    KAFKA_NUM_PARTITIONS: 100  # Plus de partitions
    KAFKA_REPLICATION_FACTOR: 3
```

**2. Consumer groups parallélisés**
```python
# Au lieu de 1 Edge par consumer group
# → 1 consumer group avec 100 consommateurs

consumers = []
for i in range(100):  # 100 workers parallèles
    consumer = KafkaConsumer(
        'sensor_data',
        group_id='edge_nodes',  # Même groupe
        # Kafka assigne automatiquement partitions
    )
    consumers.append(consumer)
```

**3. Fog: plusieurs instances Spark**
```bash
# Spark cluster avec 10 workers
spark-submit \
  --master spark://master:7077 \
  --executor-memory 4g \
  --num-executors 10 \
  fog_aggregator_spark.py
```

**4. Cloud: agrégation hiérarchique**
```
1000 villages
  → 100 régions (Fog layer 1)
    → 10 super-régions (Fog layer 2)
      → 1 Cloud (FedAvg global)
```

**5. Optimisations**
```python
# Compression poids
import zlib
compressed = zlib.compress(json.dumps(weights).encode())
# Réduction ~70%

# Sampling
# Au lieu d'agréger 1000 villages chaque round
# → Sélectionner aléatoirement 100 (10%)
selected = random.sample(villages, k=100)
```

**Scalabilité estimée :**

| Métrique | 4 villages | 1000 villages | Facteur |
|----------|-----------|---------------|---------|
| Messages/s | 8 | 2,000 | 250× |
| Bande passante | 1 KB/s | 250 KB/s | 250× |
| Latence round | 30s | 60s | 2× |
| RAM Fog | 500 MB | 8 GB | 16× |
| Coût Cloud | $10/mois | $500/mois | 50× |

**Goulots d'étranglement potentiels :**
- ❌ Kafka: >10,000 msg/s → besoin cluster
- ❌ Spark: > 10 GB données → besoin plus RAM
- ❌ Réseau: > 1 Gbps → besoin fiber

---

## ✅ CHECKLIST DE PRÉPARATION EXAMEN

**Maîtrise des concepts** :
- [ ] Je peux expliquer Federated Learning en 1 minute
- [ ] Je comprends Edge-Fog-Cloud et pourquoi 3 couches
- [ ] Je sais expliquer FedAvg mathématiquement
- [ ] Je connais les avantages/inconvénients vs centralisé

**Maîtrise technique** :
- [ ] Je sais pourquoi Kafka (vs autres message brokers)
- [ ] Je comprends Spark Structured Streaming
- [ ] Je connais le rôle de chaque composant Python
- [ ] Je peux tracer le flux d'un message de bout en bout

**Maîtrise implémentation** :
- [ ] Je sais comment fonctionne l'entraînement Edge
- [ ] Je comprends l'agrégation Fog (fenêtres Spark)
- [ ] Je peux expliquer le code FedAvg
- [ ] Je sais résoudre les problèmes courants

**Questions typiques examen** :
- [ ] "Expliquez l'architecture" → Schéma 3 couches + rôles
- [ ] "Pourquoi pas tout au Cloud ?" → Privacy, bande passante, latence
- [ ] "Comment FedAvg fonctionne ?" → Formule mathématique + exemple
- [ ] "Quel est le rôle de Kafka ?" → Décou couplage, streaming, scalabilité
- [ ] "Comment gérer 1000 villages ?" → Partitions, clustering, hiérarchie

---

## 📖 RESSOURCES COMPLÉMENTAIRES

**Papers académiques :**
1. McMahan et al. (2017) - "Communication-Efficient Learning of Deep Networks from Decentralized Data"
2. Bonawitz et al. (2019) - "Towards Federated Learning at Scale"
3. Kairouz et al. (2021) - "Advances and Open Problems in Federated Learning"

**Documentation technique :**
- Apache Kafka: https://kafka.apache.org/documentation/
- Apache Spark: https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- scikit-learn SGD: https://scikit-learn.org/stable/modules/sgd.html

**Fichiers du projet à réviser :**
- `ARCHITECTURE.md` - Architecture détaillée
- `CONFIGURATION.md` - Paramètres techniques
- `PROJECT_SUMMARY.md` - Vue d'ensemble
- `SYSTEM_STATUS.md` - État actuel du système

---

**Bon courage pour l'examen ! 🎓**

*Ce document couvre tous les aspects du projet. Révisez chaque partie et assurez-vous de pouvoir répondre aux questions sans regarder les réponses.*
