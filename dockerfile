# Étape 1: Choisir une image de base
FROM python:3.9-slim as builder

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Étape 2: Installer les dépendances
# Copier seulement les fichiers nécessaires pour l'installation des dépendances
# afin d'éviter de reconstruire toute l'image à chaque modification du code source
COPY requirements.txt .

# Installer les dépendances dans une couche distincte pour la réutilisation du cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Étape 3: Copier le reste des fichiers de l'application
COPY . .

# Étape 4: Exécuter l'application
# Utiliser un utilisateur non-root pour des raisons de sécurité
RUN useradd appuser && chown -R appuser /app
USER appuser

# Définir la commande pour lancer l'application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]