#!/usr/bin/env python3
"""
Phase 1.4 - Résolveur de commandes avec spaCy
Système complet: Entrée texte -> Extraction départ/arrivée
"""

import spacy
import re
from typing import Optional, Tuple, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpacyTravelOrderResolver:
    """Résolveur de commandes de voyage avec spaCy"""

    # Mots-clés pour détecter départ
    DEPARTURE_KEYWORDS = [
        "de", "depuis", "partir de", "départ de", "en partance de",
        "partant de", "provenance", "venant de"
    ]

    # Mots-clés pour détecter arrivée
    ARRIVAL_KEYWORDS = [
        "à", "vers", "pour", "arrivée à", "destination", "direction",
        "aller à", "me rendre à", "rejoindre"
    ]

    def __init__(self, model_name: str = "fr_core_news_md"):
        """
        Initialiser le résolveur

        Args:
            model_name: Modèle spaCy français
        """
        logger.info(f"🔄 Chargement du modèle spaCy: {model_name}")
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"✅ Résolveur initialisé avec {model_name}")
        except OSError:
            logger.error(f"❌ Modèle {model_name} non trouvé.")
            logger.error(f"   Installez-le: python -m spacy download {model_name}")
            raise

    def extract_locations(self, text: str) -> List[Dict]:
        """
        Extraire toutes les entités de type location (LOC, GPE)

        Args:
            text: Phrase à analyser

        Returns:
            Liste des locations avec position et texte
        """
        doc = self.nlp(text)
        locations = []

        for ent in doc.ents:
            # LOC = location, GPE = geopolitical entity (villes, pays)
            if ent.label_ in ["LOC", "GPE"]:
                locations.append({
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "label": ent.label_
                })

        return locations

    def detect_departure_arrival(
        self,
        text: str,
        locations: List[Dict]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Détecter départ et arrivée via règles linguistiques

        Stratégie:
        1. Chercher mots-clés ("de", "à", "depuis", "vers")
        2. Associer location la plus proche au mot-clé
        3. Ordre par défaut: première location = départ, dernière = arrivée

        Args:
            text: Phrase originale
            locations: Liste des locations extraites

        Returns:
            Tuple (départ, arrivée) ou (None, None) si invalide
        """
        if len(locations) < 2:
            # Besoin d'au moins 2 locations
            return None, None

        text_lower = text.lower()
        departure = None
        arrival = None

        # Stratégie 1: Chercher mots-clés de départ
        for keyword in self.DEPARTURE_KEYWORDS:
            if keyword in text_lower:
                # Trouver position du keyword
                keyword_pos = text_lower.find(keyword)
                # Chercher la location la plus proche APRÈS le keyword
                closest_loc = None
                min_distance = float('inf')

                for loc in locations:
                    distance = loc['start'] - (keyword_pos + len(keyword))
                    if 0 <= distance < min_distance:
                        min_distance = distance
                        closest_loc = loc['text']

                if closest_loc:
                    departure = closest_loc
                    break

        # Stratégie 2: Chercher mots-clés d'arrivée
        for keyword in self.ARRIVAL_KEYWORDS:
            if keyword in text_lower:
                keyword_pos = text_lower.find(keyword)
                closest_loc = None
                min_distance = float('inf')

                for loc in locations:
                    distance = loc['start'] - (keyword_pos + len(keyword))
                    if 0 <= distance < min_distance:
                        min_distance = distance
                        closest_loc = loc['text']

                if closest_loc:
                    arrival = closest_loc
                    break

        # Stratégie 3: Ordre par défaut (si pas de keywords trouvés)
        if not departure and len(locations) >= 2:
            departure = locations[0]['text']

        if not arrival and len(locations) >= 2:
            arrival = locations[-1]['text']

        # Vérifier que départ != arrivée
        if departure and arrival and departure == arrival:
            return None, None

        return departure, arrival

    def resolve(self, sentence: str) -> str:
        """
        Résoudre une commande de voyage

        Format de sortie:
        - Valide: "sentenceID,Départ,Arrivée"
        - Invalide: "sentenceID,INVALID"

        Args:
            sentence: Phrase au format "sentenceID,texte"

        Returns:
            Résultat formaté
        """
        # Parser l'entrée
        parts = sentence.split(',', 1)
        if len(parts) != 2:
            return f"?,INVALID,ERROR_FORMAT"

        sentence_id = parts[0].strip()
        text = parts[1].strip()

        # Extraire les locations
        locations = self.extract_locations(text)

        if len(locations) < 2:
            logger.debug(f"❌ Pas assez de locations: {len(locations)}")
            return f"{sentence_id},INVALID,NOT_ENOUGH_LOCATIONS"

        # Détecter départ et arrivée
        departure, arrival = self.detect_departure_arrival(text, locations)

        if not departure or not arrival:
            logger.debug(f"❌ Impossible de déterminer départ/arrivée")
            return f"{sentence_id},INVALID,AMBIGUOUS"

        logger.info(f"✅ {sentence_id}: {departure} -> {arrival}")
        return f"{sentence_id},{departure},{arrival}"

    def resolve_batch(self, input_file: str, output_file: str):
        """
        Résoudre un fichier de commandes

        Args:
            input_file: Fichier d'entrée (sentenceID,texte par ligne)
            output_file: Fichier de sortie
        """
        logger.info(f"📂 Traitement de {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f_in:
            lines = f_in.readlines()

        results = []
        for line in lines:
            line = line.strip()
            if line:
                result = self.resolve(line)
                results.append(result)

        # Écrire les résultats
        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.write('\n'.join(results))

        logger.info(f"✅ Résultats écrits dans {output_file}")
        logger.info(f"📊 {len(results)} commandes traitées")


def main():
    """Test du résolveur"""
    resolver = SpacyTravelOrderResolver()

    # Tests
    test_sentences = [
        "1,Comment me rendre à Port Boulet depuis Tours ?",
        "2,Je veux aller de Paris à Lyon",
        "3,Je souhaite me rendre à Paris depuis Toulouse",
        "4,A quelle heure y a-t-il des trains vers Paris en partance de Toulouse ?",
        "5,Avec mes amis florence et paris, je voudrais aller de paris a florence.",
        "6,Bonjour comment allez-vous ?",  # Invalide
    ]

    print("\n" + "="*70)
    print("🚂 TEST DU RÉSOLVEUR spaCy")
    print("="*70)

    for sentence in test_sentences:
        result = resolver.resolve(sentence)
        print(f"➜ {result}")

    print("="*70)


if __name__ == "__main__":
    main()
