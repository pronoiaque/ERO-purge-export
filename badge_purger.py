#!/usr/bin/env python3
"""
Badge Database Purger - Advanced Edition
Removes duplicates and validates badge records from a CSV file.

Input format: N°badge(8digits);Nom;Prenom;Matricule(8digits);Categorie(texte);Immatriculation(10digits);N°Cat(1-4digits)

Output files:
- badges_valides.csv: Valid records without duplicates
- badges_doublons_a_garder.csv: Definitive badge + MIFARE twin (normal, keep)
- badges_doublons_a_purger.csv: Excess badges beyond the pair (purge)
- badges_matricule_collectif.csv: Shared matricules (multiple different persons)
- badges_sans_matricule.csv: Records with no matricule (vehicles, shared equipment)
- badges_erreurs.csv: Records that failed validation (with error type)
- rapport_purge.txt: Processing statistics report
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re


class BadgePurger:
    def __init__(self, input_file, output_dir=None):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir) if output_dir else self.input_file.parent
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            'total_lines': 0,
            'header_lines': 0,
            'valid_lines': 0,
            'doublon_keep_lines': 0,
            'doublon_purge_lines': 0,
            'collectif_lines': 0,
            'no_matricule_lines': 0,
            'error_lines': 0,
            'error_types': defaultdict(int),
            'matricules_collectif': set(),
            'matricules_doublon': set(),
        }

        # Data storage
        self.valid_records = []
        self.doublon_keep_records = []
        self.doublon_purge_records = []
        self.collectif_records = []
        self.no_matricule_records = []
        self.error_records = []

    @staticmethod
    def is_header_or_separator(fields):
        """Check if line is header or separator line."""
        if len(fields) == 0:
            return True
        if len(fields) == 1 and all(c == '-' for c in fields[0]):
            return True
        if len(fields) > 0 and 'badge' in fields[0].lower() and 'nom' in str(fields).lower():
            return True
        return False

    @staticmethod
    def classify_error(fields):
        """Classify the type of error in the record."""
        if len(fields) < 7:
            return "Invalid_field_count"

        badge_num, nom, prenom, matricule, categorie, immatriculation, num_cat = fields[:7]

        errors = []

        # N° Badge validation
        if not re.match(r'^\d{8}$', badge_num):
            if not re.match(r'^\d+$', badge_num):
                errors.append("Badge_non_numerique")
            else:
                errors.append("Badge_mauvaise_longueur")

        # N° Matricule validation
        if matricule.strip():
            if not re.match(r'^\d{8}$', matricule):
                if not re.match(r'^\d+$', matricule):
                    errors.append("Matricule_non_numerique")
                else:
                    errors.append("Matricule_mauvaise_longueur")

        # N° Immatriculation validation
        immat_clean = immatriculation.strip()
        if immat_clean and immat_clean.lower() != '<vide>':
            if not re.match(r'^\d+$', immat_clean):
                errors.append("Immatriculation_texte_libre")
            elif len(immat_clean) != 10:
                errors.append("Immatriculation_mauvaise_longueur")

        # N° Cat validation
        if num_cat.strip() and not re.match(r'^\d{1,4}$', num_cat):
            if not re.match(r'^\d+$', num_cat):
                errors.append("NumCat_non_numerique")
            else:
                errors.append("NumCat_mauvaise_longueur")

        return errors[0] if errors else "Unknown"

    @staticmethod
    def validate_record(line_number, fields):
        """
        Validate a record against business rules.

        Returns: (is_valid: bool, has_matricule: bool, error_message: str or None)
        """
        errors = []

        # Check field count
        if len(fields) != 7:
            return False, True, f"Invalid field count: {len(fields)}, expected 7"

        badge_num, nom, prenom, matricule, categorie, immatriculation, num_cat = fields

        # Check if matricule is empty (vehicle/equipment)
        has_matricule = bool(matricule.strip())

        # Validate N° Badge (8 digits)
        if not re.match(r'^\d{8}$', badge_num):
            errors.append(f"N°Badge invalid: '{badge_num}' (must be 8 digits)")

        # N° Matricule validation: 8 digits IF present
        if has_matricule and not re.match(r'^\d{8}$', matricule):
            errors.append(f"N°Matricule invalid: '{matricule}' (must be 8 digits if present)")

        # Validate N° Immatriculation (NULL or 10 digits)
        immat_clean = immatriculation.strip()
        if immat_clean and immat_clean.lower() != '<vide>' and not re.match(r'^\d{10}$', immat_clean):
            errors.append(f"N°Immatriculation invalid: '{immat_clean}' (must be NULL or 10 digits)")

        # Validate N° Cat (1-4 digits)
        if num_cat.strip() and not re.match(r'^\d{1,4}$', num_cat):
            errors.append(f"N°Cat invalid: '{num_cat}' (must be 1-4 digits)")

        if errors:
            return False, has_matricule, "; ".join(errors)

        return True, has_matricule, None

    def process_file(self):
        """Process the input file and categorize records."""
        print(f"Processing file: {self.input_file}")
        print("=" * 70)

        # First pass: validate and collect records
        records_by_matricule = defaultdict(list)

        try:
            with open(self.input_file, 'r', encoding='cp1252', newline='') as f:
                reader = csv.reader(f, delimiter=';')

                for line_num, row in enumerate(reader, start=1):
                    self.stats['total_lines'] += 1

                    # Skip header/separator lines
                    if self.is_header_or_separator(row):
                        self.stats['header_lines'] += 1
                        continue

                    is_valid, has_matricule, error_msg = self.validate_record(line_num, row)

                    if not is_valid:
                        error_type = self.classify_error(row)
                        self.error_records.append((line_num, row, error_msg, error_type))
                        self.stats['error_lines'] += 1
                        self.stats['error_types'][error_type] += 1
                        continue

                    # If valid but no matricule, separate category
                    if not has_matricule:
                        self.no_matricule_records.append((line_num, row))
                        self.stats['no_matricule_lines'] += 1
                        continue

                    # Valid record with matricule
                    matricule = row[3]
                    badge_num = row[0]
                    immatriculation = row[5].strip()

                    records_by_matricule[matricule].append({
                        'line_num': line_num,
                        'badge': badge_num,
                        'fields': row,
                        'immatriculation': immatriculation
                    })

        except UnicodeDecodeError as e:
            print(f"ERROR: File encoding issue: {e}")
            print("Attempting with UTF-8 encoding...")
            with open(self.input_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f, delimiter=';')

                for line_num, row in enumerate(reader, start=1):
                    self.stats['total_lines'] += 1

                    if self.is_header_or_separator(row):
                        self.stats['header_lines'] += 1
                        continue

                    is_valid, has_matricule, error_msg = self.validate_record(line_num, row)

                    if not is_valid:
                        error_type = self.classify_error(row)
                        self.error_records.append((line_num, row, error_msg, error_type))
                        self.stats['error_lines'] += 1
                        self.stats['error_types'][error_type] += 1
                        continue

                    if not has_matricule:
                        self.no_matricule_records.append((line_num, row))
                        self.stats['no_matricule_lines'] += 1
                        continue

                    matricule = row[3]
                    badge_num = row[0]
                    immatriculation = row[5].strip()

                    records_by_matricule[matricule].append({
                        'line_num': line_num,
                        'badge': badge_num,
                        'fields': row,
                        'immatriculation': immatriculation
                    })

        # Second pass: detect duplicates and categorize
        for matricule, records in records_by_matricule.items():
            distinct_badges = set(r['badge'] for r in records)

            if len(distinct_badges) <= 2:
                # Normal: 1 or 2 badges per matricule
                for record in records:
                    self.valid_records.append((record['line_num'], record['fields']))
                    self.stats['valid_lines'] += 1
            else:
                # Doublon: 3+ badges
                self.stats['matricules_doublon'].add(matricule)

                # Strategy: keep the 2 badges with the earliest line numbers
                # (usually definitive + MIFARE twin), purge the rest
                sorted_records = sorted(records, key=lambda r: r['line_num'])

                for i, record in enumerate(sorted_records):
                    if i < 2:
                        # Keep first 2
                        self.doublon_keep_records.append((record['line_num'], record['fields']))
                        self.stats['doublon_keep_lines'] += 1
                    else:
                        # Purge the rest
                        self.doublon_purge_records.append((record['line_num'], record['fields']))
                        self.stats['doublon_purge_lines'] += 1

        # Third pass: detect collective matricules (shared by different persons)
        for matricule, records in records_by_matricule.items():
            if matricule in self.stats['matricules_doublon']:
                # Extract unique persons (clean name by removing PRET suffix)
                persons = set()
                for r in records:
                    name = r['fields'][1].replace(' PRET', '').replace(' pret', '').strip().upper()
                    persons.add(name)

                if len(persons) >= 3:
                    self.stats['matricules_collectif'].add(matricule)
                    # Move from doublon_keep to collectif
                    self.doublon_keep_records = [
                        (ln, f) for ln, f in self.doublon_keep_records
                        if f[3] != matricule
                    ]
                    self.doublon_purge_records = [
                        (ln, f) for ln, f in self.doublon_purge_records
                        if f[3] != matricule
                    ]
                    self.stats['doublon_keep_lines'] -= sum(1 for r in records if r['badge'] == matricule or (r['immatriculation'] and r['immatriculation'][2:] == r['badge']))
                    self.stats['doublon_purge_lines'] -= sum(1 for r in records if r['badge'] != matricule and (not r['immatriculation'] or r['immatriculation'][2:] != r['badge']))

                    # Add all to collectif
                    for record in records:
                        self.collectif_records.append((record['line_num'], record['fields']))
                        self.stats['collectif_lines'] += 1

    def write_output_files(self):
        """Write the categorized records to output files."""
        print("\nWriting output files...")

        # Write valid records
        valid_file = self.output_dir / 'badges_valides.csv'
        with open(valid_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            for _, fields in sorted(self.valid_records):
                writer.writerow(fields)
        print(f"[OK] Valid records: {valid_file}")

        # Write doublon keep records
        doublon_keep_file = self.output_dir / 'badges_doublons_a_garder.csv'
        with open(doublon_keep_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            for _, fields in sorted(self.doublon_keep_records):
                writer.writerow(fields)
        print(f"[OK] Doublon keep: {doublon_keep_file}")

        # Write doublon purge records
        doublon_purge_file = self.output_dir / 'badges_doublons_a_purger.csv'
        with open(doublon_purge_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            for _, fields in sorted(self.doublon_purge_records):
                writer.writerow(fields)
        print(f"[OK] Doublon purge: {doublon_purge_file}")

        # Write collectif records
        collectif_file = self.output_dir / 'badges_matricule_collectif.csv'
        with open(collectif_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            for _, fields in sorted(self.collectif_records):
                writer.writerow(fields)
        print(f"[OK] Collective matricules: {collectif_file}")

        # Write no-matricule records
        no_matricule_file = self.output_dir / 'badges_sans_matricule.csv'
        with open(no_matricule_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            for _, fields in sorted(self.no_matricule_records):
                writer.writerow(fields)
        print(f"[OK] No-matricule records: {no_matricule_file}")

        # Write error records with type
        error_file = self.output_dir / 'badges_erreurs.csv'
        with open(error_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            f.write("# Ligne;N°Badge;Nom;Prenom;Matricule;Categorie;Immatriculation;N°Cat;TYPE_ERREUR;ERREUR\r\n")
            for line_num, fields, error_msg, error_type in sorted(self.error_records):
                row = [str(line_num)] + fields + [error_type, error_msg]
                writer.writerow(row)
        print(f"[OK] Error records: {error_file}")

    def write_report(self):
        """Generate and write the processing report."""
        report_file = self.output_dir / 'rapport_purge.txt'

        with open(report_file, 'w', encoding='cp1252', newline='') as f:
            f.write("RAPPORT DE PURGE DE BASE DE BADGES - EDITION AVANCEE\r\n")
            f.write("=" * 70 + "\r\n\r\n")

            f.write(f"Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\r\n")
            f.write(f"Fichier d'entree: {self.input_file}\r\n")
            f.write(f"Repertoire de sortie: {self.output_dir}\r\n\r\n")

            f.write("STATISTIQUES DE TRAITEMENT\r\n")
            f.write("-" * 70 + "\r\n")
            f.write(f"Nombre total de lignes: {self.stats['total_lines']:,}\r\n")
            f.write(f"Lignes d'en-tete/separateurs ignorees: {self.stats['header_lines']:,}\r\n")
            f.write(f"Lignes traitees: {self.stats['total_lines'] - self.stats['header_lines']:,}\r\n\r\n")

            f.write(f"Lignes valides (sans doublon, avec matricule): {self.stats['valid_lines']:,}\r\n")
            f.write(f"Lignes doublons a GARDER (definitif+jumeau): {self.stats['doublon_keep_lines']:,}\r\n")
            f.write(f"Lignes doublons a PURGER (exces): {self.stats['doublon_purge_lines']:,}\r\n")
            f.write(f"Lignes matricule collectif (partage): {self.stats['collectif_lines']:,}\r\n")
            f.write(f"Lignes sans matricule (vehicules/partage): {self.stats['no_matricule_lines']:,}\r\n")
            f.write(f"Lignes en erreur: {self.stats['error_lines']:,}\r\n\r\n")

            f.write("RESUME\r\n")
            f.write("-" * 70 + "\r\n")
            total_acceptables = (self.stats['valid_lines'] + self.stats['doublon_keep_lines'] +
                                 self.stats['no_matricule_lines'])
            all_traites = self.stats['total_lines'] - self.stats['header_lines']
            valid_percent = (total_acceptables / all_traites * 100) if all_traites > 0 else 0

            f.write(f"Lignes acceptables (valides + a garder + sans mat): {total_acceptables:,}\r\n")
            f.write(f"Lignes a purger (doublons excess): {self.stats['doublon_purge_lines']:,}\r\n")
            f.write(f"Lignes avec erreurs: {self.stats['error_lines']:,}\r\n")
            f.write(f"Taux d'acceptabilite: {valid_percent:.2f}%\r\n\r\n")

            f.write("DETAILS DES DOUBLONS\r\n")
            f.write("-" * 70 + "\r\n")
            f.write(f"Nombre de matricules en doublon: {len(self.stats['matricules_doublon']):,}\r\n")
            f.write(f"  - Matricules collectifs (3+ personnes): {len(self.stats['matricules_collectif']):,}\r\n")
            f.write(f"  - Matricules vrais doublons (meme personne): {len(self.stats['matricules_doublon']) - len(self.stats['matricules_collectif']):,}\r\n\r\n")

            f.write("ACTION RECOMMANDEE:\r\n")
            f.write(f"  - CONSERVER: {self.stats['doublon_keep_lines']:,} badges (badges_doublons_a_garder.csv)\r\n")
            f.write(f"  - PURGER: {self.stats['doublon_purge_lines']:,} badges (badges_doublons_a_purger.csv)\r\n")
            f.write(f"  - REVISER: {self.stats['collectif_lines']:,} badges partages (badges_matricule_collectif.csv)\r\n\r\n")

            f.write("DETAILS DES ERREURS\r\n")
            f.write("-" * 70 + "\r\n")
            if self.stats['error_lines'] > 0:
                f.write(f"Total d'erreurs detectees: {self.stats['error_lines']:,}\r\n\r\n")
                f.write("Repartition par type d'erreur:\r\n")
                for error_type, count in sorted(self.stats['error_types'].items(), key=lambda x: x[1], reverse=True):
                    percent = (count / self.stats['error_lines'] * 100) if self.stats['error_lines'] > 0 else 0
                    f.write(f"  - {error_type}: {count} ({percent:.1f}%)\r\n")
                f.write("\r\n")
            else:
                f.write("Aucune erreur detectee.\r\n\r\n")

            f.write("FICHIERS GENERES\r\n")
            f.write("-" * 70 + "\r\n")
            f.write(f"[OK] badges_valides.csv ({self.stats['valid_lines']} lignes)\r\n")
            f.write(f"[OK] badges_doublons_a_garder.csv ({self.stats['doublon_keep_lines']} lignes)\r\n")
            f.write(f"[OK] badges_doublons_a_purger.csv ({self.stats['doublon_purge_lines']} lignes)\r\n")
            f.write(f"[OK] badges_matricule_collectif.csv ({self.stats['collectif_lines']} lignes)\r\n")
            f.write(f"[OK] badges_sans_matricule.csv ({self.stats['no_matricule_lines']} lignes)\r\n")
            f.write(f"[OK] badges_erreurs.csv ({self.stats['error_lines']} lignes)\r\n\r\n")

            f.write("=" * 70 + "\r\n")
            f.write("Fin du rapport\r\n")

        print(f"[OK] Rapport: {report_file}")

    def run(self):
        """Execute the purge process."""
        try:
            self.process_file()
            self.write_output_files()
            self.write_report()

            print("\n" + "=" * 70)
            print("PURGE COMPLETEE")
            print("=" * 70)
            print(f"Lignes valides: {self.stats['valid_lines']:,}")
            print(f"Doublons (garder): {self.stats['doublon_keep_lines']:,}")
            print(f"Doublons (purger): {self.stats['doublon_purge_lines']:,}")
            print(f"Matricule collectif: {self.stats['collectif_lines']:,}")
            print(f"Sans matricule: {self.stats['no_matricule_lines']:,}")
            print(f"Erreurs: {self.stats['error_lines']:,}")

            return True

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python badge_purger.py <input_file> [output_dir]")
        print("\nExample: python badge_purger.py badges.csv ./output")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(input_file).exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)

    purger = BadgePurger(input_file, output_dir)
    success = purger.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
