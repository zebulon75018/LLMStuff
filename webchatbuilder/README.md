

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



Absolument ! Voici la conversion de votre description en un format Markdown structuré et facile à lire :

---

# ✨ Améliorations de l'Interface Utilisateur : Barre de Menu Complète

L'application a été enrichie d'une barre de menu complète, offrant un accès intuitif à toutes les fonctionnalités et améliorant significativement l'expérience utilisateur.

## 🎯 Nouvelle Barre de Menu (4 Menus)

La barre de menu est structurée en quatre sections principales : **Fichier**, **Affichage**, **Outils** et **Aide**.

### 📁 Menu Fichier

Permet de gérer l'ouverture, le chargement et la sauvegarde des fichiers HTML.

*   **Ouvrir HTML local** (`Ctrl+O`)
    *   Charge un fichier `.html` ou `.htm` depuis le disque.
    *   Affiche le contenu à la fois dans `QWebEngineView` (Aperçu) et dans l'éditeur de code.
    *   Gère l'encodage `UTF-8` et les erreurs de lecture.
*   **Charger depuis URL** (`Ctrl+U`)
    *   Ouvre un dialogue pour saisir une URL.
    *   Télécharge et affiche la page web dans `QWebEngineView`.
    *   Récupère et affiche le code source HTML dans l'éditeur après le chargement.
*   **Sauvegarder HTML** (`Ctrl+S`)
    *   Effectue une sauvegarde rapide du code HTML actuel.
    *   Mémorise le dernier chemin de sauvegarde utilisé.
*   **Sauvegarder HTML sous...** (`Ctrl+Shift+S`)
    *   Permet de choisir un nouvel emplacement et un nom de fichier pour la sauvegarde.
*   **Exporter le code de l'éditeur** (`Ctrl+E`)
    *   Sauvegarde spécifiquement le contenu de l'onglet "Code HTML" dans un fichier.
*   **Quitter** (`Ctrl+Q`)
    *   Ferme l'application.

### 👁️ Menu Affichage

Contrôle l'affichage et le zoom de la page web.

*   **Recharger la page** (`F5`)
    *   Rafraîchit le contenu de `QWebEngineView`.
*   **Zoom avant** (`Ctrl++`)
    *   Agrandit l'affichage de la page web.
*   **Zoom arrière** (`Ctrl+-`)
    *   Réduit l'affichage de la page web.
*   **Réinitialiser zoom** (`Ctrl+0`)
    *   Rétablit le niveau de zoom par défaut (100%).

### 🔧 Menu Outils

Propose des utilitaires pour interagir avec le contenu HTML et l'application.

*   **Exécuter JavaScript personnalisé** (`Ctrl+J`)
    *   Ouvre un dialogue permettant de saisir et d'exécuter du code JavaScript sur la page actuelle.
*   **Inspecter HTML actuel** (`Ctrl+I`)
    *   Affiche des statistiques et des informations sur le HTML actuellement rendu.
*   **Effacer l'historique**
    *   Supprime toutes les versions sauvegardées dans l'historique de génération. Une boîte de dialogue de confirmation est affichée.

### ❓ Menu Aide

Fournit des informations sur l'application et ses fonctionnalités.

*   **À propos**
    *   Affiche des informations générales sur l'application.
*   **Raccourcis clavier** (`F1`)
    *   Présente une liste complète des raccourcis clavier disponibles.

## ✨ Fonctionnalités Clés et Améliorations

*   **Gestion Robuste des Fichiers** : Prise en charge de l'ouverture et de la sauvegarde de fichiers HTML locaux avec gestion d'erreurs et mémorisation du chemin.
*   **Chargement Web Complet** : Capacité de charger n'importe quelle page web via URL, affichant à la fois le rendu et le code source.
*   **Contrôle de l'Affichage** : Fonctions de zoom et de rechargement intégrées pour une navigation fluide.
*   **Outils de Développement** : Exécution de JavaScript personnalisé et inspection HTML facilitent le débogage et l'expérimentation.
*   **Raccourcis Clavier Standardisés** : Toutes les actions courantes sont associées à des raccourcis clavier intuitifs pour une meilleure ergonomie.
*   **Messages de Confirmation** : Des messages visuels confirment les actions importantes (sauvegarde, effacement d'historique).
*   **Logging Intégré** : Toutes les actions de menu sont tracées et affichées dans l'onglet "Logs", assurant un suivi complet de l'activité de l'application.

## 🎮 Exemples d'Utilisation

1.  **Charger une page web existante :**
    *   `Menu` → `Fichier` → `Charger depuis URL`
    *   Entrer : `https://example.com`

2.  **Ouvrir un template HTML local :**
    *   `Menu` → `Fichier` → `Ouvrir HTML local`
    *   Sélectionner votre fichier `.html` ou `.htm`.

3.  **Modifier le code et sauvegarder :**
    *   Modifier le code dans l'onglet "Code HTML".
    *   `Menu` → `Fichier` → `Sauvegarder` (`Ctrl+S`).

4.  **Tester du JavaScript personnalisé :**
    *   `Menu` → `Outils` → `Exécuter JavaScript`
    *   Entrer votre code JavaScript dans la boîte de dialogue.

---
