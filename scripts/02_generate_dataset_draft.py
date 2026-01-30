"""
Script pour générer un draft de dataset de phrases à partir des templates.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_templates() -> Dict:
    """Charge les templates depuis le fichier JSON."""
    templates_file = Path("data/templates/sentence_templates.json")
    with open(templates_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cities() -> List[str]:
    """Charge la liste des villes depuis le fichier JSON."""
    cities_file = Path("data/sncf/villes_list.json")
    with open(cities_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ambiguous_cities() -> List[str]:
    """Charge la liste des villes ambiguës."""
    ambiguous_file = Path("data/sncf/villes_ambiguës.json")
    with open(ambiguous_file, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_case_variation(text: str) -> str:
    """Applique des variations de casse."""
    variation_type = random.choice(["lower", "upper_first", "mixed", "keep"])
    
    if variation_type == "lower":
        return text.lower()
    elif variation_type == "upper_first":
        return text[0].upper() + text[1:].lower() if len(text) > 1 else text.upper()
    elif variation_type == "mixed":
        # Mélange majuscules/minuscules de manière aléatoire
        result = ""
        for char in text:
            if char.isalpha():
                result += char.lower() if random.random() < 0.5 else char.upper()
            else:
                result += char
        return result
    else:
        return text


def apply_tiret_variation(text: str) -> str:
    """Applique des variations de tirets (Saint-Denis vs saint denis)."""
    if "-" in text:
        if random.random() < 0.3:  # 30% de chance de remplacer par espace
            return text.replace("-", " ")
    elif " " in text and any(word.lower().startswith("saint") or word.lower().startswith("port") for word in text.split()):
        if random.random() < 0.2:  # 20% de chance d'ajouter un tiret
            words = text.split()
            for i, word in enumerate(words):
                if word.lower().startswith("saint") or word.lower().startswith("port"):
                    if i + 1 < len(words):
                        words[i] = word + "-" + words[i+1]
                        words.pop(i+1)
                        break
            return " ".join(words)
    return text


def apply_typo_variation(text: str) -> str:
    """Applique des fautes d'orthographe légères."""
    if random.random() < 0.15:  # 15% de chance d'avoir une faute
        # Supprimer une lettre aléatoire (sauf la première)
        if len(text) > 3:
            pos = random.randint(1, len(text) - 2)
            return text[:pos] + text[pos+1:]
    return text


def apply_variations(text: str) -> str:
    """Applique toutes les variations possibles."""
    text = apply_tiret_variation(text)
    text = apply_typo_variation(text)
    text = apply_case_variation(text)
    return text


def generate_valid_sentences(templates: Dict, cities: List[str], count: int) -> List[str]:
    """Génère des phrases valides avec origine et destination."""
    sentences = []
    
    # Combiner tous les templates valides
    all_templates = []
    for category in ["valides_directes", "valides_interrogatives", "valides_avec_contexte", "valides_ordre_inverse"]:
        if category in templates:
            for template_group in templates[category]:
                if isinstance(template_group, dict) and "template" in template_group:
                    all_templates.append(template_group["template"])
                    if "variations" in template_group:
                        all_templates.extend(template_group["variations"])
                elif isinstance(template_group, str):
                    all_templates.append(template_group)
    
    logger.info(f"Nombre de templates valides disponibles : {len(all_templates)}")
    
    for i in range(count):
        # Choisir un template aléatoire
        template = random.choice(all_templates)
        
        # Choisir deux villes différentes
        origin = random.choice(cities)
        destination = random.choice(cities)
        while destination == origin:
            destination = random.choice(cities)
        
        # Remplacer les placeholders
        sentence = template.replace("{origin}", origin).replace("{destination}", destination)
        
        # Appliquer des variations
        sentence = apply_variations(sentence)
        
        sentences.append(sentence)
    
    return sentences


def generate_invalid_sentences(templates: Dict, cities: List[str], count: int) -> List[str]:
    """Génère des phrases invalides (sans origine ou sans destination)."""
    sentences = []
    
    # Combiner tous les templates invalides
    all_templates_no_origin = []
    all_templates_no_dest = []
    all_templates_unrelated = []
    
    if "invalides_sans_origine" in templates:
        for template_group in templates["invalides_sans_origine"]:
            if isinstance(template_group, dict) and "template" in template_group:
                all_templates_no_origin.append(template_group["template"])
                if "variations" in template_group:
                    all_templates_no_origin.extend(template_group["variations"])
            elif isinstance(template_group, str):
                all_templates_no_origin.append(template_group)
    
    if "invalides_sans_destination" in templates:
        for template_group in templates["invalides_sans_destination"]:
            if isinstance(template_group, dict) and "template" in template_group:
                all_templates_no_dest.append(template_group["template"])
                if "variations" in template_group:
                    all_templates_no_dest.extend(template_group["variations"])
            elif isinstance(template_group, str):
                all_templates_no_dest.append(template_group)
    
    if "invalides_phrases_non_liees" in templates:
        all_templates_unrelated = templates["invalides_phrases_non_liees"]
    
    logger.info(f"Templates invalides - sans origine: {len(all_templates_no_origin)}, sans destination: {len(all_templates_no_dest)}, non liées: {len(all_templates_unrelated)}")
    
    # Générer environ 1/3 de chaque type
    no_origin_count = count // 3
    no_dest_count = count // 3
    unrelated_count = count - no_origin_count - no_dest_count
    
    # Phrases sans origine
    for i in range(no_origin_count):
        template = random.choice(all_templates_no_origin)
        destination = random.choice(cities)
        sentence = template.replace("{destination}", destination)
        sentence = apply_variations(sentence)
        sentences.append(sentence)
    
    # Phrases sans destination
    for i in range(no_dest_count):
        template = random.choice(all_templates_no_dest)
        origin = random.choice(cities)
        sentence = template.replace("{origin}", origin)
        sentence = apply_variations(sentence)
        sentences.append(sentence)
    
    # Phrases non liées
    for i in range(unrelated_count):
        sentence = random.choice(all_templates_unrelated)
        sentence = apply_variations(sentence)
        sentences.append(sentence)
    
    return sentences


def generate_ambiguous_sentences(templates: Dict, cities: List[str], ambiguous_cities: List[str], count: int) -> List[str]:
    """Génère des phrases avec ambiguïtés (prénoms, mots communs)."""
    sentences = []
    
    # Prénoms communs français
    common_names = ["Albert", "Pierre", "Marie", "Jean", "Paul", "Louis", "Henri", "François", "Claude", "Bernard"]
    
    # Combiner tous les templates d'ambiguïté
    all_templates_prenoms = []
    all_templates_mots_communs = []
    
    if "ambiguites_prenoms" in templates:
        for template_group in templates["ambiguites_prenoms"]:
            if isinstance(template_group, dict) and "template" in template_group:
                all_templates_prenoms.append(template_group["template"])
                if "variations" in template_group:
                    all_templates_prenoms.extend(template_group["variations"])
    
    if "ambiguites_mots_communs" in templates:
        for template_group in templates["ambiguites_mots_communs"]:
            if isinstance(template_group, dict) and "template" in template_group:
                all_templates_mots_communs.append(template_group["template"])
                if "variations" in template_group:
                    all_templates_mots_communs.extend(template_group["variations"])
    
    logger.info(f"Templates ambiguïtés - prénoms: {len(all_templates_prenoms)}, mots communs: {len(all_templates_mots_communs)}")
    
    # Générer environ 60% avec prénoms, 40% avec mots communs
    prenoms_count = int(count * 0.6)
    mots_communs_count = count - prenoms_count
    
    # Phrases avec prénoms
    for i in range(prenoms_count):
        template = random.choice(all_templates_prenoms)
        name = random.choice(common_names)
        origin = random.choice(cities)
        destination = random.choice(cities)
        while destination == origin:
            destination = random.choice(cities)
        
        # Remplacer les placeholders
        sentence = template.replace("{name}", name)
        if "{name1}" in sentence and "{name2}" in sentence:
            name1 = random.choice(common_names)
            name2 = random.choice(common_names)
            while name2 == name1:
                name2 = random.choice(common_names)
            sentence = sentence.replace("{name1}", name1).replace("{name2}", name2)
        sentence = sentence.replace("{origin}", origin).replace("{destination}", destination)
        
        sentence = apply_variations(sentence)
        sentences.append(sentence)
    
    # Phrases avec mots communs (Port-Boulet, etc.)
    for i in range(mots_communs_count):
        template = random.choice(all_templates_mots_communs)
        origin = random.choice(cities)
        destination = random.choice(cities)
        while destination == origin:
            destination = random.choice(cities)
        
        sentence = template.replace("{origin}", origin).replace("{destination}", destination)
        sentence = apply_variations(sentence)
        sentences.append(sentence)
    
    return sentences


def main():
    """Fonction principale."""
    logger.info("Début de la génération du dataset")
    
    # Charger les données
    logger.info("Chargement des templates...")
    templates = load_templates()
    
    logger.info("Chargement des villes...")
    cities = load_cities()
    logger.info(f"Nombre de villes disponibles : {len(cities)}")
    
    logger.info("Chargement des villes ambiguës...")
    ambiguous_cities = load_ambiguous_cities()
    logger.info(f"Nombre de villes ambiguës : {len(ambiguous_cities)}")
    
    # Générer les phrases selon la répartition
    logger.info("Génération des phrases valides (70)...")
    valid_sentences = generate_valid_sentences(templates, cities, 70)
    
    logger.info("Génération des phrases invalides (20)...")
    invalid_sentences = generate_invalid_sentences(templates, cities, 20)
    
    logger.info("Génération des phrases avec ambiguïtés (10)...")
    ambiguous_sentences = generate_ambiguous_sentences(templates, cities, ambiguous_cities, 10)
    
    # Combiner toutes les phrases
    all_sentences = valid_sentences + invalid_sentences + ambiguous_sentences
    
    # Mélanger
    random.shuffle(all_sentences)
    
    # Sauvegarder
    output_file = Path("data/dataset/draft/sentences_raw.txt")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for i, sentence in enumerate(all_sentences, 1):
            f.write(f"{i},{sentence}\n")
    
    logger.info(f"Dataset généré : {len(all_sentences)} phrases sauvegardées dans {output_file}")
    logger.info(f"  - Phrases valides : {len(valid_sentences)}")
    logger.info(f"  - Phrases invalides : {len(invalid_sentences)}")
    logger.info(f"  - Phrases avec ambiguïtés : {len(ambiguous_sentences)}")
    
    # Afficher quelques exemples
    logger.info("\nExemples de phrases générées :")
    for i, sentence in enumerate(all_sentences[:5], 1):
        logger.info(f"  {i}. {sentence}")


if __name__ == "__main__":
    main()
