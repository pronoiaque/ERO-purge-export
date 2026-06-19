#!/usr/bin/env python3
"""
Badge Database Purger
Removes duplicates and validates badge records from a CSV file.

Input format: N°badge(8digits);Nom;Prenom;Matricule(8digits);Categorie(texte);Immatriculation(10digits);N°Cat(1-4digits)

Output files:
- badges_valides.csv: Valid records without duplicates
- badges_doublons.csv: Records flagged as duplicates (badge derived from immatriculation)
- badges_sans_matricule.csv: Records with no matricule (vehicles, shared equipment)
- badges_erreurs.csv: Records that failed validation
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
            'separator_lines': 0,
            'valid_lines': 0,
            'duplicate_lines': 0,
            'no_matricule_lines': 0,
            'error_lines': 0,
            'duplicates_by_badge': defaultdict(list)
        }

        # Data storage
        self.valid_records = []
        self.duplicate_records = []
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
        records_by_badge = defaultdict(list)
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
                        self.error_records.append((line_num, row, error_msg))
                        self.stats['error_lines'] += 1
                        continue

                    # If valid but no matricule, separate category
                    if not has_matricule:
                        self.no_matricule_records.append((line_num, row))
                        self.stats['no_matricule_lines'] += 1
                        continue

                    # Valid record with matricule
                    badge_num = row[0]
                    matricule = row[3]
                    immatriculation = row[5].strip()

                    records_by_badge[badge_num].append({
                        'line_num': line_num,
                        'fields': row,
                        'immatriculation': immatriculation
                    })
                    records_by_matricule[matricule].append({
                        'line_num': line_num,
                        'badge': badge_num,
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
                        self.error_records.append((line_num, row, error_msg))
                        self.stats['error_lines'] += 1
                        continue

                    if not has_matricule:
                        self.no_matricule_records.append((line_num, row))
                        self.stats['no_matricule_lines'] += 1
                        continue

                    badge_num = row[0]
                    matricule = row[3]
                    immatriculation = row[5].strip()

                    records_by_badge[badge_num].append({
                        'line_num': line_num,
                        'fields': row,
                        'immatriculation': immatriculation
                    })
                    records_by_matricule[matricule].append({
                        'line_num': line_num,
                        'badge': badge_num,
                        'immatriculation': immatriculation
                    })

        # Second pass: detect duplicates
        # Strategy: A badge is a duplicate if:
        # 1. Same badge number appears multiple times (badge reused), OR
        # 2. Same matricule has multiple different badges (person has multiple badges)
        # Track which records are flagged as duplicates
        duplicate_matricules = set()
        duplicate_badge_nums = set()

        # Check for same matricule on different badges
        for matricule, records in records_by_matricule.items():
            badge_nums = set(r['badge'] for r in records)
            if len(badge_nums) > 1:
                # Same matricule, multiple badges = duplicate
                duplicate_matricules.add(matricule)
                for r in records:
                    duplicate_badge_nums.add(r['badge'])

        # Check for same badge number on multiple records
        for badge_num, records in records_by_badge.items():
            if len(records) > 1:
                duplicate_badge_nums.add(badge_num)

        # Categorize records
        for badge_num, records in records_by_badge.items():
            if badge_num in duplicate_badge_nums:
                for record in records:
                    self.duplicate_records.append((record['line_num'], record['fields']))
                    self.stats['duplicate_lines'] += 1
                    self.stats['duplicates_by_badge'][badge_num] = records
            else:
                for record in records:
                    self.valid_records.append((record['line_num'], record['fields']))
                    self.stats['valid_lines'] += 1

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

        # Write duplicate records
        duplicate_file = self.output_dir / 'badges_doublons.csv'
        with open(duplicate_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            for _, fields in sorted(self.duplicate_records):
                writer.writerow(fields)
        print(f"[OK] Duplicate records: {duplicate_file}")

        # Write no-matricule records
        no_matricule_file = self.output_dir / 'badges_sans_matricule.csv'
        with open(no_matricule_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            for _, fields in sorted(self.no_matricule_records):
                writer.writerow(fields)
        print(f"[OK] No-matricule records: {no_matricule_file}")

        # Write error records
        error_file = self.output_dir / 'badges_erreurs.csv'
        with open(error_file, 'w', encoding='cp1252', newline='') as f:
            writer = csv.writer(f, delimiter=';', lineterminator='\r\n')
            # Write header with error message
            f.write("# Ligne;N°Badge;Nom;Prenom;Matricule;Categorie;Immatriculation;N°Cat;ERREUR\r\n")
            for line_num, fields, error_msg in sorted(self.error_records):
                row = [str(line_num)] + fields + [error_msg]
                writer.writerow(row)
        print(f"[OK] Error records: {error_file}")

    def write_report(self):
        """Generate and write the processing report."""
        report_file = self.output_dir / 'rapport_purge.txt'

        with open(report_file, 'w', encoding='cp1252', newline='') as f:
            f.write("RAPPORT DE PURGE DE BASE DE BADGES\r\n")
            f.write("=" * 70 + "\r\n\r\n")

            f.write(f"Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\r\n")
            f.write(f"Fichier d'entree: {self.input_file}\r\n")
            f.write(f"Repertoire de sortie: {self.output_dir}\r\n\r\n")

            f.write("STATISTIQUES DE TRAITEMENT\r\n")
            f.write("-" * 70 + "\r\n")
            f.write(f"Nombre total de lignes: {self.stats['total_lines']:,}\r\n")
            f.write(f"Lignes d'en-tete/separateurs ignorees: {self.stats['header_lines']:,}\r\n")
            f.write(f"Lignes traitees: {self.stats['total_lines'] - self.stats['header_lines']:,}\r\n\r\n")

            f.write(f"Lignes valides (avec matricule, sans doublon): {self.stats['valid_lines']:,}\r\n")
            f.write(f"Lignes en doublon (badge duplique): {self.stats['duplicate_lines']:,}\r\n")
            f.write(f"Lignes sans matricule (vehicules/partage): {self.stats['no_matricule_lines']:,}\r\n")
            f.write(f"Lignes en erreur: {self.stats['error_lines']:,}\r\n\r\n")

            f.write("RESUME\r\n")
            f.write("-" * 70 + "\r\n")
            total_traites = self.stats['valid_lines'] + self.stats['duplicate_lines'] + self.stats['no_matricule_lines']
            all_traites = self.stats['total_lines'] - self.stats['header_lines']
            valid_percent = (self.stats['valid_lines'] / all_traites * 100) if all_traites > 0 else 0
            f.write(f"Lignes acceptables (valides + sans matricule): {total_traites:,}\r\n")
            f.write(f"Lignes avec erreurs: {self.stats['error_lines']:,}\r\n")
            f.write(f"Taux d'acceptabilite: {valid_percent:.2f}%\r\n\r\n")

            if self.stats['duplicate_lines'] > 0:
                f.write("DETAILS DES DOUBLONS (BADGES DUPLIQUES)\r\n")
                f.write("-" * 70 + "\r\n")

                f.write(f"Nombre de badges en doublon: {len(self.stats['duplicates_by_badge']):,}\r\n")
                f.write(f"Total de lignes concernees: {self.stats['duplicate_lines']:,}\r\n\r\n")

                # List all duplicates by badge
                if self.stats['duplicates_by_badge']:
                    f.write("Badges dupliques (meme numero de badge sur plusieurs lignes):\r\n")
                    f.write("-" * 70 + "\r\n")
                    for badge_num, count in sorted(self.stats['duplicates_by_badge'].items()):
                        badges_for_badge = [(ln, fi) for ln, fi in self.duplicate_records if fi[0] == badge_num]
                        f.write(f"  Badge {badge_num}: {count} occurrences\r\n")
                        for line_num, fields in sorted(badges_for_badge):
                            matricule = fields[3] if len(fields) > 3 else ''
                            immat = fields[5] if len(fields) > 5 else ''
                            immat_display = immat.strip() if immat else '<vide>'
                            f.write(f"    Ligne {line_num}: {fields[1]} {fields[2]}, Matricule={matricule}, Immat={immat_display}\r\n")
                    f.write("\r\n")

            if self.stats['no_matricule_lines'] > 0:
                f.write("DETAILS DES BADGES SANS MATRICULE\r\n")
                f.write("-" * 70 + "\r\n")
                f.write(f"Total: {self.stats['no_matricule_lines']:,} badges\r\n")
                f.write("(Vehicules de service, equipements partages, etc.)\r\n\r\n")

            if self.stats['error_lines'] > 0:
                f.write("DETAILS DES ERREURS\r\n")
                f.write("-" * 70 + "\r\n")
                error_types = defaultdict(int)
                for _, _, error_msg in self.error_records:
                    # Extract first error type
                    first_error = error_msg.split(';')[0] if error_msg else 'Unknown'
                    error_types[first_error] += 1

                f.write(f"Total d'erreurs detectees: {self.stats['error_lines']:,}\r\n\r\n")
                f.write("Repartition par type d'erreur:\r\n")
                for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                    percent = (count / self.stats['error_lines'] * 100) if self.stats['error_lines'] > 0 else 0
                    f.write(f"  - {error_type}: {count} ({percent:.1f}%)\r\n")
                f.write("\r\n")

                # List first 20 errors as examples
                f.write("Exemples d'erreurs (20 premieres):\r\n")
                f.write("-" * 70 + "\r\n")
                for i, (line_num, fields, error_msg) in enumerate(sorted(self.error_records)[:20]):
                    badge = fields[0] if len(fields) > 0 else 'N/A'
                    nom = fields[1] if len(fields) > 1 else ''
                    f.write(f"  Ligne {line_num} - Badge {badge} ({nom}): {error_msg}\r\n")
                if len(self.error_records) > 20:
                    f.write(f"  ... et {len(self.error_records) - 20} autres erreurs\r\n")
                f.write("\r\n")

            f.write("FICHIERS GENERES\r\n")
            f.write("-" * 70 + "\r\n")
            f.write(f"[OK] badges_valides.csv ({self.stats['valid_lines']} lignes)\r\n")
            f.write(f"[OK] badges_doublons.csv ({self.stats['duplicate_lines']} lignes)\r\n")
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
            print(f"Doublons: {self.stats['duplicate_lines']:,}")
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
