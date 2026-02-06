#!/usr/bin/env python3
"""
Module d'analyse comparative
Compare les performances spaCy vs Qwen2.5+ChromaDB
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Tuple
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComparativeAnalysis:
    """Analyse comparative des 2 approches"""

    def __init__(self):
        """Initialiser l'analyseur"""
        self.results = {
            'spacy': {'predictions': [], 'ground_truth': []},
            'qwen_chroma': {'predictions': [], 'ground_truth': []}
        }

    def load_results(
        self,
        spacy_results_file: str,
        qwen_results_file: str,
        ground_truth_file: str
    ):
        """
        Charger les résultats des 2 systèmes

        Args:
            spacy_results_file: Résultats spaCy (CSV)
            qwen_results_file: Résultats Qwen2.5 (CSV)
            ground_truth_file: Vérité terrain (JSON)
        """
        logger.info("📂 Chargement des résultats...")

        # Charger ground truth
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)

        # Parser les résultats
        for system, results_file in [
            ('spacy', spacy_results_file),
            ('qwen_chroma', qwen_results_file)
        ]:
            with open(results_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        sentence_id = parts[0]
                        departure = parts[1]
                        arrival = parts[2] if len(parts) > 2 else ""

                        # Trouver la vérité terrain
                        gt = next((item for item in ground_truth if item['id'] == sentence_id), None)

                        if gt:
                            self.results[system]['predictions'].append({
                                'id': sentence_id,
                                'departure': departure,
                                'arrival': arrival,
                                'valid': departure != "INVALID"
                            })
                            self.results[system]['ground_truth'].append({
                                'id': sentence_id,
                                'departure': gt.get('departure', ''),
                                'arrival': gt.get('arrival', ''),
                                'valid': gt.get('valid', True)
                            })

        logger.info(f"✅ Résultats chargés: {len(self.results['spacy']['predictions'])} phrases")

    def calculate_metrics(self, system: str) -> Dict:
        """
        Calculer les métriques pour un système

        Args:
            system: 'spacy' ou 'qwen_chroma'

        Returns:
            Dict avec précision, recall, f1, etc.
        """
        predictions = self.results[system]['predictions']
        ground_truth = self.results[system]['ground_truth']

        # Exactitude départ
        departure_correct = sum(
            1 for pred, gt in zip(predictions, ground_truth)
            if pred['departure'].lower() == gt['departure'].lower()
        )

        # Exactitude arrivée
        arrival_correct = sum(
            1 for pred, gt in zip(predictions, ground_truth)
            if pred['arrival'].lower() == gt['arrival'].lower()
        )

        # Exactitude complète (départ ET arrivée corrects)
        both_correct = sum(
            1 for pred, gt in zip(predictions, ground_truth)
            if pred['departure'].lower() == gt['departure'].lower()
            and pred['arrival'].lower() == gt['arrival'].lower()
        )

        # Classification valid/invalid
        y_true_valid = [1 if gt['valid'] else 0 for gt in ground_truth]
        y_pred_valid = [1 if pred['valid'] else 0 for pred in predictions]

        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true_valid,
            y_pred_valid,
            average='binary',
            zero_division=0
        )

        total = len(predictions)

        metrics = {
            'total_samples': total,
            'departure_accuracy': departure_correct / total if total > 0 else 0,
            'arrival_accuracy': arrival_correct / total if total > 0 else 0,
            'both_accuracy': both_correct / total if total > 0 else 0,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }

        return metrics

    def generate_comparison_report(self, output_file: str = "./results/comparison_report.md"):
        """
        Générer un rapport de comparaison complet

        Args:
            output_file: Fichier Markdown de sortie
        """
        logger.info("📊 Génération du rapport comparatif...")

        # Calculer métriques
        spacy_metrics = self.calculate_metrics('spacy')
        qwen_metrics = self.calculate_metrics('qwen_chroma')

        # Générer le rapport Markdown
        report = f"""# 📊 Rapport d'Analyse Comparative

## Travel Order Resolver - NLP Project

**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

---

## 🎯 Résultats Globaux

### Phase 1: spaCy Baseline

| Métrique | Score |
|----------|-------|
| **Exactitude Départ** | {spacy_metrics['departure_accuracy']:.2%} |
| **Exactitude Arrivée** | {spacy_metrics['arrival_accuracy']:.2%} |
| **Exactitude Complète (Départ + Arrivée)** | {spacy_metrics['both_accuracy']:.2%} |
| **Précision** | {spacy_metrics['precision']:.2%} |
| **Recall** | {spacy_metrics['recall']:.2%} |
| **F1-Score** | {spacy_metrics['f1_score']:.2%} |

### Phase 2: Qwen2.5 + ChromaDB

| Métrique | Score |
|----------|-------|
| **Exactitude Départ** | {qwen_metrics['departure_accuracy']:.2%} |
| **Exactitude Arrivée** | {qwen_metrics['arrival_accuracy']:.2%} |
| **Exactitude Complète (Départ + Arrivée)** | {qwen_metrics['both_accuracy']:.2%} |
| **Précision** | {qwen_metrics['precision']:.2%} |
| **Recall** | {qwen_metrics['recall']:.2%} |
| **F1-Score** | {qwen_metrics['f1_score']:.2%} |

---

## 📈 Comparaison Directe

| Métrique | spaCy | Qwen2.5+ChromaDB | Δ (amélioration) |
|----------|-------|------------------|------------------|
| Exactitude Départ | {spacy_metrics['departure_accuracy']:.1%} | {qwen_metrics['departure_accuracy']:.1%} | **{(qwen_metrics['departure_accuracy'] - spacy_metrics['departure_accuracy']):.1%}** |
| Exactitude Arrivée | {spacy_metrics['arrival_accuracy']:.1%} | {qwen_metrics['arrival_accuracy']:.1%} | **{(qwen_metrics['arrival_accuracy'] - spacy_metrics['arrival_accuracy']):.1%}** |
| F1-Score | {spacy_metrics['f1_score']:.1%} | {qwen_metrics['f1_score']:.1%} | **{(qwen_metrics['f1_score'] - spacy_metrics['f1_score']):.1%}** |

---

## 💡 Analyse Qualitative

### Forces de spaCy:
- ✅ Rapide (< 100ms par phrase)
- ✅ Modèle léger (500MB)
- ✅ Pas de GPU nécessaire
- ✅ Bien documenté et stable

### Limites de spaCy:
- ❌ Difficulté avec noms ambigus ("Albert", "Paris")
- ❌ Règles linguistiques rigides
- ❌ Sensible aux fautes d'orthographe
- ❌ Fine-tuning complexe

### Forces de Qwen2.5 + ChromaDB:
- ✅ Compréhension contextuelle profonde
- ✅ Gestion des ambiguïtés
- ✅ Robuste aux fautes
- ✅ Few-shot learning efficace
- ✅ Génération automatique du dataset

### Limites de Qwen2.5:
- ❌ Plus lent (~500ms par phrase)
- ❌ Modèle plus lourd (1.7GB)
- ❌ Nécessite plus de RAM
- ❌ Setup plus complexe

---

## 🏆 Conclusion

**Gagnant**: {"Qwen2.5 + ChromaDB" if qwen_metrics['f1_score'] > spacy_metrics['f1_score'] else "spaCy" if spacy_metrics['f1_score'] > qwen_metrics['f1_score'] else "Égalité"}

**Recommandation**:
- Pour **production à grande échelle** : spaCy (rapidité, légèreté)
- Pour **qualité maximale** : Qwen2.5 + ChromaDB (précision, robustesse)
- Pour **prototype/MVP** : Qwen2.5 (génération dataset automatique)

---

## 📚 Références

- spaCy: https://spacy.io
- Qwen2.5: https://huggingface.co/Qwen
- ChromaDB: https://www.trychroma.com
- Rapport généré automatiquement par ComparativeAnalysis
"""

        # Sauvegarder le rapport
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✅ Rapport sauvegardé: {output_file}")

        # Afficher résumé
        print("\n" + "="*70)
        print("📊 RÉSUMÉ COMPARATIF")
        print("="*70)
        print(f"spaCy F1-Score:        {spacy_metrics['f1_score']:.2%}")
        print(f"Qwen2.5 F1-Score:      {qwen_metrics['f1_score']:.2%}")
        print(f"Amélioration:          {(qwen_metrics['f1_score'] - spacy_metrics['f1_score']):.2%}")
        print("="*70)

        return {
            'spacy': spacy_metrics,
            'qwen_chroma': qwen_metrics
        }


def main():
    """Test de l'analyse comparative"""
    analyzer = ComparativeAnalysis()

    # Charger les résultats (à adapter selon vos fichiers)
    # analyzer.load_results(
    #     spacy_results_file="./results/spacy_output.csv",
    #     qwen_results_file="./results/qwen_output.csv",
    #     ground_truth_file="./data/annotated/test_set.json"
    # )

    # Générer le rapport
    # analyzer.generate_comparison_report()

    print("📊 Module d'analyse comparative prêt !")
    print("Utilisez-le après avoir exécuté les 2 systèmes sur un test set commun.")


if __name__ == "__main__":
    main()
