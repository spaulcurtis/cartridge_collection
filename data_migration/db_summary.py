import sqlite3
import os

def check_table_row_counts(database_path):
    # Connect to the SQLite3 database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        # Fetch all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("No tables found in the database.")
            return

        print("Row Counts for All Tables:")
        print("----------------------------------")
        for (table_name,) in tables:
            # Fetch row count for each table
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            print(f"{table_name}: {row_count} rows")

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
        check_table_row_counts(database_path)
