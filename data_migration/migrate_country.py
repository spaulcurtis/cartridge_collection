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

from collection.models import Country, Caliber

# Generate a timestamp for unique filenames
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Configure logging
log_filename = f'/Users/paulcurtis/Development/cartridge_collection/cartridge_collection/data_migration/output/migration_country_{timestamp}.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

db_path = '/Users/paulcurtis/Development/cartridge_collection/cartridge_site/collect.sqlite'


def extract_countries():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT name, full_name, note FROM Country')
    rows = cursor.fetchall()
    conn.close()
    return rows

def migrate_countries():
    rows = extract_countries()
    caliber = Caliber.objects.get(id=1)  # Assuming the only Caliber entry

    for name, full_name, note in rows:
        try:
            with transaction.atomic():
                country, created = Country.objects.get_or_create(
                    name=name,
                    defaults={
                        'full_name': full_name,
                        'note': note,
                        'caliber': caliber,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now(),
                    }
                )

                if created:
                    logging.info(f"Created new Country: {name}")
                else:
                    logging.info(f"Country already exists: {name}")

        except Exception as e:
            logging.error(f"Error migrating country {name}: {e}")


if __name__ == '__main__':
    migrate_countries()
