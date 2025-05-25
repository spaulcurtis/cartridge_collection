from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings
import json
import os

class Command(BaseCommand):
    help = 'Generate SQL to fix box content types on Render based on local PostgreSQL data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='fix_boxes.sql',
            help='Output SQL file name'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        
        # Make sure we're on local PostgreSQL database
        if 'postgres' not in settings.DATABASES['default']['ENGINE']:
            self.stdout.write(self.style.ERROR("This command must be run with the local PostgreSQL database"))
            return
        
        # Get all boxes from the database
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT id, bid, content_type_id, object_id FROM collection_box")
            boxes = [
                {
                    'id': row[0],
                    'bid': row[1],
                    'content_type_id': row[2],
                    'object_id': row[3]
                }
                for row in cursor.fetchall()
            ]
        
        self.stdout.write(f"Found {len(boxes)} boxes in local PostgreSQL database")
        
        # Generate SQL update statements
        sql_statements = []
        sql_statements.append("-- SQL to fix box content types on Render\n")
        sql_statements.append("BEGIN;\n")
        
        for box in boxes:
            sql = (
                f"UPDATE collection_box SET content_type_id = {box['content_type_id']} "
                f"WHERE bid = '{box['bid']}';"
            )
            sql_statements.append(sql)
        
        sql_statements.append("\nCOMMIT;")
        
        # Write SQL to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(sql_statements))
        
        self.stdout.write(self.style.SUCCESS(
            f"Generated SQL update script with {len(boxes)} statements in {output_file}"
        ))
        self.stdout.write(
            "You can apply this to your Render database with:"
        )
        self.stdout.write(
            f"psql \"postgresql://cartridge_collection_user:xxx@dpg-cvt9mtre5dus73a55iq0-a.virginia-postgres.render.com/cartridge_collection\" -f {output_file}"
        )
