#!/usr/bin/env python3
"""
ChromaDB Manager pour Travel Order Resolver
Réutilise l'architecture de Virida/chroma_manager.py
"""

import os
import json
import logging
import gc
from typing import List, Dict, Any
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TravelChromaManager:
    """Gestionnaire ChromaDB pour phrases de voyage annotées"""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        model_name: str = "paraphrase-MiniLM-L3-v2"
    ):
        """
        Initialiser ChromaDB

        Args:
            persist_directory: Répertoire de stockage
            model_name: Modèle d'embeddings (léger, 22MB)
        """
        self.persist_directory = persist_directory
        self.model_name = model_name
        self.client = None
        self.collection = None
        self.initialized = False

    def initialize(self) -> bool:
        """Initialiser ChromaDB et la collection"""
        try:
            logger.info("🔄 Initialisation ChromaDB...")

            # Client persistent
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=chromadb.config.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Fonction d'embedding
            embedding_function = SentenceTransformerEmbeddingFunction(
                model_name=self.model_name,
                device='cpu'
            )

            # Créer ou récupérer la collection
            collection_name = "travel_orders"
            try:
                self.collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=embedding_function
                )
                logger.info(f"✅ Collection '{collection_name}' trouvée")
            except:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={
                        "description": "Dataset de commandes de train annotées",
                        "hnsw:space": "cosine"
                    },
                    embedding_function=embedding_function
                )
                logger.info(f"✅ Collection '{collection_name}' créée")

            self.initialized = True
            logger.info("✅ ChromaDB initialisé")
            gc.collect()
            return True

        except Exception as e:
            logger.error(f"❌ Erreur initialisation ChromaDB: {e}")
            self.initialized = False
            return False

    def load_annotated_dataset(self, json_path: str) -> bool:
        """
        Charger un dataset annoté dans ChromaDB

        Format JSON attendu:
        [
            {
                "id": "1",
                "sentence": "Je veux aller de Paris à Lyon",
                "departure": "Paris",
                "arrival": "Lyon",
                "valid": true
            },
            ...
        ]

        Args:
            json_path: Chemin vers le fichier JSON

        Returns:
            True si succès
        """
        try:
            if not self.initialized:
                logger.error("❌ ChromaDB non initialisé")
                return False

            logger.info(f"📂 Chargement du dataset: {json_path}")

            # Charger le JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)

            logger.info(f"📦 {len(dataset)} phrases à indexer")

            # Vérifier si déjà chargé
            existing_count = self.collection.count()
            if existing_count > 0:
                logger.info(f"✅ Dataset déjà chargé ({existing_count} phrases)")
                return True

            # Indexer par batch
            BATCH_SIZE = 50
            total_indexed = 0

            for i in range(0, len(dataset), BATCH_SIZE):
                batch = dataset[i:i + BATCH_SIZE]

                documents = []
                metadatas = []
                ids = []

                for item in batch:
                    if item.get('valid', True):  # Indexer seulement les valides
                        documents.append(item['sentence'])
                        metadatas.append({
                            'departure': item.get('departure', ''),
                            'arrival': item.get('arrival', ''),
                            'valid': True
                        })
                        ids.append(item.get('id', f"train_{total_indexed}"))
                        total_indexed += 1

                # Ajouter le batch
                if documents:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    logger.info(f"💾 Batch {i//BATCH_SIZE + 1}: {len(documents)} phrases indexées")

                # Garbage collection
                if (i // BATCH_SIZE) % 5 == 0:
                    gc.collect()

            logger.info(f"✅ {total_indexed} phrases indexées dans ChromaDB")
            gc.collect()
            return True

        except Exception as e:
            logger.error(f"❌ Erreur chargement dataset: {e}")
            return False

    def search_similar(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Rechercher des phrases similaires

        Args:
            query: Phrase à rechercher
            limit: Nombre de résultats

        Returns:
            Liste des résultats avec scores
        """
        try:
            if not self.initialized:
                logger.error("❌ ChromaDB non initialisé")
                return []

            # Recherche vectorielle
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )

            # Formater les résultats
            formatted_results = []
            if results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i]
                    score = max(0.0, 1.0 - distance)  # Normaliser en score de similarité

                    metadata = results['metadatas'][0][i]
                    formatted_results.append({
                        'sentence': doc,
                        'departure': metadata.get('departure', ''),
                        'arrival': metadata.get('arrival', ''),
                        'score': score,
                        'distance': distance
                    })

            logger.info(f"🔍 '{query[:50]}...' -> {len(formatted_results)} résultats")
            return formatted_results

        except Exception as e:
            logger.error(f"❌ Erreur recherche: {e}")
            return []

    def get_stats(self) -> Dict:
        """Statistiques de la base ChromaDB"""
        try:
            if not self.initialized:
                return {"status": "not_initialized"}

            count = self.collection.count()
            sample = self.collection.peek(limit=3)

            return {
                "status": "initialized",
                "total_sentences": count,
                "model": self.model_name,
                "persist_directory": self.persist_directory,
                "sample": sample.get('documents', [])[:3]
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


# Instance globale
chroma_manager = TravelChromaManager()


def main():
    """Test ChromaDB Manager"""
    logger.info("🚀 Test ChromaDB Manager")

    # Initialiser
    if not chroma_manager.initialize():
        logger.error("❌ Échec initialisation")
        return

    # Créer un mini dataset de test
    test_dataset = [
        {
            "id": "1",
            "sentence": "Je veux aller de Paris à Lyon",
            "departure": "Paris",
            "arrival": "Lyon",
            "valid": True
        },
        {
            "id": "2",
            "sentence": "Comment me rendre à Marseille depuis Toulouse ?",
            "departure": "Toulouse",
            "arrival": "Marseille",
            "valid": True
        },
    ]

    # Sauvegarder en JSON
    test_json = "./test_dataset.json"
    with open(test_json, 'w', encoding='utf-8') as f:
        json.dump(test_dataset, f, ensure_ascii=False, indent=2)

    # Charger dans ChromaDB
    chroma_manager.load_annotated_dataset(test_json)

    # Tester la recherche
    query = "Je souhaite partir de Paris vers Lyon"
    results = chroma_manager.search_similar(query, limit=2)

    print("\n" + "="*70)
    print("🔍 TEST RECHERCHE CHROMADB")
    print("="*70)
    print(f"Query: {query}")
    print("-" * 70)
    for result in results:
        print(f"✅ Score: {result['score']:.3f} | {result['sentence']}")
        print(f"   → {result['departure']} -> {result['arrival']}")
    print("="*70)


if __name__ == "__main__":
    main()
