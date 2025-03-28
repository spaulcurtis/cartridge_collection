import sqlite3
import os

def reset_tables(database_path):
    # Tables to clear and reset
    tables_to_reset = [
        'collection_box',
        'collection_boxsource',
        'collection_country',
        'collection_date',
        'collection_datesource',
        'collection_headstamp',
        'collection_headstampsource',
        'collection_load',
        'collection_loadsource',
        'collection_manufacturer',
        'collection_source',
        'collection_variation',
        'collection_variationsource'
    ]

    # Connect to the SQLite3 database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        for table in tables_to_reset:
            # Delete all records from the table
            cursor.execute(f'DELETE FROM {table};')
            # Reset the auto-index
            cursor.execute(f'DELETE FROM sqlite_sequence WHERE name = "{table}";')
            print(f"Table '{table}' cleared and auto-index reset.")

        # Commit changes
        conn.commit()
        print("All specified tables have been reset successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        conn.close()


if __name__ == "__main__":
    # Path to your SQLite3 database
    database_path = '/Users/paulcurtis/Development/cartridge_collection/cartridge_collection/db.sqlite3'
    
    if not os.path.exists(database_path):
        print(f"Database not found at: {database_path}")
    else:
        reset_tables(database_path)
