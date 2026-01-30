"""
Script pour évaluer la baseline sur le dataset de validation.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Tuple
import logging
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from models.baseline.baseline_model import BaselineModel
from evaluation.metrics import (
    calculate_metrics_for_label,
    calculate_exact_match,
    calculate_valid_invalid_detection
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_validation_data() -> Tuple[List[Dict], List[Dict]]:
    """
    Charge les données de validation (phrases et labels).
    
    Returns:
        Tuple (sentences, labels) où chaque élément est une liste de dictionnaires
    """
    data_dir = Path("data/dataset/draft")
    
    # Charger les phrases depuis JSONL
    sentences = []
    validation_file = data_dir / "validation.jsonl"
    if validation_file.exists():
        with open(validation_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    sentences.append(json.loads(line))
    else:
        # Fallback : charger depuis CSV
        csv_file = data_dir / "validation.csv"
        if csv_file.exists():
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sentences.append({
                        "id": int(row["id"]),
                        "text": row["text"]
                    })
    
    # Charger les labels depuis CSV
    labels = []
    labels_file = data_dir / "validation_labels.csv"
    if labels_file.exists():
        with open(labels_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                labels.append({
                    "id": int(row["id"]),
                    "origin": row["origin"] if row["origin"] else None,
                    "destination": row["destination"] if row["destination"] else None,
                    "is_valid": row["is_valid"].lower() == "true" if row["is_valid"] else False
                })
    
    # Trier par ID pour correspondance
    sentences.sort(key=lambda x: x["id"])
    labels.sort(key=lambda x: x["id"])
    
    return sentences, labels


def load_cities() -> List[str]:
    """Charge la liste des villes."""
    cities_file = Path("data/sncf/villes_list.json")
    with open(cities_file, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_baseline(model: BaselineModel, sentences: List[Dict], labels: List[Dict]) -> Dict:
    """
    Évalue la baseline sur les phrases de validation.
    
    Args:
        model: Modèle baseline
        sentences: Liste des phrases
        labels: Liste des labels réels
        
    Returns:
        Dictionnaire avec toutes les métriques
    """
    predictions_origin = []
    predictions_dest = []
    predictions_is_valid = []
    
    ground_truth_origin = []
    ground_truth_dest = []
    ground_truth_is_valid = []
    
    logger.info(f"Évaluation sur {len(sentences)} phrases...")
    
    # Créer un dictionnaire pour accès rapide aux labels
    labels_dict = {label["id"]: label for label in labels}
    
    # Faire les prédictions
    for sentence in sentences:
        sentence_id = sentence["id"]
        text = sentence["text"]
        
        # Prédiction
        pred_id, pred_origin, pred_dest = model.predict(sentence_id, text)
        predictions_origin.append(pred_origin)
        predictions_dest.append(pred_dest)
        predictions_is_valid.append(pred_origin != "INVALID" and pred_dest != "")
        
        # Ground truth
        if sentence_id in labels_dict:
            label = labels_dict[sentence_id]
            ground_truth_origin.append(label["origin"] if label["origin"] else "")
            ground_truth_dest.append(label["destination"] if label["destination"] else "")
            ground_truth_is_valid.append(label["is_valid"])
        else:
            logger.warning(f"Label manquant pour la phrase {sentence_id}")
            ground_truth_origin.append("")
            ground_truth_dest.append("")
            ground_truth_is_valid.append(False)
    
    # Calculer les métriques
    logger.info("Calcul des métriques...")
    
    metrics_origin = calculate_metrics_for_label(
        predictions_origin, ground_truth_origin, "ORIGIN"
    )
    metrics_dest = calculate_metrics_for_label(
        predictions_dest, ground_truth_dest, "DESTINATION"
    )
    
    exact_match_rate = calculate_exact_match(
        predictions_origin, predictions_dest,
        ground_truth_origin, ground_truth_dest
    )
    
    valid_invalid_metrics = calculate_valid_invalid_detection(
        predictions_is_valid, ground_truth_is_valid
    )
    
    # Compiler tous les résultats
    results = {
        "total_phrases": len(sentences),
        "origin_metrics": metrics_origin,
        "destination_metrics": metrics_dest,
        "exact_match_rate": exact_match_rate,
        "valid_invalid_detection": valid_invalid_metrics,
        "summary": {
            "origin_precision": metrics_origin["precision"],
            "origin_recall": metrics_origin["recall"],
            "origin_f1": metrics_origin["f1_score"],
            "destination_precision": metrics_dest["precision"],
            "destination_recall": metrics_dest["recall"],
            "destination_f1": metrics_dest["f1_score"],
            "exact_match": exact_match_rate,
            "valid_detection_rate": valid_invalid_metrics["valid_detection_rate"],
            "invalid_detection_rate": valid_invalid_metrics["invalid_detection_rate"]
        }
    }
    
    return results


def main():
    """Fonction principale."""
    logger.info("=" * 60)
    logger.info("ÉVALUATION DE LA BASELINE")
    logger.info("=" * 60)
    
    # Charger les données
    logger.info("Chargement des données...")
    cities = load_cities()
    logger.info(f"Nombre de villes chargées : {len(cities)}")
    
    sentences, labels = load_validation_data()
    logger.info(f"Nombre de phrases de validation : {len(sentences)}")
    logger.info(f"Nombre de labels : {len(labels)}")
    
    # Créer le modèle
    logger.info("Initialisation du modèle baseline...")
    model = BaselineModel(cities)
    
    # Évaluer
    results = evaluate_baseline(model, sentences, labels)
    
    # Afficher les résultats
    logger.info("\n" + "=" * 60)
    logger.info("RÉSULTATS DE L'ÉVALUATION")
    logger.info("=" * 60)
    
    logger.info(f"\nMétriques pour ORIGIN :")
    logger.info(f"  Precision : {results['origin_metrics']['precision']:.4f}")
    logger.info(f"  Recall    : {results['origin_metrics']['recall']:.4f}")
    logger.info(f"  F1-score  : {results['origin_metrics']['f1_score']:.4f}")
    logger.info(f"  TP: {results['origin_metrics']['TP']}, FP: {results['origin_metrics']['FP']}, FN: {results['origin_metrics']['FN']}")
    
    logger.info(f"\nMétriques pour DESTINATION :")
    logger.info(f"  Precision : {results['destination_metrics']['precision']:.4f}")
    logger.info(f"  Recall    : {results['destination_metrics']['recall']:.4f}")
    logger.info(f"  F1-score  : {results['destination_metrics']['f1_score']:.4f}")
    logger.info(f"  TP: {results['destination_metrics']['TP']}, FP: {results['destination_metrics']['FP']}, FN: {results['destination_metrics']['FN']}")
    
    logger.info(f"\nMétriques globales :")
    logger.info(f"  Exact match rate : {results['exact_match_rate']:.4f}")
    logger.info(f"  Valid detection rate : {results['valid_invalid_detection']['valid_detection_rate']:.4f}")
    logger.info(f"  Invalid detection rate : {results['valid_invalid_detection']['invalid_detection_rate']:.4f}")
    
    # Sauvegarder les résultats
    output_file = Path("evaluation/results/baseline_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nRésultats sauvegardés dans {output_file}")
    logger.info("\n" + "=" * 60)
    logger.info("ÉVALUATION TERMINÉE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
