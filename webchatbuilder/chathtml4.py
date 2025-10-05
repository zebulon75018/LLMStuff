import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QComboBox, 
                             QLabel, QStatusBar, QTabWidget, QPlainTextEdit, QTextEdit)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QUrl, QObject, pyqtSlot
from PyQt5.QtGui import QFont, QTextCursor
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks.base import BaseCallbackHandler
from datetime import datetime
import re


class QtLogHandler(BaseCallbackHandler):
    """Callback handler pour capturer les logs de Langchain et les envoyer à Qt"""
    
    def __init__(self, signal):
        self.log_signal = signal
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Appelé quand le LLM commence"""
        self.log_signal.emit("INFO", "🚀 Démarrage du LLM")
        self.log_signal.emit("DEBUG", f"Modèle: {serialized.get('id', ['N/A'])}")
        self.log_signal.emit("DEBUG", f"Nombre de prompts: {len(prompts)}")
        for i, prompt in enumerate(prompts):
            self.log_signal.emit("PROMPT", f"Prompt #{i+1}:\n{prompt}\n{'-'*60}")
    
    def on_llm_end(self, response, **kwargs):
        """Appelé quand le LLM termine"""
        self.log_signal.emit("INFO", "✅ LLM terminé avec succès")
        if hasattr(response, 'generations'):
            for i, gen in enumerate(response.generations):
                if gen:
                    text = gen[0].text[:200] + "..." if len(gen[0].text) > 200 else gen[0].text
                    self.log_signal.emit("RESPONSE", f"Réponse #{i+1}:\n{text}\n{'-'*60}")
    
    def on_llm_error(self, error, **kwargs):
        """Appelé en cas d'erreur du LLM"""
        self.log_signal.emit("ERROR", f"❌ Erreur LLM: {str(error)}")
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        """Appelé quand une chaîne démarre"""
        self.log_signal.emit("INFO", "🔗 Démarrage de la chaîne Langchain")
        self.log_signal.emit("DEBUG", f"Inputs: {inputs}")
    
    def on_chain_end(self, outputs, **kwargs):
        """Appelé quand une chaîne se termine"""
        self.log_signal.emit("INFO", "✅ Chaîne terminée")
        self.log_signal.emit("DEBUG", f"Outputs clés: {list(outputs.keys()) if isinstance(outputs, dict) else 'N/A'}")
    
    def on_chain_error(self, error, **kwargs):
        """Appelé en cas d'erreur de chaîne"""
        self.log_signal.emit("ERROR", f"❌ Erreur de chaîne: {str(error)}")
    
    def on_text(self, text, **kwargs):
        """Appelé pour tout texte généré"""
        if text.strip():
            self.log_signal.emit("TEXT", f"📝 Texte: {text[:100]}...")


class WebEnginePage(QWebEnginePage):
    """Page personnalisée pour capturer les logs console JavaScript"""
    
    def __init__(self, parent=None, log_callback=None):
        super().__init__(parent)
        self.log_callback = log_callback
        
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Capture les messages console.log de JavaScript"""
        level_names = {
            QWebEnginePage.InfoMessageLevel: "JS-INFO",
            QWebEnginePage.WarningMessageLevel: "JS-WARNING",
            QWebEnginePage.ErrorMessageLevel: "JS-ERROR"
        }
        level_name = level_names.get(level, "JS-INFO")
        
        log_msg = f"[Line {lineNumber}] {message}"
        if sourceID:
            log_msg += f" (Source: {sourceID})"
            
        if self.log_callback:
            self.log_callback(level_name, log_msg)


class WebBridge(QObject):
    """Bridge pour communication Python <-> JavaScript"""
    
    messageFromJS = pyqtSignal(str)
    
    @pyqtSlot(str)
    def sendToPython(self, message):
        """Appelé depuis JavaScript pour envoyer un message à Python"""
        self.messageFromJS.emit(message)
    
    @pyqtSlot(str, result=str)
    def echo(self, message):
        """Echo pour tester la communication JS <-> Python"""
        return f"Python reçu: {message}"


class LangchainWorker(QThread):
    """Thread worker pour exécuter Langchain sans bloquer l'UI"""
    finished = pyqtSignal(str, str)  # Retourne (html, timestamp)
    error = pyqtSignal(str)
    log_signal = pyqtSignal(str, str)  # (level, message)
    
    def __init__(self, query, current_html=""):
        super().__init__()
        self.query = query
        self.current_html = current_html
        
    def run(self):
        try:
            self.log_signal.emit("INFO", "="*80)
            self.log_signal.emit("INFO", f"🎯 Nouvelle requête: {self.query}")
            self.log_signal.emit("INFO", "="*80)
            
            # Configuration Ollama via Langchain
            self.log_signal.emit("INFO", "🔧 Configuration du modèle Ollama...")
            llm = Ollama(
                model="llama3", 
                temperature=0.7,
                verbose=True
            )
            self.log_signal.emit("SUCCESS", "✓ Modèle Ollama configuré (llama2, temp=0.7)")
            
            # Template de prompt pour générer/modifier du HTML
            template = """Tu es un expert en développement web. 

HTML actuel:
{current_html}

Requête utilisateur: {query}

Génère un code HTML5 complet et valide basé sur la requête. 
Si du HTML existe déjà, modifie-le selon la demande.
Réponds avec le code HTML au format markdown dans un bloc de code.

Format de réponse:
```html
[Ton code HTML ici]
```

Ne mets RIEN d'autre que le bloc de code markdown avec le HTML."""

            self.log_signal.emit("INFO", "📝 Création du template de prompt...")
            prompt = PromptTemplate(
                input_variables=["current_html", "query"],
                template=template
            )
            self.log_signal.emit("SUCCESS", "✓ Template créé")
            
            # Créer le callback handler
            callback_handler = QtLogHandler(self.log_signal)
            
            # Créer la chaîne avec le callback
            self.log_signal.emit("INFO", "🔗 Construction de la chaîne LLM...")
            chain = LLMChain(
                llm=llm, 
                prompt=prompt,
                verbose=True,
                callbacks=[callback_handler]
            )
            self.log_signal.emit("SUCCESS", "✓ Chaîne construite avec callbacks")
            
            # Exécution avec runnable interface
            self.log_signal.emit("INFO", "▶️  Exécution de la chaîne...")
            self.log_signal.emit("DEBUG", f"HTML actuel: {len(self.current_html)} caractères")
            self.log_signal.emit("DEBUG", f"Requête: {self.query}")
            
            # Utiliser invoke (Runnable interface)
            result = chain.invoke(
                {
                    "current_html": self.current_html, 
                    "query": self.query
                },
                config={"callbacks": [callback_handler]}
            )
            
            # Le résultat avec invoke est un dict
            result_text = result.get('text', str(result))
            
            self.log_signal.emit("INFO", "🔍 Extraction du HTML depuis le markdown...")
            # Extraire le HTML du markdown
            html = self.extract_html_from_markdown(result_text)
            self.log_signal.emit("SUCCESS", f"✓ HTML extrait ({len(html)} caractères)")
            
            # Timestamp pour identifier la version
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.log_signal.emit("INFO", "="*80)
            self.log_signal.emit("SUCCESS", f"🎉 Génération terminée avec succès à {timestamp}")
            self.log_signal.emit("INFO", "="*80)
            
            self.finished.emit(html, timestamp)
            
        except Exception as e:
            self.log_signal.emit("ERROR", "="*80)
            self.log_signal.emit("ERROR", f"💥 ERREUR FATALE: {str(e)}")
            self.log_signal.emit("ERROR", f"Type: {type(e).__name__}")
            import traceback
            self.log_signal.emit("ERROR", f"Traceback:\n{traceback.format_exc()}")
            self.log_signal.emit("ERROR", "="*80)
            self.error.emit(str(e))
    
    def extract_html_from_markdown(self, text):
        """Extrait le code HTML des blocs markdown"""
        self.log_signal.emit("DEBUG", "Recherche de blocs markdown...")
        
        # Chercher les blocs ```html ou ```
        pattern = r'```(?:html)?\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            self.log_signal.emit("SUCCESS", f"✓ {len(matches)} bloc(s) markdown trouvé(s)")
            return matches[0].strip()
        else:
            self.log_signal.emit("WARNING", "⚠️ Aucun bloc markdown trouvé, nettoyage basique...")
            # Si pas de bloc markdown, nettoyer le texte brut
            html = text.strip()
            if html.startswith("```html"):
                html = html[7:]
            elif html.startswith("```"):
                html = html[3:]
            if html.endswith("```"):
                html = html[:-3]
            return html.strip()


class HTMLGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.html_versions = []
        self.current_html = ""
        self.worker = None
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Générateur HTML Dynamique - Langchain + Ollama")
        self.setGeometry(100, 100, 1400, 900)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Section historique des versions
        history_layout = QHBoxLayout()
        history_label = QLabel("Historique:")
        self.version_combo = QComboBox()
        self.version_combo.addItem("Aucune version")
        self.version_combo.currentIndexChanged.connect(self.load_version)
        
        # Bouton pour effacer les logs
        self.clear_logs_btn = QPushButton("🗑️ Effacer logs")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        
        # Bouton pour exécuter du JavaScript
        self.exec_js_btn = QPushButton("⚡ Exec JS")
        self.exec_js_btn.clicked.connect(self.execute_custom_js)
        
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.version_combo, 1)
        history_layout.addWidget(self.exec_js_btn)
        history_layout.addWidget(self.clear_logs_btn)
        
        main_layout.addLayout(history_layout)
        
        # QTabWidget pour les onglets
        self.tab_widget = QTabWidget()
        
        # ===== ONGLET 1: Preview HTML =====
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        # Créer une page personnalisée pour capturer les logs JS
        self.web_page = WebEnginePage(log_callback=self.add_log)
        
        # Créer le QWebEngineView
        self.web_view = QWebEngineView()
        self.web_view.setPage(self.web_page)
        
        # Configuration des paramètres QWebEngine
        settings = self.web_view.settings()
        
        # JavaScript
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        
        # Accès réseau et ressources externes
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        
        # Fonctionnalités web modernes
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.AllowWindowActivationFromJavaScript, True)
        
        # Médias et autoplay
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.AutoLoadIconsForPage, True)
        
        # Console et développement
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        settings.setAttribute(QWebEngineSettings.ShowScrollBars, True)
        
        # Performance
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, False)
        
        # Sécurité (tout en permettant l'accès externe)
        settings.setAttribute(QWebEngineSettings.XSSAuditingEnabled, False)
        settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, True)
        
        # WebChannel pour communication Python <-> JavaScript
        self.channel = QWebChannel()
        self.bridge = WebBridge()
        self.bridge.messageFromJS.connect(self.on_message_from_js)
        self.channel.registerObject('bridge', self.bridge)
        self.web_page.setWebChannel(self.channel)
        
        self.web_view.setHtml(self.get_default_html())
        preview_layout.addWidget(self.web_view)
        
        self.tab_widget.addTab(preview_tab, "🖼️ Aperçu")
        
        # ===== ONGLET 2: Code HTML Éditable =====
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)
        
        # Zone de texte pour le code HTML
        self.html_editor = QPlainTextEdit()
        self.html_editor.setPlainText(self.get_default_html())
        
        # Police monospace pour le code
        font = QFont("Courier New", 10)
        self.html_editor.setFont(font)
        
        # Bouton Refresh
        refresh_btn_layout = QHBoxLayout()
        refresh_btn_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Rafraîchir l'aperçu")
        self.refresh_btn.clicked.connect(self.refresh_preview)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        refresh_btn_layout.addWidget(self.refresh_btn)
        refresh_btn_layout.addStretch()
        
        code_layout.addWidget(QLabel("Code HTML (éditable):"))
        code_layout.addWidget(self.html_editor, 1)
        code_layout.addLayout(refresh_btn_layout)
        
        self.tab_widget.addTab(code_tab, "💻 Code HTML")
        
        # ===== ONGLET 3: Logs Langchain =====
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        # Zone de texte pour les logs
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 9))
        
        # Couleurs de fond pour différencier
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        
        log_layout.addWidget(QLabel("📋 Logs de debug Langchain:"))
        log_layout.addWidget(self.log_viewer, 1)
        
        self.tab_widget.addTab(log_tab, "📋 Logs")
        
        main_layout.addWidget(self.tab_widget, 1)
        
        # Section de saisie utilisateur
        input_layout = QHBoxLayout()
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Entrez votre requête (ex: 'Crée une page d'accueil avec un titre bleu')")
        self.query_input.returnPressed.connect(self.generate_html)
        
        self.generate_btn = QPushButton("✨ Générer")
        self.generate_btn.clicked.connect(self.generate_html)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5568d3;
            }
        """)
        
        input_layout.addWidget(QLabel("Requête:"))
        input_layout.addWidget(self.query_input, 1)
        input_layout.addWidget(self.generate_btn)
        
        main_layout.addLayout(input_layout)
        
        # Barre de status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt - Assurez-vous qu'Ollama est en cours d'exécution")
        
        # Ajouter log initial
        self.add_log("INFO", "Application démarrée")
        self.add_log("INFO", "En attente de requête utilisateur...")
        
    def add_log(self, level, message):
        """Ajoute un message dans le viewer de logs avec couleur"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Couleurs selon le niveau
        colors = {
            "INFO": "#61afef",      # Bleu
            "SUCCESS": "#98c379",   # Vert
            "WARNING": "#e5c07b",   # Jaune
            "ERROR": "#e06c75",     # Rouge
            "DEBUG": "#abb2bf",     # Gris
            "PROMPT": "#c678dd",    # Violet
            "RESPONSE": "#56b6c2",  # Cyan
            "TEXT": "#d19a66"       # Orange
        }
        
        color = colors.get(level, "#d4d4d4")
        
        # Format du log
        html_log = f'<span style="color: #5c6370;">[{timestamp}]</span> '
        html_log += f'<span style="color: {color}; font-weight: bold;">[{level}]</span> '
        html_log += f'<span style="color: #d4d4d4;">{message}</span><br>'
        
        # Ajouter au viewer
        self.log_viewer.moveCursor(QTextCursor.End)
        self.log_viewer.insertHtml(html_log)
        self.log_viewer.moveCursor(QTextCursor.End)
        
    def clear_logs(self):
        """Efface tous les logs"""
        self.log_viewer.clear()
        self.add_log("INFO", "Logs effacés")
    
    def execute_custom_js(self):
        """Exécute du JavaScript personnalisé pour test"""
        js_code = """
        console.log('Test depuis Python: JavaScript fonctionne !');
        alert('JavaScript est activé ! 🎉');
        
        // Test de communication avec Python via WebChannel
        if (typeof qt !== 'undefined' && qt.webChannelTransport) {
            new QWebChannel(qt.webChannelTransport, function(channel) {
                var bridge = channel.objects.bridge;
                var response = bridge.echo('Hello from JavaScript!');
                console.log(response);
            });
        }
        
        // Retourner des infos sur la page
        JSON.stringify({
            userAgent: navigator.userAgent,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screenWidth: screen.width,
            screenHeight: screen.height
        });
        """
        
        self.web_page.runJavaScript(js_code, self.on_js_result)
        self.add_log("INFO", "Exécution de JavaScript de test...")
    
    def on_js_result(self, result):
        """Callback pour les résultats JavaScript"""
        if result:
            self.add_log("SUCCESS", f"JavaScript retourné: {result}")
    
    def on_message_from_js(self, message):
        """Callback quand JavaScript envoie un message à Python"""
        self.add_log("INFO", f"Message reçu de JavaScript: {message}")
        
    def get_default_html(self):
        """HTML par défaut au démarrage"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Générateur HTML IA</title>
    
    <!-- Script QWebChannel pour communication avec Python -->
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 3rem;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 600px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 1rem;
        }
        p {
            color: #666;
            line-height: 1.6;
        }
        .feature-list {
            text-align: left;
            margin-top: 2rem;
            padding: 1rem;
            background: #f5f5f5;
            border-radius: 5px;
        }
        .feature-list li {
            margin: 0.5rem 0;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            font-size: 14px;
        }
        button:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Générateur HTML avec IA</h1>
        <p>Entrez votre requête ci-dessous pour générer ou modifier cette page HTML</p>
        <p><strong>Exemple:</strong> "Ajoute un bouton rouge" ou "Crée un formulaire de contact"</p>
        
        <div class="feature-list">
            <h3>✨ Fonctionnalités activées:</h3>
            <ul>
                <li>✅ JavaScript activé</li>
                <li>✅ Accès réseau externe (CDN, API, etc.)</li>
                <li>✅ WebGL et Canvas 2D</li>
                <li>✅ LocalStorage et SessionStorage</li>
                <li>✅ Communication Python ↔ JavaScript</li>
                <li>✅ Console.log capturée dans les logs</li>
                <li>✅ Médias et autoplay</li>
            </ul>
        </div>
        
        <div style="margin-top: 2rem;">
            <button onclick="testJS()">Test JavaScript</button>
            <button onclick="testPythonBridge()">Test Bridge Python</button>
            <button onclick="testExternalAPI()">Test API Externe</button>
        </div>
    </div>
    
    <script>
        // Test JavaScript simple
        function testJS() {
            console.log('✅ JavaScript fonctionne parfaitement!');
            alert('JavaScript est actif! 🎉');
        }
        
        // Test communication avec Python via QWebChannel
        var bridge = null;
        
        new QWebChannel(qt.webChannelTransport, function(channel) {
            bridge = channel.objects.bridge;
            console.log('✅ Bridge Python initialisé');
        });
        
        function testPythonBridge() {
            if (bridge) {
                var response = bridge.echo('Bonjour depuis JavaScript!');
                console.log('Réponse de Python:', response);
                alert('Communication avec Python réussie! Voir les logs.');
                bridge.sendToPython('Message depuis le HTML');
            } else {
                console.error('Bridge non initialisé');
            }
        }
        
        // Test d'une API externe
        function testExternalAPI() {
            console.log('Tentative de connexion à une API externe...');
            fetch('https://api.github.com/users/github')
                .then(response => response.json())
                .then(data => {
                    console.log('✅ API externe accessible!', data);
                    alert('API externe fonctionne! User: ' + data.login);
                })
                .catch(error => {
                    console.error('❌ Erreur API:', error);
                });
        }
        
        // Log au chargement
        console.log('Page chargée avec succès!');
        console.log('Navigator:', navigator.userAgent);
    </script>
</body>
</html>"""
        
    def refresh_preview(self):
        """Rafraîchit l'aperçu avec le code HTML de l'éditeur"""
        html_code = self.html_editor.toPlainText()
        self.current_html = html_code
        self.web_view.setHtml(html_code)
        self.status_bar.showMessage("✓ Aperçu rafraîchi depuis l'éditeur")
        self.add_log("INFO", "Aperçu rafraîchi manuellement depuis l'éditeur")
        
        # Basculer vers l'onglet aperçu
        self.tab_widget.setCurrentIndex(0)
        
    def generate_html(self):
        """Démarre la génération HTML via Langchain"""
        query = self.query_input.text().strip()
        
        if not query:
            self.status_bar.showMessage("Veuillez entrer une requête")
            self.add_log("WARNING", "Tentative de génération sans requête")
            return
            
        # Utiliser le code HTML de l'éditeur comme base
        self.current_html = self.html_editor.toPlainText()
            
        # Désactiver les contrôles pendant la génération
        self.query_input.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.html_editor.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.status_bar.showMessage(f"⏳ Génération en cours... ({query})")
        
        # Basculer vers l'onglet logs
        self.tab_widget.setCurrentIndex(2)
        
        # Lancer le worker thread
        self.worker = LangchainWorker(query, self.current_html)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.log_signal.connect(self.add_log)
        self.worker.start()
        
    def on_generation_finished(self, html, timestamp):
        """Callback quand la génération est terminée"""
        # Sauvegarder la version
        query = self.query_input.text().strip()
        self.html_versions.append({
            'timestamp': timestamp,
            'html': html,
            'query': query
        })
        
        # Mettre à jour le HTML courant
        self.current_html = html
        
        # Afficher dans la webview ET dans l'éditeur
        self.web_view.setHtml(html)
        self.html_editor.setPlainText(html)
        
        # Ajouter à la combobox
        version_label = f"{timestamp} - {query[:50]}"
        self.version_combo.addItem(version_label)
        self.version_combo.setCurrentIndex(self.version_combo.count() - 1)
        
        # Réactiver les contrôles
        self.query_input.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.html_editor.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.query_input.clear()
        self.status_bar.showMessage(f"✓ Génération terminée ({timestamp})")
        
        # Basculer vers l'onglet aperçu pour voir le résultat
        self.tab_widget.setCurrentIndex(0)
        
    def on_generation_error(self, error_msg):
        """Callback en cas d'erreur"""
        self.status_bar.showMessage(f"❌ Erreur: {error_msg}")
        self.query_input.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.html_editor.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        
        # Afficher un message d'erreur dans la page
        error_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 2rem;
            background: #fee;
        }}
        .error {{
            background: #fdd;
            border: 2px solid #c33;
            padding: 1.5rem;
            border-radius: 8px;
            max-width: 800px;
            margin: 0 auto;
        }}
        h2 {{ color: #c33; }}
        code {{
            background: #fff;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
            font-family: monospace;
        }}
        ul {{ line-height: 1.8; }}
    </style>
</head>
<body>
    <div class="error">
        <h2>⚠️ Erreur de génération</h2>
        <p><strong>Message:</strong> <code>{error_msg}</code></p>
        <p><strong>Vérifications:</strong></p>
        <ul>
            <li>Ollama est-il en cours d'exécution ? <code>ollama serve</code></li>
            <li>Le modèle llama2 est-il installé ? <code>ollama pull llama2</code></li>
            <li>Langchain est-il installé ? <code>pip install langchain langchain-community</code></li>
        </ul>
        <p><strong>Consultez l'onglet "Logs" pour plus de détails.</strong></p>
    </div>
</body>
</html>"""
        self.web_view.setHtml(error_html)
        self.html_editor.setPlainText(error_html)
        
    def load_version(self, index):
        """Charger une version depuis l'historique"""
        if index == 0 or index >= len(self.html_versions) + 1:
            # Version par défaut
            default_html = self.get_default_html()
            self.web_view.setHtml(default_html)
            self.html_editor.setPlainText(default_html)
            self.current_html = ""
            self.add_log("INFO", "Version par défaut chargée")
        else:
            # Charger la version sélectionnée
            version = self.html_versions[index - 1]
            self.current_html = version['html']
            self.web_view.setHtml(version['html'])
            self.html_editor.setPlainText(version['html'])
            self.status_bar.showMessage(f"Version chargée: {version['timestamp']}")
            self.add_log("INFO", f"Version chargée: {version['timestamp']} - {version['query']}")


def main():
    app = QApplication(sys.argv)
    window = HTMLGeneratorApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
