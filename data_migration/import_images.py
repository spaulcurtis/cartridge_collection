#!/usr/bin/env python
"""
Image Import Script for Cartridge Collection

This script imports image files into a Django cartridge collection database,
copying the files to the appropriate media directories and updating the database
records to reference these images.

Usage:
    python import_images.py --type [headstamp|load|box] --source [directory]

Example:
    python import_images.py --type headstamp --source ~/Downloads/headstamp_images
"""

import os
import sys
import shutil
import sqlite3
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Main logger setup
logger = logging.getLogger("image_import")
logger.setLevel(logging.INFO)

# Create success log file handler
success_handler = logging.FileHandler(f"{log_dir}/successful_imports_{timestamp}.log")
success_handler.setLevel(logging.INFO)
success_formatter = logging.Formatter('%(message)s')
success_handler.setFormatter(success_formatter)

# Create error log file handler
error_handler = logging.FileHandler(f"{log_dir}/failed_imports_{timestamp}.log")
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(success_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Import images into the cartridge collection database.")
    parser.add_argument("--type", required=True, choices=["headstamp", "load", "box"],
                        help="Type of images to import (headstamp, load, or box)")
    parser.add_argument("--source", required=True, help="Directory containing the images to import")
    parser.add_argument("--db", default="db.sqlite3", help="Path to the SQLite database (default: db.sqlite3)")
    parser.add_argument("--media", default="media", help="Path to the media directory (default: media)")
    return parser.parse_args()

def connect_to_database(db_path):
    """Connect to the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        sys.exit(1)

def get_caliber_id(conn, caliber_code='9mmP'):
    """Get the ID of the specified caliber."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM collection_caliber WHERE code = ?", (caliber_code,))
        result = cursor.fetchone()
        return result['id'] if result else None
    except sqlite3.Error as e:
        logger.error(f"Error getting caliber ID: {e}")
        return None

def import_headstamp_images(conn, source_dir, media_dir, caliber_id):
    """Import headstamp images into the database."""
    cursor = conn.cursor()
    
    # Get all headstamps for 9mmP caliber with country information
    try:
        cursor.execute("""
            SELECT h.id, h.code, 
                   m.code as manufacturer_code, m.id as manufacturer_id, 
                   c.id as country_id, c.name as country_name
            FROM collection_headstamp h
            JOIN collection_manufacturer m ON h.manufacturer_id = m.id
            JOIN collection_country c ON m.country_id = c.id
            WHERE c.caliber_id = ?
        """, (caliber_id,))
        
        headstamps = cursor.fetchall()
        logger.info(f"Found {len(headstamps)} headstamps for 9mmP caliber")
        
        # Process each source image file
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for source_file in os.listdir(source_dir):
            if not (source_file.lower().endswith('.png') or 
                    source_file.lower().endswith('.jpg') or 
                    source_file.lower().endswith('.jpeg')):
                continue
                
            # Extract headstamp code from filename (remove extension)
            headstamp_code = os.path.splitext(source_file)[0]
            
            # Find matching headstamps in the database
            matching_headstamps = [h for h in headstamps if h['code'] == headstamp_code]
            
            if not matching_headstamps:
                logger.error(f"No matching headstamp found for code: {headstamp_code}")
                error_count += 1
                continue
            
            # Process each matching headstamp
            for headstamp in matching_headstamps:
                # Create a unique, safe filename using country ID, manufacturer code, and headstamp code
                file_ext = os.path.splitext(source_file)[1]
                target_filename = f"{headstamp['country_id']}_{headstamp['manufacturer_code']}_{headstamp['code']}{file_ext}"
                
                # Create target directory path
                target_dir = os.path.join(media_dir, '9mmP', 'headstamps')
                os.makedirs(target_dir, exist_ok=True)
                
                # Full target path
                target_path = os.path.join(target_dir, target_filename)
                
                # Relative path for database
                db_path = os.path.join('9mmP', 'headstamps', target_filename)
                
                try:
                    # Copy the file
                    shutil.copy2(os.path.join(source_dir, source_file), target_path)
                    
                    # Update database
                    cursor.execute(
                        "UPDATE collection_headstamp SET image = ? WHERE id = ?",
                        (db_path, headstamp['id'])
                    )
                    
                    conn.commit()
                    success_count += 1
                    logger.info(f"Successfully imported headstamp {headstamp['code']} (ID: {headstamp['id']}) - "
                                f"Country: {headstamp['country_name']} (ID: {headstamp['country_id']}) - "
                                f"Manufacturer: {headstamp['manufacturer_code']} - "
                                f"Source: {source_file} -> Target: {db_path}")
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error importing headstamp {headstamp_code}: {e}")
                    error_count += 1
        
        logger.info(f"Headstamp import complete. Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}")
        
    except sqlite3.Error as e:
        logger.error(f"Database error during headstamp import: {e}")
        return False
        
    return True

def import_load_images(conn, source_dir, media_dir, caliber_id):
    """Import load, date, and variation images into the database."""
    cursor = conn.cursor()
    
    # Process each source image file
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for source_file in os.listdir(source_dir):
        if not (source_file.lower().endswith('.png') or 
                source_file.lower().endswith('.jpg') or 
                source_file.lower().endswith('.jpeg')):
            continue
            
        # Extract cart_id from filename (remove extension)
        cart_id = os.path.splitext(source_file)[0]
        
        try:
            # Determine the type based on the cart_id prefix
            if cart_id.startswith('L'):
                table = 'collection_load'
                target_subdir = 'loads'
            elif cart_id.startswith('D'):
                table = 'collection_date'
                target_subdir = 'dates'
            elif cart_id.startswith('V'):
                table = 'collection_variation'
                target_subdir = 'variations'
            else:
                logger.error(f"Unknown cart_id format: {cart_id}")
                error_count += 1
                continue
            
            # Get the record from the database
            if table == 'collection_load':
                cursor.execute(f"""
                    SELECT l.id, h.manufacturer_id
                    FROM {table} l
                    JOIN collection_headstamp h ON l.headstamp_id = h.id
                    JOIN collection_manufacturer m ON h.manufacturer_id = m.id
                    JOIN collection_country c ON m.country_id = c.id
                    WHERE l.cart_id = ? AND c.caliber_id = ?
                """, (cart_id, caliber_id))
            elif table == 'collection_date':
                cursor.execute(f"""
                    SELECT d.id, h.manufacturer_id
                    FROM {table} d
                    JOIN collection_load l ON d.load_id = l.id
                    JOIN collection_headstamp h ON l.headstamp_id = h.id
                    JOIN collection_manufacturer m ON h.manufacturer_id = m.id
                    JOIN collection_country c ON m.country_id = c.id
                    WHERE d.cart_id = ? AND c.caliber_id = ?
                """, (cart_id, caliber_id))
            elif table == 'collection_variation':
                cursor.execute(f"""
                    SELECT v.id, h.manufacturer_id
                    FROM {table} v
                    LEFT JOIN collection_load l ON v.load_id = l.id
                    LEFT JOIN collection_date d ON v.date_id = d.id
                    LEFT JOIN collection_load l2 ON d.load_id = l2.id
                    LEFT JOIN collection_headstamp h ON 
                        CASE 
                            WHEN l.id IS NOT NULL THEN l.headstamp_id
                            ELSE l2.headstamp_id
                        END = h.id
                    JOIN collection_manufacturer m ON h.manufacturer_id = m.id
                    JOIN collection_country c ON m.country_id = c.id
                    WHERE v.cart_id = ? AND c.caliber_id = ?
                """, (cart_id, caliber_id))
            
            record = cursor.fetchone()
            
            if not record:
                logger.error(f"No matching record found for cart_id: {cart_id}")
                error_count += 1
                continue
            
            # Create target directory path
            target_dir = os.path.join(media_dir, '9mmP', target_subdir)
            os.makedirs(target_dir, exist_ok=True)
            
            # Full target path (keep original filename)
            target_path = os.path.join(target_dir, source_file)
            
            # Relative path for database
            db_path = os.path.join('9mmP', target_subdir, source_file)
            
            # Copy the file
            shutil.copy2(os.path.join(source_dir, source_file), target_path)
            
            # Update database
            cursor.execute(
                f"UPDATE {table} SET image = ? WHERE id = ?",
                (db_path, record['id'])
            )
            
            conn.commit()
            success_count += 1
            logger.info(f"Successfully imported {target_subdir[:-1]} {cart_id} (ID: {record['id']}) - "
                        f"Source: {source_file} -> Target: {db_path}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error importing {cart_id}: {e}")
            error_count += 1
    
    logger.info(f"Load/Date/Variation import complete. Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}")
    return True

def import_box_images(conn, source_dir, media_dir, caliber_id):
    """Import box images into the database."""
    cursor = conn.cursor()
    
    # Process each source image file
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for source_file in os.listdir(source_dir):
        if not (source_file.lower().endswith('.png') or 
                source_file.lower().endswith('.jpg') or 
                source_file.lower().endswith('.jpeg')):
            continue
            
        # Extract bid from filename (remove extension)
        bid = os.path.splitext(source_file)[0]
        
        try:
            # Get the box from the database that belongs to the 9mmP caliber
            cursor.execute("""
                SELECT b.id, b.content_type_id, b.object_id
                FROM collection_box b
                WHERE b.bid = ? AND EXISTS (
                    -- Join with relevant tables to find boxes related to 9mmP
                    SELECT 1 FROM collection_country c
                    JOIN django_content_type ct ON ct.id = b.content_type_id
                    WHERE (
                        -- Direct country relationship
                        (ct.model = 'country' AND b.object_id = c.id AND c.caliber_id = ?)
                        -- Or through other relationships that we'll expand below
                    )
                    
                    UNION
                    
                    SELECT 1 FROM collection_manufacturer m
                    JOIN collection_country c ON m.country_id = c.id
                    JOIN django_content_type ct ON ct.id = b.content_type_id
                    WHERE ct.model = 'manufacturer' AND b.object_id = m.id AND c.caliber_id = ?
                    
                    UNION
                    
                    SELECT 1 FROM collection_headstamp h
                    JOIN collection_manufacturer m ON h.manufacturer_id = m.id
                    JOIN collection_country c ON m.country_id = c.id
                    JOIN django_content_type ct ON ct.id = b.content_type_id
                    WHERE ct.model = 'headstamp' AND b.object_id = h.id AND c.caliber_id = ?
                    
                    UNION
                    
                    SELECT 1 FROM collection_load l
                    JOIN collection_headstamp h ON l.headstamp_id = h.id
                    JOIN collection_manufacturer m ON h.manufacturer_id = m.id
                    JOIN collection_country c ON m.country_id = c.id
                    JOIN django_content_type ct ON ct.id = b.content_type_id
                    WHERE ct.model = 'load' AND b.object_id = l.id AND c.caliber_id = ?
                    
                    UNION
                    
                    SELECT 1 FROM collection_date d
                    JOIN collection_load l ON d.load_id = l.id
                    JOIN collection_headstamp h ON l.headstamp_id = h.id
                    JOIN collection_manufacturer m ON h.manufacturer_id = m.id
                    JOIN collection_country c ON m.country_id = c.id
                    JOIN django_content_type ct ON ct.id = b.content_type_id
                    WHERE ct.model = 'date' AND b.object_id = d.id AND c.caliber_id = ?
                    
                    UNION
                    
                    SELECT 1 FROM collection_variation v
                    LEFT JOIN collection_load l ON v.load_id = l.id
                    LEFT JOIN collection_date d ON v.date_id = d.id
                    LEFT JOIN collection_load l2 ON d.load_id = l2.id
                    JOIN collection_headstamp h ON 
                        CASE 
                            WHEN l.id IS NOT NULL THEN l.headstamp_id
                            ELSE l2.headstamp_id
                        END = h.id
                    JOIN collection_manufacturer m ON h.manufacturer_id = m.id
                    JOIN collection_country c ON m.country_id = c.id
                    JOIN django_content_type ct ON ct.id = b.content_type_id
                    WHERE ct.model = 'variation' AND b.object_id = v.id AND c.caliber_id = ?
                )
            """, (bid, caliber_id, caliber_id, caliber_id, caliber_id, caliber_id, caliber_id))
            
            box = cursor.fetchone()
            
            if not box:
                logger.error(f"No matching box found for bid: {bid}")
                error_count += 1
                continue
            
            # Create target directory path
            target_dir = os.path.join(media_dir, '9mmP', 'boxes')
            os.makedirs(target_dir, exist_ok=True)
            
            # Full target path (keep original filename)
            target_path = os.path.join(target_dir, source_file)
            
            # Relative path for database
            db_path = os.path.join('9mmP', 'boxes', source_file)
            
            # Copy the file
            shutil.copy2(os.path.join(source_dir, source_file), target_path)
            
            # Update database
            cursor.execute(
                "UPDATE collection_box SET image = ? WHERE id = ?",
                (db_path, box['id'])
            )
            
            conn.commit()
            success_count += 1
            logger.info(f"Successfully imported box {bid} (ID: {box['id']}) - "
                        f"Source: {source_file} -> Target: {db_path}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error importing box {bid}: {e}")
            error_count += 1
    
    logger.info(f"Box import complete. Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}")
    return True

def main():
    """Main function to run the import process."""
    args = parse_arguments()
    
    # Validate source directory
    if not os.path.isdir(args.source):
        logger.error(f"Source directory doesn't exist: {args.source}")
        sys.exit(1)
    
    # Connect to the database
    conn = connect_to_database(args.db)
    
    # Get the caliber ID for 9mmP
    caliber_id = get_caliber_id(conn)
    if not caliber_id:
        logger.error("Caliber '9mmP' not found in the database")
        sys.exit(1)
    
    logger.info(f"Starting import for type: {args.type}, source: {args.source}")
    
    try:
        if args.type == "headstamp":
            success = import_headstamp_images(conn, args.source, args.media, caliber_id)
        elif args.type == "load":
            success = import_load_images(conn, args.source, args.media, caliber_id)
        elif args.type == "box":
            success = import_box_images(conn, args.source, args.media, caliber_id)
        else:
            logger.error(f"Invalid type: {args.type}")
            success = False
            
        if success:
            logger.info(f"Import completed successfully for type: {args.type}")
        else:
            logger.error(f"Import failed for type: {args.type}")
            
    except Exception as e:
        logger.error(f"An error occurred during import: {e}")
        conn.close()
        sys.exit(1)
        
    conn.close()
    logger.info("Import process completed")

if __name__ == "__main__":
    main()
