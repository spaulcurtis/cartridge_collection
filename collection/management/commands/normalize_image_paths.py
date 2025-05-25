from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models
from django.db import connection
import sys
import re

class Command(BaseCommand):
    help = 'Normalize all ImageField paths in the database to use forward slashes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the changes without actually making them',
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Limit to specific Django app (e.g., "collection")',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show more detailed information',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        app_name = options['app']
        verbose = options['verbose']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Check which database we're connected to
        db_vendor = connection.vendor
        self.stdout.write(f"Connected to {db_vendor} database: {connection.settings_dict['NAME']}")
        
        # Get all models from the specified app, or all apps if not specified
        all_models = []
        if app_name:
            try:
                app_config = apps.get_app_config(app_name)
                all_models = app_config.get_models()
            except LookupError:
                self.stdout.write(self.style.ERROR(f"App '{app_name}' not found"))
                sys.exit(1)
        else:
            # Get models from all apps
            for app_config in apps.get_app_configs():
                all_models.extend(app_config.get_models())
        
        total_fields_fixed = 0
        total_records_checked = 0
        
        # Process each model
        for model in all_models:
            # Skip abstract models
            if model._meta.abstract:
                continue
            
            # Find all ImageField fields in this model
            image_fields = []
            for field in model._meta.fields:
                if isinstance(field, models.ImageField):
                    image_fields.append(field.name)
            
            if not image_fields:
                continue
            
            model_name = f"{model._meta.app_label}.{model.__name__}"
            self.stdout.write(f"Processing {model_name} with image fields: {', '.join(image_fields)}")
            
            # Process each ImageField
            for field_name in image_fields:
                # Get the database column name for this field
                field = model._meta.get_field(field_name)
                column_name = field.column
                table_name = model._meta.db_table
                
                # For SQLite, we'll fetch all non-null values and check them in Python
                # For PostgreSQL, we can use the LIKE operator
                with connection.cursor() as cursor:
                    if db_vendor == 'sqlite':
                        # Get all non-null image paths
                        cursor.execute(
                            f"SELECT id, {column_name} FROM {table_name} "
                            f"WHERE {column_name} IS NOT NULL AND {column_name} != ''"
                        )
                        records = cursor.fetchall()
                        
                        # Filter for backslashes in Python
                        needs_fixing = []
                        for record_id, path in records:
                            # Check for Windows-style paths
                            if '\\' in path:
                                needs_fixing.append((record_id, path))
                                
                        if verbose:
                            self.stdout.write(f"  Checked {len(records)} records, found {len(needs_fixing)} with backslashes")
                    else:
                        # PostgreSQL can use LIKE with the proper escape
                        cursor.execute(
                            f"SELECT id, {column_name} FROM {table_name} "
                            f"WHERE {column_name} LIKE '%\\\\%' AND {column_name} IS NOT NULL"
                        )
                        needs_fixing = cursor.fetchall()
                        
                    if not needs_fixing:
                        self.stdout.write(f"  No paths need fixing in {model_name}.{field_name}")
                        continue
                    
                    records_fixed = 0
                    for record_id, path in needs_fixing:
                        # Replace backslashes with forward slashes
                        new_path = path.replace('\\', '/')
                        
                        self.stdout.write(f"  {model_name} #{record_id}: {path} → {new_path}")
                        
                        if not dry_run:
                            # Update the record
                            cursor.execute(
                                f"UPDATE {table_name} SET {column_name} = %s WHERE id = %s",
                                [new_path, record_id]
                            )
                            records_fixed += 1
                    
                    total_fields_fixed += records_fixed
                    total_records_checked += len(needs_fixing)
                    
                    self.stdout.write(f"  Fixed {records_fixed} paths in {model_name}.{field_name}")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"DRY RUN COMPLETE: {total_fields_fixed} paths would be fixed in {total_records_checked} records"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully normalized {total_fields_fixed} paths in {total_records_checked} records"
            ))
