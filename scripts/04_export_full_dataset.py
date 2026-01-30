"""
Script pour exporter le dataset complet annoté dans les formats JSONL (BERT) et CSV (validation).
"""

import json
import csv
import random
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_annotations() -> List[Dict]:
    """Charge les annotations depuis le fichier JSON."""
    annotations_file = Path("data/dataset/full/annotations.json")
    with open(annotations_file, "r", encoding="utf-8") as f:
        return json.load(f)


def export_jsonl(annotations: List[Dict], output_file: Path):
    """Exporte les annotations au format JSONL (une ligne par phrase)."""
    with open(output_file, "w", encoding="utf-8") as f:
        for annotation in annotations:
            # Format JSONL : une ligne JSON par phrase
            json_line = json.dumps(annotation, ensure_ascii=False)
            f.write(json_line + "\n")
    logger.info(f"Export JSONL : {len(annotations)} phrases dans {output_file}")


def export_csv(annotations: List[Dict], sentences_file: Path, labels_file: Path):
    """Exporte les annotations au format CSV (deux fichiers : phrases et labels)."""
    # Fichier des phrases
    with open(sentences_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "text"])
        for annotation in annotations:
            writer.writerow([annotation["id"], annotation["text"]])
    logger.info(f"Export CSV phrases : {len(annotations)} phrases dans {sentences_file}")
    
    # Fichier des labels
    with open(labels_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "origin", "destination", "is_valid"])
        for annotation in annotations:
            origin = annotation.get("origin", "") if annotation.get("origin") else ""
            destination = annotation.get("destination", "") if annotation.get("destination") else ""
            is_valid = "true" if annotation.get("is_valid") else "false"
            writer.writerow([annotation["id"], origin, destination, is_valid])
    logger.info(f"Export CSV labels : {len(annotations)} labels dans {labels_file}")


def split_train_validation(annotations: List[Dict], train_ratio: float = 0.8) -> Tuple[List[Dict], List[Dict]]:
    """Split les annotations en train et validation."""
    # Mélanger
    shuffled = annotations.copy()
    random.shuffle(shuffled)
    
    # Calculer le point de coupure
    split_point = int(len(shuffled) * train_ratio)
    
    train = shuffled[:split_point]
    validation = shuffled[split_point:]
    
    return train, validation


def main():
    """Fonction principale."""
    logger.info("=" * 60)
    logger.info("EXPORT DU DATASET COMPLET")
    logger.info("=" * 60)
    
    # Charger les annotations
    logger.info("Chargement des annotations...")
    annotations = load_annotations()
    logger.info(f"Nombre d'annotations : {len(annotations)}")
    
    # Split train/validation (80/20)
    logger.info("Split train/validation (80/20)...")
    train_annotations, validation_annotations = split_train_validation(annotations, 0.8)
    logger.info(f"  - Train : {len(train_annotations)} phrases")
    logger.info(f"  - Validation : {len(validation_annotations)} phrases")
    
    # Créer le dossier de sortie
    output_dir = Path("data/dataset/full")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Exporter en JSONL (format BERT)
    logger.info("\nExport JSONL...")
    export_jsonl(train_annotations, output_dir / "train.jsonl")
    export_jsonl(validation_annotations, output_dir / "validation.jsonl")
    
    # Exporter en CSV (format lisible)
    logger.info("\nExport CSV...")
    export_csv(train_annotations, output_dir / "train.csv", output_dir / "train_labels.csv")
    export_csv(validation_annotations, output_dir / "validation.csv", output_dir / "validation_labels.csv")
    
    # Statistiques
    train_valid = sum(1 for a in train_annotations if a["is_valid"])
    train_invalid = len(train_annotations) - train_valid
    val_valid = sum(1 for a in validation_annotations if a["is_valid"])
    val_invalid = len(validation_annotations) - val_valid
    
    logger.info(f"\n{'='*60}")
    logger.info("STATISTIQUES DU SPLIT")
    logger.info(f"{'='*60}")
    logger.info(f"Train :")
    logger.info(f"  - Total : {len(train_annotations)}")
    logger.info(f"  - Valides : {train_valid} ({train_valid*100//len(train_annotations)}%)")
    logger.info(f"  - Invalides : {train_invalid} ({train_invalid*100//len(train_annotations)}%)")
    logger.info(f"Validation :")
    logger.info(f"  - Total : {len(validation_annotations)}")
    logger.info(f"  - Valides : {val_valid} ({val_valid*100//len(validation_annotations)}%)")
    logger.info(f"  - Invalides : {val_invalid} ({val_invalid*100//len(validation_annotations)}%)")
    
    logger.info(f"\n{'='*60}")
    logger.info("EXPORT TERMINÉ AVEC SUCCÈS")
    logger.info(f"{'='*60}")
    logger.info(f"Fichiers créés dans {output_dir} :")
    logger.info(f"  - train.jsonl ({len(train_annotations)} phrases)")
    logger.info(f"  - validation.jsonl ({len(validation_annotations)} phrases)")
    logger.info(f"  - train.csv")
    logger.info(f"  - train_labels.csv")
    logger.info(f"  - validation.csv")
    logger.info(f"  - validation_labels.csv")


if __name__ == "__main__":
    main()
