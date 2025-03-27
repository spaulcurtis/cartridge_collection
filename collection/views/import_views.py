import os
import tempfile
import sqlite3
import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ..models import Caliber



# ===============================
# Shared Import Utility Functions
# ===============================

def _get_table_count(cursor, table_name):
    """Helper function to get the count of rows in a table"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        return cursor.fetchone()[0]
    except:
        return 0

def extract_sources_from_note(note):
    """
    Extract source information from a note field.
    
    Args:
        note (str): The note text containing source information
        
    Returns:
        tuple: (cleaned_note, sources_info, warnings)
            - cleaned_note: Note with source info removed
            - sources_info: List of dicts with source details
            - warnings: List of warning messages
    """
    from datetime import date
    import re
    
    if not note:
        return "", [], []
    
    sources_info = []
    warnings = []
    
    # Extract sources using regex
    source_pattern = r'\[Source:\s*(.*?)\]'
    source_matches = re.findall(source_pattern, note, re.DOTALL)
    
    for source_match in source_matches:
        source_entries = source_match.split(';')
        for entry in source_entries:
            entry = entry.strip()
            if not entry:
                continue
                
            # Parse source entry (name, cc, year)
            parts = entry.split(',')
            if len(parts) >= 3:
                source_name = parts[0].strip()
                try:
                    source_cc = int(parts[1].strip())
                except ValueError:
                    source_cc = 3  # Default if not valid
                    warnings.append(f"Invalid credibility code in source '{source_name}', using default (3)")
                
                try:
                    year_str = parts[2].strip()
                    year_int = int(year_str)
                    if year_int < 60:
                        year = 2000 + year_int
                    else:
                        year = 1900 + year_int
                    source_date = date(year, 1, 1)
                except ValueError:
                    source_date = None
                    warnings.append(f"Invalid year in source '{source_name}', date will be empty")
                
                sources_info.append({
                    'name': source_name,
                    'cc': source_cc,
                    'date': source_date
                })
            else:
                warnings.append(f"Malformed source entry: '{entry}', skipping")
    
    # Clean the note by removing source information
    clean_note = re.sub(source_pattern, '', note).strip()
    
    return clean_note, sources_info, warnings


def extract_sources_from_note(note):
    """
    Extract source information from a note field.

    Args:
        note (str): The note text containing source information

    Returns:
        tuple: (cleaned_note, sources_info, warnings)
            - cleaned_note: Note with source info removed
            - sources_info: List of dicts with source details
            - warnings: List of warning messages
    """
    from datetime import date
    import re

    if not note:
        return "", [], []

    sources_info = []
    warnings = []

    # Extract sources using regex
    source_pattern = r'\[Source:\s*(.*?)\]'
    source_matches = re.findall(source_pattern, note, re.DOTALL)

    for source_match in source_matches:
        source_entries = source_match.split(';')
        for entry in source_entries:
            entry = entry.strip()
            if not entry:
                continue

            # Parse source entry (name, cc, year, optional note)
            parts = re.split(r',\s*(?=\d+)', entry, maxsplit=2)
            if len(parts) >= 3:
                source_name = parts[0].strip()
                try:
                    source_cc = int(parts[1].strip())
                except ValueError:
                    source_cc = 3  # Default if not valid
                    warnings.append(f"Invalid credibility code in source '{source_name}', using default (3)")

                try:
                    year_part = parts[2].strip()
                    year_match = re.match(r'(\d{2,4})(.*)', year_part)

                    if year_match:
                        year_str, note_part = year_match.groups()
                        year_int = int(year_str)
                        if year_int < 60:  # Assuming year is in 2000s if < 60
                            year = 2000 + year_int
                        elif year_int < 100:  # Assuming year is in 1900s if between 60 and 99
                            year = 1900 + year_int
                        else:  # For four-digit years
                            year = year_int

                        source_date = date(year, 1, 1)
                        source_note = note_part.strip().lstrip('(').rstrip(')') if note_part else None
                    else:
                        source_date = None
                        source_note = None
                        warnings.append(f"Invalid year format in source '{source_name}', date will be empty")

                    sources_info.append({
                        'name': source_name,
                        'cc': source_cc,
                        'date': source_date,
                        'note': source_note
                    })
                except ValueError:
                    warnings.append(f"Invalid year in source '{source_name}', date will be empty")
            else:
                warnings.append(f"Malformed source entry: '{entry}', skipping")

    # Clean the note by removing source information
    clean_note = re.sub(source_pattern, '', note).strip()

    return clean_note, sources_info, warnings


def process_sources(record_obj, sources_info, dry_run=True):
    """
    Process source information and link sources to a record object.

    Args:
        record_obj: The Django model instance to link sources to
        sources_info (list): List of dictionaries with source data
        dry_run (bool): If True, no database changes are made

    Returns:
        tuple: (sources_created, source_links_created, source_messages)
            - sources_created (int): Number of new sources created
            - source_links_created (int): Number of sources linked
            - source_messages (list): Messages about created/linked sources
    """
    from django.utils import timezone
    from ..models import Source

    sources_created = 0
    source_links_created = 0
    source_messages = []

    if dry_run:
        for source_info in sources_info:
            existing_source = Source.objects.filter(name=source_info['name']).exists()
            if not existing_source:
                sources_created += 1
                source_messages.append(f"Would create new source: {source_info['name']}")

            source_links_created += 1
            source_messages.append(f"Would link source: {source_info['name']} ({source_info['date']})")

    else:
        for source_info in sources_info:
            source, source_created = Source.objects.get_or_create(
                name=source_info['name'],
                defaults={'description': '', 'created_at': timezone.now()}
            )

            if source_created:
                sources_created += 1
                source_messages.append(f"Created new source: {source_info['name']}")

            if hasattr(record_obj, 'add_source'):
                record_obj.add_source(
                    source=source,
                    date=source_info['date'],
                    note=f"credibility is {source_info['cc']}; note: {source_info['note']}"
                )
                source_links_created += 1
                source_messages.append(f"Linked source: {source_info['name']} ({source_info['date']})")

    return sources_created, source_links_created, source_messages


def parse_date(date_str):
    """
    Parse a date string in various formats.
    
    Args:
        date_str (str): The date string to parse
        
    Returns:
        tuple: (date_obj, warning)
            - date_obj: Python date object or None if parsing failed
            - warning: Warning message if parsing failed, empty string otherwise
    """
    from datetime import datetime
    
    if not date_str:
        return None, ""
    
    # Try various date formats
    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt).date()
            return date_obj, ""
        except ValueError:
            continue
    
    return None, f"Invalid date format '{date_str}', leaving blank"

def parse_price(price_str):
    """
    Parse a price string into a Decimal.
    
    Args:
        price_str (str): The price string to parse
        
    Returns:
        tuple: (price, warning)
            - price: Decimal value or None if parsing failed
            - warning: Warning message if parsing failed, empty string otherwise
    """
    import re
    from decimal import Decimal, InvalidOperation
    
    if not price_str:
        return None, ""
    
    try:
        # Remove currency symbols and whitespace
        price_str = re.sub(r'[^\d.]', '', price_str)
        price = Decimal(price_str)
        return price, ""
    except (InvalidOperation, ValueError):
        return None, f"Invalid price format '{price_str}', leaving blank"

def find_manufacturer_by_code_and_country(manuf_code, country_name):
    """
    Find a manufacturer by code and country name.
    
    Args:
        manuf_code (str): The manufacturer code
        country_name (str): The country name
        
    Returns:
        tuple: (manufacturer, error_message)
            - manufacturer: Manufacturer object or None if not found
            - error_message: Error message if not found, empty string otherwise
    """
    from ..models import Manufacturer, Country
    
    if not manuf_code or not country_name:
        return None, "Missing manufacturer code or country name"
    
    try:
        # First find the country
        country = Country.objects.filter(name=country_name).first()
        if not country:
            return None, f"Country '{country_name}' not found in the new database"
        
        # Then find the manufacturer by both code and country
        manufacturer = Manufacturer.objects.get(code=manuf_code, country=country)
        return manufacturer, ""
    except Manufacturer.DoesNotExist:
        return None, f"Manufacturer with code '{manuf_code}' for country '{country_name}' not found"
    except Manufacturer.MultipleObjectsReturned:
        return None, f"Multiple manufacturers found with code '{manuf_code}' for country '{country_name}'"
    except Exception as e:
        return None, f"Error finding manufacturer: {str(e)}"

def generate_import_report(table_name, total_records, processed, success, failed, warnings, 
                           sources_created, source_links_created, record_results, 
                           field_mapping_items, first_failures, first_warnings, dry_run=True):
    """
    Generate import report with summary and details.
    
    Args:
        table_name (str): The name of the table being imported
        total_records (int): Total number of records in the table
        processed (int): Number of records processed
        success (int): Number of records successfully imported
        failed (int): Number of records that failed to import
        warnings (int): Number of warnings generated
        sources_created (int): Number of new sources created
        source_links_created (int): Number of source links created
        record_results (list): Detailed results for each record
        field_mapping_items (list): List of tuples with field mappings (old_field, new_field)
        first_failures (list): List of first few failures for web display
        first_warnings (list): List of first few warnings for web display
        dry_run (bool): Whether this was a dry run
        
    Returns:
        dict: Report components including summary, details, and web summary
    """
    # Generate summary
    summary = f"{table_name} Import Summary\n"
    summary += "-" * 40 + "\n"
    summary += f"Source records: {total_records}\n"
    summary += f"Records processed: {processed}\n"
    summary += f"{'Would be ' if dry_run else ''}Successfully imported: {success}\n"
    summary += f"{'Would be ' if dry_run else ''}Failed: {failed}\n"
    summary += f"{'Would be ' if dry_run else ''}Warnings: {warnings}\n"
    summary += f"{'Would be ' if dry_run else ''}Sources created: {sources_created}\n"
    summary += f"{'Would be ' if dry_run else ''}Source links created: {source_links_created}\n"
    
    # Field mapping info
    field_mapping = "\nField mapping used:\n"
    field_mapping += "-" * 30 + "\n"
    field_mapping += "Old DB             →  Django Model\n"
    field_mapping += "----------------      ----------------\n"
    
    for old_field, new_field in field_mapping_items:
        field_mapping += f"{old_field.ljust(20)} →  {new_field}\n"
    
    # Create web-friendly version with summary and first few failures/warnings
    web_summary = summary
    
    if first_failures:
        web_summary += "\nSample Failures:\n"
        web_summary += "-" * 30 + "\n"
        for i, failure in enumerate(first_failures):
            identifier = failure.get('code', failure.get('cart_id', failure.get('id', 'Unknown')))
            web_summary += f"{i+1}. {table_name} {identifier} (ID: {failure['id']}): {failure['error']}\n"
    
    if first_warnings:
        web_summary += "\nSample Warnings:\n"
        web_summary += "-" * 30 + "\n"
        for i, warning in enumerate(first_warnings):
            identifier = warning.get('code', warning.get('cart_id', warning.get('id', 'Unknown')))
            web_summary += f"{i+1}. {table_name} {identifier} (ID: {warning['id']}): {warning['warning']}\n"
    
    # Create detailed report depending on record type
    details = f"\nDETAILED RECORD PROCESSING - {table_name.upper()}\n"
    details += "-" * 40 + "\n"
    
    for i, record in enumerate(record_results):
        # Get a primary identifier (code for headstamps, cart_id for others)
        identifier = record.get('code', record.get('cart_id', record.get('id', 'Unknown')))
        details += f"Record {i+1}: {identifier} ({table_name} ID: {record['id']}) - {record['status'].upper()}\n"
        
        # Include record-specific details if successful
        if record['status'] == 'success':
            for key, value in record.items():
                if key not in ['id', 'code', 'cart_id', 'status', 'warnings', 'errors', 'sources', 'details', 'note_before', 'note_after', 'sources_count']:
                    details += f"  {key.replace('_', ' ').title()}: {value}\n"
            
            # Add source information
            if record.get('sources_count', 0) > 0:
                details += f"  Sources found: {record.get('sources_count', 0)}\n"
                
                if record.get('note_before') != record.get('note_after'):
                    details += f"  Note cleaned: '{record.get('note_before', '')}' -> '{record.get('note_after', '')}'\n"
                
                for source in record.get('sources', []):
                    details += f"  {source}\n"
            
            # Add record-specific details if available
            if 'details' in record and isinstance(record['details'], dict):
                for key, value in record['details'].items():
                    if key not in ['note_before', 'note_after', 'sources_count']:
                        details += f"  {key.replace('_', ' ').title()}: {value}\n"
        
        # Add warnings
        if record.get('warnings'):
            details += "  Warnings:\n"
            for warning in record['warnings']:
                details += f"    - {warning}\n"
        
        # Add errors
        if record.get('errors'):
            details += "  Errors:\n"
            for error in record['errors']:
                details += f"    - {error}\n"
        
        details += "\n"
    
    # Return all components
    return {
        'summary': summary + field_mapping,  # For downloadable report
        'web_summary': web_summary,          # For web display
        'details': details,                  # Detailed results for downloadable report
        'complete_report': summary + field_mapping + details,  # Full report
        'stats': {
            'processed': processed,
            'success': success,
            'failed': failed,
            'warnings': warnings,
            'sources_created': sources_created,
            'source_links_created': source_links_created
        },
        'first_failures': first_failures,
        'first_warnings': first_warnings
    }

def import_countries(cursor, dry_run):
    """
    Import country records from SQLite database
    Returns a dictionary with summary, stats, and detailed results
    """
    from django.utils import timezone
    from django.db import transaction, IntegrityError
    from ..models import Country, Caliber
    
    # Get the caliber - we'll use the same caliber for all countries
    try:
        caliber = Caliber.objects.get(pk=1)  # Default to first caliber
    except Caliber.DoesNotExist:
        caliber = Caliber.objects.first()
        if not caliber:
            raise ValueError("No Caliber found. Please create at least one Caliber before importing countries.")
    
    # Get record count
    total_records = _get_table_count(cursor, "Country")
    
    # Get all countries
    cursor.execute("SELECT * FROM Country")
    countries = cursor.fetchall()
    
    # Initialize counters
    processed = 0
    success = 0
    failed = 0
    warnings = 0
    sources_created = 0
    source_links_created = 0
    
    # Track the first two failures and warnings for the web display
    first_failures = []
    first_warnings = []
    
    # Results for detailed record processing
    record_results = []
    
    # Process each country
    for country in countries:
        processed += 1
        record_result = {
            'id': country['country_id'],
            'name': country['name'],
            'status': 'pending',
            'warnings': [],
            'errors': [],
            'sources': [],
            'details': {}
        }
        
        try:
            # Process note and extract sources if needed
            note = country['note'] or ''
            clean_note, sources_info, source_warnings = extract_sources_from_note(note)
            
            # Add any source warnings to the record
            for warning in source_warnings:
                record_result['warnings'].append(warning)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': country['country_id'],
                        'name': country['name'],
                        'warning': warning
                    })
            
            # Store details in record result
            record_result['details'] = {
                'name': country['name'],
                'full_name': country['full_name'],
                'caliber': caliber.name,
                'note_before': note,
                'note_after': clean_note,
                'sources_count': len(sources_info)
            }
            
            # Check if country already exists
            if Country.objects.filter(name=country['name']).exists() and not dry_run:
                warning_msg = f"Country with name '{country['name']}' already exists, will update"
                record_result['warnings'].append(warning_msg)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': country['country_id'],
                        'name': country['name'],
                        'warning': warning_msg
                    })
            
            # Process the country record
            if not dry_run:
                with transaction.atomic():
                    # Create or update the country
                    country_obj, created = Country.objects.update_or_create(
                        name=country['name'],
                        defaults={
                            'full_name': country['full_name'],
                            'caliber': caliber,
                            'note': clean_note,
                            'updated_at': timezone.now()
                        }
                    )
                    
                    # Process source links if supported
                    if hasattr(country_obj, 'add_source'):
                        new_sources, new_links, source_msgs = process_sources(
                            country_obj, 
                            sources_info, 
                            dry_run=False
                        )
                        
                        sources_created += new_sources
                        source_links_created += new_links
                        record_result['sources'].extend(source_msgs)
            else:
                # Simulate source processing in dry run mode
                if sources_info:
                    new_sources, new_links, source_msgs = process_sources(
                        None,  # No actual object in dry run
                        sources_info, 
                        dry_run=True
                    )
                    
                    sources_created += new_sources
                    source_links_created += new_links
                    record_result['sources'].extend(source_msgs)
            
            # Mark record as successful
            record_result['status'] = 'success'
            record_result['note_before'] = note
            record_result['note_after'] = clean_note
            success += 1
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            record_result['status'] = 'error'
            record_result['errors'].append(error_msg)
            failed += 1
            
            # Track for web display
            if len(first_failures) < 2:
                first_failures.append({
                    'id': country['country_id'],
                    'name': country['name'],
                    'error': error_msg
                })
        
        record_results.append(record_result)
    
    # Generate the import report using the utility function
    field_mapping_items = [
        ('country_id', 'id'),
        ('name', 'name'),
        ('full_name', 'full_name'),
        ('note', 'note (with source info extracted)'),
        ('N/A', 'caliber (assigned during import)')
    ]
    
    return generate_import_report(
        table_name="Country",
        total_records=total_records,
        processed=processed,
        success=success,
        failed=failed,
        warnings=warnings,
        sources_created=sources_created,
        source_links_created=source_links_created,
        record_results=record_results,
        field_mapping_items=field_mapping_items,
        first_failures=first_failures,
        first_warnings=first_warnings,
        dry_run=dry_run
    )


def import_manufacturers(cursor, dry_run):
    """
    Import manufacturer records from SQLite database
    Returns a dictionary with summary, stats, and detailed results
    """
    from django.utils import timezone
    from django.db import transaction, IntegrityError
    from ..models import Manufacturer, Country
    
    # Get record count
    total_records = _get_table_count(cursor, "Manuf")
    
    # Get all manufacturers with country info
    cursor.execute("""
        SELECT 
            m.*,
            c.name as country_name
        FROM Manuf m
        LEFT JOIN Country c ON m.country_id = c.country_id
    """)
    manufacturers = cursor.fetchall()
    
    # Initialize counters
    processed = 0
    success = 0
    failed = 0
    warnings = 0
    sources_created = 0
    source_links_created = 0
    
    # Track the first two failures and warnings for the web display
    first_failures = []
    first_warnings = []
    
    # Results for detailed record processing
    record_results = []
    
    # Process each manufacturer
    for manuf in manufacturers:
        processed += 1
        record_result = {
            'id': manuf['manuf_id'],
            'code': manuf['code'],
            'status': 'pending',
            'warnings': [],
            'errors': [],
            'sources': [],
            'details': {}
        }
        
        try:
            # Find country by name
            try:
                country = Country.objects.get(name=manuf['country_name'])
            except Country.DoesNotExist:
                error_msg = f"Country '{manuf['country_name']}' not found"
                record_result['status'] = 'error'
                record_result['errors'].append(error_msg)
                failed += 1
                
                # Track for web display
                if len(first_failures) < 2:
                    first_failures.append({
                        'id': manuf['manuf_id'],
                        'code': manuf['code'],
                        'error': error_msg
                    })
                
                record_results.append(record_result)
                continue
            
            # Process note and extract sources
            note = manuf['note'] or ''
            clean_note, sources_info, source_warnings = extract_sources_from_note(note)
            
            # Add any source warnings to the record
            for warning in source_warnings:
                record_result['warnings'].append(warning)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': manuf['manuf_id'],
                        'code': manuf['code'],
                        'warning': warning
                    })
            
            # Check if manufacturer already exists for this country
            if Manufacturer.objects.filter(code=manuf['code'], country=country).exists() and not dry_run:
                warning_msg = f"Manufacturer with code '{manuf['code']}' already exists for country '{manuf['country_name']}', will update"
                record_result['warnings'].append(warning_msg)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': manuf['manuf_id'],
                        'code': manuf['code'],
                        'warning': warning_msg
                    })
            
            # Store details in record result
            record_result['details'] = {
                'code': manuf['code'],
                'name': manuf['name'],
                'country': manuf['country_name'],
                'note_before': note,
                'note_after': clean_note,
                'sources_count': len(sources_info)
            }
            
            # Process the manufacturer record
            if not dry_run:
                with transaction.atomic():
                    # Create or update the manufacturer
                    manufacturer, created = Manufacturer.objects.update_or_create(
                        code=manuf['code'],
                        country=country,
                        defaults={
                            'name': manuf['name'],
                            'note': clean_note,
                            'updated_at': timezone.now()
                        }
                    )
                    
                    # Process source links if supported
                    if hasattr(manufacturer, 'add_source'):
                        new_sources, new_links, source_msgs = process_sources(
                            manufacturer, 
                            sources_info, 
                            dry_run=False
                        )
                        
                        sources_created += new_sources
                        source_links_created += new_links
                        record_result['sources'].extend(source_msgs)
            else:
                # Simulate source processing in dry run mode
                if sources_info:
                    new_sources, new_links, source_msgs = process_sources(
                        None,  # No actual object in dry run
                        sources_info, 
                        dry_run=True
                    )
                    
                    sources_created += new_sources
                    source_links_created += new_links
                    record_result['sources'].extend(source_msgs)
            
            # Mark record as successful
            record_result['status'] = 'success'
            record_result['note_before'] = note
            record_result['note_after'] = clean_note
            success += 1
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            record_result['status'] = 'error'
            record_result['errors'].append(error_msg)
            failed += 1
            
            # Track for web display
            if len(first_failures) < 2:
                first_failures.append({
                    'id': manuf['manuf_id'],
                    'code': manuf['code'],
                    'error': error_msg
                })
        
        record_results.append(record_result)
    
    # Generate the import report using the utility function
    field_mapping_items = [
        ('manuf_id', 'id'),
        ('code', 'code'),
        ('name', 'name'),
        ('country_id', 'country (mapped by name)'),
        ('note', 'note (with source info extracted)')
    ]
    
    return generate_import_report(
        table_name="Manufacturer",
        total_records=total_records,
        processed=processed,
        success=success,
        failed=failed,
        warnings=warnings,
        sources_created=sources_created,
        source_links_created=source_links_created,
        record_results=record_results,
        field_mapping_items=field_mapping_items,
        first_failures=first_failures,
        first_warnings=first_warnings,
        dry_run=dry_run
    )


def import_headstamps(cursor, dry_run):
    """
    Import headstamp records from SQLite database
    Returns a dictionary with summary, stats, and detailed results
    """
    from datetime import datetime, date
    from django.utils import timezone
    from ..models import Headstamp, Manufacturer, Source, HeadstampSource, Country
    import re
    from django.db import transaction, IntegrityError
    
    # Get record count
    total_records = _get_table_count(cursor, "Headstamp")
    
    # Get all headstamps with manufacturer and country info
    cursor.execute("""
        SELECT 
            h.*, 
            m1.code as manuf_code,
            m1.country_id as manuf_country_id,
            c1.name as country_name,
            m2.code as prim_man_code,
            m2.country_id as prim_man_country_id,
            c2.name as prim_country_name
        FROM Headstamp h
        LEFT JOIN Manuf m1 ON h.manuf_id = m1.manuf_id
        LEFT JOIN Country c1 ON m1.country_id = c1.country_id
        LEFT JOIN Manuf m2 ON h.prim_man_id = m2.manuf_id
        LEFT JOIN Country c2 ON m2.country_id = c2.country_id
    """)
    headstamps = cursor.fetchall()
    
    # Initialize counters
    processed = 0
    success = 0
    failed = 0
    warnings = 0
    sources_created = 0
    source_links_created = 0
    
    # Track the first two failures and warnings for the web display
    first_failures = []
    first_warnings = []
    
    # Results for detailed record processing
    record_results = []
    
    # Process each headstamp
    for hs in headstamps:
        processed += 1
        record_result = {
            'id': hs['headstamp_id'],
            'code': hs['code'],
            'status': 'pending',
            'warnings': [],
            'errors': [],
            'sources': []
        }
        
        try:
            # Find manufacturer by code and country
            manufacturer, error_msg = find_manufacturer_by_code_and_country(
                hs['manuf_code'], 
                hs['country_name']
            )
            
            if not manufacturer:
                record_result['status'] = 'error'
                record_result['errors'].append(error_msg)
                failed += 1
                
                # Track for web display
                if len(first_failures) < 2:
                    first_failures.append({
                        'id': hs['headstamp_id'],
                        'code': hs['code'],
                        'error': error_msg
                    })
                
                record_results.append(record_result)
                continue
            
            # Find primary manufacturer
            primary_manufacturer = None
            if hs['prim_man_id']:
                # Try to find primary manufacturer by code and country
                primary_manufacturer, error_msg = find_manufacturer_by_code_and_country(
                    hs['prim_man_code'], 
                    hs['prim_country_name']
                )
                
                if not primary_manufacturer:
                    warning_msg = f"Primary manufacturer issue: {error_msg}, using main manufacturer"
                    record_result['warnings'].append(warning_msg)
                    warnings += 1
                    
                    # Track for web display
                    if len(first_warnings) < 2:
                        first_warnings.append({
                            'id': hs['headstamp_id'],
                            'code': hs['code'],
                            'warning': warning_msg
                        })
                    
                    primary_manufacturer = manufacturer
            else:
                primary_manufacturer = manufacturer
            
            # Process note and extract sources
            note = hs['note'] or ''
            clean_note, sources_info, source_warnings = extract_sources_from_note(note)
            
            # Add any source warnings to the record
            for warning in source_warnings:
                record_result['warnings'].append(warning)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': hs['headstamp_id'],
                        'code': hs['code'],
                        'warning': warning
                    })
            
            # Process the headstamp record
            if not dry_run:
                with transaction.atomic():
                    # Create or update the headstamp
                    headstamp, created = Headstamp.objects.update_or_create(
                        code=hs['code'],
                        manufacturer=manufacturer,
                        defaults={
                            'name': hs['name'],
                            'primary_manufacturer': primary_manufacturer,
                            'cc': hs['cc'],
                            'note': clean_note,
                            'updated_at': timezone.now()
                        }
                    )
                    
                    # Process source links
                    new_sources, new_links, source_msgs = process_sources(
                        headstamp, 
                        sources_info, 
                        dry_run=False
                    )
                    
                    sources_created += new_sources
                    source_links_created += new_links
                    record_result['sources'].extend(source_msgs)
            else:
                # Simulate source processing in dry run mode
                new_sources, new_links, source_msgs = process_sources(
                    None,  # No actual object in dry run
                    sources_info, 
                    dry_run=True
                )
                
                sources_created += new_sources
                source_links_created += new_links
                record_result['sources'].extend(source_msgs)
            
            record_result['status'] = 'success'
            record_result['note_before'] = note
            record_result['note_after'] = clean_note
            record_result['manufacturer'] = f"{hs['manuf_code']} ({hs['country_name']})"
            record_result['primary_manufacturer'] = f"{hs['prim_man_code']} ({hs['prim_country_name']})" if hs['prim_man_code'] else 'Same as manufacturer'
            record_result['sources_count'] = len(sources_info)
            success += 1
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            record_result['status'] = 'error'
            record_result['errors'].append(error_msg)
            failed += 1
            
            # Track for web display
            if len(first_failures) < 2:
                first_failures.append({
                    'id': hs['headstamp_id'],
                    'code': hs['code'],
                    'error': error_msg
                })
        
        record_results.append(record_result)
    
    # Generate the import report using the utility function
    field_mapping_items = [
        ('headstamp_id', 'id'),
        ('code', 'code'),
        ('name', 'name'),
        ('manuf_id', 'manufacturer_id'),
        ('cc', 'cc'),
        ('prim_man_id', 'primary_manufacturer_id'),
        ('note', 'note (with source info extracted)')
    ]
    
    return generate_import_report(
        table_name="Headstamp",
        total_records=total_records,
        processed=processed,
        success=success,
        failed=failed,
        warnings=warnings,
        sources_created=sources_created,
        source_links_created=source_links_created,
        record_results=record_results,
        field_mapping_items=field_mapping_items,
        first_failures=first_failures,
        first_warnings=first_warnings,
        dry_run=dry_run
    )

def create_legacy_mapping(objects_dict):
    """
    Create a mapping dictionary from legacy values to model objects.
    
    Args:
        objects_dict (dict): Dictionary of model objects keyed by id
        
    Returns:
        dict: Mapping from legacy values to model objects
    """
    mapping = {}
    
    for obj in objects_dict.values():
        if hasattr(obj, 'legacy_mappings') and obj.legacy_mappings:
            # Handle different string formats that might be in the database
            legacy_str = obj.legacy_mappings
            
            # Check if the field contains a JSON-like format with brackets
            if legacy_str.startswith('[') and legacy_str.endswith(']'):
                try:
                    # Try to parse it like JSON (removing single quotes if present)
                    import json
                    legacy_str = legacy_str.replace("'", '"')
                    mappings = json.loads(legacy_str)
                except json.JSONDecodeError:
                    # If JSON parsing fails, fall back to simpler processing
                    # Remove brackets and split by commas
                    legacy_str = legacy_str.strip('[]')
                    mappings = [m.strip(' "\'') for m in legacy_str.split(',')]
            else:
                # Plain comma-separated string
                mappings = [m.strip() for m in legacy_str.split(',')]
            
            # Add each mapping to the dictionary
            for m in mappings:
                if m:  # Only add non-empty mappings
                    mapping[m] = obj
                    
                    # Also add lowercase version for case-insensitive matching
                    mapping[m.lower()] = obj
    
    return mapping

def map_lookup_value(value, mapping_dict, field_name, get_default=None):
    """
    Map a value from the old database to a model object using a mapping dictionary.
    
    Args:
        value (str): The value to map
        mapping_dict (dict): Dictionary mapping old values to model objects
        field_name (str): Name of the field (for warning messages)
        get_default (callable, optional): Function to get a default value if not found
        
    Returns:
        tuple: (mapped_object, warning_message)
            - mapped_object: The mapped model object or None
            - warning_message: Warning message if mapping failed, empty string otherwise
    """
    if not value:
        if get_default:
            default_obj = get_default()
            return default_obj, f"No {field_name} specified, using default"
        return None, ""
    
    # Try an exact match first
    mapped_obj = mapping_dict.get(value)
    
    # If no match, try a case-insensitive match
    if not mapped_obj:
        mapped_obj = mapping_dict.get(value.lower())
    
    # If still no match, try with whitespace trimmed
    if not mapped_obj and value.strip() != value:
        mapped_obj = mapping_dict.get(value.strip())
        if not mapped_obj:
            mapped_obj = mapping_dict.get(value.strip().lower())
    
    # If no match found, use default or return None with warning
    if not mapped_obj:
        if get_default:
            default_obj = get_default()
            return default_obj, f"Unknown {field_name} '{value}', using default"
        return None, f"Unknown {field_name} '{value}', leaving blank"
    
    return mapped_obj, ""

# For debugging purposes
def print_legacy_mappings(model_class):
    """
    Print all legacy mappings for a given model class.
    This is useful for debugging mapping issues.
    
    Args:
        model_class: The Django model class to inspect
    """
    for obj in model_class.objects.all():
        if hasattr(obj, 'legacy_mappings') and obj.legacy_mappings:
            print(f"ID: {obj.id}, Display: {obj.display_name}, Legacy: {obj.legacy_mappings}, Type: {type(obj.legacy_mappings)}")


def import_loads(cursor, dry_run):
    """
    Import load records from SQLite database
    Returns a dictionary with summary, stats, and detailed results
    """
    from django.utils import timezone
    from django.db import transaction
    from ..models import (
        Load, Headstamp, Source, LoadSource, 
        LoadType, BulletType, CaseType, PrimerType, PAColor
    )
    
    # Get record count
    total_records = _get_table_count(cursor, "Load")
    
    # Get all loads with headstamp info
    cursor.execute("""
        SELECT 
            l.*,
            h.code as headstamp_code,
            m.code as manuf_code,
            c.name as country_name
        FROM Load l
        LEFT JOIN Headstamp h ON l.headstamp_id = h.headstamp_id
        LEFT JOIN Manuf m ON h.manuf_id = m.manuf_id
        LEFT JOIN Country c ON m.country_id = c.country_id
    """)
    loads = cursor.fetchall()
    
    # Initialize counters
    processed = 0
    success = 0
    failed = 0
    warnings = 0
    sources_created = 0
    source_links_created = 0
    
    # Track the first two failures and warnings for the web display
    first_failures = []
    first_warnings = []
    
    # Results for detailed record processing
    record_results = []
    
    # Load all lookup tables for reference
    load_types = {lt.id: lt for lt in LoadType.objects.all()}
    bullet_types = {bt.id: bt for bt in BulletType.objects.all()}
    case_types = {ct.id: ct for ct in CaseType.objects.all()}
    primer_types = {pt.id: pt for pt in PrimerType.objects.all()}
    pa_colors = {pc.id: pc for pc in PAColor.objects.all()}
    
    # Create mapping dictionaries from legacy_mappings
    lookup_tables = {
        'load_type': create_legacy_mapping(load_types),
        'bullet': create_legacy_mapping(bullet_types),
        'case_type': create_legacy_mapping(case_types),
        'primer': create_legacy_mapping(primer_types),
        'pa_color': create_legacy_mapping(pa_colors)
    }
    
    # Find a good default LoadType to use for both blank and unknown values
    default_load_type = None
    for lt in load_types.values():
        if lt.display_name == "Unknown" or lt.display_name == "Unspecified":  
            default_load_type = lt
            break

    # If no specific match found, use the first load type as a fallback
    if not default_load_type and load_types:
        default_load_type = next(iter(load_types.values()))
    
    # Process each load
    for ld in loads:
        processed += 1
        record_result = {
            'id': ld['load_id'],
            'cart_id': ld['cart_id'],
            'status': 'pending',
            'warnings': [],
            'errors': [],
            'sources': [],
            'details': {}
        }
        
        try:
            # Check if headstamp exists
            try:
                # Find the headstamp by its code and manufacturer (country)
                headstamp = Headstamp.objects.get(
                    code=ld['headstamp_code'],
                    manufacturer__code=ld['manuf_code'],
                    manufacturer__country__name=ld['country_name']
                )
            except Headstamp.DoesNotExist:
                error_msg = f"Headstamp '{ld['headstamp_code']}' (manufacturer: {ld['manuf_code']}, country: {ld['country_name']}) not found"
                record_result['status'] = 'error'
                record_result['errors'].append(error_msg)
                failed += 1
                
                # Track for web display
                if len(first_failures) < 2:
                    first_failures.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'error': error_msg
                    })
                
                record_results.append(record_result)
                continue
            except Headstamp.MultipleObjectsReturned:
                # Try to find a unique match with just code and manufacturer
                try:
                    headstamp = Headstamp.objects.filter(
                        code=ld['headstamp_code'],
                        manufacturer__code=ld['manuf_code']
                    ).first()
                    
                    if not headstamp:
                        raise Headstamp.DoesNotExist()
                        
                    warning_msg = f"Multiple headstamps found with code '{ld['headstamp_code']}' for manufacturer '{ld['manuf_code']}', using the first one"
                    record_result['warnings'].append(warning_msg)
                    warnings += 1
                    
                    # Track for web display
                    if len(first_warnings) < 2:
                        first_warnings.append({
                            'id': ld['load_id'],
                            'cart_id': ld['cart_id'],
                            'warning': warning_msg
                        })
                except Headstamp.DoesNotExist:
                    error_msg = f"Headstamp '{ld['headstamp_code']}' (manufacturer: {ld['manuf_code']}) not found"
                    record_result['status'] = 'error'
                    record_result['errors'].append(error_msg)
                    failed += 1
                    
                    # Track for web display
                    if len(first_failures) < 2:
                        first_failures.append({
                            'id': ld['load_id'],
                            'cart_id': ld['cart_id'],
                            'error': error_msg
                        })
                    
                    record_results.append(record_result)
                    continue
            
            # Map lookup fields using the utility function
            mappings = {}
            
            # Map load_type
            mappings['load_type'], warning = map_lookup_value(
                ld['load_type'], 
                lookup_tables['load_type'], 
                'load_type', 
                get_default=lambda: default_load_type
            )
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'warning': warning
                    })
            
            # Map bullet
            mappings['bullet'], warning = map_lookup_value(
                ld['bullet'], 
                lookup_tables['bullet'], 
                'bullet'
            )
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'warning': warning
                    })
            
            # Map is_magnetic
            mappings['is_magnetic'] = ld['magnetic'] == 'Y' if ld['magnetic'] else False
            
            # Map case_type
            mappings['case_type'], warning = map_lookup_value(
                ld['case_type'], 
                lookup_tables['case_type'], 
                'case_type'
            )
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'warning': warning
                    })
                    
            # Map primer
            mappings['primer'], warning = map_lookup_value(
                ld['primer'], 
                lookup_tables['primer'], 
                'primer'
            )
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'warning': warning
                    })
            
            # Map pa_color
            mappings['pa_color'], warning = map_lookup_value(
                ld['pa_color'], 
                lookup_tables['pa_color'], 
                'pa_color'
            )
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'warning': warning
                    })
            
            # Get acquisition_note from col_date (no parsing, just use the string as-is)
            acquisition_note = ld['col_date'] or ""
            
            # Process price
            price, warning = parse_price(ld['price'])
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'warning': warning
                    })
            
            # Process note and extract sources
            note = ld['note'] or ''
            clean_note, sources_info, source_warnings = extract_sources_from_note(note)
            
            # Add any source warnings to the record
            for warning in source_warnings:
                record_result['warnings'].append(warning)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': ld['load_id'],
                        'cart_id': ld['cart_id'],
                        'warning': warning
                    })
            
            # Store mapping details in record result
            record_result['details'] = {
                'headstamp': ld['headstamp_code'],
                'manufacturer': ld['manuf_code'],
                'load_type': mappings['load_type'].display_name if mappings['load_type'] else 'None',
                'original_load_type': ld['load_type'],
                'bullet': mappings['bullet'].display_name if mappings['bullet'] else 'None',
                'original_bullet': ld['bullet'],
                'is_magnetic': mappings['is_magnetic'],
                'original_magnetic': ld['magnetic'],
                'case_type': mappings['case_type'].display_name if mappings['case_type'] else 'None',
                'original_case_type': ld['case_type'],
                'primer': mappings['primer'].display_name if mappings['primer'] else 'None',
                'original_primer': ld['primer'],
                'pa_color': mappings['pa_color'].display_name if mappings['pa_color'] else 'None',
                'original_pa_color': ld['pa_color'],
                'acquisition_note': acquisition_note,
                'original_col_date': ld['col_date'],
                'price': price,
                'description': ld['description'],
                'note_before': note,
                'note_after': clean_note,
                'sources_count': len(sources_info)
            }
            
            # Process the load record
            if not dry_run:
                with transaction.atomic():
                    # Create or update the load
                    load, created = Load.objects.update_or_create(
                        cart_id=ld['cart_id'],
                        defaults={
                            'load_type': mappings['load_type'],
                            'bullet': mappings['bullet'],
                            'is_magnetic': mappings['is_magnetic'],
                            'case_type': mappings['case_type'],
                            'primer': mappings['primer'],
                            'pa_color': mappings['pa_color'],
                            'description': ld['description'],
                            'headstamp': headstamp,
                            'cc': ld['cc'],
                            'acquisition_note': acquisition_note,  # Use col_date as acquisition_note
                            'price': price,
                            'note': clean_note,
                            'updated_at': timezone.now()
                        }
                    )
                    
                    # Process source links
                    new_sources, new_links, source_msgs = process_sources(
                        load, 
                        sources_info, 
                        dry_run=False
                    )
                    
                    sources_created += new_sources
                    source_links_created += new_links
                    record_result['sources'].extend(source_msgs)
            else:
                # Simulate source processing in dry run mode
                new_sources, new_links, source_msgs = process_sources(
                    None,  # No actual object in dry run
                    sources_info, 
                    dry_run=True
                )
                
                sources_created += new_sources
                source_links_created += new_links
                record_result['sources'].extend(source_msgs)
            
            # Mark record as successful
            record_result['status'] = 'success'
            success += 1
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            record_result['status'] = 'error'
            record_result['errors'].append(error_msg)
            failed += 1
            
            # Track for web display
            if len(first_failures) < 2:
                first_failures.append({
                    'id': ld['load_id'],
                    'cart_id': ld['cart_id'],
                    'error': error_msg
                })
        
        # Add result to record results list
        record_results.append(record_result)
    
    # Generate the import report using the utility function
    field_mapping_items = [
        ('load_id', 'id'),
        ('cart_id', 'cart_id'),
        ('load_type', 'load_type (via lookup)'),
        ('bullet', 'bullet (via lookup)'),
        ('magnetic', 'is_magnetic'),
        ('case_type', 'case_type (via lookup)'),
        ('primer', 'primer (via lookup)'),
        ('pa_color', 'pa_color (via lookup)'),
        ('description', 'description'),
        ('headstamp_id', 'headstamp'),
        ('cc', 'cc'),
        ('col_date', 'acquisition_note'),  # Updated mapping
        ('price', 'price'),
        ('note', 'note (with source info extracted)')
    ]
    
    return generate_import_report(
        table_name="Load",
        total_records=total_records,
        processed=processed,
        success=success,
        failed=failed,
        warnings=warnings,
        sources_created=sources_created,
        source_links_created=source_links_created,
        record_results=record_results,
        field_mapping_items=field_mapping_items,
        first_failures=first_failures,
        first_warnings=first_warnings,
        dry_run=dry_run
    )


def import_dates(cursor, dry_run):
    """
    Import date records from SQLite database
    Returns a dictionary with summary, stats, and detailed results
    """
    from datetime import datetime, date
    from django.utils import timezone
    from django.db import transaction, IntegrityError
    from ..models import Date, Load, Source, DateSource
    
    # Get record count
    total_records = _get_table_count(cursor, "Date")
    
    # Get all dates with load info
    cursor.execute("""
        SELECT 
            d.*,
            l.cart_id as load_cart_id,
            l.headstamp_id,
            h.code as headstamp_code,
            m.code as manuf_code,
            c.name as country_name
        FROM Date d
        LEFT JOIN Load l ON d.load_id = l.load_id
        LEFT JOIN Headstamp h ON l.headstamp_id = h.headstamp_id
        LEFT JOIN Manuf m ON h.manuf_id = m.manuf_id
        LEFT JOIN Country c ON m.country_id = c.country_id
    """)
    dates = cursor.fetchall()
    
    # Initialize counters
    processed = 0
    success = 0
    failed = 0
    warnings = 0
    sources_created = 0
    source_links_created = 0
    
    # Track the first two failures and warnings for the web display
    first_failures = []
    first_warnings = []
    
    # Results for detailed record processing
    record_results = []
    
    # Process each date
    for dt in dates:
        processed += 1
        record_result = {
            'id': dt['date_id'],
            'cart_id': dt['cart_id'],
            'status': 'pending',
            'warnings': [],
            'errors': [],
            'sources': [],
            'details': {}
        }
        
        try:
            # Find the load by cart_id
            try:
                load = Load.objects.get(cart_id=dt['load_cart_id'])
            except Load.DoesNotExist:
                error_msg = f"Load with cart_id '{dt['load_cart_id']}' not found"
                record_result['status'] = 'error'
                record_result['errors'].append(error_msg)
                failed += 1
                
                # Track for web display
                if len(first_failures) < 2:
                    first_failures.append({
                        'id': dt['date_id'],
                        'cart_id': dt['cart_id'],
                        'error': error_msg
                    })
                
                record_results.append(record_result)
                continue
            
            # Get acquisition_note from col_date (no parsing, just use the string as-is)
            acquisition_note = dt['col_date'] or ""
            
            # Process price
            price, warning = parse_price(dt['price'])
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': dt['date_id'],
                        'cart_id': dt['cart_id'],
                        'warning': warning
                    })
            
            # Process note and extract sources
            note = dt['note'] or ''
            clean_note, sources_info, source_warnings = extract_sources_from_note(note)
            
            # Add any source warnings to the record
            for warning in source_warnings:
                record_result['warnings'].append(warning)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': dt['date_id'],
                        'cart_id': dt['cart_id'],
                        'warning': warning
                    })
            
            # Store details in record result
            record_result['details'] = {
                'load': dt['load_cart_id'],
                'year': dt['year'],
                'lot_month': dt['lot_month'],
                'acquisition_note': acquisition_note,
                'price': price,
                'note_before': note,
                'note_after': clean_note,
                'sources_count': len(sources_info)
            }
            
            # Process the date record
            if not dry_run:
                with transaction.atomic():
                    # Create or update the date
                    date, created = Date.objects.update_or_create(
                        cart_id=dt['cart_id'],
                        defaults={
                            'year': dt['year'],
                            'lot_month': dt['lot_month'],
                            'load': load,
                            'cc': dt['cc'],
                            'acquisition_note': acquisition_note,
                            'price': price,
                            'note': clean_note,
                            'updated_at': timezone.now()
                        }
                    )
                    
                    # Process source links
                    new_sources, new_links, source_msgs = process_sources(
                        date, 
                        sources_info, 
                        dry_run=False
                    )
                    
                    sources_created += new_sources
                    source_links_created += new_links
                    record_result['sources'].extend(source_msgs)
            else:
                # Simulate source processing in dry run mode
                new_sources, new_links, source_msgs = process_sources(
                    None,  # No actual object in dry run
                    sources_info, 
                    dry_run=True
                )
                
                sources_created += new_sources
                source_links_created += new_links
                record_result['sources'].extend(source_msgs)
            
            # Mark record as successful
            record_result['status'] = 'success'
            record_result['note_before'] = note
            record_result['note_after'] = clean_note
            success += 1
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            record_result['status'] = 'error'
            record_result['errors'].append(error_msg)
            failed += 1
            
            # Track for web display
            if len(first_failures) < 2:
                first_failures.append({
                    'id': dt['date_id'],
                    'cart_id': dt['cart_id'],
                    'error': error_msg
                })
        
        record_results.append(record_result)
    
    # Generate the import report using the utility function
    field_mapping_items = [
        ('date_id', 'id'),
        ('cart_id', 'cart_id'),
        ('year', 'year'),
        ('lot_month', 'lot_month'),
        ('load_id', 'load_id'),
        ('cc', 'cc'),
        ('col_date', 'acquisition_note'),
        ('price', 'price'),
        ('note', 'note (with source info extracted)')
    ]
    
    return generate_import_report(
        table_name="Date",
        total_records=total_records,
        processed=processed,
        success=success,
        failed=failed,
        warnings=warnings,
        sources_created=sources_created,
        source_links_created=source_links_created,
        record_results=record_results,
        field_mapping_items=field_mapping_items,
        first_failures=first_failures,
        first_warnings=first_warnings,
        dry_run=dry_run
    )


def import_variations(cursor, dry_run):
    """
    Import variation records from SQLite database
    Returns a dictionary with summary, stats, and detailed results
    """
    from django.utils import timezone
    from django.db import transaction, IntegrityError
    from ..models import Variation, Load, Date, Source, VariationSource
    
    # Get record count
    total_records = _get_table_count(cursor, "Variation")
    
    # Get all variations with load and date info
    cursor.execute("""
        SELECT 
            v.*,
            l.cart_id as load_cart_id,
            d.cart_id as date_cart_id
        FROM Variation v
        LEFT JOIN Load l ON v.load_id = l.load_id
        LEFT JOIN Date d ON v.date_id = d.date_id
    """)
    variations = cursor.fetchall()
    
    # Initialize counters
    processed = 0
    success = 0
    failed = 0
    warnings = 0
    sources_created = 0
    source_links_created = 0
    
    # Track the first two failures and warnings for the web display
    first_failures = []
    first_warnings = []
    
    # Results for detailed record processing
    record_results = []
    
    # Process each variation
    for var in variations:
        processed += 1
        record_result = {
            'id': var['var_id'],
            'cart_id': var['cart_id'],
            'status': 'pending',
            'warnings': [],
            'errors': [],
            'sources': [],
            'details': {}
        }
        
        try:
            # Check if we have either a load or a date, but not both
            if var['load_id'] and var['date_id']:
                warning_msg = "Variation has both load_id and date_id set, according to the new schema it should have only one"
                record_result['warnings'].append(warning_msg)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': var['var_id'],
                        'cart_id': var['cart_id'],
                        'warning': warning_msg
                    })
            
            # Find the load or date by cart_id
            load = None
            date = None
            
            if var['load_id']:
                try:
                    load = Load.objects.get(cart_id=var['load_cart_id'])
                except Load.DoesNotExist:
                    if var['date_id']:
                        # We'll try to use date instead
                        warning_msg = f"Load with cart_id '{var['load_cart_id']}' not found, trying to use date instead"
                        record_result['warnings'].append(warning_msg)
                        warnings += 1
                        
                        # Track for web display
                        if len(first_warnings) < 2:
                            first_warnings.append({
                                'id': var['var_id'],
                                'cart_id': var['cart_id'],
                                'warning': warning_msg
                            })
                    else:
                        error_msg = f"Load with cart_id '{var['load_cart_id']}' not found"
                        record_result['status'] = 'error'
                        record_result['errors'].append(error_msg)
                        failed += 1
                        
                        # Track for web display
                        if len(first_failures) < 2:
                            first_failures.append({
                                'id': var['var_id'],
                                'cart_id': var['cart_id'],
                                'error': error_msg
                            })
                        
                        record_results.append(record_result)
                        continue
            
            if var['date_id'] and not load:
                try:
                    date = Date.objects.get(cart_id=var['date_cart_id'])
                except Date.DoesNotExist:
                    error_msg = f"Date with cart_id '{var['date_cart_id']}' not found"
                    record_result['status'] = 'error'
                    record_result['errors'].append(error_msg)
                    failed += 1
                    
                    # Track for web display
                    if len(first_failures) < 2:
                        first_failures.append({
                            'id': var['var_id'],
                            'cart_id': var['cart_id'],
                            'error': error_msg
                        })
                    
                    record_results.append(record_result)
                    continue
            
            # Ensure we have either a load or a date
            if not load and not date:
                error_msg = "Variation must have either a load or a date, but neither was found"
                record_result['status'] = 'error'
                record_result['errors'].append(error_msg)
                failed += 1
                
                # Track for web display
                if len(first_failures) < 2:
                    first_failures.append({
                        'id': var['var_id'],
                        'cart_id': var['cart_id'],
                        'error': error_msg
                    })
                
                record_results.append(record_result)
                continue
            
            # Get acquisition_note from col_date (no parsing, just use the string as-is)
            acquisition_note = var['col_date'] or ""
            
            # Process price
            price, warning = parse_price(var['price'])
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': var['var_id'],
                        'cart_id': var['cart_id'],
                        'warning': warning
                    })
            
            # Process note and extract sources
            note = var['note'] or ''
            clean_note, sources_info, source_warnings = extract_sources_from_note(note)
            
            # Add any source warnings to the record
            for warning in source_warnings:
                record_result['warnings'].append(warning)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': var['var_id'],
                        'cart_id': var['cart_id'],
                        'warning': warning
                    })
            
            # Store details in record result
            record_result['details'] = {
                'parent_type': 'Load' if load else 'Date',
                'parent_id': var['load_cart_id'] if load else var['date_cart_id'],
                'description': var['description'],
                'acquisition_note': acquisition_note,
                'price': price,
                'note_before': note,
                'note_after': clean_note,
                'sources_count': len(sources_info)
            }
            
            # Process the variation record
            if not dry_run:
                with transaction.atomic():
                    # Create or update the variation
                    variation, created = Variation.objects.update_or_create(
                        cart_id=var['cart_id'],
                        defaults={
                            'load': load,
                            'date': date,
                            'description': var['description'],
                            'cc': var['cc'],
                            'acquisition_note': acquisition_note,
                            'price': price,
                            'note': clean_note,
                            'updated_at': timezone.now()
                        }
                    )
                    
                    # Process source links
                    new_sources, new_links, source_msgs = process_sources(
                        variation, 
                        sources_info, 
                        dry_run=False
                    )
                    
                    sources_created += new_sources
                    source_links_created += new_links
                    record_result['sources'].extend(source_msgs)
            else:
                # Simulate source processing in dry run mode
                new_sources, new_links, source_msgs = process_sources(
                    None,  # No actual object in dry run
                    sources_info, 
                    dry_run=True
                )
                
                sources_created += new_sources
                source_links_created += new_links
                record_result['sources'].extend(source_msgs)
            
            # Mark record as successful
            record_result['status'] = 'success'
            record_result['note_before'] = note
            record_result['note_after'] = clean_note
            success += 1
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            record_result['status'] = 'error'
            record_result['errors'].append(error_msg)
            failed += 1
            
            # Track for web display
            if len(first_failures) < 2:
                first_failures.append({
                    'id': var['var_id'],
                    'cart_id': var['cart_id'],
                    'error': error_msg
                })
        
        record_results.append(record_result)
    
    # Generate the import report using the utility function
    field_mapping_items = [
        ('var_id', 'id'),
        ('cart_id', 'cart_id'),
        ('description', 'description'),
        ('var_type', '(used to determine if load or date is used)'),
        ('load_id', 'load_id'),
        ('date_id', 'date_id'),
        ('cc', 'cc'),
        ('col_date', 'acquisition_note'),
        ('price', 'price'),
        ('note', 'note (with source info extracted)')
    ]
    
    return generate_import_report(
        table_name="Variation",
        total_records=total_records,
        processed=processed,
        success=success,
        failed=failed,
        warnings=warnings,
        sources_created=sources_created,
        source_links_created=source_links_created,
        record_results=record_results,
        field_mapping_items=field_mapping_items,
        first_failures=first_failures,
        first_warnings=first_warnings,
        dry_run=dry_run
    )


def import_boxes(cursor, dry_run):
    """
    Import box records from SQLite database
    Returns a dictionary with summary, stats, and detailed results
    """
    from django.utils import timezone
    from django.db import transaction, IntegrityError
    from django.contrib.contenttypes.models import ContentType
    from ..models import Box, Country, Manufacturer, Headstamp, Load, Date, Variation, Source, BoxSource
    
    # Get record count
    total_records = _get_table_count(cursor, "Box")
    
    # Get all boxes
    cursor.execute("""
        SELECT * FROM Box
    """)
    boxes = cursor.fetchall()
    
    # Initialize counters
    processed = 0
    success = 0
    failed = 0
    warnings = 0
    sources_created = 0
    source_links_created = 0
    
    # Track the first two failures and warnings for the web display
    first_failures = []
    first_warnings = []
    
    # Results for detailed record processing
    record_results = []
    
    # Get ContentType objects for all potential parent models
    content_types = {
        'country': ContentType.objects.get_for_model(Country),
        'manuf': ContentType.objects.get_for_model(Manufacturer),
        'headstamp': ContentType.objects.get_for_model(Headstamp),
        'hst': ContentType.objects.get_for_model(Headstamp),  # Alternative key for headstamp
        'load': ContentType.objects.get_for_model(Load),
        'date': ContentType.objects.get_for_model(Date),
        'var': ContentType.objects.get_for_model(Variation),
        'box': None  # We won't import boxes with box parents
    }
    
    # Process each box
    for box in boxes:
        processed += 1
        record_result = {
            'id': box['box_id'],
            'bid': box['bid'],
            'status': 'pending',
            'warnings': [],
            'errors': [],
            'sources': [],
            'details': {}
        }
        
        try:
            # Map the old sup_type to the appropriate model/ContentType
            parent_obj = None
            content_type = None
            parent_id = box['sup_id']
            
            # Add detailed debugging information to help diagnose parent mapping issues
            debug_info = {
                'sup_type_raw': box['sup_type'],
                'sup_type_normalized': box['sup_type'].lower() if box['sup_type'] else None,
                'sup_id': parent_id
            }
            record_result['details']['debug_info'] = debug_info
            
            # Check if this box has a box as parent - if so, skip importing
            if box['sup_type'] and box['sup_type'].lower() == 'box':
                error_msg = f"Box with ID {box['box_id']} has another box as parent, skipping import"
                record_result['status'] = 'error'
                record_result['errors'].append(error_msg)
                failed += 1
                
                # Track for web display
                if len(first_failures) < 2:
                    first_failures.append({
                        'id': box['box_id'],
                        'bid': box['bid'],
                        'error': error_msg
                    })
                
                record_results.append(record_result)
                continue
            
            # Improved check for missing parent type or ID
            # Check explicitly for None or empty string to avoid false negatives
            if (box['sup_type'] is None or box['sup_type'] == '') or (parent_id is None or parent_id == 0):
                error_msg = f"Box has no valid parent reference (sup_type: '{box['sup_type']}', sup_id: {parent_id}), skipping import"
                record_result['status'] = 'error'
                record_result['errors'].append(error_msg)
                failed += 1
                
                # Track for web display
                if len(first_failures) < 2:
                    first_failures.append({
                        'id': box['box_id'],
                        'bid': box['bid'],
                        'error': error_msg
                    })
                
                record_results.append(record_result)
                continue
            else:
                # Normalize sup_type to handle potential case variations
                sup_type = box['sup_type'].lower()
                
                # If this is a box with 'box' parent type, skip it
                if sup_type == 'box':
                    error_msg = f"Box with ID {box['box_id']} has another box as parent, skipping import"
                    record_result['status'] = 'error'
                    record_result['errors'].append(error_msg)
                    failed += 1
                    
                    # Track for web display
                    if len(first_failures) < 2:
                        first_failures.append({
                            'id': box['box_id'],
                            'bid': box['bid'],
                            'error': error_msg
                        })
                    
                    record_results.append(record_result)
                    continue
                
                # Check if the sup_type is in our content_types dictionary
                if sup_type not in content_types:
                    warning_msg = f"Unknown parent type '{box['sup_type']}', box will be orphaned"
                    record_result['warnings'].append(warning_msg)
                    warnings += 1
                    
                    # Track for web display
                    if len(first_warnings) < 2:
                        first_warnings.append({
                            'id': box['box_id'],
                            'bid': box['bid'],
                            'warning': warning_msg
                        })
                    
                    # Create without parent reference
                    parent_obj = None
                    content_type = None
                    continue
                
                # Get the content type
                content_type = content_types[sup_type]
                
                # Find the parent object using the appropriate model
                try:
                    if sup_type == 'country':
                        parent_obj = Country.objects.get(pk=parent_id)
                    elif sup_type == 'manuf':
                        parent_obj = Manufacturer.objects.get(pk=parent_id)
                    elif sup_type in ['headstamp', 'hst']:
                        parent_obj = Headstamp.objects.get(pk=parent_id)
                    elif sup_type == 'load':
                        parent_obj = Load.objects.get(pk=parent_id)
                    elif sup_type == 'date':
                        parent_obj = Date.objects.get(pk=parent_id)
                    elif sup_type == 'var':
                        parent_obj = Variation.objects.get(pk=parent_id)
                except (Country.DoesNotExist, Manufacturer.DoesNotExist, 
                        Headstamp.DoesNotExist, Load.DoesNotExist,
                        Date.DoesNotExist, Variation.DoesNotExist) as e:
                    error_msg = f"{sup_type.capitalize()} with ID {parent_id} not found"
                    record_result['status'] = 'error'
                    record_result['errors'].append(error_msg)
                    failed += 1
                    
                    # Track for web display
                    if len(first_failures) < 2:
                        first_failures.append({
                            'id': box['box_id'],
                            'bid': box['bid'],
                            'error': error_msg
                        })
                    
                    record_results.append(record_result)
                    continue
            
            # Map artifact type
            artifact_type = 'box'  # Default
            artifact_type_other = None
            
            if box['art_type']:
                art_type = box['art_type'].lower()
                if art_type in ['box', 'photo', 'drawing', 'label', 'document']:
                    artifact_type = art_type
                else:
                    artifact_type = 'other'
                    artifact_type_other = box['art_type']
            
            # Get acquisition_note from col_date (no parsing, just use the string as-is)
            acquisition_note = box['col_date'] or ""
            
            # Process price
            price, warning = parse_price(box['price'])
            if warning:
                record_result['warnings'].append(warning)
                warnings += 1
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': box['box_id'],
                        'bid': box['bid'],
                        'warning': warning
                    })
            
            # Process note and extract sources
            note = box['note'] or ''
            clean_note, sources_info, source_warnings = extract_sources_from_note(note)
            
            # Add any source warnings to the record
            for warning in source_warnings:
                record_result['warnings'].append(warning)
                warnings += 1
                
                # Track for web display
                if len(first_warnings) < 2:
                    first_warnings.append({
                        'id': box['box_id'],
                        'bid': box['bid'],
                        'warning': warning
                    })
            
            # Store details in record result
            record_result['details'] = {
                'parent_type': box['sup_type'] if box['sup_type'] else 'None',
                'parent_id': parent_id if parent_id else 'None',
                'location': box['location'],
                'art_type': artifact_type,
                'art_type_other': artifact_type_other,
                'description': box['description'],
                'acquisition_note': acquisition_note,
                'price': price,
                'note_before': note,
                'note_after': clean_note,
                'sources_count': len(sources_info)
            }
            
            # Process the box record
            if not dry_run:
                with transaction.atomic():
                    # Make sure we have both content_type and object_id or neither
                    if not (content_type and parent_obj):
                        # This should not happen now that we're skipping orphaned boxes,
                        # but keeping as an extra safeguard
                        error_msg = "Cannot create box without both content_type and object_id"
                        record_result['status'] = 'error'
                        record_result['errors'].append(error_msg)
                        failed += 1
                        record_results.append(record_result)
                        continue
                        
                    # Create or update the box
                    box_obj, created = Box.objects.update_or_create(
                        bid=box['bid'],
                        defaults={
                            'location': box['location'],
                            'description': box['description'],
                            'art_type': artifact_type,
                            'art_type_other': artifact_type_other,
                            'cc': box['cc'],
                            'acquisition_note': acquisition_note,
                            'price': price,
                            'note': clean_note,
                            'content_type': content_type,
                            'object_id': parent_obj.id,
                            'updated_at': timezone.now()
                        }
                    )
                    
                    # Process source links
                    new_sources, new_links, source_msgs = process_sources(
                        box_obj, 
                        sources_info, 
                        dry_run=False
                    )
                    
                    sources_created += new_sources
                    source_links_created += new_links
                    record_result['sources'].extend(source_msgs)
            else:
                # Simulate source processing in dry run mode
                new_sources, new_links, source_msgs = process_sources(
                    None,  # No actual object in dry run
                    sources_info, 
                    dry_run=True
                )
                
                sources_created += new_sources
                source_links_created += new_links
                record_result['sources'].extend(source_msgs)
            
            # Mark record as successful
            record_result['status'] = 'success'
            record_result['note_before'] = note
            record_result['note_after'] = clean_note
            success += 1
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            record_result['status'] = 'error'
            record_result['errors'].append(error_msg)
            failed += 1
            
            # Track for web display
            if len(first_failures) < 2:
                first_failures.append({
                    'id': box['box_id'],
                    'bid': box['bid'],
                    'error': error_msg
                })
        
        record_results.append(record_result)
    
    # Generate the import report using the utility function
    field_mapping_items = [
        ('box_id', 'id'),
        ('bid', 'bid'),
        ('location', 'location'),
        ('description', 'description'),
        ('sup_type', 'content_type (via mapping)'),
        ('sup_id', 'object_id'),
        ('cc', 'cc'),
        ('art_type', 'art_type'),
        ('col_date', 'acquisition_note'),
        ('price', 'price'),
        ('note', 'note (with source info extracted)')
    ]
    
    return generate_import_report(
        table_name="Box",
        total_records=total_records,
        processed=processed,
        success=success,
        failed=failed,
        warnings=warnings,
        sources_created=sources_created,
        source_links_created=source_links_created,
        record_results=record_results,
        field_mapping_items=field_mapping_items,
        first_failures=first_failures,
        first_warnings=first_warnings,
        dry_run=dry_run
    )


def import_records(request, caliber_code):
    """View for importing records from SQLite database"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'title': 'Import Records',
    }
    
    # Define Django system tables that shouldn't be imported
    django_tables = [
        'auth_group', 'auth_group_permissions', 'auth_permission', 
        'auth_user', 'auth_user_groups', 'auth_user_user_permissions',
        'django_admin_log', 'django_content_type', 'django_migrations',
        'django_session', 'sqlite_sequence'
    ]
    
    # Define supported tables for import - UPDATED to include all importers
    supported_tables = ['Country', 'Manuf', 'Headstamp', 'Load', 'Date', 'Variation', 'Box']
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        # Step 1: Examine the database
        if action == 'examine':
            database_file = request.FILES.get('database_file')
            
            if not database_file:
                messages.error(request, "Please select a database file to import")
                return render(request, 'collection/import_records.html', context)
            
            # Generate a unique session ID for this import
            session_id = str(uuid.uuid4())
            
            try:
                # Save the uploaded file temporarily
                temp_path = os.path.join('temp_imports', f"{session_id}_{database_file.name}")
                path = default_storage.save(temp_path, ContentFile(database_file.read()))
                full_path = default_storage.path(path)
                
                # Connect to the SQLite database
                conn = sqlite3.connect(full_path)
                cursor = conn.cursor()
                
                # Get the list of tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                table_names = cursor.fetchall()
                
                # Format table info
                tables = []
                for table in table_names:
                    table_name = table[0]
                    
                    # Get row count for the table
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                        count = cursor.fetchone()[0]
                    except sqlite3.OperationalError:
                        count = 0
                    
                    # Check if it's a Django system table
                    is_django_table = table_name in django_tables
                    # Check if it's supported for import
                    is_supported = table_name in supported_tables
                    
                    tables.append({
                        'name': table_name,
                        'count': count,
                        'django_table': is_django_table,
                        'supported': is_supported
                    })
                
                # Store the database info in session
                request.session[f'database_info_{session_id}'] = {
                    'file_path': path,
                    'full_path': full_path,
                    'file_name': database_file.name,
                    'tables': tables
                }
                
                # Update context for template
                importable_tables = [t for t in tables if not t['django_table']]
                supported_importable_tables = [t for t in importable_tables if t['supported']]
                context.update({
                    'database_examined': True,
                    'database_name': database_file.name,
                    'tables': tables,
                    'table_count': len(tables),
                    'importable_table_count': len(importable_tables),
                    'supported_importable_count': len(supported_importable_tables),
                    'session_id': session_id,
                    'supported_tables': supported_tables
                })
                
                # Close connection
                conn.close()
                
            except sqlite3.Error as e:
                messages.error(request, f"SQLite error: {str(e)}")
                return render(request, 'collection/import_records.html', context)
            except Exception as e:
                messages.error(request, f"Error processing database: {str(e)}")
                return render(request, 'collection/import_records.html', context)
        
        # Step 2: Process the import
        elif action == 'import':
            session_id = request.POST.get('session_id')
            
            if not session_id or f'database_info_{session_id}' not in request.session:
                messages.error(request, "Database information not found. Please upload the database again.")
                return render(request, 'collection/import_records.html', context)
            
            # Get stored database info
            db_info = request.session[f'database_info_{session_id}']
            
            # Get import options
            selected_table = request.POST.get('selected_table')
            import_mode = request.POST.get('import_mode', 'merge')
            import_images = request.POST.get('import_images') == 'yes'
            dry_run = request.POST.get('dry_run') == 'yes'
            
            if not selected_table:
                messages.warning(request, "No table selected for import.")
                
                # Re-populate the examination context
                context.update({
                    'database_examined': True,
                    'database_name': db_info['file_name'],
                    'tables': db_info['tables'],
                    'table_count': len(db_info['tables']),
                    'importable_table_count': len([t for t in db_info['tables'] if not t.get('django_table')]),
                    'supported_importable_count': len([t for t in db_info['tables'] if not t.get('django_table') and t.get('supported')]),
                    'session_id': session_id,
                    'supported_tables': supported_tables
                })
                return render(request, 'collection/import_records.html', context)
            
            # Check if the selected table is supported
            if selected_table not in supported_tables:
                messages.error(request, f"The selected table '{selected_table}' is not currently supported for import.")
                
                # Re-populate the examination context
                context.update({
                    'database_examined': True,
                    'database_name': db_info['file_name'],
                    'tables': db_info['tables'],
                    'table_count': len(db_info['tables']),
                    'importable_table_count': len([t for t in db_info['tables'] if not t.get('django_table')]),
                    'supported_importable_count': len([t for t in db_info['tables'] if not t.get('django_table') and t.get('supported')]),
                    'session_id': session_id,
                    'supported_tables': supported_tables
                })
                return render(request, 'collection/import_records.html', context)
            
            try:
                # Connect to the database
                conn = sqlite3.connect(db_info['full_path'])
                conn.row_factory = sqlite3.Row  # Use row factory for named columns
                cursor = conn.cursor()
                
                # Prepare results
                results = "IMPORT ANALYSIS REPORT\n"
                results += "=" * 50 + "\n\n"
                results += f"Database: {db_info['file_name']}\n"
                results += f"Table: {selected_table}\n"
                results += f"Mode: {'Dry Run (no changes made)' if dry_run else 'Actual Import'}\n"
                results += f"Import Type: {import_mode.capitalize()}\n"
                results += f"Import Images: {'Yes' if import_images else 'No'}\n\n"
                
                # Import the selected table
                import_results = None
                
                if selected_table == "Country":
                    import_results = import_countries(cursor, dry_run)
                elif selected_table == "Manuf":
                    import_results = import_manufacturers(cursor, dry_run)
                elif selected_table == "Headstamp":
                    import_results = import_headstamps(cursor, dry_run)
                elif selected_table == "Load":
                    import_results = import_loads(cursor, dry_run)
                elif selected_table == "Date":
                    import_results = import_dates(cursor, dry_run)
                elif selected_table == "Variation":
                    import_results = import_variations(cursor, dry_run)
                elif selected_table == "Box":
                    import_results = import_boxes(cursor, dry_run)
                
                if import_results:
                    # For web display: use the web_summary
                    web_display = import_results['web_summary']
                    
                    # For downloadable report: use the complete report
                    complete_report = results + import_results['complete_report']
                    
                    # Store the results
                    request.session[f'import_results_{session_id}'] = {
                        'results': web_display,             # For display in the UI
                        'complete_results': complete_report,  # For downloadable report
                        'dry_run': dry_run,
                        'file_name': db_info['file_name'],
                        'selected_table': selected_table,
                        'import_mode': import_mode,
                        'import_images': import_images,
                        'stats': import_results['stats'],
                        'first_failures': import_results.get('first_failures', []),
                        'first_warnings': import_results.get('first_warnings', [])
                    }
                    
                    # Add results to context
                    context.update({
                        'results': web_display,
                        'complete_results': complete_report,
                        'dry_run': dry_run,
                        'session_id': session_id,
                        'selected_table': selected_table,
                        'import_mode': import_mode,
                        'import_images': 'yes' if import_images else 'no',
                        'stats': import_results['stats'],
                        'first_failures': import_results.get('first_failures', []),
                        'first_warnings': import_results.get('first_warnings', [])
                    })
                    
                    # Show appropriate message
                    if dry_run:
                        messages.info(request, "Dry run completed successfully. You can review the results before running the actual import.")
                    else:
                        messages.success(request, "Import completed successfully.")
                else:
                    messages.warning(request, f"No implementation found to import table '{selected_table}'.")
                
                # Close connection
                conn.close()
                
            except sqlite3.Error as e:
                messages.error(request, f"SQLite error: {str(e)}")
                # Re-populate context for the form
                context.update({
                    'database_examined': True,
                    'database_name': db_info['file_name'],
                    'tables': db_info['tables'],
                    'table_count': len(db_info['tables']),
                    'importable_table_count': len([t for t in db_info['tables'] if not t.get('django_table')]),
                    'supported_importable_count': len([t for t in db_info['tables'] if not t.get('django_table') and t.get('supported')]),
                    'session_id': session_id,
                    'supported_tables': supported_tables
                })
            except Exception as e:
                messages.error(request, f"Error processing import: {str(e)}")
                # Re-populate context for the form
                context.update({
                    'database_examined': True,
                    'database_name': db_info['file_name'],
                    'tables': db_info['tables'],
                    'table_count': len(db_info['tables']),
                    'importable_table_count': len([t for t in db_info['tables'] if not t.get('django_table')]),
                    'supported_importable_count': len([t for t in db_info['tables'] if not t.get('django_table') and t.get('supported')]),
                    'session_id': session_id,
                    'supported_tables': supported_tables
                })
    
    return render(request, 'collection/import_records.html', context)


def download_results(request, caliber_code):
    """Download import results as a text file"""
    session_id = request.GET.get('session_id')
    
    if not session_id or f'import_results_{session_id}' not in request.session:
        messages.error(request, "Results not found or expired")
        return redirect('import_records', caliber_code=caliber_code)
    
    # Get the stored results
    stored_data = request.session[f'import_results_{session_id}']
    
    # Use the complete_results for the download, not the web display version
    results = stored_data.get('complete_results', stored_data.get('results', ''))
    dry_run = stored_data['dry_run']
    file_name = stored_data['file_name']
    table_name = stored_data.get('selected_table', 'unknown')
    
    # Create response with text file
    response = HttpResponse(results, content_type='text/plain')
    response_filename = f"import_{table_name}_{os.path.splitext(file_name)[0]}_{'dry_run' if dry_run else 'actual'}.txt"
    response['Content-Disposition'] = f'attachment; filename="{response_filename}"'
    
    return response