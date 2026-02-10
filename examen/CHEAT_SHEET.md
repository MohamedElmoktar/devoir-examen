# 🎯 Aide-mémoire Rapide - Federated Learning

Guide de révision rapide pour l'examen (1 page)

---

## 📌 DÉFINITIONS CLÉS

**Federated Learning**
- Entraînement distribué sans centraliser les données
- Seuls les poids du modèle sont partagés
- Privacy-preserving par design

**Edge-Fog-Cloud**
- **Edge** : Périphérie (capteurs, IoT) - faible latence, ressources limitées
- **Fog** : Intermédiaire (serveurs régionaux) - pré-traitement, agrégation
- **Cloud** : Central (datacenters) - ressources illimitées, haute latence

**FedAvg (Federated Averaging)**
```
w_global = Σ(n_i × w_i) / Σ(n_i)
```
Moyenne pondérée des poids par nombre d'échantillons

---

## 🏗️ ARCHITECTURE PROJET

```
Simulator → sensor_data → Edge (4 villages)
                            ↓
                        edge_weights → Fog (Spark)
                                        ↓
                                    fog_agg → Cloud (FedAvg)
                                                ↓
                                    global_model + global_metrics → Dashboard
```

**Composants :**
- `simulator.py` : Génère données V, I + anomalies
- `edge_node.py` : Entraîne SGDClassifier localement
- `fog_aggregator_spark.py` : Agrège par région (Spark Streaming)
- `cloud_fedavg.py` : Applique FedAvg global
- `dashboard_app.py` : Visualisation Streamlit

---

## 🔑 TECHNOLOGIES

| Techno | Rôle | Pourquoi |
|--------|------|----------|
| **Kafka** | Message broker | Streaming temps réel, scalable |
| **Spark** | Fog aggregation | Fenêtres temporelles, distribué |
| **SGDClassifier** | ML Edge | Incrémental, léger, FedAvg-compatible |
| **Streamlit** | Dashboard | Rapide, Python, temps réel |

---

## 📊 TOPICS KAFKA

| Topic | Contenu | Flux |
|-------|---------|------|
| `sensor_data` | {V, I, P, label} | Simulator → Edge |
| `edge_weights` | {weights, n_samples} | Edge → Fog |
| `fog_agg` | {région, weights agrégés} | Fog → Cloud |
| `global_model` | {global_weights, round} | Cloud → Edge |
| `global_metrics` | {samples, anomalies, round} | Cloud → Dashboard |

---

## 🧮 FORMULES IMPORTANTES

**Normalisation (Z-score)**
```
X_norm = (X - μ) / σ
```

**SGD Update**
```
w_new = w_old - η × ∇L(w)
```

**FedAvg**
```
w_global = (n₁w₁ + n₂w₂ + ... + nₖwₖ) / (n₁ + n₂ + ... + nₖ)
```

**Accuracy**
```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
```

---

## ⚡ FLUX DE DONNÉES

**Timeline type :**
```
T=0s   : Simulator génère {V=235, I=12, label=0}
T=0.1s : Edge normalise + accumule buffer
T=6s   : Edge entraîne (50 samples) → publie poids
T=30s  : Fog agrège fenêtre 30s → publie
T=31s  : Cloud FedAvg → publie global_model
T=32s  : Edge reçoit global_model → update local
T=33s  : Dashboard affiche métriques
```

**Taille données :**
```
Données brutes : 5 KB (50 messages)
Poids modèle   : 500 bytes
Réduction      : 90%
```

---

## 🔍 AVANTAGES FL vs CENTRALISÉ

| Critère | Centralisé | Federated |
|---------|-----------|-----------|
| **Privacy** | ❌ Faible | ✅ Forte |
| **Bande passante** | ❌ Haute | ✅ Basse |
| **Latence** | ❌ Haute | ✅ Basse |
| **Offline** | ❌ Non | ✅ Oui |
| **Complexité** | ✅ Simple | ❌ Complexe |

---

## 🛠️ COMMANDES ESSENTIELLES

**Démarrage**
```bash
docker compose up -d           # Kafka
python create_kafka_topics.py  # Topics
./start_all.sh                 # Tous composants
```

**Monitoring**
```bash
tail -f logs/*.log             # Logs temps réel
docker compose ps              # État containers
ps aux | grep python           # Processus Python
```

**Tests**
```bash
pytest test_components.py -v   # Tests unitaires
python test_kafka.py           # Test Kafka
```

**Interfaces**
```
Dashboard : http://localhost:8501
Kafka UI  : http://localhost:8080
```

---

## 🐛 DÉPANNAGE EXPRESS

**Kafka down**
```bash
docker compose down -v && docker compose up -d && sleep 30
```

**Edge pas de data**
```bash
python create_kafka_topics.py
ps aux | grep simulator  # Vérifier simulator
```

**Dashboard inaccessible**
```bash
pkill -f streamlit
STREAMLIT_SERVER_HEADLESS=true streamlit run dashboard_app.py &
```

---

## 💡 POINTS CLÉS EXAMEN

**À savoir absolument :**
1. ✅ FedAvg = moyenne pondérée par n_samples
2. ✅ Privacy = poids partagés, pas données
3. ✅ Edge-Fog-Cloud = 3 couches hiérarchiques
4. ✅ Kafka = streaming décentralisé
5. ✅ Spark = fenêtres temporelles + distribution

**Questions pièges :**
- ❓ "Pourquoi pas tout au Cloud ?" → Privacy + bande passante
- ❓ "FedAvg vs moyenne simple ?" → Pondération par n_samples
- ❓ "Rôle du Fog ?" → Agrégation régionale, réduit trafic Cloud
- ❓ "SGD vs batch GD ?" → Incrémental = adapté Edge streaming

**Schéma à savoir dessiner :**
```
    Cloud (FedAvg)
       ↑
    Fog (Spark)
     ↑   ↑
   Edge Edge
    ↑     ↑
  Sensor Sensor
```

---

## 📈 MÉTRIQUES PROJET

**Performance :**
- Latence E2E : <2s
- Throughput : 8 msg/s
- Précision : ~85% (Round 10)

**Scalabilité :**
- 4 villages (actuel)
- → 1000 villages (partitions Kafka + Spark cluster)

**Ressources :**
- Edge : ~20 MB RAM
- Fog : ~500 MB RAM
- Cloud : ~20 MB RAM

---

## 🎓 CHECKLIST AVANT EXAMEN

Êtes-vous capable de :
- [ ] Expliquer FL en 30 secondes ?
- [ ] Dessiner l'architecture Edge-Fog-Cloud ?
- [ ] Écrire la formule FedAvg ?
- [ ] Lister 3 avantages FL vs centralisé ?
- [ ] Expliquer le rôle de chaque topic Kafka ?
- [ ] Décrire le flux d'un message de bout en bout ?
- [ ] Justifier le choix de Spark au Fog ?
- [ ] Résoudre "Kafka ne démarre pas" ?

---

**Si oui à tout → Vous êtes prêt ! 🎉**

*Révisez EXAM_PREPARATION.md pour détails complets*
