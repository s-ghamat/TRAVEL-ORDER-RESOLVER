#!/usr/bin/env python3
"""
Phase 2.2 - Générateur automatique de dataset
Génère 10 000 phrases de commandes de train avec Qwen2.5
GAME CHANGER: Plus besoin d'annoter manuellement !
"""

import json
import logging
from typing import List, Dict
from tqdm import tqdm
from .qwen_manager import qwen_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetGenerator:
    """Générateur automatique de dataset avec Qwen2.5"""

    # Villes françaises populaires
    FRENCH_CITIES = [
        "Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes",
        "Strasbourg", "Montpellier", "Bordeaux", "Lille", "Rennes",
        "Reims", "Le Havre", "Saint-Étienne", "Toulon", "Grenoble",
        "Dijon", "Angers", "Nîmes", "Villeurbanne", "Le Mans",
        "Aix-en-Provence", "Clermont-Ferrand", "Brest", "Tours",
        "Amiens", "Limoges", "Annecy", "Perpignan", "Boulogne-Billancourt",
        "Orléans", "Mulhouse", "Rouen", "Caen", "Nancy", "Argenteuil",
        "Montreuil", "Saint-Denis", "Roubaix", "Tourcoing", "Avignon",
        "Poitiers", "Versailles", "Courbevoie", "Créteil", "Pau",
        "La Rochelle", "Cannes", "Antibes", "Bayonne", "Monaco",
        "Port-Boulet", "Albert", "Lourdes"  # Villes ambigües du sujet
    ]

    def __init__(self):
        """Initialiser le générateur"""
        self.generated_sentences = []

    def generate_batch(
        self,
        num_sentences: int = 100,
        add_variations: bool = True
    ) -> List[Dict]:
        """
        Générer un batch de phrases avec Qwen2.5

        Args:
            num_sentences: Nombre de phrases à générer
            add_variations: Ajouter des variations (fautes, ambiguïtés)

        Returns:
            Liste de dictionnaires {id, sentence, departure, arrival, valid}
        """
        variations_text = ""
        if add_variations:
            variations_text = """
Ajoute de la diversité :
- Phrases avec fautes d'orthographe (20%)
- Phrases sans accents (15%)
- Phrases ambigües avec prénoms (10%) ex: "avec mon ami Paris, je vais à Lyon"
- Phrases mal formulées (10%)
- Quelques phrases invalides (5%) ex: "Bonjour comment allez-vous ?"
"""

        prompt = f"""Tu es un générateur de données pour entraîner un modèle NLP.
Génère {num_sentences} phrases françaises variées demandant un itinéraire de train.

Utilise ces villes françaises (varie les combinaisons) :
{', '.join(self.FRENCH_CITIES[:30])}

Formats variés à utiliser :
- "Je veux aller de [ville1] à [ville2]"
- "Comment me rendre à [ville2] depuis [ville1] ?"
- "Trajet [ville1] [ville2]"
- "Je souhaite partir de [ville1] vers [ville2]"
- "A quelle heure y a-t-il des trains pour [ville2] en partance de [ville1] ?"
- "Avec mon ami [prénom], je veux aller de [ville1] à [ville2]"
{variations_text}

Réponds UNIQUEMENT au format JSON suivant (un objet JSON par ligne) :
{{"id": "1", "sentence": "Je veux aller de Paris à Lyon", "departure": "Paris", "arrival": "Lyon", "valid": true}}
{{"id": "2", "sentence": "Bonjour !", "departure": "", "arrival": "", "valid": false}}

Génère maintenant {num_sentences} lignes JSON :"""

        # Générer avec Qwen2.5
        response = qwen_manager.generate_response(
            prompt,
            max_tokens=num_sentences * 50,  # ~50 tokens par phrase
            temperature=0.8  # Plus de créativité
        )

        # Parser les lignes JSON
        sentences = []
        for i, line in enumerate(response.split('\n')):
            line = line.strip()
            if not line or not line.startswith('{'):
                continue

            try:
                data = json.loads(line)
                # Forcer un ID unique
                data['id'] = str(len(self.generated_sentences) + len(sentences) + 1)
                sentences.append(data)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Ligne JSON invalide ignorée: {line[:50]}...")
                continue

        logger.info(f"✅ {len(sentences)} phrases générées dans ce batch")
        return sentences

    def generate_dataset(
        self,
        total_sentences: int = 10000,
        batch_size: int = 100,
        output_file: str = "./data/generated/train_dataset_10k.json"
    ) -> bool:
        """
        Générer un dataset complet de 10 000 phrases

        Args:
            total_sentences: Nombre total de phrases à générer
            batch_size: Taille des batchs
            output_file: Fichier de sortie JSON

        Returns:
            True si succès
        """
        try:
            logger.info(f"🚀 Génération de {total_sentences} phrases...")
            logger.info(f"📦 Batch size: {batch_size}")

            # Initialiser Qwen2.5 si nécessaire
            if not qwen_manager.llm:
                logger.info("🔄 Initialisation de Qwen2.5...")
                if not qwen_manager.initialize():
                    logger.error("❌ Échec init Qwen2.5")
                    return False

            # Générer par batch avec barre de progression
            num_batches = (total_sentences + batch_size - 1) // batch_size
            self.generated_sentences = []

            for batch_num in tqdm(range(num_batches), desc="Génération"):
                # Nombre de phrases pour ce batch
                remaining = total_sentences - len(self.generated_sentences)
                current_batch_size = min(batch_size, remaining)

                # Générer le batch
                batch = self.generate_batch(
                    num_sentences=current_batch_size,
                    add_variations=True
                )

                self.generated_sentences.extend(batch)

                # Log progression
                if (batch_num + 1) % 10 == 0:
                    logger.info(
                        f"📊 Progression: {len(self.generated_sentences)}/{total_sentences} "
                        f"({len(self.generated_sentences)/total_sentences*100:.1f}%)"
                    )

                # Arrêter si on a atteint le nombre cible
                if len(self.generated_sentences) >= total_sentences:
                    break

            # Sauvegarder le dataset
            logger.info(f"💾 Sauvegarde dans {output_file}...")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.generated_sentences, f, ensure_ascii=False, indent=2)

            # Statistiques
            valid_count = sum(1 for s in self.generated_sentences if s.get('valid', True))
            invalid_count = len(self.generated_sentences) - valid_count

            logger.info(f"✅ Dataset généré avec succès !")
            logger.info(f"📊 Statistiques:")
            logger.info(f"   - Total: {len(self.generated_sentences)} phrases")
            logger.info(f"   - Valides: {valid_count} ({valid_count/len(self.generated_sentences)*100:.1f}%)")
            logger.info(f"   - Invalides: {invalid_count} ({invalid_count/len(self.generated_sentences)*100:.1f}%)")
            logger.info(f"📁 Fichier: {output_file}")

            return True

        except Exception as e:
            logger.error(f"❌ Erreur génération dataset: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


def main():
    """Générer le dataset de 10k phrases"""
    generator = DatasetGenerator()

    # Générer 10 000 phrases
    success = generator.generate_dataset(
        total_sentences=10000,
        batch_size=100,
        output_file="./data/generated/train_dataset_10k.json"
    )

    if success:
        print("\n" + "="*70)
        print("🎉 DATASET GÉNÉRÉ AVEC SUCCÈS !")
        print("="*70)
        print("📁 Fichier: ./data/generated/train_dataset_10k.json")
        print("📊 10 000 phrases de commandes de train annotées automatiquement")
        print("🚀 Prochaine étape: Indexer dans ChromaDB")
        print("="*70)
    else:
        print("❌ Échec de la génération")


if __name__ == "__main__":
    main()
