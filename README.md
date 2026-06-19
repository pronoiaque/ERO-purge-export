# Badge Database Purger (ERO Purge Export)

Script Python pour nettoyer et valider une base de données de badges, avec détection automatique des doublons.

## 📋 Description

Ce projet automatise le processus de purge d'une base de badges selon les critères de validation métier spécifiques. Le script:

- **Valide** chaque enregistrement contre des règles strictes
- **Détecte** les doublons (même matricule sur badges différents)
- **Génère** 5 fichiers de sortie catégorisés (valides, doublons, sans matricule, erreurs, rapport)
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
| **N° Matricule** | 8 chiffres OU vide (pour véhicules/équipement) |
| **N° Immatriculation** | NULL/'<vide>' ou exactement 10 chiffres |
| **N° Cat** | 1 à 4 chiffres |
| **Nombre de champs** | Exactement 7 champs |

### Détection de doublons

**Algorithme**: Un matricule est flaggé comme **doublon** uniquement s'il porte **STRICTEMENT PLUS DE 2 badges** (> 2, soit 3 ou plus).

- **1 ou 2 badges** par matricule = **NORMAL** (badge provisoire + badge définitif, les deux valides)
- **3 badges et plus** (triplon, quadruplon...) = **DOUBLON**

> Note métier : le numéro de badge définitif est dérivé du numéro d'immatriculation (les 2 premiers digits de gauche sont retirés). Exemple : immatriculation `1884564620` → badge `84564620`. Un agent a donc légitimement jusqu'à 2 badges (provisoire + définitif).

**Exemples**:
```
BENDRIES - Matricule 01901464: 2 badges (01901464 + 84564620)
  → NORMAL (provisoire + definitif), reste en VALIDE

TRIPLON - Matricule 55555555: 3 badges (99999996 + 99999997 + 99999998)
  → DOUBLON (3 > 2), les 3 lignes vont en doublons
```

## 📤 Format de sortie

Le script génère **5 fichiers** dans le répertoire de sortie:

### 1. `badges_valides.csv`
- Enregistrements valides avec matricule, sans doublon
- Format identique au fichier d'entrée
- Encodage: CP1252, fins de ligne: CR LF

### 2. `badges_doublons.csv`
- Enregistrements dont le matricule porte **plus de 2 badges** (triplon, quadruplon...)
- Format identique au fichier d'entrée
- Toutes les lignes du matricule concerné sont incluses

### 3. `badges_sans_matricule.csv`
- Enregistrements valides mais SANS matricule
- Catégorie: véhicules de service, équipements partagés, SAMU, etc.
- Format identique au fichier d'entrée
- Ces lignes ne sont pas considérées comme des erreurs

### 4. `badges_erreurs.csv`
- Enregistrements qui n'ont pas passé la validation
- Format enrichi avec colonne d'erreur:
  ```
  # Ligne;N°Badge;Nom;Prenom;Matricule;Categorie;Immatriculation;N°Cat;ERREUR
  3;00011404;PENELLO;CHARLENE;01347502;2110 Z S T C D HE;;766;N°Cat invalid: '766' (must be 1-4 digits)
  ```

### 5. `rapport_purge.txt`
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

### Exemple 1: Mix valides, erreurs, sans matricule
**Fichier d'entrée** (`badges.csv`):
```
12345678;Dupont;Jean;87654321;Manager;1234567890;0001
12345679;Martin;Marie;87654322;Operateur;1234567891;0002
INVALID;Durand;Paul;87654323;Operateur;1234567892;0003
12345680;SAMU;;;;<vide>;0004
12345681;Lefevre;Pierre;87654324;Manager;;90
```

**Résultats**:
- `badges_valides.csv`: 2 lignes (12345678, 12345679, 12345681)
- `badges_sans_matricule.csv`: 1 ligne (SAMU - véhicule sans matricule)
- `badges_erreurs.csv`: 1 ligne (INVALID - mauvais numéro de badge)
- `rapport_purge.txt`: Statistiques détaillées

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
