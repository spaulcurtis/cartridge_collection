# Notes on migration

## Extensible Lookup Tables

They're good

## Source Tables

Source Model System: Purpose and Benefits
The source models in your collection database serve an important purpose: they track where information about your collection items came from. This is especially valuable for a specialized collection where provenance and authenticity matter.
How the Source Models Work

Main Source table: This central table stores information about each source (e.g., reference books, catalogs, experts, auction houses).
Linking tables (HeadstampSource, LoadSource, etc.): These tables create many-to-many relationships between collection items and sources.

Example Usage Scenario
Let's say you've documented a rare headstamp based on information from multiple sources:

A reference in "Wilson's Headstamp Guide" (2005 edition)
Correspondence with expert John Smith in 2018
An auction catalog from Rock Island Auction

You'd create records like:
CopySource #1: "Wilson's Headstamp Guide (2005)"
Source #2: "John Smith (correspondence)"
Source #3: "Rock Island Auction Catalog #72"

HeadstampSource: 
- Headstamp: DA03J, Source: #1, Date: 2020-05-12, Note: "Confirms manufacturer as DAG"
- Headstamp: DA03J, Source: #2, Date: 2018-09-15, Note: "Smith identified special production run"
- Headstamp: DA03J, Source: #3, Date: 2019-03-20, Note: "Example sold for $450"
Why Separate Source Tables Are Beneficial

Granular attribution: Different aspects of an item might be sourced from different references. Example: manufacturer from one source, production date from another.
Source credibility tracking: You can note which sources provided which information, helping assess reliability.
Historical record: When new information conflicts with old, you maintain a history of how your understanding evolved.
Selective querying: Find all items from a particular source or all sources for a particular item.
Normalized data model: Following database best practices, many-to-many relationships are implemented with junction tables.
Flexible source annotation: The linking tables allow notes about the specific relationship between the source and the item.

## Migrating Country

I migrated the country records by using "migrate_country.py".  I then manually added the full_name.  I deleted United Arab Emerates (70) in favor of the UAE (74).  When migrating manufacturers, we need to point 70 to 74 (or was it vice versa?)

This was a mistake.  CLEAN UP COUNTRY ISSUES AFTER MIGRATION.

Country is now part of Django app import.

## Migrating Manufacturer

The new database schema requires country/man code compbo to be unique.  It wasn't, since US had two RMIs.  I renamed one to RMI2 (it had no children).  The AI said it changed the program to gracefully handle this and just note in log file, but I don't think it did correctly.

If you need to start from scratch on manuf input use SQLite command line:

sqlite3 /Users/paulcurtis/Development/cartridge_collection/cartridge_collection/db.sqlite3

DELETE FROM collection_manufacturer;

DELETE FROM sqlite_sequence WHERE name='collection_manufacturer';

The third line resets the auto-index counter so the next import will start at 1.

Manufacturer  is now part of Django app import.


## Current Status

First manually empty the target database readying it for migration.  Run "empty_for_migration.py"

Then prep the source database by running "old_db_prep_for_migration.py"  This will
Delete boxes with Sup ID of 0
Change load_type of blank or NULL to "various"
Move mis-linked boxes to UNK country.

Should have already renamed the second SMI to SMI2 and the second AP01B to AP01B-2

Use Web App to pull in each table.

After migration run the shell commands below to set legacy_id
python manage.py shell

from collection.models import Load, Date, Variation, Box

for obj in Load.objects.all():
    obj.legacy_id = obj.cart_id
    obj.save()

for obj in Date.objects.all():
    obj.legacy_id = obj.cart_id
    obj.save()

for obj in Variation.objects.all():
    obj.legacy_id = obj.cart_id
    obj.save()

for obj in Box.objects.all():
    obj.legacy_id = obj.bid
    obj.save()

Then you can clean up and improve Countries, potentially relinking UAE and deleting one.

/* Indexes for collection_manufacturer Table */
CREATE INDEX IF NOT EXISTS idx_collection_manufacturer_country_id ON collection_manufacturer (country_id);

/* Indexes for collection_headstamp Table */
CREATE INDEX IF NOT EXISTS idx_collection_headstamp_manufacturer_id ON collection_headstamp (manufacturer_id);

/* Indexes for collection_load Table */
CREATE INDEX IF NOT EXISTS idx_collection_load_headstamp_id ON collection_load (headstamp_id);

/* Indexes for collection_date Table */
CREATE INDEX IF NOT EXISTS idx_collection_date_load_id ON collection_date (load_id);

/* Indexes for collection_variation Table */
CREATE INDEX IF NOT EXISTS idx_collection_variation_load_id ON collection_variation (load_id);
CREATE INDEX IF NOT EXISTS idx_collection_variation_date_id ON collection_variation (date_id);

/* Indexes for collection_box Table (Generic Relation) */
CREATE INDEX IF NOT EXISTS idx_collection_box_content_type_id ON collection_box (content_type_id);
CREATE INDEX IF NOT EXISTS idx_collection_box_object_id ON collection_box (object_id);


