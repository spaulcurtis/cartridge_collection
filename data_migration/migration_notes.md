# Notes on migration

## Extensible Lookup Tables

I entered these by hand after using a python script to find all unique values in the existing database.
I entered the "leagacy_values" as json.  I was told "your parsing code would be"

'''

    import json
    legacy_values = json.loads(lookup_record.legacy_mappings)
'''

This was AI telling me what do do before I decided to use JSON.  Migration Logic: When migrating data, your script would use these mappings to convert old values to new references:

'''

    def get_case_type_for_legacy_value(legacy_value):
        """Find the CaseType object that matches a legacy value"""
        for case_type in CaseType.objects.all():
            if not case_type.legacy_mappings:
                continue
                
            # Check if the legacy value matches any of the mapped values
            legacy_values = [v.strip() for v in case_type.legacy_mappings.split(',')]
            if legacy_value in legacy_values:
                return case_type
                
        # If no match found, create a new one or use a default
        return CaseType.objects.get_or_create(
            value=legacy_value.lower(),
            display_name=legacy_value,
            is_common=False
        )[0]

'''


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

## Migrating Manufacturer

The new database schema requires country/man code compbo to be unique.  It wasn't, since US had two RMIs.  I renamed one to RMI2 (it had no children).  The AI said it changed the program to gracefully handle this and just note in log file, but I don't think it did correctly.

If you need to start from scratch on manuf input use SQLite command line:

sqlite3 /Users/paulcurtis/Development/cartridge_collection/cartridge_collection/db.sqlite3

DELETE FROM collection_manufacturer;

DELETE FROM sqlite_sequence WHERE name='collection_manufacturer';

The third line resets the auto-index counter so the next import will start at 1.

## Current Status

The migration scripts are not finalized, but good enough to import data for development down to Load.  Still need Date, Variation, and Box migration.
For Poppy's real data import:

1. Clean up source database Load Type ("HS Only" for anything with blank)
2. rename the second SMI to SMI2
3. Leave contries
4. Use data_migration scripts to pull in country and manufacturer.  If you redo, don't forget to reset indexes.
5. Use web app to pull in Headstamp and Load

Longer term migration clean up
1. Fix default for load_type
2. Pull all migration into web app (vs data migration scripts)
3. Correctly handle "replace" including reseting indexes.
4. Add spreadsheets and other formats



