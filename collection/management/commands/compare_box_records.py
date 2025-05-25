from django.core.management.base import BaseCommand
from django.db import connections
import sqlite3
import os
import json
from collections import defaultdict

class Command(BaseCommand):
    help = 'Compare Box records between PostgreSQL and SQLite databases'

    def add_arguments(self, parser):
        parser.add_argument(
            'sqlite_path',
            type=str,
            help='Path to the SQLite database file'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix mismatched content_type_ids in PostgreSQL based on SQLite data'
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export mismatches to a JSON file'
        )

    def handle(self, *args, **options):
        sqlite_path = options['sqlite_path']
        fix_mode = options['fix']
        export_mode = options['export']
        
        # Validate that SQLite file exists
        if not os.path.exists(sqlite_path):
            self.stdout.write(self.style.ERROR(f"SQLite database file not found: {sqlite_path}"))
            return
        
        self.stdout.write(f"Comparing Box records between PostgreSQL and SQLite: {sqlite_path}")
        
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        
        # Get contenttype mappings from both databases
        pg_contenttypes = self.get_postgres_contenttypes()
        sqlite_contenttypes = self.get_sqlite_contenttypes(sqlite_conn)
        
        # Display contenttype mappings
        self.stdout.write("Content Type Mappings:")
        self.stdout.write("PostgreSQL ContentTypes:")
        for ct_id, (app_label, model) in sorted(pg_contenttypes.items()):
            self.stdout.write(f"  ID: {ct_id}, App: {app_label}, Model: {model}")
        
        self.stdout.write("\nSQLite ContentTypes:")
        for ct_id, (app_label, model) in sorted(sqlite_contenttypes.items()):
            self.stdout.write(f"  ID: {ct_id}, App: {app_label}, Model: {model}")
        
        # Create mapping from (app_label, model) to ID for both databases
        sqlite_model_to_id = {(app_label, model): ct_id for ct_id, (app_label, model) in sqlite_contenttypes.items()}
        pg_model_to_id = {(app_label, model): ct_id for ct_id, (app_label, model) in pg_contenttypes.items()}
        
        # Get box records from both databases
        pg_boxes = self.get_postgres_boxes()
        sqlite_boxes = self.get_sqlite_boxes(sqlite_conn)
        
        self.stdout.write(f"\nFound {len(pg_boxes)} boxes in PostgreSQL and {len(sqlite_boxes)} boxes in SQLite")
        
        # Compare boxes based on bid (box ID)
        mismatches = []
        for box_bid, pg_box in pg_boxes.items():
            if box_bid in sqlite_boxes:
                sqlite_box = sqlite_boxes[box_bid]
                
                # Get the model names for the content types
                pg_content_type = pg_contenttypes.get(pg_box['content_type_id'], ("unknown", "unknown"))
                sqlite_content_type = sqlite_contenttypes.get(sqlite_box['content_type_id'], ("unknown", "unknown"))
                
                # Check if they refer to the same model
                if pg_content_type != sqlite_content_type:
                    mismatch = {
                        'bid': box_bid,
                        'pg_id': pg_box['id'],
                        'sqlite_id': sqlite_box['id'],
                        'pg_content_type_id': pg_box['content_type_id'],
                        'sqlite_content_type_id': sqlite_box['content_type_id'],
                        'pg_model': f"{pg_content_type[0]}.{pg_content_type[1]}",
                        'sqlite_model': f"{sqlite_content_type[0]}.{sqlite_content_type[1]}",
                        'pg_object_id': pg_box['object_id'],
                        'sqlite_object_id': sqlite_box['object_id']
                    }
                    
                    # Determine the correct content_type_id in PostgreSQL
                    if sqlite_content_type != ("unknown", "unknown"):
                        correct_pg_content_type_id = pg_model_to_id.get(sqlite_content_type)
                        mismatch['correct_pg_content_type_id'] = correct_pg_content_type_id
                    else:
                        mismatch['correct_pg_content_type_id'] = None
                    
                    mismatches.append(mismatch)
        
        # Report and optionally fix mismatches
        if mismatches:
            self.stdout.write(f"\nFound {len(mismatches)} mismatched Box records:")
            
            for mismatch in mismatches:
                self.stdout.write(
                    f"Box {mismatch['bid']}: PostgreSQL content_type={mismatch['pg_content_type_id']} "
                    f"({mismatch['pg_model']}), SQLite content_type={mismatch['sqlite_content_type_id']} "
                    f"({mismatch['sqlite_model']})"
                )
            
            # Fix mismatches if requested
            if fix_mode:
                self.fix_mismatches(mismatches)
            
            # Export mismatches if requested
            if export_mode:
                self.export_mismatches(mismatches)
        else:
            self.stdout.write(self.style.SUCCESS("\nNo mismatches found! All Box records match between databases."))
        
        # Close SQLite connection
        sqlite_conn.close()

    def get_postgres_contenttypes(self):
        """Get content types from PostgreSQL database"""
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT id, app_label, model FROM django_content_type")
            return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    
    def get_sqlite_contenttypes(self, sqlite_conn):
        """Get content types from SQLite database"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, app_label, model FROM django_content_type")
        return {row['id']: (row['app_label'], row['model']) for row in cursor.fetchall()}
    
    def get_postgres_boxes(self):
        """Get box records from PostgreSQL database"""
        boxes = {}
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT id, bid, content_type_id, object_id FROM collection_box")
            for row in cursor.fetchall():
                boxes[row[1]] = {
                    'id': row[0],
                    'bid': row[1],
                    'content_type_id': row[2],
                    'object_id': row[3]
                }
        return boxes
    
    def get_sqlite_boxes(self, sqlite_conn):
        """Get box records from SQLite database"""
        boxes = {}
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, bid, content_type_id, object_id FROM collection_box")
        for row in cursor.fetchall():
            boxes[row['bid']] = {
                'id': row['id'],
                'bid': row['bid'],
                'content_type_id': row['content_type_id'],
                'object_id': row['object_id']
            }
        return boxes
    
    def fix_mismatches(self, mismatches):
        """Fix mismatched content_type_ids in PostgreSQL based on SQLite data"""
        self.stdout.write("\nFixing mismatches...")
        
        fixed_count = 0
        with connections['default'].cursor() as cursor:
            for mismatch in mismatches:
                if mismatch['correct_pg_content_type_id'] is not None:
                    cursor.execute(
                        "UPDATE collection_box SET content_type_id = %s WHERE id = %s",
                        [mismatch['correct_pg_content_type_id'], mismatch['pg_id']]
                    )
                    fixed_count += 1
                    self.stdout.write(f"  Fixed Box {mismatch['bid']}: content_type_id {mismatch['pg_content_type_id']} → {mismatch['correct_pg_content_type_id']}")
                else:
                    self.stdout.write(self.style.WARNING(f"  Could not determine correct content_type_id for Box {mismatch['bid']}"))
        
        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} out of {len(mismatches)} mismatches"))
    
    def export_mismatches(self, mismatches):
        """Export mismatches to a JSON file"""
        filename = "box_mismatches.json"
        with open(filename, 'w') as f:
            json.dump(mismatches, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f"Exported {len(mismatches)} mismatches to {filename}"))
