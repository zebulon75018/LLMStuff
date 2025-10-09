"""
Application Flask ChatBot avec authentification et LangChain/Ollama
Installation requise:
pip install flask flask-sqlalchemy werkzeug langchain langchain-community
pip install pypdf chromadb

Structure du projet:
project/
├── app.py
├── templates/
│   └── index.html
├── uploads/
└── chatbot.db (créé automatiquement)
"""

from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Configuration LangChain/Ollama
try:
    from langchain_community.llms import Ollama
    from langchain.chains import ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️  LangChain non disponible. Installation: pip install langchain langchain-community pypdf chromadb")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre-cle-secrete-super-securisee-changez-moi'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============= MODÈLES DE BASE DE DONNÉES =============

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============= CONFIGURATION LANGCHAIN =============

qa_chain = None

def init_langchain():
    """Initialise LangChain avec Ollama"""
    global qa_chain
    if not LANGCHAIN_AVAILABLE:
        return
    try:
        llm = Ollama(model="llama3", temperature=0.7)
        embeddings = OllamaEmbeddings(model="llama3")
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        qa_chain = {"llm": llm, "memory": memory, "embeddings": embeddings}
        print("✅ LangChain initialisé avec succès")
    except Exception as e:
        print(f"❌ Erreur initialisation LangChain: {e}")

def process_pdf(filepath, user_id):
    """Traite un PDF et crée un vectorstore"""
    if not LANGCHAIN_AVAILABLE:
        return False
    try:
        loader = PyPDFLoader(filepath)
        pages = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(pages)
        
        embeddings = qa_chain["embeddings"]
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=f"./chroma_db_{user_id}"
        )
        print(f"✅ PDF traité avec succès: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Erreur traitement PDF: {e}")
        return False

def get_ai_response(message, user_id):
    """Génère une réponse IA avec LangChain/Ollama"""
    if not LANGCHAIN_AVAILABLE:
        return "⚠️ LangChain n'est pas configuré. Veuillez installer les dépendances requises."
    
    try:
        llm = qa_chain["llm"]
        response = llm.invoke(message)
        return response
    except Exception as e:
        return f"❌ Erreur lors de la génération de la réponse: {str(e)}"

# ============= ROUTES =============

@app.route('/')
def index():
    """Page principale"""
    return render_template('index.html')

@app.route('/api/check-session')
def check_session():
    """Vérifie si l'utilisateur est connecté"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return jsonify({'logged_in': True, 'username': user.username})
    return jsonify({'logged_in': False})

@app.route('/api/register', methods=['POST'])
def register():
    """Inscription d'un nouvel utilisateur"""
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Validation
    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'Tous les champs sont requis'})

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email déjà utilisé'})
    
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Nom d\'utilisateur déjà pris'})

    # Créer l'utilisateur
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    
    db.session.add(new_user)
    db.session.commit()
    
    # Connexion automatique
    session['user_id'] = new_user.id
    return jsonify({'success': True, 'username': username})

@app.route('/api/login', methods=['POST'])
def login():
    """Connexion d'un utilisateur"""
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        return jsonify({'success': True, 'username': user.username})
    
    return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect'})

@app.route('/api/logout', methods=['POST'])
def logout():
    """Déconnexion de l'utilisateur"""
    session.pop('user_id', None)
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Envoie un message et reçoit une réponse IA"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non authentifié'})

    data = request.json
    message = data.get('message')
    user_id = session['user_id']

    if not message:
        return jsonify({'success': False, 'message': 'Message vide'})

    # Obtenir la réponse de l'IA
    ai_response = get_ai_response(message, user_id)

    # Sauvegarder dans la base de données
    chat_message = ChatMessage(user_id=user_id, message=message, response=ai_response)
    db.session.add(chat_message)
    db.session.commit()

    return jsonify({'success': True, 'response': ai_response})

@app.route('/api/history')
def history():
    """Récupère l'historique des conversations"""
    if 'user_id' not in session:
        return jsonify({'success': False})

    messages = ChatMessage.query.filter_by(
        user_id=session['user_id']
    ).order_by(ChatMessage.timestamp).limit(50).all()
    
    return jsonify({
        'success': True,
        'messages': [
            {'message': m.message, 'response': m.response} 
            for m in messages
        ]
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload un fichier PDF"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non authentifié'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'})

    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        user_id = session['user_id']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{user_id}_{filename}")
        file.save(filepath)

        # Traiter le PDF avec LangChain
        process_pdf(filepath, user_id)

        # Sauvegarder dans la BDD
        uploaded_file = UploadedFile(user_id=user_id, filename=filename, filepath=filepath)
        db.session.add(uploaded_file)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Fichier uploadé avec succès'})

    return jsonify({'success': False, 'message': 'Format de fichier invalide (PDF uniquement)'})

@app.route('/api/files')
def get_files():
    """Récupère la liste des fichiers uploadés"""
    if 'user_id' not in session:
        return jsonify({'success': False})

    files = UploadedFile.query.filter_by(
        user_id=session['user_id']
    ).order_by(UploadedFile.uploaded_at.desc()).all()
    
    return jsonify({
        'success': True,
        'files': [
            {
                'filename': f.filename, 
                'uploaded_at': f.uploaded_at.isoformat()
            } 
            for f in files
        ]
    })

# ============= DÉMARRAGE DE L'APPLICATION =============

if __name__ == '__main__':
    with app.app_context():
        # Créer toutes les tables
        db.create_all()
        print("✅ Base de données initialisée")
        
        # Initialiser LangChain
        init_langchain()
    
    print("\n" + "="*50)
    print("🚀 Application ChatBot démarrée !")
    print("📍 URL: http://localhost:5000")
    print("="*50)
    print("\n⚠️  Assurez-vous qu'Ollama est en cours d'exécution:")
    print("   1. Télécharger Ollama: https://ollama.ai")
    print("   2. Lancer: ollama pull llama2")
    print("   3. Vérifier: ollama list\n")
    
    app.run(debug=True, port=5005, host='0.0.0.0')
