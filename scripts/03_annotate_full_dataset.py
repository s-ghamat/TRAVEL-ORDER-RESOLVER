"""
Script pour annoter le dataset complet de 10 000 phrases.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_cities() -> List[str]:
    """Charge la liste des villes depuis le fichier JSON."""
    cities_file = Path("data/sncf/villes_list.json")
    with open(cities_file, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_for_matching(text: str) -> str:
    """Normalise un texte pour la correspondance (minuscules, sans accents, sans tirets)."""
    # Convertir en minuscules
    text = text.lower()
    # Remplacer les tirets par des espaces
    text = text.replace("-", " ")
    # Supprimer les accents (approximation simple)
    replacements = {
        "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ò": "o", "ó": "o", "ô": "o", "õ": "o", "ö": "o",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
        "ç": "c", "ñ": "n"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()


def find_city_in_text(text: str, city: str) -> List[Tuple[int, int]]:
    """Trouve toutes les occurrences d'une ville dans le texte (insensible à la casse, tirets, accents)."""
    positions = []
    
    # Normaliser le texte et la ville
    normalized_text = normalize_for_matching(text)
    normalized_city = normalize_for_matching(city)
    
    # Chercher la ville normalisée dans le texte normalisé
    start = 0
    while True:
        pos = normalized_text.find(normalized_city, start)
        if pos == -1:
            break
        
        # Trouver la position réelle dans le texte original
        # Chercher dans le texte original avec différentes variations
        city_variations = [
            city,
            city.lower(),
            city.upper(),
            city.capitalize(),
            city.replace("-", " "),
            city.replace(" ", "-")
        ]
        
        for variation in city_variations:
            # Chercher avec regex insensible à la casse
            pattern = re.escape(variation)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start_pos = match.start()
                end_pos = match.end()
                # Vérifier que c'est un mot complet (pas une partie d'un autre mot)
                if (start_pos == 0 or not text[start_pos-1].isalnum()) and \
                   (end_pos == len(text) or not text[end_pos].isalnum()):
                    positions.append((start_pos, end_pos))
        
        start = pos + 1
    
    # Dédupliquer
    positions = list(set(positions))
    return positions


def extract_origin_destination(text: str, cities: List[str]) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Extrait l'origine et la destination d'une phrase.
    Retourne (origin, destination, is_valid)
    """
    # Mots-clés pour identifier l'origine
    origin_keywords = ["de", "depuis", "à partir de", "en partant de", "quitter"]
    # Mots-clés pour identifier la destination
    dest_keywords = ["à", "vers", "jusqu'à", "pour aller à", "pour se rendre à"]
    
    found_cities = []
    city_positions = {}
    
    # Trouver toutes les villes présentes dans le texte
    for city in cities:
        positions = find_city_in_text(text, city)
        if positions:
            found_cities.append(city)
            city_positions[city] = positions
    
    if len(found_cities) == 0:
        # Aucune ville trouvée
        return None, None, False
    
    if len(found_cities) == 1:
        # Une seule ville trouvée - déterminer si c'est origine ou destination
        city = found_cities[0]
        city_lower = city.lower()
        text_lower = text.lower()
        
        # Chercher les mots-clés autour de la ville
        for keyword in origin_keywords:
            if keyword in text_lower:
                keyword_pos = text_lower.find(keyword)
                city_pos = text_lower.find(city_lower)
                # Si le mot-clé est avant la ville, c'est probablement une origine
                if keyword_pos < city_pos and abs(keyword_pos - city_pos) < 50:
                    return city, None, False
        
        for keyword in dest_keywords:
            if keyword in text_lower:
                keyword_pos = text_lower.find(keyword)
                city_pos = text_lower.find(city_lower)
                # Si le mot-clé est avant la ville, c'est probablement une destination
                if keyword_pos < city_pos and abs(keyword_pos - city_pos) < 50:
                    return None, city, False
        
        # Si on ne peut pas déterminer, considérer comme invalide
        return None, None, False
    
    # Plusieurs villes trouvées - déterminer origine et destination
    text_lower = text.lower()
    
    # Chercher les patterns "de X à Y" ou "depuis X vers Y"
    origin = None
    destination = None
    
    # Pattern 1: "de X à Y" ou "depuis X vers Y"
    for origin_kw in origin_keywords:
        for dest_kw in dest_keywords:
            pattern = f"{origin_kw} (.*?) {dest_kw} (.*?)(?: |$|\\?|!|,|\\.)"
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                origin_candidate = match.group(1).strip()
                dest_candidate = match.group(2).strip()
                
                # Trouver la ville correspondante
                for city in found_cities:
                    if normalize_for_matching(city) in normalize_for_matching(origin_candidate):
                        origin = city
                    if normalize_for_matching(city) in normalize_for_matching(dest_candidate):
                        destination = city
    
    # Pattern 2: ordre inversé "à Y depuis X"
    if not origin or not destination:
        for dest_kw in dest_keywords:
            for origin_kw in origin_keywords:
                pattern = f"{dest_kw} (.*?) {origin_kw} (.*?)(?: |$|\\?|!|,|\\.)"
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    dest_candidate = match.group(1).strip()
                    origin_candidate = match.group(2).strip()
                    
                    for city in found_cities:
                        if normalize_for_matching(city) in normalize_for_matching(origin_candidate):
                            origin = city
                        if normalize_for_matching(city) in normalize_for_matching(dest_candidate):
                            destination = city
    
    # Pattern 3: deux villes consécutives "X Y" (première = origine, deuxième = destination)
    if not origin or not destination:
        for i, city1 in enumerate(found_cities):
            for city2 in found_cities[i+1:]:
                # Chercher si les deux villes sont proches dans le texte
                pos1 = text_lower.find(city1.lower())
                pos2 = text_lower.find(city2.lower())
                if pos1 != -1 and pos2 != -1:
                    # Si la première ville est avant la deuxième
                    if pos1 < pos2 and abs(pos2 - pos1) < 100:
                        origin = city1
                        destination = city2
                        break
            if origin and destination:
                break
    
    # Si on a trouvé origine et destination, la phrase est valide
    if origin and destination:
        return origin, destination, True
    
    # Sinon, invalide
    return origin, destination, False


def annotate_sentence(sentence_id: int, text: str, cities: List[str]) -> Dict:
    """Annote une phrase avec origine, destination et positions."""
    origin, destination, is_valid = extract_origin_destination(text, cities)
    
    entities = []
    
    # Trouver les positions de l'origine
    if origin:
        positions = find_city_in_text(text, origin)
        if positions:
            # Prendre la première occurrence
            start, end = positions[0]
            entities.append({
                "text": text[start:end],
                "label": "ORIGIN",
                "start": start,
                "end": end
            })
    
    # Trouver les positions de la destination
    if destination:
        positions = find_city_in_text(text, destination)
        if positions:
            # Prendre la première occurrence
            start, end = positions[0]
            entities.append({
                "text": text[start:end],
                "label": "DESTINATION",
                "start": start,
                "end": end
            })
    
    return {
        "id": sentence_id,
        "text": text,
        "entities": entities,
        "is_valid": is_valid,
        "origin": origin if origin else None,
        "destination": destination if destination else None
    }


def main():
    """Fonction principale."""
    logger.info("=" * 60)
    logger.info("ANNOTATION DU DATASET COMPLET")
    logger.info("=" * 60)
    
    # Charger les villes
    logger.info("Chargement des villes...")
    cities = load_cities()
    logger.info(f"Nombre de villes chargées : {len(cities)}")
    
    # Charger les phrases générées
    input_file = Path("data/dataset/full/sentences_raw.txt")
    if not input_file.exists():
        logger.error(f"Fichier {input_file} introuvable. Exécutez d'abord 02_generate_full_dataset.py")
        return
    
    logger.info(f"Chargement des phrases depuis {input_file}...")
    sentences = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    sentence_id = int(parts[0])
                    text = parts[1]
                    sentences.append((sentence_id, text))
    
    logger.info(f"Nombre de phrases à annoter : {len(sentences)}")
    
    # Annoter chaque phrase (avec barre de progression)
    annotations = []
    total = len(sentences)
    for idx, (sentence_id, text) in enumerate(sentences, 1):
        if idx % 1000 == 0:
            logger.info(f"Annotation en cours : {idx}/{total} ({idx*100//total}%)")
        annotation = annotate_sentence(sentence_id, text, cities)
        annotations.append(annotation)
    
    # Sauvegarder les annotations
    output_file = Path("data/dataset/full/annotations.json")
    logger.info(f"\nSauvegarde des annotations dans {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(annotations, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Annotations sauvegardées dans {output_file}")
    
    # Statistiques
    valid_count = sum(1 for a in annotations if a["is_valid"])
    invalid_count = len(annotations) - valid_count
    with_origin = sum(1 for a in annotations if a["origin"])
    with_destination = sum(1 for a in annotations if a["destination"])
    
    logger.info(f"\n{'='*60}")
    logger.info("STATISTIQUES")
    logger.info(f"{'='*60}")
    logger.info(f"  - Phrases valides : {valid_count} ({valid_count*100//total}%)")
    logger.info(f"  - Phrases invalides : {invalid_count} ({invalid_count*100//total}%)")
    logger.info(f"  - Phrases avec origine : {with_origin}")
    logger.info(f"  - Phrases avec destination : {with_destination}")
    logger.info(f"\nAnnotation terminée avec succès !")


if __name__ == "__main__":
    main()
