import sqlite3
import os
import logging


def setup_logging():
    logging.basicConfig(
        filename='old_database_preparation.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def prepare_old_database(database_path):
    if not os.path.exists(database_path):
        logging.error(f"Database not found at: {database_path}")
        print(f"Database not found at: {database_path}")
        return

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        # 1. Delete any Box record with a sup_id of 0
        cursor.execute("DELETE FROM Box WHERE sup_id = 0;")
        deleted_rows = cursor.rowcount
        logging.info(f"Deleted {deleted_rows} Box records with sup_id = 0.")

        # 2. Change Box records with sup_type of 'box' to 'country' and sup_id to 27, prepend note
        cursor.execute("UPDATE Box SET sup_type = 'country', sup_id = 27, note = 'MIGRATION: mislinked as box under box. ' || CASE WHEN note IS NULL OR note = '' THEN '' ELSE '\n' || note END WHERE sup_type = 'box';")
        updated_rows = cursor.rowcount
        logging.info(f"Updated {updated_rows} Box records with sup_type 'box' to 'country' and sup_id to 27 with note prepended.")

        # 3. Modify Load records with NULL or empty load_type to 'various'
        cursor.execute("UPDATE Load SET load_type = 'various' WHERE load_type IS NULL OR TRIM(load_type) = '';")
        modified_rows = cursor.rowcount
        logging.info(f"Updated {modified_rows} Load records with NULL or empty load_type to 'various'.")

        # 4. Validate and Fix Boxes with sup_type = 'var' (Check Variation existence)
        cursor.execute("SELECT var_id FROM Variation;")
        valid_variation_ids = {row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT box_id, sup_id, note FROM Box WHERE sup_type = 'var';")
        boxes_to_fix = cursor.fetchall()

        corrected_count = 0
        for box_id, sup_id, note in boxes_to_fix:
            if sup_id not in valid_variation_ids:
                new_note = f"MIGRATION: mislinked to a non-existent variation.\n{note}" if note else "MIGRATION: mislinked to a non-existent variation."
                cursor.execute("UPDATE Box SET sup_type = 'country', sup_id = 27, note = ? WHERE box_id = ?;", (new_note, box_id))
                corrected_count += 1

        logging.info(f"Corrected {corrected_count} Box records that were incorrectly linked to non-existent Variations.")

        # Commit the changes
        conn.commit()
        logging.info("Database preparation completed successfully.")
        print("Database preparation completed successfully.")
    except sqlite3.Error as e:
        logging.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    setup_logging()
    database_path = '/Users/paulcurtis/Development/cartridge_collection/cartridge_site/collect.sqlite'
    prepare_old_database(database_path)
