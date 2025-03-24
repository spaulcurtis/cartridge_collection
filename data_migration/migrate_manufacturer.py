import os
import sys
import sqlite3
import logging
import django
from datetime import datetime
from django.db import transaction

# Setup Django Environment
sys.path.append('/Users/paulcurtis/Development/cartridge_collection/cartridge_collection')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cartridge_collection.settings')
django.setup()

from collection.models import Manufacturer, Country

# Generate a timestamp for unique filenames
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Configure logging
log_filename = f'/Users/paulcurtis/Development/cartridge_collection/cartridge_collection/data_migration/output/migration_manufacturer_{timestamp}.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

db_path = '/Users/paulcurtis/Development/cartridge_collection/cartridge_site/collect.sqlite'


country_mapping = {70: 74}  # Old country ID -> New country ID mapping

def extract_manufacturers():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT name, code, country_id, note FROM Manuf')
    rows = cursor.fetchall()
    conn.close()
    return rows

def dry_run_manufacturers(rows):
    print("\nDry Run: Showing manufacturers that would be added")
    dry_run_filename = f'/Users/paulcurtis/Development/cartridge_collection/cartridge_collection/data_migration/output/dry_run_manufacturer_{timestamp}.txt'
    with open(dry_run_filename, 'w') as dry_run_file:
        for name, code, country_id, note in rows:
            new_country_id = country_mapping.get(country_id, country_id)
            try:
                country = Country.objects.get(id=new_country_id)
                if Manufacturer.objects.filter(code=code, country=country).exists():
                    log_message = f"CONFLICT: Manufacturer with Code={code} already exists for Country={country.name}."
                    logging.warning(log_message)
                    dry_run_file.write(log_message + '\n')
                else:
                    log_message = f"Would create Manufacturer: Name={name}, Code={code}, Country={country.name}, Note={note.strip() if note else ''}"
                    logging.info(log_message)
                    dry_run_file.write(log_message + '\n')
            except Country.DoesNotExist:
                error_message = f"Country ID {new_country_id} not found for Manufacturer: {name}"
                logging.error(error_message)
                dry_run_file.write(error_message + '\n')
    print(f"Dry run results saved to {dry_run_filename}")


def migrate_manufacturers(rows):
    for name, code, country_id, note in rows:
        new_country_id = country_mapping.get(country_id, country_id)
        try:
            with transaction.atomic():
                country = Country.objects.get(id=new_country_id)
                if Manufacturer.objects.filter(code=code, country=country).exists():
                    logging.warning(f"CONFLICT: Manufacturer with Code={code} already exists for Country={country.name}.")
                    continue
                manufacturer, created = Manufacturer.objects.get_or_create(
                    name=name,
                    defaults={
                        'code': code,
                        'country': country,
                        'note': note.strip() if note else '',
                        'created_at': datetime.now(),
                        'updated_at': datetime.now(),
                    }
                )
                if created:
                    logging.info(f"Created new Manufacturer: Name={name}, Code={code}, Country={country.name}, Note={note}")
                else:
                    logging.info(f"Manufacturer already exists: {name}")

        except Country.DoesNotExist:
            logging.error(f"Country ID {new_country_id} not found for Manufacturer: {name}")


def main():
    rows = extract_manufacturers()
    if len(sys.argv) > 1 and sys.argv[1] == 'dry_run':
        dry_run_manufacturers(rows)
    else:
        migrate_manufacturers(rows)


if __name__ == '__main__':
    main()

