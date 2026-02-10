"""
Dashboard Streamlit: Visualisation temps réel des métriques Federated Learning
Affiche anomalies, rounds, métriques par edge/région
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from collections import deque
from utils.kafka_utils import KafkaConsumerWrapper
import config

st.set_page_config(
    page_title="Federated Learning Dashboard",
    page_icon="⚡",
    layout="wide"
)


class FederatedDashboard:
    """Dashboard Streamlit pour monitoring temps réel"""

    def __init__(self):
        # Buffers de données
        if 'metrics_history' not in st.session_state:
            st.session_state.metrics_history = deque(maxlen=100)
        if 'anomaly_counts' not in st.session_state:
            st.session_state.anomaly_counts = {edge_id: 0 for edge_id in config.EDGE_IDS}
        if 'current_round' not in st.session_state:
            st.session_state.current_round = 0
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()

        self.consumer = None

    def connect_kafka(self):
        """Initialise le consumer Kafka"""
        try:
            self.consumer = KafkaConsumerWrapper(
                topics=[
                    config.KAFKA_TOPICS['global_metrics'],
                    config.KAFKA_TOPICS['sensor_data']
                ],
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                group_id='dashboard',
                auto_offset_reset='latest'
            )
            return True
        except Exception as e:
            st.error(f"❌ Erreur connexion Kafka: {e}")
            return False

    def fetch_latest_data(self):
        """Récupère les dernières données depuis Kafka (non-bloquant)"""
        if not self.consumer:
            return

        try:
            # Poll non-bloquant
            self.consumer.consumer.poll(timeout_ms=100, max_records=10)
            for message in self.consumer.consumer:
                self.process_message(message.value)

                # Limite pour ne pas bloquer le dashboard
                if len(st.session_state.metrics_history) > 0:
                    break
        except StopIteration:
            pass
        except Exception as e:
            st.warning(f"Erreur fetch data: {e}")

    def process_message(self, message: dict):
        """Traite un message Kafka"""
        # Métriques globales
        if 'round' in message and 'participating_regions' in message:
            st.session_state.current_round = message['round']
            st.session_state.metrics_history.append({
                'timestamp': datetime.fromisoformat(message['timestamp']),
                'round': message['round'],
                'total_samples': message['total_samples'],
                'anomalies': message.get('anomalies_detected', 0),
                'num_updates': message['num_updates']
            })
            st.session_state.last_update = datetime.now()

        # Données capteurs (pour comptage anomalies)
        elif 'edge_id' in message and 'label' in message:
            if message['label'] == 1:
                edge_id = message['edge_id']
                if edge_id in st.session_state.anomaly_counts:
                    st.session_state.anomaly_counts[edge_id] += 1

    def render_header(self):
        """Affiche l'en-tête du dashboard"""
        st.title("⚡ Federated Learning Dashboard - Réseau Électrique Rural")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Round actuel",
                f"#{st.session_state.current_round}",
                delta=None
            )

        with col2:
            total_anomalies = sum(st.session_state.anomaly_counts.values())
            st.metric(
                "Anomalies totales",
                total_anomalies,
                delta=None
            )

        with col3:
            last_update_str = st.session_state.last_update.strftime("%H:%M:%S")
            st.metric(
                "Dernière MAJ",
                last_update_str,
                delta=None
            )

        with col4:
            if st.session_state.metrics_history:
                total_samples = st.session_state.metrics_history[-1]['total_samples']
                st.metric(
                    "Échantillons traités",
                    f"{total_samples:,}",
                    delta=None
                )

    def render_anomaly_chart(self):
        """Graphique anomalies par village"""
        st.subheader("🔴 Anomalies détectées par village")

        df = pd.DataFrame([
            {'Village': edge_id, 'Anomalies': count, 'Région': config.EDGE_REGIONS.get(edge_id, 'unknown')}
            for edge_id, count in st.session_state.anomaly_counts.items()
        ])

        fig = px.bar(
            df,
            x='Village',
            y='Anomalies',
            color='Région',
            title='Distribution des anomalies',
            color_discrete_map={'north': '#FF6B6B', 'south': '#4ECDC4'}
        )
        st.plotly_chart(fig, use_container_width=True)

    def render_rounds_timeline(self):
        """Timeline des rounds FedAvg"""
        st.subheader("📊 Évolution par round")

        if not st.session_state.metrics_history:
            st.info("En attente de données...")
            return

        df = pd.DataFrame(st.session_state.metrics_history)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['round'],
            y=df['total_samples'],
            mode='lines+markers',
            name='Échantillons',
            line=dict(color='#4ECDC4', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=df['round'],
            y=df['anomalies'],
            mode='lines+markers',
            name='Anomalies',
            line=dict(color='#FF6B6B', width=2),
            yaxis='y2'
        ))

        fig.update_layout(
            title='Métriques globales par round',
            xaxis_title='Round',
            yaxis_title='Échantillons',
            yaxis2=dict(
                title='Anomalies',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

    def render_real_time_stats(self):
        """Statistiques temps réel"""
        st.subheader("📈 Statistiques temps réel")

        col1, col2 = st.columns(2)

        with col1:
            if st.session_state.metrics_history:
                latest = st.session_state.metrics_history[-1]

                st.write("**Dernier round:**")
                st.json({
                    'Round': latest['round'],
                    'Échantillons': latest['total_samples'],
                    'Anomalies': latest['anomalies'],
                    'Updates agrégées': latest['num_updates']
                })

        with col2:
            st.write("**Configuration Edge:**")
            for edge_id in config.EDGE_IDS:
                region = config.EDGE_REGIONS[edge_id]
                anomalies = st.session_state.anomaly_counts[edge_id]
                st.write(f"• {edge_id} ({region}): {anomalies} anomalies")

    def render_architecture_diagram(self):
        """Diagramme d'architecture"""
        with st.expander("📐 Architecture Edge-Fog-Cloud"):
            st.markdown("""
            ### Architecture Federated Learning

            **Edge Layer (Villages):**
            - Capteurs de tension/courant
            - Entraînement local (SGDClassifier)
            - Publie uniquement les poids du modèle

            **Fog Layer (Régions):**
            - Agrégation régionale (Spark Streaming)
            - Fenêtres temporelles de 30s
            - Pré-agrégation avant Cloud

            **Cloud Layer:**
            - Algorithme FedAvg (moyenne pondérée)
            - Génération modèle global
            - Distribution aux Edge nodes

            **Privacy-preserving:**
            - ✅ Pas de données brutes transmises
            - ✅ Uniquement les poids de modèles
            - ✅ Agrégation sécurisée
            """)

    def run(self):
        """Boucle principale du dashboard"""
        if not self.connect_kafka():
            st.error("Impossible de se connecter à Kafka. Vérifiez que le serveur est démarré.")
            return

        # Auto-refresh
        placeholder = st.empty()

        while True:
            with placeholder.container():
                self.fetch_latest_data()

                self.render_header()
                st.divider()

                col1, col2 = st.columns(2)

                with col1:
                    self.render_anomaly_chart()

                with col2:
                    self.render_rounds_timeline()

                st.divider()
                self.render_real_time_stats()

                self.render_architecture_diagram()

                st.caption(f"🔄 Rafraîchissement automatique toutes les 2 secondes • {datetime.now().strftime('%H:%M:%S')}")

            time.sleep(2)


def main():
    dashboard = FederatedDashboard()
    dashboard.run()


if __name__ == '__main__':
    main()
