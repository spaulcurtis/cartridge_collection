from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from collection.models import Box

class Command(BaseCommand):
    help = 'Fix content type IDs in Box objects after SQLite to PostgreSQL migration'

    def handle(self, *args, **options):
        # Mapping from SQLite content_type_id to model name
        sqlite_mapping = {
            15: 'box',
            16: 'country',
            17: 'load',
            18: 'date',
            19: 'manufacturer',
            20: 'variation',
            10: 'headstamp'
            # Add other models as needed
        }

        # Get the correct PostgreSQL content_type_ids
        pg_mapping = {}
        for old_id, model_name in sqlite_mapping.items():
            try:
                ct = ContentType.objects.get(app_label='collection', model=model_name)
                pg_mapping[old_id] = ct.id
                self.stdout.write(f"Mapping {model_name}: SQLite ID {old_id} → PostgreSQL ID {ct.id}")
            except ContentType.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"ContentType for model {model_name} not found!"))

        # Get all boxes
        boxes = Box.objects.all()
        self.stdout.write(f"Found {boxes.count()} Box objects to check")
        
        updated_count = 0
        for box in boxes:
            old_content_type_id = box.content_type_id
            
            # Skip if the content_type_id is already correct 
            # (i.e., it's a value in the pg_mapping values)
            if old_content_type_id in pg_mapping.values():
                continue
                
            # Find the corresponding new content_type_id
            if old_content_type_id in pg_mapping:
                new_content_type_id = pg_mapping[old_content_type_id]
                
                # Update the content_type_id
                box.content_type_id = new_content_type_id
                box.save(update_fields=['content_type_id'])
                
                updated_count += 1
                self.stdout.write(f"Updated Box {box.bid}: content_type_id {old_content_type_id} → {new_content_type_id}")
            else:
                self.stdout.write(
                    self.style.WARNING(f"Box {box.bid} has content_type_id {old_content_type_id} which is not in the mapping")
                )
        
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} Box objects"))
