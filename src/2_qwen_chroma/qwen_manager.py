#!/usr/bin/env python3
"""
Qwen2.5 Manager - Gestionnaire LLM Local
Réutilise l'architecture de Virida/phi_manager.py
"""

import os
import logging
from typing import Optional, Dict
from llama_cpp import Llama
from huggingface_hub import hf_hub_download

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenManager:
    """Gestionnaire Qwen2.5 pour extraction NER et génération de dataset"""

    # Configuration du modèle (adaptable selon vos besoins)
    QWEN_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
    QWEN_FILENAME = "qwen2.5-3b-instruct-q4_0.gguf"

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 8192,
        n_threads: int = 4
    ):
        """
        Initialiser Qwen2.5

        Args:
            model_path: Chemin vers le modèle GGUF (ou None pour télécharger)
            n_ctx: Taille du contexte (tokens)
            n_threads: Nombre de threads CPU
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.llm: Optional[Llama] = None

    def download_model(self) -> str:
        """
        Télécharger le modèle depuis HuggingFace

        Returns:
            Chemin vers le modèle téléchargé
        """
        logger.info(f"📦 Téléchargement de {self.QWEN_REPO}/{self.QWEN_FILENAME}")
        logger.info("⏳ Cela peut prendre quelques minutes (~1.7GB)...")

        try:
            model_path = hf_hub_download(
                repo_id=self.QWEN_REPO,
                filename=self.QWEN_FILENAME,
                cache_dir="./models/qwen"
            )
            logger.info(f"✅ Modèle téléchargé: {model_path}")
            return model_path

        except Exception as e:
            logger.error(f"❌ Erreur téléchargement: {e}")
            raise

    def initialize(self) -> bool:
        """
        Initialiser le modèle Qwen2.5

        Returns:
            True si succès
        """
        try:
            # Télécharger si nécessaire
            if not self.model_path or not os.path.exists(self.model_path):
                self.model_path = self.download_model()

            logger.info(f"🔄 Chargement de Qwen2.5 depuis {self.model_path}")

            # Charger le modèle GGUF
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_batch=8,
                use_mmap=True,
                use_mlock=False,
                verbose=False
            )

            logger.info("✅ Qwen2.5 initialisé avec succès")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation: {e}")
            return False

    def generate_response(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.1,
        stop: Optional[list] = None
    ) -> str:
        """
        Générer une réponse avec Qwen2.5

        Args:
            prompt: Prompt système + user
            max_tokens: Nombre max de tokens à générer
            temperature: Créativité (0.0 = déterministe, 1.0 = créatif)
            stop: Liste de tokens d'arrêt

        Returns:
            Réponse générée
        """
        if not self.llm:
            raise RuntimeError("Qwen2.5 non initialisé. Appelez initialize() d'abord.")

        try:
            response = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or ["</s>", "\n\n"],
                echo=False
            )

            text = response['choices'][0]['text'].strip()
            return text

        except Exception as e:
            logger.error(f"❌ Erreur génération: {e}")
            return ""

    def extract_travel_entities(self, sentence: str) -> Dict:
        """
        Extraire départ et arrivée d'une phrase avec Qwen2.5

        Args:
            sentence: Phrase utilisateur

        Returns:
            Dict avec {departure, arrival, valid}
        """
        prompt = f"""Tu es un expert en traitement du langage naturel.
Extrait le lieu de départ et le lieu d'arrivée de cette commande de train.

Phrase : "{sentence}"

Réponds UNIQUEMENT au format JSON suivant (sans autre texte) :
{{"departure": "ville_départ", "arrival": "ville_arrivée", "valid": true}}

Si la phrase n'est pas une commande de train valide, réponds :
{{"departure": "", "arrival": "", "valid": false}}

JSON :"""

        response = self.generate_response(prompt, max_tokens=100, temperature=0.0)

        # Parser le JSON
        import json
        try:
            # Nettoyer la réponse
            response = response.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "")

            result = json.loads(response)
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Erreur parsing JSON: {e}")
            logger.warning(f"Réponse brute: {response}")
            return {"departure": "", "arrival": "", "valid": False}

    def get_stats(self) -> Dict:
        """Obtenir les statistiques du modèle"""
        return {
            "status": "initialized" if self.llm else "not_initialized",
            "model": self.QWEN_REPO,
            "filename": self.QWEN_FILENAME,
            "size": "~1.7GB (Q4_0)",
            "context_window": f"{self.n_ctx} tokens",
            "threads": self.n_threads
        }


# Instance globale
qwen_manager = QwenManager()


def main():
    """Test du Qwen Manager"""
    logger.info("🚀 Test Qwen Manager")

    # Initialiser
    if not qwen_manager.initialize():
        logger.error("❌ Échec initialisation")
        return

    # Tests d'extraction
    test_sentences = [
        "Comment me rendre à Port Boulet depuis Tours ?",
        "Je veux aller de Paris à Lyon",
        "Bonjour comment allez-vous ?",  # Invalide
        "Avec Albert, on voudrait faire Paris-Monaco.",
    ]

    print("\n" + "="*70)
    print("🤖 TEST EXTRACTION QWEN2.5")
    print("="*70)

    for sentence in test_sentences:
        result = qwen_manager.extract_travel_entities(sentence)
        valid = "✅" if result.get("valid") else "❌"
        print(f"{valid} {sentence}")
        print(f"   → Départ: {result.get('departure', 'N/A')}, Arrivée: {result.get('arrival', 'N/A')}")

    print("="*70)


if __name__ == "__main__":
    main()
