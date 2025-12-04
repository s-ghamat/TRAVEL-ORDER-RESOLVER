# T-AIA-911-PAR_14

## Résolveur de Commandes de Voyage - Itinéraires SNCF

Ce projet vise à créer un programme de traitement du langage naturel (NLP) capable de générer des itinéraires de train SNCF à partir de commandes textuelles en français.

### Objectifs

- Identifier les villes ou gares de départ et d'arrivée à partir de commandes en langage naturel
- Distinguer les commandes valides des invalides
- Générer des itinéraires optimaux en utilisant les horaires de la SNCF
- Traiter principalement le français, avec possibilité d'extension à d'autres langues

### Fonctionnalités

Le programme doit être capable de comprendre des phrases variées telles que :
- "Comment me rendre à Port Boulet depuis Tours ?"
- "Je veux aller de Paris à Lyon"
- "Trajet Marseille vers Nice"

### Technologies

- **NLP** : Modèles Transformers pour l'extraction de sens
- **Optimisation** : Algorithmes de recherche de chemin dans un graphe
- **Base de données** : Neo4j ou similaire pour gérer les données de train
- **Données** : API SNCF Open Data pour les horaires

### Spécifications

- **Entrée** : Fichiers texte en UTF-8 avec identifiants de phrase
- **Sortie** : Validation de commande et itinéraire détaillé
- **Dataset** : ~10 000 phrases variées pour l'entraînement

### Livrables

- Module NLP fonctionnel
- Documentation complète (architecture, processus d'entraînement, exemples)
- Métriques d'évaluation de performance
- Intégration avec les données SNCF

### Améliorations Futures

- Reconnaissance vocale
- Gestion des arrêts intermédiaires
- Support multilingue
- Interface utilisateur interactive
