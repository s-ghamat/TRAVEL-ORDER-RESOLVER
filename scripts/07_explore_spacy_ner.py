"""
Script pour explorer spaCy NER sur les phrases du dataset.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from models.baseline.baseline_model import BaselineModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_spacy_model():
    """Charge le modèle spaCy français."""
    try:
        import spacy
        nlp = spacy.load("fr_core_news_sm")
        return nlp
    except OSError:
        logger.error("Modèle spaCy 'fr_core_news_sm' non trouvé. Exécutez: python -m spacy download fr_core_news_sm")
        return None
    except Exception as e:
        logger.error(f"Erreur lors du chargement de spaCy: {e}")
        return None


def extract_cities_with_spacy(nlp, text: str) -> List[Tuple[str, str, int, int]]:
    """
    Extrait les villes d'une phrase avec spaCy.
    
    Args:
        nlp: Modèle spaCy
        text: Texte à analyser
        
    Returns:
        Liste de tuples (text, label, start, end) pour les entités géographiques
    """
    if nlp is None:
        return []
    
    doc = nlp(text)
    cities = []
    
    for ent in doc.ents:
        # Filtrer les entités géographiques (LOC, GPE)
        if ent.label_ in ["LOC", "GPE"]:
            cities.append((ent.text, ent.label_, ent.start_char, ent.end_char))
    
    return cities


def determine_origin_destination_spacy(cities: List[Tuple[str, str, int, int]], text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Détermine l'origine et la destination à partir des villes détectées par spaCy.
    Utilise les prépositions pour distinguer origine/destination.
    
    Args:
        cities: Liste des villes détectées par spaCy
        text: Texte original
        
    Returns:
        Tuple (origin, destination)
    """
    if len(cities) == 0:
        return None, None
    
    if len(cities) == 1:
        # Une seule ville : essayer de déterminer si c'est origine ou destination
        city_text, _, start, _ = cities[0]
        text_before = text[:start].lower()
        
        # Si "de" ou "depuis" avant, c'est probablement une origine
        if any(kw in text_before for kw in ["de ", "depuis ", "à partir de ", "en partant de "]):
            return city_text, None
        # Si "à" ou "vers" avant, c'est probablement une destination
        elif any(kw in text_before for kw in ["à ", "vers ", "jusqu'à ", "pour aller à "]):
            return None, city_text
        else:
            return None, city_text  # Par défaut, considérer comme destination
    
    # Plusieurs villes : utiliser les prépositions pour déterminer
    origin = None
    destination = None
    
    text_lower = text.lower()
    
    for city_text, label, start, end in cities:
        # Chercher les prépositions avant cette ville
        text_before = text_lower[:start]
        
        # Vérifier si c'est une origine
        if any(kw in text_before[-30:] for kw in ["de ", "depuis ", "à partir de ", "en partant de "]):
            if origin is None:
                origin = city_text
        # Vérifier si c'est une destination
        elif any(kw in text_before[-30:] for kw in ["à ", "vers ", "jusqu'à ", "pour aller à "]):
            if destination is None:
                destination = city_text
        else:
            # Si aucune préposition claire, utiliser l'ordre
            if origin is None:
                origin = city_text
            elif destination is None:
                destination = city_text
    
    # Si on n'a toujours pas les deux, utiliser l'ordre des villes
    if origin is None and len(cities) > 0:
        origin = cities[0][0]
    if destination is None and len(cities) > 1:
        destination = cities[1][0]
    elif destination is None and len(cities) == 1:
        destination = cities[0][0]
    
    return origin, destination


def load_validation_samples(count: int = 10) -> List[Dict]:
    """Charge quelques phrases de validation."""
    validation_file = Path("data/dataset/draft/validation.jsonl")
    sentences = []
    
    if validation_file.exists():
        with open(validation_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= count:
                    break
                if line.strip():
                    sentences.append(json.loads(line))
    else:
        logger.warning(f"Fichier {validation_file} introuvable")
    
    return sentences


def load_cities() -> List[str]:
    """Charge la liste des villes."""
    cities_file = Path("data/sncf/villes_list.json")
    with open(cities_file, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Fonction principale."""
    logger.info("=" * 60)
    logger.info("EXPLORATION SPACY NER")
    logger.info("=" * 60)
    
    # Charger spaCy
    logger.info("Chargement du modèle spaCy...")
    nlp = load_spacy_model()
    
    if nlp is None:
        logger.error("Impossible de charger spaCy. Le script va continuer sans spaCy.")
        logger.info("Note: Il y a peut-être un problème de compatibilité avec Python 3.14")
        logger.info("Vous pouvez essayer avec une version antérieure de Python ou attendre une mise à jour de spaCy")
        return
    
    logger.info("Modèle spaCy chargé avec succès")
    
    # Charger les données
    logger.info("Chargement des phrases de validation...")
    sentences = load_validation_samples(10)
    logger.info(f"Nombre de phrases chargées : {len(sentences)}")
    
    cities_list = load_cities()
    baseline_model = BaselineModel(cities_list)
    
    logger.info("\n" + "=" * 60)
    logger.info("RÉSULTATS DE L'EXPLORATION")
    logger.info("=" * 60)
    
    for sentence in sentences:
        sentence_id = sentence["id"]
        text = sentence["text"]
        true_origin = sentence.get("origin")
        true_destination = sentence.get("destination")
        true_is_valid = sentence.get("is_valid", False)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Phrase {sentence_id}: {text}")
        logger.info(f"Vérité terrain: Origin={true_origin}, Dest={true_destination}, Valid={true_is_valid}")
        
        # Analyse spaCy
        spacy_cities = extract_cities_with_spacy(nlp, text)
        logger.info(f"\nspaCy - Entités détectées ({len(spacy_cities)}):")
        for city_text, label, start, end in spacy_cities:
            logger.info(f"  - {city_text} ({label}) à la position {start}-{end}")
        
        spacy_origin, spacy_dest = determine_origin_destination_spacy(spacy_cities, text)
        logger.info(f"spaCy - Résultat: Origin={spacy_origin}, Dest={spacy_dest}")
        
        # Baseline
        baseline_origin, baseline_dest, baseline_valid = baseline_model.extract_origin_destination(text)
        logger.info(f"Baseline - Résultat: Origin={baseline_origin}, Dest={baseline_dest}, Valid={baseline_valid}")
        
        # Comparaison
        spacy_correct = (spacy_origin == true_origin or (spacy_origin is None and true_origin is None)) and \
                       (spacy_dest == true_destination or (spacy_dest is None and true_destination is None))
        baseline_correct = (baseline_origin == true_origin or (baseline_origin is None and true_origin is None)) and \
                          (baseline_dest == true_destination or (baseline_dest is None and true_destination is None))
        
        logger.info(f"\nComparaison:")
        logger.info(f"  spaCy correct    : {spacy_correct}")
        logger.info(f"  Baseline correct : {baseline_correct}")
    
    logger.info("\n" + "=" * 60)
    logger.info("EXPLORATION TERMINÉE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
