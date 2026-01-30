"""
Utilitaires pour calculer les métriques d'évaluation.
"""

from typing import List, Dict, Tuple
import json


def calculate_metrics_for_label(predictions: List[str], ground_truth: List[str], label_name: str) -> Dict:
    """
    Calcule Precision, Recall et F1-score pour un label donné.
    
    Args:
        predictions: Liste des prédictions (peut être None ou "")
        ground_truth: Liste des valeurs réelles (peut être None ou "")
        label_name: Nom du label (pour les logs)
        
    Returns:
        Dictionnaire avec les métriques
    """
    # Normaliser : None et "" sont considérés comme absents
    pred_normalized = [p if p and p != "INVALID" else None for p in predictions]
    gt_normalized = [g if g and g != "" else None for g in ground_truth]
    
    TP = 0  # True Positives
    FP = 0  # False Positives
    FN = 0  # False Negatives
    
    for pred, gt in zip(pred_normalized, gt_normalized):
        if pred is not None and gt is not None:
            if pred == gt:
                TP += 1
            else:
                FP += 1
                FN += 1
        elif pred is not None and gt is None:
            FP += 1
        elif pred is None and gt is not None:
            FN += 1
        # Si les deux sont None, on ne compte rien (True Negative)
    
    # Calculer les métriques
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "label": label_name,
        "TP": TP,
        "FP": FP,
        "FN": FN,
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }


def calculate_exact_match(predictions_origin: List[str], predictions_dest: List[str],
                         ground_truth_origin: List[str], ground_truth_dest: List[str]) -> float:
    """
    Calcule le taux de correspondance exacte (origine ET destination correctes).
    
    Args:
        predictions_origin: Prédictions pour l'origine
        predictions_dest: Prédictions pour la destination
        ground_truth_origin: Valeurs réelles pour l'origine
        ground_truth_dest: Valeurs réelles pour la destination
        
    Returns:
        Taux de correspondance exacte (0.0 à 1.0)
    """
    exact_matches = 0
    total = len(predictions_origin)
    
    for pred_orig, pred_dest, gt_orig, gt_dest in zip(
        predictions_origin, predictions_dest, ground_truth_origin, ground_truth_dest
    ):
        # Normaliser
        pred_orig_norm = pred_orig if pred_orig and pred_orig != "INVALID" else None
        pred_dest_norm = pred_dest if pred_dest and pred_dest != "INVALID" else None
        gt_orig_norm = gt_orig if gt_orig and gt_orig != "" else None
        gt_dest_norm = gt_dest if gt_dest and gt_dest != "" else None
        
        # Vérifier correspondance exacte
        if pred_orig_norm == gt_orig_norm and pred_dest_norm == gt_dest_norm:
            exact_matches += 1
    
    return exact_matches / total if total > 0 else 0.0


def calculate_valid_invalid_detection(predictions_is_valid: List[bool], 
                                     ground_truth_is_valid: List[bool]) -> Dict:
    """
    Calcule le taux de détection correcte des phrases valides/invalides.
    
    Args:
        predictions_is_valid: Prédictions (True = valide, False = invalide)
        ground_truth_is_valid: Valeurs réelles
        
    Returns:
        Dictionnaire avec les taux de détection
    """
    correct_valid = 0
    correct_invalid = 0
    total_valid = 0
    total_invalid = 0
    
    for pred, gt in zip(predictions_is_valid, ground_truth_is_valid):
        if gt:
            total_valid += 1
            if pred == gt:
                correct_valid += 1
        else:
            total_invalid += 1
            if pred == gt:
                correct_invalid += 1
    
    valid_detection_rate = correct_valid / total_valid if total_valid > 0 else 0.0
    invalid_detection_rate = correct_invalid / total_invalid if total_invalid > 0 else 0.0
    
    return {
        "valid_detection_rate": valid_detection_rate,
        "invalid_detection_rate": invalid_detection_rate,
        "total_valid": total_valid,
        "total_invalid": total_invalid,
        "correct_valid": correct_valid,
        "correct_invalid": correct_invalid
    }
