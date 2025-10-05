import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,  QFormLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QComboBox, QDoubleSpinBox,
                             QLabel, QStatusBar, QTabWidget, QPlainTextEdit, QTextEdit, QAction, 
                             QFileDialog, QInputDialog, QMessageBox, QDialog, QDialogButtonBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QUrl, QObject, pyqtSlot
from PyQt5.QtGui import QFont, QTextCursor , QKeySequence , QIcon
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


class PreferencesDialog(QDialog):
    """Dialogue de préférences pour configurer le LLM"""
    
    def __init__(self, parent=None, current_model="llama3", current_temperature=0.7):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Préférences LLM")
        self.setMinimumWidth(400)
        
        self.current_model = current_model
        self.current_temperature = current_temperature
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # En-tête
        header = QLabel("<h2>⚙️ Configuration du modèle LLM</h2>")
        layout.addWidget(header)
        
        # Formulaire
        form_layout = QFormLayout()
        
        # Sélection du modèle
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "llama2",
            "llama2:13b",
            "llama2:70b",
            "llama3",
            "llama3:70b",
            "codellama",
            "codellama:13b",
            "mistral",
            "mixtral",
            "phi",
            "gemma",
            "qwen",
            "deepseek-coder"
        ])
        
        # Sélectionner le modèle actuel
        index = self.model_combo.findText(self.current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        form_layout.addRow("🤖 Modèle:", self.model_combo)
        
        # Température
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(self.current_temperature)
        self.temp_spin.setDecimals(1)
        
        temp_label = QLabel("🌡️ Température:")
        temp_help = QLabel("<small><i>0.0 = déterministe, 2.0 = créatif</i></small>")
        
        form_layout.addRow(temp_label, self.temp_spin)
        form_layout.addRow("", temp_help)
        
        layout.addLayout(form_layout)
        
        # Info supplémentaire
        info_text = QLabel("""
<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-top: 10px;'>
<b>ℹ️ Informations:</b><br>
• Les modèles doivent être préalablement téléchargés avec <code>ollama pull [model]</code><br>
• La température contrôle la créativité des réponses<br>
• Les changements prendront effet à la prochaine génération
</div>
        """)
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        # Boutons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def get_settings(self):
        """Retourne les paramètres sélectionnés"""
        return {
            'model': self.model_combo.currentText(),
            'temperature': self.temp_spin.value()
        }


class LangchainWorker(QThread):
    """Thread worker pour exécuter Langchain sans bloquer l'UI"""
    finished = pyqtSignal(str, str)  # Retourne (html, timestamp)
    error = pyqtSignal(str)
    log_signal = pyqtSignal(str, str)  # (level, message)
    
    def __init__(self, query, current_html="", model="llama2", temperature=0.7):
        super().__init__()
        self.query = query
        self.current_html = current_html
        self.model = model
        self.temperature = temperature
        
    def run(self):
        try:
            self.log_signal.emit("INFO", "="*80)
            self.log_signal.emit("INFO", f"🎯 Nouvelle requête: {self.query}")
            self.log_signal.emit("INFO", "="*80)
            
            # Configuration Ollama via Langchain
            self.log_signal.emit("INFO", "🔧 Configuration du modèle Ollama...")
            llm = Ollama(
                model=self.model, 
                temperature=self.temperature,
                verbose=True
            )
            self.log_signal.emit("SUCCESS", f"✓ Modèle Ollama configuré ({self.model}, temp={self.temperature})")
            
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
        self.last_save_path = None  # Pour la sauvegarde rapide
        
        # Paramètres LLM par défaut
        self.llm_model = "llama3"
        self.llm_temperature = 0.7
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Générateur HTML Dynamique - Langchain + Ollama")
        self.setGeometry(100, 100, 1400, 900)
        
        # ===== MENU BAR =====
        self.create_menu_bar()
        
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
    
    def create_menu_bar(self):
        """Crée la barre de menu"""
        menubar = self.menuBar()
        
        # ===== MENU FICHIER =====
        file_menu = menubar.addMenu("📁 Fichier")
        
        # Ouvrir HTML depuis disque
        open_file_action = QAction("📂 Ouvrir HTML local...", self)
        open_file_action.setShortcut(QKeySequence.Open)
        open_file_action.triggered.connect(self.open_html_file)
        file_menu.addAction(open_file_action)
        
        # Charger depuis URL
        open_url_action = QAction("🌐 Charger depuis URL...", self)
        open_url_action.setShortcut("Ctrl+U")
        open_url_action.triggered.connect(self.load_from_url)
        file_menu.addAction(open_url_action)
        
        file_menu.addSeparator()
        
        # Sauvegarder HTML
        save_action = QAction("💾 Sauvegarder HTML...", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_html_file)
        file_menu.addAction(save_action)
        
        # Sauvegarder HTML sous...
        save_as_action = QAction("💾 Sauvegarder HTML sous...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_html_as)
        file_menu.addAction(save_as_action)
        
        # Exporter le code édité
        export_code_action = QAction("📤 Exporter le code de l'éditeur...", self)
        export_code_action.setShortcut("Ctrl+E")
        export_code_action.triggered.connect(self.export_editor_code)
        file_menu.addAction(export_code_action)
        
        file_menu.addSeparator()
        
        # Quitter
        quit_action = QAction("🚪 Quitter", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # ===== MENU AFFICHAGE =====
        view_menu = menubar.addMenu("👁️ Affichage")
        
        # Recharger la page
        reload_action = QAction("🔄 Recharger la page", self)
        reload_action.setShortcut(QKeySequence.Refresh)
        reload_action.triggered.connect(self.reload_page)
        view_menu.addAction(reload_action)
        
        # Zoom
        view_menu.addSeparator()
        zoom_in_action = QAction("🔍 Zoom avant", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("🔍 Zoom arrière", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        zoom_reset_action = QAction("🔍 Réinitialiser zoom", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(self.zoom_reset)
        view_menu.addAction(zoom_reset_action)
        
        # ===== MENU OUTILS =====
        tools_menu = menubar.addMenu("🔧 Outils")
        
        # Exécuter JavaScript
        exec_js_action = QAction("⚡ Exécuter JavaScript personnalisé...", self)
        exec_js_action.setShortcut("Ctrl+J")
        exec_js_action.triggered.connect(self.execute_custom_js_dialog)
        tools_menu.addAction(exec_js_action)
        
        # Inspecter le HTML actuel
        inspect_action = QAction("🔍 Inspecter HTML actuel", self)
        inspect_action.setShortcut("Ctrl+I")
        inspect_action.triggered.connect(self.inspect_current_html)
        tools_menu.addAction(inspect_action)
        
        tools_menu.addSeparator()
        
        # Effacer l'historique
        clear_history_action = QAction("🗑️ Effacer l'historique", self)
        clear_history_action.triggered.connect(self.clear_history)
        tools_menu.addAction(clear_history_action)
        
        tools_menu.addSeparator()
        
        # Préférences LLM
        preferences_action = QAction("⚙️ Préférences LLM...", self)
        preferences_action.setShortcut("Ctrl+P")
        preferences_action.triggered.connect(self.show_preferences)
        tools_menu.addAction(preferences_action)
        
        # ===== MENU AIDE =====
        help_menu = menubar.addMenu("❓ Aide")
        
        about_action = QAction("ℹ️ À propos", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        shortcuts_action = QAction("⌨️ Raccourcis clavier", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
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
    
    # ===== MÉTHODES DU MENU FICHIER =====
    
    def open_html_file(self):
        """Ouvre un fichier HTML depuis le disque"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un fichier HTML",
            "",
            "Fichiers HTML (*.html *.htm);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Afficher dans les deux vues
                self.web_view.setHtml(html_content)
                self.html_editor.setPlainText(html_content)
                self.current_html = html_content
                
                self.add_log("SUCCESS", f"✓ Fichier chargé: {file_path}")
                self.status_bar.showMessage(f"Fichier chargé: {file_path}")
                
                # Basculer vers l'aperçu
                self.tab_widget.setCurrentIndex(0)
                
            except Exception as e:
                self.add_log("ERROR", f"Erreur lors du chargement: {str(e)}")
                QMessageBox.critical(self, "Erreur", f"Impossible de charger le fichier:\n{str(e)}")
    
    def load_from_url(self):
        """Charge une page HTML depuis une URL"""
        url, ok = QInputDialog.getText(
            self,
            "Charger depuis URL",
            "Entrez l'URL de la page à charger:",
            text="https://"
        )
        
        if ok and url:
            try:
                self.add_log("INFO", f"Chargement de l'URL: {url}")
                self.status_bar.showMessage(f"Chargement de {url}...")
                
                # Charger l'URL directement
                self.web_view.load(QUrl(url))
                
                # Callback pour récupérer le HTML une fois chargé
                def on_load_finished(success):
                    if success:
                        self.add_log("SUCCESS", f"✓ URL chargée: {url}")
                        self.status_bar.showMessage(f"URL chargée: {url}")
                        
                        # Récupérer le HTML de la page
                        self.web_page.toHtml(self.on_html_retrieved)
                    else:
                        self.add_log("ERROR", f"❌ Échec du chargement de l'URL: {url}")
                        QMessageBox.warning(self, "Erreur", f"Impossible de charger l'URL:\n{url}")
                
                self.web_view.loadFinished.connect(on_load_finished)
                
            except Exception as e:
                self.add_log("ERROR", f"Erreur URL: {str(e)}")
                QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement de l'URL:\n{str(e)}")
    
    def on_html_retrieved(self, html):
        """Callback quand le HTML d'une page est récupéré"""
        self.html_editor.setPlainText(html)
        self.current_html = html
        self.add_log("INFO", "HTML de la page récupéré dans l'éditeur")
    
    def save_html_file(self):
        """Sauvegarde le HTML actuel"""
        if hasattr(self, 'last_save_path') and self.last_save_path:
            self._save_to_file(self.last_save_path)
        else:
            self.save_html_as()
    
    def save_html_as(self):
        """Sauvegarde le HTML sous un nouveau nom"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder HTML",
            "page.html",
            "Fichiers HTML (*.html *.htm);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            self._save_to_file(file_path)
            self.last_save_path = file_path
    
    def _save_to_file(self, file_path):
        """Sauvegarde le HTML dans un fichier"""
        try:
            html_to_save = self.html_editor.toPlainText()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_to_save)
            
            self.add_log("SUCCESS", f"✓ Fichier sauvegardé: {file_path}")
            self.status_bar.showMessage(f"Fichier sauvegardé: {file_path}")
            QMessageBox.information(self, "Succès", f"HTML sauvegardé dans:\n{file_path}")
            
        except Exception as e:
            self.add_log("ERROR", f"Erreur de sauvegarde: {str(e)}")
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder le fichier:\n{str(e)}")
    
    def export_editor_code(self):
        """Exporte le code de l'éditeur"""
        self.save_html_as()
    
    # ===== MÉTHODES DU MENU AFFICHAGE =====
    
    def reload_page(self):
        """Recharge la page web"""
        self.web_view.reload()
        self.add_log("INFO", "Page rechargée")
        self.status_bar.showMessage("Page rechargée")
    
    def zoom_in(self):
        """Zoom avant"""
        current_zoom = self.web_view.zoomFactor()
        self.web_view.setZoomFactor(current_zoom + 0.1)
        self.add_log("INFO", f"Zoom: {int((current_zoom + 0.1) * 100)}%")
    
    def zoom_out(self):
        """Zoom arrière"""
        current_zoom = self.web_view.zoomFactor()
        new_zoom = max(0.25, current_zoom - 0.1)
        self.web_view.setZoomFactor(new_zoom)
        self.add_log("INFO", f"Zoom: {int(new_zoom * 100)}%")
    
    def zoom_reset(self):
        """Réinitialise le zoom"""
        self.web_view.setZoomFactor(1.0)
        self.add_log("INFO", "Zoom réinitialisé à 100%")
    
    # ===== MÉTHODES DU MENU OUTILS =====
    
    def execute_custom_js_dialog(self):
        """Dialogue pour exécuter du JavaScript personnalisé"""
        js_code, ok = QInputDialog.getMultiLineText(
            self,
            "Exécuter JavaScript",
            "Entrez le code JavaScript à exécuter:",
            "console.log('Hello from custom JS!');"
        )
        
        if ok and js_code:
            self.add_log("INFO", f"Exécution de JavaScript personnalisé...")
            self.web_page.runJavaScript(js_code, self.on_js_result)
    
    def inspect_current_html(self):
        """Inspecte et affiche des infos sur le HTML actuel"""
        html = self.html_editor.toPlainText()
        
        # Statistiques
        stats = f"""
📊 Statistiques du HTML actuel:

- Caractères: {len(html)}
- Lignes: {html.count(chr(10)) + 1}
- Balises estimées: {html.count('<')}
- Taille: {len(html.encode('utf-8')) / 1024:.2f} KB

Début du code:
{html[:500]}...
"""
        
        QMessageBox.information(self, "Inspection HTML", stats)
        self.add_log("INFO", "HTML inspecté")
    
    def clear_history(self):
        """Efface l'historique des versions"""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous vraiment effacer tout l'historique?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.html_versions.clear()
            self.version_combo.clear()
            self.version_combo.addItem("Aucune version")
            self.add_log("WARNING", "Historique effacé")
            self.status_bar.showMessage("Historique effacé")
    
    def show_preferences(self):
        """Affiche le dialogue de préférences LLM"""
        dialog = PreferencesDialog(
            self, 
            current_model=self.llm_model,
            current_temperature=self.llm_temperature
        )
        
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            old_model = self.llm_model
            old_temp = self.llm_temperature
            
            self.llm_model = settings['model']
            self.llm_temperature = settings['temperature']
            
            # Logger le changement
            self.add_log("INFO", "="*60)
            self.add_log("SUCCESS", "⚙️ Paramètres LLM mis à jour:")
            self.add_log("INFO", f"  Modèle: {old_model} → {self.llm_model}")
            self.add_log("INFO", f"  Température: {old_temp} → {self.llm_temperature}")
            self.add_log("INFO", "Les changements prendront effet à la prochaine génération")
            self.add_log("INFO", "="*60)
            
            self.status_bar.showMessage(
                f"Paramètres LLM mis à jour: {self.llm_model} (temp={self.llm_temperature})"
            )
            
            # Message de confirmation
            QMessageBox.information(
                self,
                "Préférences enregistrées",
                f"Les nouveaux paramètres LLM ont été enregistrés:\n\n"
                f"• Modèle: {self.llm_model}\n"
                f"• Température: {self.llm_temperature}\n\n"
                f"Assurez-vous que le modèle est installé avec:\n"
                f"ollama pull {self.llm_model}"
            )
    
    # ===== MÉTHODES DU MENU AIDE =====
    
    def show_about(self):
        """Affiche la boîte de dialogue À propos"""
        about_text = """
<h2>🚀 Générateur HTML Dynamique</h2>
<p><b>Version:</b> 1.0</p>
<p><b>Technologies:</b></p>
<ul>
    <li>Python 3 + PyQt5</li>
    <li>QWebEngineView avec JavaScript activé</li>
    <li>Langchain + Ollama (LLM local)</li>
    <li>Communication Python ↔ JavaScript</li>
</ul>
<p><b>Fonctionnalités:</b></p>
<ul>
    <li>✅ Génération HTML par IA</li>
    <li>✅ Éditeur de code en temps réel</li>
    <li>✅ Logs détaillés de debug</li>
    <li>✅ Chargement depuis fichier/URL</li>
    <li>✅ Sauvegarde des résultats</li>
    <li>✅ Historique des versions</li>
</ul>
<p><i>Créé avec ❤️ pour le développement web assisté par IA</i></p>
"""
        QMessageBox.about(self, "À propos", about_text)
    
    def show_shortcuts(self):
        """Affiche les raccourcis clavier"""
        shortcuts_text = """
<h3>⌨️ Raccourcis clavier</h3>

<b>Fichier:</b>
<ul>
    <li><b>Ctrl+O</b> - Ouvrir HTML local</li>
    <li><b>Ctrl+U</b> - Charger depuis URL</li>
    <li><b>Ctrl+S</b> - Sauvegarder</li>
    <li><b>Ctrl+Shift+S</b> - Sauvegarder sous...</li>
    <li><b>Ctrl+E</b> - Exporter le code</li>
    <li><b>Ctrl+Q</b> - Quitter</li>
</ul>

<b>Affichage:</b>
<ul>
    <li><b>F5</b> - Recharger la page</li>
    <li><b>Ctrl++</b> - Zoom avant</li>
    <li><b>Ctrl+-</b> - Zoom arrière</li>
    <li><b>Ctrl+0</b> - Réinitialiser zoom</li>
</ul>

<b>Outils:</b>
<ul>
    <li><b>Ctrl+J</b> - Exécuter JavaScript</li>
    <li><b>Ctrl+I</b> - Inspecter HTML</li>
    <li><b>Ctrl+P</b> - Préférences LLM</li>
</ul>

<b>Aide:</b>
<ul>
    <li><b>F1</b> - Afficher les raccourcis</li>
</ul>
"""
        QMessageBox.information(self, "Raccourcis clavier", shortcuts_text)
        
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
        
        # Lancer le worker thread avec les paramètres LLM
        self.worker = LangchainWorker(
            query, 
            self.current_html,
            model=self.llm_model,
            temperature=self.llm_temperature
        )
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
