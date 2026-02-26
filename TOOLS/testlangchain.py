# ──────────────────────────────────────────────────────────────────────────────
#  Fichier : ollama_langchain_file_tools.py
#  But    : Démontrer l'utilisation de tools lecture/écriture fichier
#           avec un agent LangChain + Ollama
# ──────────────────────────────────────────────────────────────────────────────

import os
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.messages import SystemMessage

# ─── Configuration ───────────────────────────────────────────────────────────

ALLOWED_BASE_DIR = Path.cwd() #/ "ollama_sandbox"          # dossier autorisé
#ALLOWED_BASE_DIR.mkdir(parents=True, exist_ok=True)        # on le crée s'il n'existe pas

print(f"Dossier de travail autorisé : {ALLOWED_BASE_DIR.resolve()}\n")

# ─── Tools ───────────────────────────────────────────────────────────────────

@tool
def read_text_file(file_path: str) -> str:
    """
    Lit intégralement le contenu d'un fichier texte et retourne son contenu.

    Args:
        file_path: Chemin du fichier (relatif au dossier autorisé ou absolu)
                   Exemples valides :
                   - "notes.txt"
                   - "projet/idees.md"
                   - "/home/user/ollama_sandbox/rapport.txt"

    Retourne:
        Le contenu du fichier ou un message d'erreur explicite
    """
    try:
        # Sécurité : on résout toujours par rapport au dossier autorisé
        #full_path = (ALLOWED_BASE_DIR / file_path).resolve()
        # DO NOT PUT IN PRODUCTION...
        full_path = Path(file_path)

        # Vérification stricte qu'on reste dans le dossier autorisé
        #if not full_path.is_relative_to(ALLOWED_BASE_DIR.resolve()):
        #    return f"Erreur de sécurité : le chemin '{file_path}' sort du dossier autorisé !"

        if not full_path.is_file():
            return f"Le fichier '{file_path}' n'existe pas ou n'est pas un fichier."

        encoding = "utf-8"
        try:
            content = full_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            # Dernier recours : on tente latin-1 (souvent utile pour vieux fichiers Windows)
            content = full_path.read_text(encoding="latin-1", errors="replace")

        return content

    except Exception as e:
        return f"Erreur lors de la lecture : {type(e).__name__} → {str(e)}"


@tool
def write_text_file(file_path: str, content: str, append: bool = False) -> str:
    """
    Écrit ou ajoute du texte dans un fichier.

    Args:
        file_path: Chemin du fichier (mêmes règles que read_text_file)
        content:   Texte à écrire / ajouter
        append:    Si True → ajoute à la fin (mode 'a'), sinon écrase (mode 'w')

    Retourne:
        Message de confirmation ou d'erreur
    """
    try:
        # DO NOT PUT IN PRODUCTION...
        full_path = Path(file_path) # (ALLOWED_BASE_DIR / file_path).resolve()

        #if not full_path.is_relative_to(ALLOWED_BASE_DIR.resolve()):
        #    return f"Erreur de sécurité : le chemin '{file_path}' sort du dossier autorisé !"

        # On crée les dossiers parents si nécessaire
        #full_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        encoding = "utf-8"

        print(f"write file {full_path} : {content} ")
        with full_path.open(mode, encoding=encoding) as f:
            f.write(content)

        action = "ajouté à" if append else "écrit dans"
        size = full_path.stat().st_size

        return f"Ok — {size:,} octets {action} '{file_path}'"

    except Exception as e:
        return f"Erreur lors de l'écriture : {type(e).__name__} → {str(e)}"


# ─── Liste des tools disponibles pour l'agent ────────────────────────────────

tools = [read_text_file, write_text_file]


# ─── LLM ─────────────────────────────────────────────────────────────────────

llm = ChatOllama(
    model="qwen3:8b",          # ou mistral-nemo, qwen2.5:14b, etc.
    temperature=0.15,
    # num_ctx=32768,              # décommente si besoin de plus de contexte
)


# ─── Prompt système ──────────────────────────────────────────────────────────

system_prompt = f"""Tu es un assistant très compétent qui aide à manipuler des fichiers texte.

Règles importantes :
- Tu ne peux travailler QUE dans le dossier : {ALLOWED_BASE_DIR}
- N'invente jamais de chemins en dehors de ce dossier
- Quand tu modifies un fichier, dis toujours clairement ce que tu as fait
- Si une opération échoue, explique pourquoi (l'utilisateur doit pouvoir comprendre)
- Sois concis dans tes réponses finales, mais explique ton raisonnement

Tu disposes de deux outils :
- read_text_file
- write_text_file

Utilise-les dès que tu as besoin de lire ou modifier un fichier.
Ne prétends jamais connaître le contenu d'un fichier sans l'avoir lu.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


# ─── Création de l'agent ─────────────────────────────────────────────────────

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,               # pour voir le raisonnement
    handle_parsing_errors=True,
    max_iterations=12,
)


# ─── Boucle de discussion simple (optionnel) ─────────────────────────────────

def chat_loop():
    print("\n=== Agent fichiers prêt ===\n")
    print("Exemples de questions :\n")
    print("• lis le fichier notes.txt")
    print("• crée un fichier todo.md avec 'Faire les courses' dedans")
    print("• ajoute '- Acheter du lait' à todo.md")
    print("• montre-moi le contenu de projet/idees.md\n")

    while True:
        user_input = input("\nVous : ").strip()
        if user_input.lower() in ("quit", "exit", "q", ""):
            print("Au revoir !")
            break

        print("\nAgent réfléchit...\n")

        try:
            result = agent_executor.invoke({"input": user_input})
            print("\nRéponse :", result["output"].strip(), "\n")
        except KeyboardInterrupt:
            print("\nInterrompu.")
            break
        except Exception as e:
            print(f"\nErreur dans l'agent : {e}\n")


if __name__ == "__main__":
    chat_loop()
