import os
import sys
import sqlite3
import logging
import django
from django.db import transaction
from collections import defaultdict
from datetime import datetime

# Setup Django Environment
sys.path.append('/Users/paulcurtis/Development/cartridge_collection/cartridge_collection')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cartridge_collection.settings')
django.setup()

from collection.models import LoadType, BulletType, CaseType, PrimerType, PAColor

# Generate a timestamp for unique filenames
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Configure logging
log_filename = f'/Users/paulcurtis/Development/cartridge_collection/cartridge_collection/data_migration/output/migration_{timestamp}.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

db_path = '/Users/paulcurtis/Development/cartridge_collection/cartridge_site/collect.sqlite'

legacy_fields = {
    'load_type': LoadType,
    'bullet': BulletType,
    'case_type': CaseType,
    'primer': PrimerType,
    'pa_color': PAColor,
}

migration_summary = defaultdict(lambda: {'created': 0, 'updated': 0, 'skipped': 0})
dry_run_cache = defaultdict(set)  # Cache to avoid redundant logs


def extract_data(limit=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = 'SELECT load_type, bullet, case_type, primer, pa_color FROM Load'
    if limit:
        query += f' LIMIT {limit}'
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows


def phase1_investigate(rows):
    print("Phase 1: Investigation")
    unique_values = defaultdict(set)
    for row in rows:
        for index, field in enumerate(legacy_fields.keys()):
            value = row[index]
            if value:
                unique_values[field].add(value)

    for field, values in unique_values.items():
        print(f"\nUnique values for {field}:")
        for value in sorted(values):
            print(f"  {value}")


def phase2_dry_run(rows):
    print("\nPhase 2: Dry Run")
    for i, row in enumerate(rows):
        logging.info(f"Simulating row {i+1} of {len(rows)}")
        for field, model in legacy_fields.items():
            value = row[list(legacy_fields.keys()).index(field)]
            if value in dry_run_cache[model.__name__]:
                continue  # Skip processing if already cached
            dry_run_cache[model.__name__].add(value)  # Add to cache

            try:
                instance = model.objects.filter(value=value).first()
                if instance:
                    logging.info(f"Found existing {model.__name__}: {value}")
                else:
                    logging.info(f"Would create new {model.__name__}: {value}")
            except Exception as e:
                logging.error(f"Error checking value {value} in model {model.__name__}: {e}")


def phase3_migrate(rows):
    print("\nPhase 3: Actual Migration")
    for i, row in enumerate(rows):
        logging.info(f"Processing row {i+1} of {len(rows)}")
        for field, model in legacy_fields.items():
            value = row[list(legacy_fields.keys()).index(field)]
            if value:
                save_value(model, value)
    generate_report()


def save_value(model, value):
    try:
        with transaction.atomic():
            instance, created = model.objects.get_or_create(value=value)
            if created:
                instance.display_name = value
                instance.legacy_mappings = value
                instance.save()
                logging.info(f"Created new {model.__name__}: {value}")
                migration_summary[model.__name__]['created'] += 1
            else:
                if value not in instance.legacy_mappings.split(','):
                    instance.legacy_mappings += f',{value}'
                    instance.save()
                    logging.info(f"Updated {model.__name__}: Added '{value}' to legacy_mappings")
                    migration_summary[model.__name__]['updated'] += 1
                else:
                    migration_summary[model.__name__]['skipped'] += 1
    except Exception as e:
        logging.error(f"Error saving value {value} in model {model.__name__}: {e}")


def generate_report():
    report = "Migration Summary:\n"
    for model_name, stats in migration_summary.items():
        report += f"\nModel: {model_name}\n"
        report += f"  Created: {stats['created']}\n"
        report += f"  Updated: {stats['updated']}\n"
        report += f"  Skipped: {stats['skipped']}\n"
    report_filename = f'/Users/paulcurtis/Development/cartridge_collection/cartridge_collection/data_migration/output/migration_summary_{timestamp}.txt'
    with open(report_filename, 'w') as report_file:
        report_file.write(report)
    logging.info("Migration summary report generated.")


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else 'investigate'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    rows = extract_data(limit)

    if phase == 'investigate':
        phase1_investigate(rows)
    elif phase == 'dry_run':
        phase2_dry_run(rows)
    elif phase == 'migrate':
        phase3_migrate(rows)


if __name__ == '__main__':
    main()
