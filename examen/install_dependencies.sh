#!/bin/bash
# Script d'installation des dépendances (version simplifiée)

set -e

echo "📦 Installation des dépendances Python..."

# Activer venv
if [ -z "$VIRTUAL_ENV" ]; then
    source venv/bin/activate
fi

echo "1/3 Installation des packages de base..."
pip install kafka-python numpy scikit-learn pandas -q

echo "2/3 Installation de PySpark (cela peut prendre du temps)..."
pip install pyspark -q || {
    echo "⚠️  PySpark installation échouée. Tentative avec --no-cache-dir..."
    pip install --no-cache-dir pyspark
}

echo "3/3 Installation des packages de visualisation et test..."
pip install streamlit plotly python-json-logger pytest pytest-cov pytest-mock python-dotenv -q

echo ""
echo "✅ Installation terminée !"
echo ""
echo "Packages installés:"
pip list | grep -E "(kafka|numpy|scikit|pandas|pyspark|streamlit|plotly|pytest)"
