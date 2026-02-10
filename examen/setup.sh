#!/bin/bash
# Script d'installation et configuration initiale
# Usage: ./setup.sh

set -e

echo "🔧 Configuration du projet Federated Learning"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python $PYTHON_VERSION détecté"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi
echo "✓ Docker détecté"

# Vérifier Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi
echo "✓ Docker Compose détecté"

# Vérifier Spark
if ! command -v spark-submit &> /dev/null; then
    echo "⚠️  Spark n'est pas installé ou pas dans le PATH"
    echo "   Installez Spark : https://spark.apache.org/downloads.html"
    echo "   Ou via Homebrew (Mac) : brew install apache-spark"
    exit 1
fi
echo "✓ Spark détecté"

# Créer l'environnement virtuel
if [ ! -d "venv" ]; then
    echo ""
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
    echo "✓ Environnement virtuel créé"
else
    echo "✓ Environnement virtuel existe déjà"
fi

# Activer venv
source venv/bin/activate

# Installer les dépendances
echo ""
echo "Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dépendances installées"

# Créer le dossier logs
mkdir -p logs
echo "✓ Dossier logs créé"

# Rendre les scripts exécutables
chmod +x start_all.sh stop_all.sh setup.sh
echo "✓ Scripts rendus exécutables"

echo ""
echo "✅ Configuration terminée !"
echo ""
echo "Prochaines étapes :"
echo "  1. Activez l'environnement virtuel : source venv/bin/activate"
echo "  2. Démarrez Kafka : docker compose up -d"
echo "  3. Lancez les composants (voir README.md)"
echo "  Ou utilisez : ./start_all.sh"
