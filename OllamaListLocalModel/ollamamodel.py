#!/usr/bin/env python3
"""
Méthodes pour lister les modèles Ollama locaux
"""

import requests
import json
from typing import List, Dict


def get_ollama_models(base_url: str = "http://localhost:11434") -> List[str]:
    """
    Récupère la liste des noms de modèles Ollama disponibles localement
    
    Args:
        base_url: URL du serveur Ollama (défaut: http://localhost:11434)
    
    Returns:
        Liste des noms de modèles disponibles
    
    Example:
        >>> models = get_ollama_models()
        >>> print(models)
        ['llama3', 'mistral', 'codellama']
    """
    try:
        response = requests.get(f"{base_url}/api/tags")
        response.raise_for_status()
        
        data = response.json()
        models = [model['name'] for model in data.get('models', [])]
        
        return models
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Erreur: Impossible de se connecter à Ollama sur {base_url}")
        print("   Assurez-vous qu'Ollama est démarré (ollama serve)")
        return []
    
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des modèles: {e}")
        return []


def get_ollama_models_detailed(base_url: str = "http://localhost:11434") -> List[Dict]:
    """
    Récupère la liste détaillée des modèles Ollama avec leurs informations
    
    Args:
        base_url: URL du serveur Ollama (défaut: http://localhost:11434)
    
    Returns:
        Liste de dictionnaires contenant les détails de chaque modèle
    
    Example:
        >>> models = get_ollama_models_detailed()
        >>> for model in models:
        ...     print(f"{model['name']} - {model['size_gb']:.2f} GB")
    """
    try:
        response = requests.get(f"{base_url}/api/tags")
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
        
        return models_info
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Erreur: Impossible de se connecter à Ollama sur {base_url}")
        print("   Assurez-vous qu'Ollama est démarré (ollama serve)")
        return []
    
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des modèles: {e}")
        return []


def print_available_models(base_url: str = "http://localhost:11434"):
    """
    Affiche la liste des modèles Ollama disponibles de manière formatée
    
    Args:
        base_url: URL du serveur Ollama (défaut: http://localhost:11434)
    
    Example:
        >>> print_available_models()
        Modèles Ollama disponibles:
        ============================
        1. llama3 (4.2 GB)
        2. mistral (7.1 GB)
        3. codellama (3.8 GB)
    """
    models = get_ollama_models_detailed(base_url)
    
    if not models:
        print("Aucun modèle trouvé ou Ollama n'est pas accessible.")
        return
    
    print("\nModèles Ollama disponibles:")
    print("=" * 60)
    
    for i, model in enumerate(models, 1):
        size_str = f"{model['size_gb']:.2f} GB" if model['size_gb'] > 0 else "Taille inconnue"
        print(f"{i}. {model['name']:30} ({size_str})")
    
    print("=" * 60)
    print(f"Total: {len(models)} modèle(s)\n")


def check_model_exists(model_name: str, base_url: str = "http://localhost:11434") -> bool:
    """
    Vérifie si un modèle spécifique existe localement
    
    Args:
        model_name: Nom du modèle à vérifier
        base_url: URL du serveur Ollama
    
    Returns:
        True si le modèle existe, False sinon
    
    Example:
        >>> if check_model_exists("llama3"):
        ...     print("Modèle disponible!")
    """
    models = get_ollama_models(base_url)
    return model_name in models


# ============================================================================
# Exemple d'utilisation
# ============================================================================

if __name__ == "__main__":
    print("🦙 Vérification des modèles Ollama locaux\n")
    
    # Méthode 1: Liste simple des noms
    print("📋 Liste simple:")
    models = get_ollama_models()
    if models:
        for model in models:
            print(f"  - {model}")
    print()
    
    # Méthode 2: Liste détaillée formatée
    print_available_models()
    
    # Méthode 3: Vérifier un modèle spécifique
    model_to_check = "llama3"
    if check_model_exists(model_to_check):
        print(f"✓ Le modèle '{model_to_check}' est disponible")
    else:
        print(f"✗ Le modèle '{model_to_check}' n'est pas installé")
        print(f"  Installez-le avec: ollama pull {model_to_check}")
    
    print()
    
    # Méthode 4: Informations détaillées
    print("📊 Informations détaillées:")
    detailed_models = get_ollama_models_detailed()
    for model in detailed_models:
        print(f"\n  Modèle: {model['name']}")
        print(f"  Taille: {model['size_gb']:.2f} GB")
        print(f"  Modifié: {model['modified_at']}")
        print(f"  Digest: {model['digest']}")
