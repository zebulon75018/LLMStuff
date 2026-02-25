# Nécessite : pip install ollama
import ollama
import json
import os

# ──── Définition de l'outil ─────────────────────────────────────
def read_file(path: str) -> str:
    # WARNING CHECK THE PATH , DON T PUT IN PRODUCTION
    print("call of read_file")

    print(f"{path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content 
    except Exception as e:
        return f"Erreur lors de la lecture : {str(e)}"

def write_file(path: str, content: str) -> str:
    # WARNING CHECK THE PATH , DON T PUT IN PRODUCTION
    """Écrit du texte dans un fichier. Retourne un message de confirmation ou d'erreur."""
    print("call of write_file")
    try:
        # Option : limiter les dossiers autorisés pour éviter les catastrophes
        allowed_base = os.getcwd();
        
        full_path = os.path.abspath(os.path.join(allowed_base, path.lstrip("/")))
        print(full_path)
        
        if not full_path.startswith(allowed_base):
            return "Erreur de sécurité : chemin non autorisé !"
            
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Fichier écrit avec succès : {full_path}"
    except Exception as e:
        return f"Erreur lors de l'écriture : {str(e)}"


# Description au format OpenAI tools (Ollama le comprend depuis mi-2024)
tools = [{
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Écrit du contenu dans un fichier sur le disque. Utilise des chemins relatifs simples.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Chemin du fichier (ex: readme.md, notes/idee.txt)"
                },
                "content": {
                    "type": "string",
                    "description": "Contenu COMPLET à écrire dans le fichier"
                }
            },
            "required": ["path", "content"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Lit du contenu dans un fichier sur le disque.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Chemin du fichier (ex: readme.md, notes/idee.txt)"
                },
            },
            "required": ["path" ]
        }
    }
}
]

# ──── Boucle agent très basique ─────────────────────────────────
messages = [{
    "role": "system",
    "content": """Tu es un assistant qui peut écrire des fichiers sur le disque.
Quand l'utilisateur te demande d'écrire quelque chose dans un fichier :
→ appelle obligatoirement l'outil write_file
→ ne fais JAMAIS semblant d'écrire le fichier toi-même
→ après l'outil, confirme à l'utilisateur ce qui a été fait"""
}]

print("Pose ta question (tape 'quit' pour arrêter)")

while True:
    user_input = input("→ ")
    if user_input.lower() in ['quit', 'exit', 'q']:
        break
        
    messages.append({"role": "user", "content": user_input})

    while True:
        response = ollama.chat(
            model="llama3.1",          # ou llama3.2, deepseek-r1, etc.
            messages=messages,
            tools=tools,
            options={"temperature": 0.15}
        )
        
        msg = response['message']
        messages.append(msg)

        # Pas de tool call → on affiche et on sort de la boucle interne
        if not msg.get('tool_calls'):
            print("\nRéponse :", msg['content'])
            break

        # Il y a un ou plusieurs tool calls
        for tool in msg['tool_calls']:
            func_name = tool['function']['name']
            args = tool['function']['arguments']

            if func_name == "write_file":
                result = write_file(**args)
            elif func_name == "read_file":
                result = read_file(**args)
            else:
                result = "Outil inconnu"

            print(f"→ Outil {func_name} → {result}")

            # On renvoie le résultat à l'LLM
            messages.append({
                "role": "tool",
                "name": func_name,
                "content": result
            })

    print("-" * 50)
