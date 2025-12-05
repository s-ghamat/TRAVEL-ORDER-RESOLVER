#!/usr/bin/env python3
"""
Phase 1.1 - Warm-up avec spaCy
Test NER sur ner_dataset.csv (Kaggle dataset)
"""

import spacy
import pandas as pd
from typing import List, Dict, Tuple
from seqeval.metrics import classification_report, f1_score
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpacyNERWarmup:
    """Warm-up: Test spaCy NER sur dataset Kaggle annoté"""

    def __init__(self, model_name: str = "fr_core_news_md"):
        """
        Initialiser spaCy avec modèle français

        Args:
            model_name: Modèle spaCy (fr_core_news_sm/md/lg)
        """
        logger.info(f"🔄 Chargement du modèle spaCy: {model_name}")
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"✅ Modèle {model_name} chargé")
        except OSError:
            logger.error(f"❌ Modèle {model_name} non trouvé. Installez-le avec:")
            logger.error(f"   python -m spacy download {model_name}")
            raise

    def load_ner_dataset(self, csv_path: str) -> pd.DataFrame:
        """
        Charger le dataset NER Kaggle

        Format attendu:
        - Sentence #: ID de la phrase
        - Word: Token
        - POS: Part-of-speech tag
        - Tag: NER tag (B-PER, I-LOC, O, etc.)

        Args:
            csv_path: Chemin vers ner_dataset.csv

        Returns:
            DataFrame avec les données
        """
        logger.info(f"📂 Chargement du dataset: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8')
        logger.info(f"✅ Dataset chargé: {len(df)} lignes, {df['Sentence #'].nunique()} phrases")
        return df

    def extract_sentences(self, df: pd.DataFrame) -> List[Tuple[str, List[str]]]:
        """
        Extraire les phrases et leurs tags NER du dataset

        Args:
            df: DataFrame du dataset NER

        Returns:
            Liste de tuples (phrase, [tags])
        """
        sentences = []
        current_sentence_id = None
        current_words = []
        current_tags = []

        for _, row in df.iterrows():
            sentence_id = row['Sentence #']

            # Nouvelle phrase
            if pd.notna(sentence_id) and sentence_id != current_sentence_id:
                if current_words:
                    # Sauvegarder la phrase précédente
                    sentence_text = ' '.join(current_words)
                    sentences.append((sentence_text, current_tags))

                # Réinitialiser pour la nouvelle phrase
                current_sentence_id = sentence_id
                current_words = [row['Word']]
                current_tags = [row['Tag']]
            else:
                # Continuer la phrase courante
                current_words.append(row['Word'])
                current_tags.append(row['Tag'])

        # Dernière phrase
        if current_words:
            sentence_text = ' '.join(current_words)
            sentences.append((sentence_text, current_tags))

        logger.info(f"✅ {len(sentences)} phrases extraites")
        return sentences

    def predict_ner_tags(self, sentence: str) -> List[str]:
        """
        Prédire les tags NER avec spaCy

        Args:
            sentence: Texte à analyser

        Returns:
            Liste des tags NER (format BIO: B-PER, I-LOC, O, etc.)
        """
        doc = self.nlp(sentence)
        tags = []

        for token in doc:
            if token.ent_iob_ == 'O':
                tags.append('O')
            else:
                # B-PER, I-PER, B-LOC, I-LOC, etc.
                tag = f"{token.ent_iob_}-{token.ent_type_}"
                tags.append(tag)

        return tags

    def evaluate(self, sentences: List[Tuple[str, List[str]]]) -> Dict:
        """
        Évaluer spaCy NER sur le dataset

        Args:
            sentences: Liste de (phrase, tags_gold)

        Returns:
            Dictionnaire avec métriques (précision, recall, f1)
        """
        logger.info("🔍 Évaluation en cours...")

        y_true = []  # Tags gold standard
        y_pred = []  # Tags prédits par spaCy

        for sentence_text, gold_tags in sentences[:100]:  # Test sur 100 phrases d'abord
            # Prédiction spaCy
            pred_tags = self.predict_ner_tags(sentence_text)

            # Aligner les tags (gold et pred doivent avoir même longueur)
            min_len = min(len(gold_tags), len(pred_tags))
            y_true.append(gold_tags[:min_len])
            y_pred.append(pred_tags[:min_len])

        # Calculer les métriques avec seqeval
        logger.info("📊 Calcul des métriques...")
        report = classification_report(y_true, y_pred, output_dict=True)
        f1 = f1_score(y_true, y_pred)

        results = {
            "f1_score": f1,
            "precision": report.get("weighted avg", {}).get("precision", 0),
            "recall": report.get("weighted avg", {}).get("recall", 0),
            "detailed_report": report
        }

        logger.info(f"✅ F1-Score: {f1:.3f}")
        logger.info(f"✅ Précision: {results['precision']:.3f}")
        logger.info(f"✅ Recall: {results['recall']:.3f}")

        return results


def main():
    """Test du warm-up"""
    # Initialiser
    warmup = SpacyNERWarmup(model_name="fr_core_news_md")

    # Charger le dataset (à adapter selon votre chemin)
    df = warmup.load_ner_dataset("../../data/raw/ner_dataset.csv")

    # Extraire les phrases
    sentences = warmup.extract_sentences(df)

    # Évaluer
    results = warmup.evaluate(sentences)

    print("\n" + "="*50)
    print("📊 RÉSULTATS WARM-UP - spaCy NER")
    print("="*50)
    print(f"F1-Score: {results['f1_score']:.3f}")
    print(f"Précision: {results['precision']:.3f}")
    print(f"Recall: {results['recall']:.3f}")
    print("="*50)


if __name__ == "__main__":
    main()
