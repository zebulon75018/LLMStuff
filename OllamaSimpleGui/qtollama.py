#!/usr/bin/env python3
"""
Application Qt5 avec LangChain/Ollama en mode asynchrone
Interface non-bloquante avec threading pour les requêtes LLM
"""

import sys
import requests
import pprint
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QLabel, QComboBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


def getOllamaBaseUrl():
    return "http://localhost:11434"

class OllamaWorker(QThread):
    """Thread worker pour exécuter les requêtes Ollama sans bloquer l'UI"""
    
    # Signaux pour communiquer avec l'interface
    finished = pyqtSignal(str)  # Résultat final
    error = pyqtSignal(str)      # Message d'erreur
    
    def __init__(self, prompt: str, model_name: str = "llama3"):
        super().__init__()
        self.prompt = prompt
        self.model_name = model_name
        self.base_url = getOllamaBaseUrl()

    def getollamamodel(self):
        response = requests.get(f"{self.base_url}/api/tags")
        response.raise_for_status()

        data = response.json()
        models = [model['name'] for model in data.get('models', [])]

        return models

    
    def run(self):
        """Exécute la requête dans un thread séparé"""
        try:
            # Initialisation du modèle Ollama
            llm = Ollama(
                model=self.model_name,
                base_url=self.base_url
            )
            
            # Template de prompt simple
            template = """Tu es un assistant intelligent et utile.
            
Question: {question}

Réponse:"""
            
            prompt_template = PromptTemplate(
                template=template,
                input_variables=["question"]
            )
            
            chain = LLMChain(llm=llm, prompt=prompt_template)
            
            # Exécution de la requête
            result = chain.run(question=self.prompt)
            
            # Émission du résultat
            self.finished.emit(result.strip())
            
        except Exception as e:
            self.error.emit(f"Erreur: {str(e)}")


class OllamaChatApp(QMainWindow):
    """Application principale Qt avec interface Ollama"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("Chat Ollama - Llama3")
        self.setGeometry(100, 100, 800, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # === Zone de saisie en haut ===
        input_layout = QHBoxLayout()
        
        # Label
        label = QLabel("Question:")
        label.setFont(QFont("Arial", 10))
        input_layout.addWidget(label)
        
        # Champ de saisie
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Entrez votre question ici...")
        self.input_field.setFont(QFont("Arial", 11))
        self.input_field.returnPressed.connect(self.on_submit)
        input_layout.addWidget(self.input_field)

        self.modelchoice = QComboBox()
        for m in self.getollamamodel():
          self.modelchoice.addItem(m)
        input_layout.addWidget(self.modelchoice)

        self.info_button = QPushButton("?")
        self.info_button.clicked.connect(self.on_infomodel)
        input_layout.addWidget(self.info_button)
        
        # Bouton Envoyer
        self.submit_button = QPushButton("Envoyer")
        self.submit_button.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.submit_button.setMinimumWidth(100)
        self.submit_button.clicked.connect(self.on_submit)
        input_layout.addWidget(self.submit_button)
        
        layout.addLayout(input_layout)
        
        # === Zone de texte pour la réponse ===
        response_label = QLabel("Réponse:")
        response_label.setFont(QFont("Arial", 10))
        layout.addWidget(response_label)
        
        self.response_area = QTextEdit()
        self.response_area.setReadOnly(True)
        self.response_area.setFont(QFont("Arial", 10))
        self.response_area.setPlaceholderText("La réponse apparaîtra ici...")
        layout.addWidget(self.response_area)
        
        # === Barre de statut ===
        self.status_label = QLabel("Prêt")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.status_label)
        
        central_widget.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
            }
        """)

    def getollamamodel(self):
        response = requests.get(f"{getOllamaBaseUrl()}/api/tags")
        response.raise_for_status()

        data = response.json()
        models = [model['name'] for model in data.get('models', [])]

        self.getollammodelinfo()
        return models

    def getollammodelinfo(self):
        response = requests.get(f"{getOllamaBaseUrl()}/api/tags")
        response.raise_for_status()

        data = response.json()
        models_info = []

        for model in data.get('models', []):
            model_info = {
                'name': model['name'],
                'modified_at': model.get('modified_at', 'N/A'),
                'size': model.get('size', 0),
                'size_gb': model.get('size', 0) / (1024**3),  # Conversion en GB
                'digest': model.get('digest', 'N/A')[:12],  # Premiers caractères
            }
            models_info.append(model_info)

        #pprint.pprint(models_info)
        self._modelinfo = models_info



    def on_infomodel(self):
        try:
           minfo = self._modelinfo[self.modelchoice.currentIndex()]
           self.status_label.setText(" %s size: %d  " % (minfo["name"],minfo["size"] ))
        except Exception as e:
           print(e)
           self.status_label.setText("❌ Erreur info model ")
    
    def on_submit(self):
        """Gère l'envoi de la question"""
        question = self.input_field.text().strip()
        
        if not question:
            self.status_label.setText("⚠️ Veuillez entrer une question")
            return
        
        # Désactive l'interface pendant le traitement
        self.set_ui_enabled(False)
        self.response_area.setPlainText("⏳ Réflexion en cours...")
        self.status_label.setText("🔄 Communication avec Ollama...")
        
        # Lance le worker dans un thread séparé
        #self.worker = OllamaWorker(question, model_name="llama3")
        self.worker = OllamaWorker(question, model_name=self.modelchoice.itemText(self.modelchoice.currentIndex()))
        self.worker.finished.connect(self.on_response_received)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_response_received(self, response: str):
        """Appelé quand la réponse est reçue"""
        self.response_area.setPlainText(response)
        self.status_label.setText("✓ Réponse reçue")
        self.set_ui_enabled(True)
        self.input_field.setFocus()
    
    def on_error(self, error_msg: str):
        """Appelé en cas d'erreur"""
        self.response_area.setPlainText(error_msg)
        self.status_label.setText("❌ Erreur lors de la communication")
        self.set_ui_enabled(True)
    
    def set_ui_enabled(self, enabled: bool):
        """Active/désactive l'interface"""
        self.input_field.setEnabled(enabled)
        self.submit_button.setEnabled(enabled)
    
    def closeEvent(self, event):
        """Gère la fermeture de l'application"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()


def main():
    """Point d'entrée de l'application"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Style moderne
    
    window = OllamaChatApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
