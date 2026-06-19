#!/usr/bin/env python3
"""
Badge Database Purger
Removes duplicates and validates badge records from a CSV file.

Input format: N°badge(8digits);Nom;Prenom;Matricule(8digits);Catégorie(texte);Immatriculation(10digits);N°Cat(4digits)

Output files:
- badges_valides.csv: Valid records without duplicates
- badges_doublons.csv: Records flagged as duplicates
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
            'valid_lines': 0,
            'duplicate_lines': 0,
            'error_lines': 0,
            'duplicates_by_matricule': defaultdict(int)
        }

        # Data storage
        self.valid_records = []
        self.duplicate_records = []
        self.error_records = []

    @staticmethod
    def validate_record(line_number, fields):
        """
        Validate a record against business rules.

        Returns: (is_valid: bool, error_message: str or None)
        """
        errors = []

        # Check field count
        if len(fields) != 7:
            return False, f"Invalid field count: {len(fields)}, expected 7"

        badge_num, nom, prenom, matricule, categorie, immatriculation, num_cat = fields

        # Validate N° Badge (8 digits)
        if not re.match(r'^\d{8}$', badge_num):
            errors.append(f"N°Badge invalid: '{badge_num}' (must be 8 digits)")

        # Validate N° Matricule (8 digits)
        if not re.match(r'^\d{8}$', matricule):
            errors.append(f"N°Matricule invalid: '{matricule}' (must be 8 digits)")

        # Validate N° Immatriculation (NULL or 10 digits)
        if immatriculation.strip() and not re.match(r'^\d{10}$', immatriculation):
            errors.append(f"N°Immatriculation invalid: '{immatriculation}' (must be NULL or 10 digits)")

        # Validate N° Cat (4 digits)
        if not re.match(r'^\d{4}$', num_cat):
            errors.append(f"N°Cat invalid: '{num_cat}' (must be 4 digits)")

        if errors:
            return False, "; ".join(errors)

        return True, None

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

                    is_valid, error_msg = self.validate_record(line_num, row)

                    if not is_valid:
                        self.error_records.append((line_num, row, error_msg))
                        self.stats['error_lines'] += 1
                        continue

                    matricule = row[3]
                    immatriculation = row[5].strip() if row[5] else ''

                    records_by_matricule[matricule].append({
                        'line_num': line_num,
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

                    is_valid, error_msg = self.validate_record(line_num, row)

                    if not is_valid:
                        self.error_records.append((line_num, row, error_msg))
                        self.stats['error_lines'] += 1
                        continue

                    matricule = row[3]
                    immatriculation = row[5].strip() if row[5] else ''

                    records_by_matricule[matricule].append({
                        'line_num': line_num,
                        'fields': row,
                        'immatriculation': immatriculation
                    })

        # Second pass: detect duplicates
        for matricule, records in records_by_matricule.items():
            # Count unique immatriculations for this matricule
            immatriculations = set(r['immatriculation'] for r in records)
            num_immatriculations = len(immatriculations)

            self.stats['duplicates_by_matricule'][matricule] = num_immatriculations

            if num_immatriculations > 2:
                # Duplicate detected
                for record in records:
                    self.duplicate_records.append((record['line_num'], record['fields']))
                    self.stats['duplicate_lines'] += 1
            else:
                # Valid record
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
            f.write(f"Fichier d'entrée: {self.input_file}\r\n")
            f.write(f"Répertoire de sortie: {self.output_dir}\r\n\r\n")

            f.write("STATISTIQUES DE TRAITEMENT\r\n")
            f.write("-" * 70 + "\r\n")
            f.write(f"Nombre total de lignes: {self.stats['total_lines']:,}\r\n")
            f.write(f"Lignes valides (sans doublon): {self.stats['valid_lines']:,}\r\n")
            f.write(f"Lignes avec doublon: {self.stats['duplicate_lines']:,}\r\n")
            f.write(f"Lignes en erreur: {self.stats['error_lines']:,}\r\n\r\n")

            f.write("RÉSUMÉ\r\n")
            f.write("-" * 70 + "\r\n")
            total_traites = self.stats['valid_lines'] + self.stats['duplicate_lines']
            valid_percent = (self.stats['valid_lines'] / self.stats['total_lines'] * 100) if self.stats['total_lines'] > 0 else 0
            f.write(f"Lignes traitées avec succès: {total_traites:,}\r\n")
            f.write(f"Taux de validité: {valid_percent:.2f}%\r\n\r\n")

            if self.stats['duplicate_lines'] > 0:
                f.write("DÉTAILS DES DOUBLONS\r\n")
                f.write("-" * 70 + "\r\n")
                f.write(f"Nombre de matricules avec doublons: {sum(1 for v in self.stats['duplicates_by_matricule'].values() if v > 2):,}\r\n")
                f.write(f"Total de badges en doublons: {self.stats['duplicate_lines']:,}\r\n\r\n")

            if self.stats['error_lines'] > 0:
                f.write("DÉTAILS DES ERREURS\r\n")
                f.write("-" * 70 + "\r\n")
                error_types = defaultdict(int)
                for _, _, error_msg in self.error_records:
                    # Extract first error type
                    first_error = error_msg.split(';')[0] if error_msg else 'Unknown'
                    error_types[first_error] += 1

                for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"  - {error_type}: {count}\r\n")
                f.write("\r\n")

            f.write("FICHIERS GENERES\r\n")
            f.write("-" * 70 + "\r\n")
            f.write(f"[OK] badges_valides.csv ({self.stats['valid_lines']} lignes)\r\n")
            f.write(f"[OK] badges_doublons.csv ({self.stats['duplicate_lines']} lignes)\r\n")
            f.write(f"[OK] badges_erreurs.csv ({self.stats['error_lines']} lignes)\r\n")

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
