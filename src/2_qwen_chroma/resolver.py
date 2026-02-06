#!/usr/bin/env python3
"""
Phase 2.3 - Résolveur intelligent avec Qwen2.5 + ChromaDB
Approche moderne : LLM + RAG pour extraction robuste
"""

import logging
from typing import Dict, Optional
from .qwen_manager import qwen_manager
from .chroma_manager import chroma_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenTravelOrderResolver:
    """Résolveur intelligent avec Qwen2.5 + ChromaDB (RAG)"""

    def __init__(
        self,
        confidence_threshold: float = 0.65,
        use_rag_validation: bool = True
    ):
        """
        Initialiser le résolveur

        Args:
            confidence_threshold: Seuil de confiance pour valider (0-1)
            use_rag_validation: Utiliser ChromaDB pour validation
        """
        self.confidence_threshold = confidence_threshold
        self.use_rag_validation = use_rag_validation
        self.initialized = False

    def initialize(self) -> bool:
        """Initialiser Qwen2.5 et ChromaDB"""
        try:
            logger.info("🚀 Initialisation du résolveur Qwen2.5 + ChromaDB...")

            # Initialiser Qwen2.5
            if not qwen_manager.initialize():
                logger.error("❌ Échec init Qwen2.5")
                return False

            # Initialiser ChromaDB (si RAG activé)
            if self.use_rag_validation:
                if not chroma_manager.initialize():
                    logger.error("❌ Échec init ChromaDB")
                    return False

            self.initialized = True
            logger.info("✅ Résolveur initialisé avec succès")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            return False

    def resolve_with_rag(self, text: str) -> Dict:
        """
        Résoudre avec RAG (Retrieval-Augmented Generation)

        Étapes:
        1. Rechercher exemples similaires dans ChromaDB
        2. Extraire avec Qwen2.5 (few-shot avec exemples)
        3. Valider avec score de similarité

        Args:
            text: Phrase utilisateur

        Returns:
            Dict avec {departure, arrival, valid, confidence, method}
        """
        # 1. Recherche d'exemples similaires
        similar_examples = chroma_manager.search_similar(text, limit=3)

        if not similar_examples or similar_examples[0]['score'] < 0.5:
            # Pas d'exemples pertinents, extraction directe
            logger.debug(f"⚠️ Pas d'exemples similaires (score < 0.5)")
            return self.resolve_direct(text)

        # 2. Few-shot prompting avec exemples
        examples_text = "\n".join([
            f"Phrase: \"{ex['sentence']}\" -> Départ: \"{ex['departure']}\", Arrivée: \"{ex['arrival']}\""
            for ex in similar_examples[:2]  # Top 2 exemples
        ])

        prompt = f"""Tu es un expert en extraction d'informations de voyage.
Voici des exemples de phrases similaires et leurs extractions :

{examples_text}

Maintenant, extrait le départ et l'arrivée de cette nouvelle phrase :
Phrase: "{text}"

Réponds UNIQUEMENT au format JSON (sans texte supplémentaire) :
{{"departure": "ville_départ", "arrival": "ville_arrivée", "valid": true}}

Si ce n'est pas une commande de train valide :
{{"departure": "", "arrival": "", "valid": false}}

JSON:"""

        response = qwen_manager.generate_response(prompt, max_tokens=100, temperature=0.0)

        # 3. Parser et valider
        try:
            import json
            response = response.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "")

            result = json.loads(response)

            # Calculer confiance basée sur similarité
            confidence = similar_examples[0]['score']

            result['confidence'] = confidence
            result['method'] = 'rag'
            result['rag_score'] = confidence

            # Valider avec seuil
            if confidence < self.confidence_threshold:
                logger.debug(f"⚠️ Confiance faible: {confidence:.3f} < {self.confidence_threshold}")
                result['valid'] = False

            return result

        except Exception as e:
            logger.warning(f"⚠️ Erreur parsing avec RAG: {e}")
            return self.resolve_direct(text)

    def resolve_direct(self, text: str) -> Dict:
        """
        Résoudre directement avec Qwen2.5 (sans RAG)

        Args:
            text: Phrase utilisateur

        Returns:
            Dict avec extraction
        """
        result = qwen_manager.extract_travel_entities(text)
        result['confidence'] = 0.5  # Confiance par défaut
        result['method'] = 'direct'
        result['rag_score'] = 0.0
        return result

    def resolve(self, sentence: str) -> str:
        """
        Résoudre une commande complète

        Format entrée: "sentenceID,texte"
        Format sortie: "sentenceID,Départ,Arrivée" ou "sentenceID,INVALID"

        Args:
            sentence: Ligne au format CSV

        Returns:
            Résultat formaté
        """
        if not self.initialized:
            raise RuntimeError("Résolveur non initialisé. Appelez initialize() d'abord.")

        # Parser l'entrée
        parts = sentence.split(',', 1)
        if len(parts) != 2:
            return "?,INVALID,ERROR_FORMAT"

        sentence_id = parts[0].strip()
        text = parts[1].strip()

        # Résoudre avec ou sans RAG
        if self.use_rag_validation and chroma_manager.initialized:
            result = self.resolve_with_rag(text)
        else:
            result = self.resolve_direct(text)

        # Formater la sortie
        if result.get('valid') and result.get('departure') and result.get('arrival'):
            confidence = result.get('confidence', 0.0)
            method = result.get('method', 'unknown')
            logger.info(
                f"✅ {sentence_id}: {result['departure']} -> {result['arrival']} "
                f"(conf: {confidence:.2f}, method: {method})"
            )
            return f"{sentence_id},{result['departure']},{result['arrival']}"
        else:
            logger.debug(f"❌ {sentence_id}: INVALID")
            return f"{sentence_id},INVALID"

    def resolve_batch(self, input_file: str, output_file: str):
        """
        Traiter un fichier de commandes

        Args:
            input_file: Fichier d'entrée (sentenceID,texte)
            output_file: Fichier de sortie
        """
        if not self.initialized:
            raise RuntimeError("Résolveur non initialisé.")

        logger.info(f"📂 Traitement de {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        results = []
        for line in lines:
            line = line.strip()
            if line:
                result = self.resolve(line)
                results.append(result)

        # Écrire résultats
        with open(output_file, 'w', encoding='utf-8') as f:
            f_out.write('\n'.join(results))

        logger.info(f"✅ {len(results)} commandes traitées")
        logger.info(f"📁 Résultats: {output_file}")


def main():
    """Test du résolveur Qwen2.5 + ChromaDB"""
    resolver = QwenTravelOrderResolver(
        confidence_threshold=0.65,
        use_rag_validation=True
    )

    # Initialiser
    if not resolver.initialize():
        logger.error("❌ Échec initialisation")
        return

    # Tests
    test_sentences = [
        "1,Comment me rendre à Port Boulet depuis Tours ?",
        "2,Je veux aller de Paris à Lyon",
        "3,Je souhaite me rendre à Paris depuis Toulouse",
        "4,A quelle heure y a-t-il des trains vers Paris en partance de Toulouse ?",
        "5,Avec mes amis florence et paris, je voudrais aller de paris a florence.",
        "6,Bonjour comment allez-vous ?",  # Invalide
        "7,Trajet Marseille Nice",
    ]

    print("\n" + "="*70)
    print("🤖 TEST RÉSOLVEUR QWEN2.5 + CHROMADB")
    print("="*70)

    for sentence in test_sentences:
        result = resolver.resolve(sentence)
        print(f"➜ {result}")

    print("="*70)


if __name__ == "__main__":
    main()
