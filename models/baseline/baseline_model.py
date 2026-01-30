"""
Modèle baseline basé sur les prépositions pour extraire origine et destination.
"""

import re
from typing import Optional, Tuple, List


class BaselineModel:
    """
    Modèle simple basé sur les prépositions pour extraire origine et destination.
    """
    
    def __init__(self, cities_list: List[str]):
        """
        Initialise le modèle avec la liste des villes.
        
        Args:
            cities_list: Liste des noms de villes valides
        """
        self.cities = cities_list
        self.origin_keywords = ["de", "depuis", "à partir de", "en partant de", "quitter"]
        self.dest_keywords = ["à", "vers", "jusqu'à", "pour aller à", "pour se rendre à"]
        
        # Créer un dictionnaire de villes normalisées pour recherche rapide
        self.cities_normalized = {}
        for city in cities_list:
            normalized = self.normalize_city(city)
            if normalized not in self.cities_normalized:
                self.cities_normalized[normalized] = []
            self.cities_normalized[normalized].append(city)
    
    def normalize_city(self, city_name: str) -> str:
        """
        Normalise un nom de ville pour la correspondance (minuscules, sans accents, sans tirets).
        
        Args:
            city_name: Nom de ville à normaliser
            
        Returns:
            Nom normalisé
        """
        if not city_name:
            return ""
        
        # Convertir en minuscules
        normalized = city_name.lower()
        
        # Remplacer les tirets par des espaces
        normalized = normalized.replace("-", " ")
        
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
            normalized = normalized.replace(old, new)
        
        return normalized.strip()
    
    def find_city_in_segment(self, text: str, start_pos: int, end_pos: int) -> Optional[str]:
        """
        Trouve une ville dans un segment de texte.
        
        Args:
            text: Texte complet
            start_pos: Position de début du segment
            end_pos: Position de fin du segment
            
        Returns:
            Nom de la ville trouvée (normalisé) ou None
        """
        if start_pos >= end_pos or start_pos < 0 or end_pos > len(text):
            return None
        
        segment = text[start_pos:end_pos].strip()
        
        # Chercher dans les villes normalisées
        segment_normalized = self.normalize_city(segment)
        
        # Correspondance exacte
        if segment_normalized in self.cities_normalized:
            return self.cities_normalized[segment_normalized][0]  # Retourner la première variante
        
        # Chercher si le segment contient une ville (pour les cas comme "la gare de Paris")
        for normalized_city, cities in self.cities_normalized.items():
            if normalized_city in segment_normalized:
                # Vérifier que c'est un mot complet
                pattern = r'\b' + re.escape(normalized_city) + r'\b'
                if re.search(pattern, segment_normalized):
                    return cities[0]
        
        # Chercher si une ville est contenue dans le segment
        for normalized_city, cities in self.cities_normalized.items():
            if normalized_city in segment_normalized or segment_normalized in normalized_city:
                return cities[0]
        
        return None
    
    def extract_origin_destination(self, text: str) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Extrait l'origine et la destination d'une phrase basée sur les prépositions.
        
        Args:
            text: Phrase à analyser
            
        Returns:
            Tuple (origin, destination, is_valid)
        """
        text_lower = text.lower()
        origin = None
        destination = None
        
        # Chercher les prépositions d'origine
        for keyword in self.origin_keywords:
            # Pattern pour trouver la préposition et le mot suivant
            pattern = rf'\b{re.escape(keyword)}\s+([^\s,\.\?!]+(?:\s+[^\s,\.\?!]+){0,2})'
            matches = list(re.finditer(pattern, text_lower))
            
            for match in matches:
                # Position de début du segment (après la préposition)
                keyword_end = match.end() - len(match.group(1))
                segment_start = match.end() - len(match.group(1))
                
                # Chercher jusqu'à la prochaine préposition, ponctuation ou limite
                segment_end = len(text)
                remaining_text = text_lower[match.end():]
                
                for next_keyword in self.origin_keywords + self.dest_keywords + ["pour", "avec", "et"]:
                    next_match = re.search(rf'\b{re.escape(next_keyword)}\b', remaining_text)
                    if next_match:
                        segment_end = min(segment_end, match.end() + next_match.start())
                
                # Limiter aussi par ponctuation
                punct_match = re.search(r'[,\.\?!]', remaining_text)
                if punct_match:
                    segment_end = min(segment_end, match.end() + punct_match.start())
                
                # Trouver la ville dans ce segment (max 3-4 mots)
                city = self.find_city_in_segment(text, segment_start, segment_end)
                if city and not origin:
                    origin = city
                    break
            
            if origin:
                break
        
        # Chercher les prépositions de destination
        for keyword in self.dest_keywords:
            # Pattern pour trouver la préposition et le mot suivant
            pattern = rf'\b{re.escape(keyword)}\s+([^\s,\.\?!]+(?:\s+[^\s,\.\?!]+){0,2})'
            matches = list(re.finditer(pattern, text_lower))
            
            for match in matches:
                # Position de début du segment (après la préposition)
                segment_start = match.end() - len(match.group(1))
                
                # Chercher jusqu'à la prochaine préposition, ponctuation ou limite
                segment_end = len(text)
                remaining_text = text_lower[match.end():]
                
                for next_keyword in self.origin_keywords + self.dest_keywords + ["pour", "avec", "et"]:
                    next_match = re.search(rf'\b{re.escape(next_keyword)}\b', remaining_text)
                    if next_match:
                        segment_end = min(segment_end, match.end() + next_match.start())
                
                # Limiter aussi par ponctuation
                punct_match = re.search(r'[,\.\?!]', remaining_text)
                if punct_match:
                    segment_end = min(segment_end, match.end() + punct_match.start())
                
                # Trouver la ville dans ce segment (max 3-4 mots)
                city = self.find_city_in_segment(text, segment_start, segment_end)
                if city and not destination:
                    destination = city
                    break
            
            if destination:
                break
        
        # Si on n'a pas trouvé avec les prépositions, chercher toutes les villes dans le texte
        if not origin or not destination:
            # Chercher toutes les villes dans le texte (mot complet uniquement)
            found_cities = []
            for city in self.cities:
                city_normalized = self.normalize_city(city)
                # Chercher avec regex insensible à la casse, mot complet uniquement
                pattern = r'\b' + re.escape(city_normalized) + r'\b'
                for match in re.finditer(pattern, text_lower):
                    found_cities.append((match.start(), match.end(), city))
            
            # Dédupliquer (garder la première occurrence de chaque ville)
            seen_cities = set()
            unique_found_cities = []
            for start, end, city in found_cities:
                if city not in seen_cities:
                    seen_cities.add(city)
                    unique_found_cities.append((start, end, city))
            
            # Trier par position
            unique_found_cities.sort(key=lambda x: x[0])
            
            # Si on a deux villes et qu'on n'a pas trouvé origine/destination
            if len(unique_found_cities) >= 2 and (not origin or not destination):
                if not origin:
                    origin = unique_found_cities[0][2]
                if not destination:
                    destination = unique_found_cities[1][2]
            elif len(unique_found_cities) == 1:
                # Une seule ville trouvée
                if not origin and not destination:
                    # Essayer de déterminer si c'est origine ou destination selon le contexte
                    city_pos = unique_found_cities[0][0]
                    # Si "de" ou "depuis" est avant, c'est probablement une origine
                    if re.search(r'\b(de|depuis)\s+', text_lower[:city_pos]):
                        origin = unique_found_cities[0][2]
                    # Si "à" ou "vers" est avant, c'est probablement une destination
                    elif re.search(r'\b(à|vers)\s+', text_lower[:city_pos]):
                        destination = unique_found_cities[0][2]
        
        # Déterminer si la phrase est valide
        is_valid = origin is not None and destination is not None
        
        return origin, destination, is_valid
    
    def predict(self, sentence_id: int, text: str) -> Tuple[int, str, str]:
        """
        Prédit l'origine et la destination pour une phrase.
        
        Args:
            sentence_id: Identifiant de la phrase
            text: Texte de la phrase
            
        Returns:
            Tuple (sentence_id, origin, destination) où origin/destination peuvent être "INVALID" ou ""
        """
        origin, destination, is_valid = self.extract_origin_destination(text)
        
        if not is_valid:
            return (sentence_id, "INVALID", "")
        
        return (sentence_id, origin or "", destination or "")
