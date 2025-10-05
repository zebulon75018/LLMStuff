

# 🚀 Application HTML Dynamique avec Langchain (Python/Qt5)

Cette application complète en Python/Qt5 permet de générer, visualiser et éditer dynamiquement du code HTML à l'aide de modèles de langage (LLM) via Langchain.

## ✨ Caractéristiques Principales

*   **Interface utilisateur moderne** : Basée sur Qt5 avec un système d'onglets `QTabWidget`.
*   **Génération HTML par LLM** : Utilise `ollama` (avec `llama2` par défaut) via `Langchain` pour générer du HTML.
*   **Aperçu en temps réel** : `QWebEngineView` pour afficher le rendu HTML.
    *   **Accès réseau et ressources externes** : Support des CDN (Bootstrap, jQuery), contenu HTTP/HTTPS mixte.
    *   **Exécution JavaScript complète** : Activation de JavaScript, ouverture de fenêtres, accès au presse-papier.
    *   **Fonctionnalités web modernes** : WebGL, Canvas 2D accéléré, LocalStorage, mode plein écran, autoplay médias.
    *   **Communication bidirectionnelle Python ↔ JavaScript** : Utilisation de `QWebChannel` pour un "bridge" entre Python et le JavaScript de la page.
*   **Éditeur de code HTML** : Zone de texte éditable pour visualiser et modifier le code HTML généré.
    *   Bouton "Rafraîchir l'aperçu" pour appliquer les modifications de l'éditeur.
*   **Système de logs détaillé** : Onglet "Logs" avec `QTextEdit` stylisé (thème sombre, codes couleur).
    *   `QtLogHandler` personnalisé (implémentant `BaseCallbackHandler`) pour intercepter et afficher tous les événements Langchain (LLM, chaîne, erreurs).
    *   Capture des messages `console.log()`, `console.warn()`, `console.error()` depuis JavaScript et affichage dans les logs.
    *   Bouton "Effacer logs" et bascule automatique vers l'onglet Logs lors des générations.
*   **Historique des versions** : `QComboBox` pour naviguer entre les différentes générations HTML.
*   **Barre de statut** : Pour suivre l'état de l'application et les messages importants.
*   **Thread séparé** : Les appels Langchain s'exécutent dans un thread séparé pour maintenir l'interface utilisateur réactive.

## 🛠️ Installation des Dépendances

```bash
# Installer les packages Python nécessaires
pip install PyQt5 PyQtWebEngine langchain langchain-community
```

**Installer et démarrer Ollama :**

1.  Télécharger Ollama depuis : [https://ollama.ai](https://ollama.ai)
2.  Pull le modèle `llama2` (ou un autre modèle de votre choix) :
    ```bash
    ollama pull llama2
    ```
3.  Démarrer le serveur Ollama (doit être en cours d'exécution en arrière-plan) :
    ```bash
    ollama serve
    ```

## 🚀 Fonctionnement

1.  L'utilisateur entre une requête (par exemple, "Crée une page avec un titre rouge et un bouton") dans le `QLineEdit` du bas.
2.  L'application appelle Ollama via Langchain dans un thread séparé.
3.  Le LLM est invité à retourner le HTML dans un bloc Markdown (par exemple, ````markdown<html>...</html>````).
4.  Le code HTML généré est extrait et affiché dans l'onglet "Aperçu" via `QWebEngineView`.
5.  L'onglet "Code HTML" affiche le code source, que l'utilisateur peut éditer manuellement.
6.  Chaque version générée ou éditée est sauvegardée avec un horodatage et accessible via la `QComboBox` de l'historique. Les requêtes successives peuvent modifier le HTML précédent (modification incrémentale).
7.  L'onglet "Logs" fournit un suivi détaillé des interactions Langchain et des messages JavaScript.
8.  Un bouton "Exec JS" permet de tester l'exécution JavaScript et la communication Python ↔ JS.

## 🎯 Exemples de Requêtes

*   "Crée une page d'accueil pour un restaurant"
*   "Ajoute un formulaire de contact"
*   "Change la couleur de fond en bleu"
*   "Ajoute une galerie d'images"
*   "Ajoute un bouton qui affiche une alerte 'Hello from JS' quand on clique dessus"
*   "Intègre une carte OpenStreetMap centrée sur Paris"

## 📊 Exemple de Logs Affichés

```
[14:32:15.123] [INFO] 🎯 Nouvelle requête: Ajoute un bouton rouge
[14:32:15.145] [INFO] 🔧 Configuration du modèle Ollama...
[14:32:15.234] [SUCCESS] ✓ Modèle Ollama configuré (llama2, temp=0.7)
[14:32:15.245] [INFO] 🔗 Démarrage de la chaîne Langchain
[14:32:15.267] [PROMPT] Prompt #1:
Tu es un expert en développement web...
[14:32:18.891] [RESPONSE] Réponse #1:
<!DOCTYPE html>...
[14:32:18.923] [SUCCESS] 🎉 Génération terminée avec succès
[14:32:19.100] [JS-INFO] Message depuis JavaScript: Bonjour depuis la page web!
[14:32:20.500] [JS-WARNING] Un élément n'a pas été trouvé.
```

L'application gère les erreurs et affiche des messages clairs si Ollama n'est pas démarré ou si le modèle n'est pas installé, et fournit un outil de débogage complet pour le pipeline Langchain et l'interaction web.
