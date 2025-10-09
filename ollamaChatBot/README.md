
## ollamaChatBot
![OllamaSimpleGui](https://github.com/zebulon75018/LLMStuff/blob/main/img/chatbot.png?raw=true)


# 🤖 ChatBot AI - Flask + LangChain + Ollama

Application web de chatbot avec authentification, upload de PDFs et intelligence artificielle via LangChain et Ollama.

## 📁 Structure du Projet

```
projet-chatbot/
├── app.py                  # Application Flask principale
├── templates/
│   └── index.html         # Template HTML avec Jinja2
├── uploads/               # Dossier pour les PDFs (créé automatiquement)
├── chatbot.db            # Base de données SQLite (créée automatiquement)
└── chroma_db_*/          # Bases vectorielles (créées automatiquement)
```

## 🚀 Installation

### 1. Prérequis

- Python 3.8+
- Ollama installé sur votre machine

### 2. Installation d'Ollama

```bash
# Télécharger depuis https://ollama.ai
# Puis installer le modèle llama2
ollama pull llama2

# Vérifier l'installation
ollama list
```

### 3. Installation des dépendances Python

```bash
# Créer un environnement virtuel (recommandé)
python -m venv venv

# Activer l'environnement
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer les dépendances
pip install flask flask-sqlalchemy werkzeug
pip install langchain langchain-community
pip install pypdf chromadb
```

### 4. Structure des fichiers

Créez la structure suivante :

```bash
mkdir projet-chatbot
cd projet-chatbot

# Créer le dossier templates
mkdir templates

# Placer les fichiers :
# - app.py à la racine
# - index.html dans templates/
```

### 5. Lancer l'application

```bash
python app.py
```

L'application sera accessible sur : **http://localhost:5000**

## ✨ Fonctionnalités

### 🔐 Authentification
- Inscription avec email, username et mot de passe
- Connexion sécurisée (mots de passe hashés)
- Sessions Flask
- Déconnexion

### 💬 Chatbot
- Interface de chat moderne et responsive
- Messages utilisateur affichés à droite
- Réponses IA affichées à gauche
- Historique des conversations sauvegardé
- Support de la touche Entrée pour envoyer

### 📄 Upload de PDFs
- Upload de fichiers PDF
- Traitement automatique avec LangChain
- Création de vectorstore avec ChromaDB
- Liste des fichiers uploadés

### 🎨 Design
- Interface moderne avec gradients
- Animations fluides
- Glassmorphism
- Design responsive
- Scrollbar personnalisée

## 🗄️ Base de Données

L'application utilise SQLite avec 3 tables :

1. **User** : Utilisateurs (id, username, email, password, created_at)
2. **ChatMessage** : Historique des messages (id, user_id, message, response, timestamp)
3. **UploadedFile** : Fichiers uploadés (id, user_id, filename, filepath, uploaded_at)

## 🔧 Configuration

Dans `app.py`, vous pouvez modifier :

```python
# Clé secrète (IMPORTANT : changez-la en production)
app.config['SECRET_KEY'] = 'votre-cle-secrete-super-securisee'

# Taille maximale des fichiers (16MB par défaut)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Port de l'application
app.run(debug=True, port=5000)
```

## 📡 API Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Page principale |
| GET | `/api/check-session` | Vérifier la session |
| POST | `/api/register` | Inscription |
| POST | `/api/login` | Connexion |
| POST | `/api/logout` | Déconnexion |
| POST | `/api/chat` | Envoyer un message |
| GET | `/api/history` | Récupérer l'historique |
| POST | `/api/upload` | Upload un PDF |
| GET | `/api/files` | Liste des fichiers |

## 🛠️ Technologies Utilisées

- **Backend** : Flask, SQLAlchemy
- **IA** : LangChain, Ollama (llama2)
- **Vectorstore** : ChromaDB
- **PDF** : PyPDF
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **Template** : Jinja2

## ⚠️ Dépannage

### Erreur : "LangChain non disponible"
```bash
pip install langchain langchain-community pypdf chromadb
```

### Erreur : "Ollama not running"
```bash
# Vérifier qu'Ollama est lancé
ollama list
# Si nécessaire, télécharger le modèle
ollama pull llama2
```

### Erreur : "Port 5000 already in use"
Modifiez le port dans `app.py` :
```python
app.run(debug=True, port=5001)
```

## 🔒 Sécurité

- Mots de passe hashés avec Werkzeug
- Sessions sécurisées Flask
- Validation des fichiers PDF
- Noms de fichiers sécurisés (secure_filename)
- Limite de taille des uploads

## 📝 Notes

- L'application crée automatiquement la base de données au premier lancement
- Les fichiers PDF sont stockés dans le dossier `uploads/`
- Les vectorstores sont stockés dans `chroma_db_[user_id]/`
- En mode debug, l'application se recharge automatiquement à chaque modification

## 🚀 Améliorations Possibles

- [ ] Support de plusieurs modèles Ollama
- [ ] Export de conversations en PDF
- [ ] Recherche dans l'historique
- [ ] Thème sombre/clair
- [ ] Support multilingue
- [ ] API RESTful complète
- [ ] Tests unitaires
- [ ] Déploiement Docker

## 📄 Licence

Ce projet est libre d'utilisation.

---

**Développé avec ❤️ et IA**
