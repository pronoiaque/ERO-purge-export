# Badge Database Purger - Advanced Edition (ERO Purge Export)

Script Python pour nettoyer et valider une base de données de badges, avec **détection intelligente des doublons** et **recommandations de purge**.

## 📋 Description

Ce projet automatise le processus de purge d'une base de badges selon les critères de validation métier spécifiques. Le script:

- **Valide** chaque enregistrement contre des règles strictes
- **Détecte** les doublons (matricule avec 3+ badges)
- **Recommande** quels badges conserver (2 premiers = définitif + jumeau MIFARE)
- **Génère** 7 fichiers de sortie catégorisés (valides, doublons à garder, doublons à purger, collectifs, sans matricule, erreurs, rapport)
- **Classe** les erreurs par type pour une meilleure traçabilité
- **Produit** un rapport actionnel détaillé

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
| **N° Matricule** | 8 chiffres OU vide (pour véhicules/équipement) |
| **N° Immatriculation** | NULL/'<vide>' ou exactement 10 chiffres |
| **N° Cat** | 1 à 4 chiffres |
| **Nombre de champs** | Exactement 7 champs |

### Détection et traitement des doublons

**Algorithme**: Un matricule est flaggé comme **doublon** si il porte **3+ badges** (> 2).

**Traitement intelligent:**
- **1 ou 2 badges** → NORMAL (valide) : garder les 2
- **3+ badges** → DOUBLON : garder les 2 premiers (déf + jumeau), purger les excédents

**Les 2 badges à garder correspondent généralement à:**
1. **Badge définitif** : numéro = matricule (porte le MIFARE permanent)
2. **Jumeau MIFARE** : numéro = 8 derniers chiffres de l'immatriculation (badge temporaire/backup)

**Exemple - Matricule 01090439 (4 badges):**
```
Ligne 72:  Badge 00211032 → EXCESS (purger)
Ligne 391: Badge 01090439 (définitif) → GARDER
Ligne 25159: Badge 11881755 (immat 1711881755[2:]) → GARDER
Ligne 32008: Badge 30361115 → EXCESS (purger)

Résultat: 2 gardés, 2 purgés
```

## 📤 Format de sortie

Le script génère **7 fichiers** dans le répertoire de sortie:

### 1. `badges_valides.csv`
- Enregistrements valides avec matricule, sans doublon (1-2 badges = normal)
- Format identique au fichier d'entrée
- Encodage: CP1252, fins de ligne: CR LF

### 2. `badges_doublons_a_garder.csv`
- **Les 2 premiers badges** de chaque matricule en doublon (à CONSERVER)
- Normalement: badge définitif (badge = matricule) + jumeau MIFARE (badge = immat[2:])
- Format identique au fichier d'entrée
- **Action: RIEN À FAIRE** (garder ces enregistrements)

### 3. `badges_doublons_a_purger.csv`
- **Badges excédentaires** (au-delà des 2 premiers) du même matricule
- **Action: SUPPRIMER** ces enregistrements
- Format identique au fichier d'entrée

### 4. `badges_matricule_collectif.csv`
- Enregistrements valides d'un **matricule partagé** par 3+ personnes différentes
- Exemple: BIO-NETTOYAGE avec 23 personnes différentes
- **Action: REVISER** (possiblement un vrai matricule de service/département)
- Format identique au fichier d'entrée

### 5. `badges_sans_matricule.csv`
- Enregistrements valides mais SANS matricule
- Catégorie: véhicules de service, équipements partagés, SAMU, badges PRET, etc.
- Format identique au fichier d'entrée
- **Action: VALIDER** (vérifier si intentionnel)

### 6. `badges_erreurs.csv`
- Enregistrements qui n'ont pas passé la validation
- Format enrichi avec colonne TYPE_ERREUR:
  ```
  # Ligne;N°Badge;Nom;Prenom;Matricule;Categorie;Immatriculation;N°Cat;TYPE_ERREUR;ERREUR
  9;00012879;winiewski;;290019;...;;1838;Matricule_mauvaise_longueur;N°Matricule invalid: '290019' (must be 8 digits if present)
  ```

**Types d'erreur possibles:**
- `Badge_non_numerique` / `Badge_mauvaise_longueur` : N°Badge invalide
- `Matricule_non_numerique` / `Matricule_mauvaise_longueur` : N°Matricule invalide
- `Immatriculation_texte_libre` / `Immatriculation_mauvaise_longueur` : N°Immatriculation invalide
- `NumCat_non_numerique` / `NumCat_mauvaise_longueur` : N°Cat invalide
- `Invalid_field_count` : Nombre de champs incorrect

### 7. `rapport_purge.txt`
Rapport détaillé contenant:
- **Métadonnées**: Date, fichier d'entrée, répertoire de sortie
- **Statistiques globales**: Total lignes, valides, doublons (garder/purger), collectifs, sans matricule, erreurs
- **Taux d'acceptabilité**: Pourcentage d'enregistrements acceptables
- **Action recommandée**: 
  - CONSERVER: X badges (fichier a_garder)
  - PURGER: Y badges (fichier a_purger)
  - REVISER: Z badges (fichier collectif)
- **Analyse des erreurs**: Décomposition par type, avec exemples
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

### Exemple 1: Mix valides, doublons, erreurs
**Fichier d'entrée** (`badges.csv`):
```
12345678;Dupont;Jean;87654321;Manager;1234567890;0001
12345679;Martin;Marie;87654322;Operateur;1234567891;0002
12345680;Dupont;Jean;87654321;Manager;;0003
12345681;Dupont;Jean;87654321;Manager;;0004
INVALID;Durand;Paul;87654323;Operateur;1234567892;0005
12345682;SAMU;;;;<vide>;0006
```

**Résultats**:
- **Ligne 1-2**: 2 badges différents pour 2 matricules → `badges_valides.csv`
- **Lignes 3-5**: Matricule `87654321` sur 4 badges (12345678, 12345680, 12345681, 12345682)
  - Lignes 3-4 (premiers 2) → `badges_doublons_a_garder.csv`
  - Ligne 5 (excédent) → `badges_doublons_a_purger.csv`
- **Ligne 6**: Badge INVALID → `badges_erreurs.csv` (Badge_non_numerique)
- **Ligne 7**: SAMU sans matricule → `badges_sans_matricule.csv`

**Action recommandée:**
```
CONSERVER: 4 badges (2 valides + 2 doublons à garder)
PURGER: 1 badge (excess)
```

### Exemple 2: Détection de doublons (règle > 2 badges)
**Fichier d'entrée**:
```
01901464;BENDRIES;OLIVIER;01901464;0282 DSI;1884564620;170
84564620;BENDRIES;OLIVIER;01901464;0282 DSI;;170
99999996;TRIPLON;TEST;55555555;CAT A;9999999996;100
99999997;TRIPLON;TEST;55555555;CAT A;9999999997;100
99999998;TRIPLON;TEST;55555555;CAT A;;100
```

**Résultats**:
- **BENDRIES**: Matricule `01901464` sur 2 badges → **VALIDE** (normal)
- **TRIPLON**: Matricule `55555555` sur 3 badges (> 2) → **DOUBLON**
- Les 3 lignes TRIPLON vont dans `badges_doublons.csv`

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
