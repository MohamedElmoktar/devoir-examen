#!/bin/bash
# Script d'exécution des tests
# Usage: ./run_tests.sh

set -e

echo "🧪 Exécution des tests unitaires..."

# Activer venv si nécessaire
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Activation de l'environnement virtuel..."
    source venv/bin/activate
fi

# Installer pytest si nécessaire
pip install pytest pytest-cov pytest-mock > /dev/null 2>&1 || true

# Lancer les tests avec couverture
echo ""
echo "Running tests with coverage..."
pytest test_components.py -v --cov=. --cov-report=term-missing --cov-report=html

echo ""
echo "✅ Tests terminés !"
echo ""
echo "📊 Rapport de couverture HTML généré dans : htmlcov/index.html"
echo "   Ouvrez avec : open htmlcov/index.html"
