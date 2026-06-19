# Badge Database Purger (ERO Purge Export)

Script Python pour nettoyer et valider une base de données de badges, avec détection automatique des doublons.

## 📋 Description

Ce projet automatise le processus de purge d'une base de badges selon les critères de validation métier spécifiques. Le script:

- **Valide** chaque enregistrement contre des règles strictes
- **Détecte** les doublons basés sur les immatriculations par matricule
- **Génère** 4 fichiers de sortie catégorisés
- **Produit** un rapport statistique détaillé

## 📥 Format d'entrée

Format CSV avec délimiteur `;` (point-virgule):

```
N°badge(8digits);Nom;Prenom;Matricule(8digits);Catégorie(texte);Immatriculation(10digits);N°Cat(4digits)
```

### Exemple:
```
12345678;Dupont;Jean;87654321;Manager;1234567890;0001
12345679;Martin;Marie;87654322;Operateur;1234567891;0002
```

### Codage
- **Encodage**: ANSI Windows (CP1252)
- **Fins de ligne**: CR LF (Windows)

## ✅ Règles de validation

Chaque enregistrement doit respecter les garde-fous suivants:

| Champ | Règle | 
|-------|-------|
| **N° Badge** | Exactement 8 chiffres |
| **N° Matricule** | Exactement 8 chiffres |
| **N° Immatriculation** | NULL ou exactement 10 chiffres |
| **N° Cat** | Exactement 4 chiffres |
| **Nombre de champs** | Exactement 7 champs |

### Détection de doublons

**Algorithme**: Un matricule est considéré comme doublon si:
- Il possède **plus de 2 immatriculations différentes**

**Exemple**:
```
Matricule: 12345678
  - Immatriculation 1: 1111111111
  - Immatriculation 2: 2222222222
  - Immatriculation 3: 3333333333  ← > 2 → DOUBLON
```

## 📤 Format de sortie

Le script génère **4 fichiers** dans le répertoire de sortie:

### 1. `badges_valides.csv`
- Enregistrements valides sans doublons
- Format identique au fichier d'entrée
- Encodage: CP1252, fins de ligne: CR LF

### 2. `badges_doublons.csv`
- Enregistrements flaggés comme doublons
- Format identique au fichier d'entrée
- Chaque ligne représente un badge problématique

### 3. `badges_erreurs.csv`
- Enregistrements qui n'ont pas passé la validation
- Format enrichi avec colonne d'erreur:
  ```
  # Ligne;N°Badge;Nom;Prenom;Matricule;Catégorie;Immatriculation;N°Cat;ERREUR
  1;XXXXX;Dupont;Jean;8765432;Manager;1234567890;0001;N°Badge invalid: 'XXXXX' (must be 8 digits)
  ```

### 4. `rapport_purge.txt`
Rapport détaillé contenant:
- **Métadonnées**: Date, fichier d'entrée, répertoire de sortie
- **Statistiques globales**: Total lignes, lignes valides, doublons, erreurs
- **Taux de validité**: Pourcentage d'enregistrements correctement traités
- **Analyse des erreurs**: Décomposition par type d'erreur
- **Liste des fichiers générés**

**Exemple de rapport**:
```
RAPPORT DE PURGE DE BASE DE BADGES
======================================================================

Date/Heure: 2026-06-19 14:23:45
Fichier d'entrée: /path/to/badges.csv
Répertoire de sortie: /path/to/output

STATISTIQUES DE TRAITEMENT
----------------------------------------------------------------------
Nombre total de lignes: 60,000
Lignes valides (sans doublon): 58,500
Lignes avec doublon: 1,200
Lignes en erreur: 300

RÉSUMÉ
----------------------------------------------------------------------
Lignes traitées avec succès: 59,700
Taux de validité: 99.50%
...
```

## 🚀 Installation et utilisation

### Prérequis
- Python 3.7+
- Pas de dépendances externes (utilise la stdlib)

### Utilisation

**Mode basique** (sortie dans le même répertoire que le fichier d'entrée):
```bash
python badge_purger.py /path/to/badges.csv
```

**Mode avec répertoire de sortie spécifique**:
```bash
python badge_purger.py /path/to/badges.csv ./output
```

### Exemple complet:
```bash
# Avec un fichier de test
python badge_purger.py ./test_badges.csv ./results

# Les fichiers suivants seront générés:
# - ./results/badges_valides.csv
# - ./results/badges_doublons.csv
# - ./results/badges_erreurs.csv
# - ./results/rapport_purge.txt
```

## 📊 Cas d'usage et exemples

### Exemple 1: Entrée simple
**Fichier d'entrée** (`badges.csv`):
```
12345678;Dupont;Jean;87654321;Manager;1234567890;0001
12345679;Martin;Marie;87654322;Operateur;1234567891;0002
INVALID;Durand;Paul;87654323;Operateur;1234567892;0003
12345680;Lefevre;Pierre;87654324;Manager;;0004
```

**Résultats**:
- `badges_valides.csv`: 2 lignes (12345678, 12345680)
- `badges_erreurs.csv`: 2 lignes (INVALID - mauvais format, Durand - immatriculation manquante mais marquée comme NULL)
- `rapport_purge.txt`: Statistiques détaillées

### Exemple 2: Détection de doublons
**Fichier d'entrée**:
```
11111111;Agent1;Test;99999999;Operator;1111111111;0001
11111112;Agent2;Test;99999999;Operator;2222222222;0002
11111113;Agent3;Test;99999999;Operator;3333333333;0003
```

**Résultats**:
- Matricule `99999999` a 3 immatriculations différentes (> 2)
- Toutes les 3 lignes vont dans `badges_doublons.csv`
- Ligne 11111112, 11111113, 11111114 marquées comme doublons

## 🔄 Flux de traitement

```
┌─────────────────────────┐
│ Fichier d'entrée        │
│ (60,000 lignes)         │
└──────────────┬──────────┘
               │
        ┌──────▼──────┐
        │ Validation  │
        │ des champs  │
        └──┬───────┬──┘
           │       │
    ✓ OK   │       │  ✗ Erreur
           │       └─────────────┐
           │                     │
        ┌──▼──────────┐          │
        │ Détection   │          │
        │ doublons    │          │
        └──┬────────┬─┘          │
           │        │            │
      ✓ OK │        │ ✗ Doublon  │
           │        │            │
      ┌────▼──┐  ┌──▼─────┐  ┌──▼──────────┐
      │Valide │  │Doublon │  │ Erreur      │
      └────┬──┘  └──┬─────┘  └──┬──────────┘
           │        │           │
           └────┬───┴──────┬────┘
                │          │
        ┌───────▼──────────▼────────┐
        │   Rapport statistique      │
        └──────────────────────────┘
```

## 📝 Étapes futures

Le script est conçu comme **étape 1** d'un processus multi-étapes:

1. ✅ **Purge et validation** (ACTUEL)
   - Validation des champs
   - Détection des doublons
   - Génération des fichiers de sortie

2. 🔄 **Étape 2** (À venir)
   - Vérification contre fichier d'agents de sortie
   - Vérification d'agents présents
   - Actions de reconciliation

3. 🔄 **Étape 3+** (À définir)
   - Nettoyage supplémentaire
   - Validation métier avancée
   - Export vers système cible

## 🛠️ Architecture technique

### Classe principale: `BadgePurger`

- **`__init__(input_file, output_dir)`**: Initialisation
- **`validate_record(line_number, fields)`**: Validation statique des champs
- **`process_file()`**: Lecture et analyse du fichier
- **`write_output_files()`**: Écriture des fichiers de sortie
- **`write_report()`**: Génération du rapport
- **`run()`**: Orchestration du processus complet

### Gestion des erreurs

- Support automatique du fallback UTF-8 si CP1252 échoue
- Gestion des fins de ligne Windows (CR LF)
- Messages d'erreur détaillés et traceable

## 💡 Notes importantes

- Le fichier d'entrée n'est **pas modifié**
- Les fichiers de sortie sont **overwrite** s'ils existent déjà
- Les statistiques incluent les **lignes en doublon** en plus des valides
- Les erreurs sont **tracables** avec le numéro de ligne

## 📄 Licence

Interne - ERO Project

---

**Auteur**: Claude Code  
**Date**: 2026-06-19  
**Version**: 1.0
