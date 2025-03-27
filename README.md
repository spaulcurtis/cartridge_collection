# cartridge_collection
Web application for the display and management of a cartridge collection.

This is a [Django](https://www.djangoproject.com/) based web application for a cartridge collection management through a standard browser. The program includes an SQL database as well as views and templates to display and manipulate the data.  This is actually the 4th (and hopefully final) version of the program.  It originated from Lewis Curtis's original (memory and keystroke constrained) Turbo Pascal program from the 1980s.  In early 2020's it was rewritten as a Python/SQLite/tkinter program by Paul Curtis while learning Python for the first time.  Leveraging AI LLMs, Paul rewrote this as a backwards-compatible Django web abb.  In this final version we are also leveraging LLMs, but we're giving up on complete backwads compatibility and rebuilding from the ground up.  It should maintain a very similar UI/UX to the previous web app, but the database schema and infrastructure will be modern and brand new.

### Development Notes

#### Add to database a Table for Collection Name and Description. 
✅ Approach 2: Using App List Template Override (Recommended for Your Case)
Django allows overriding the default app_index.html template. With this method, you can display models under categories and control their order.

Example: Custom Grouping in Admin Interface
Let's say you want the following categories:

General Information: CollectionInfo

Lookup Tables: LoadType, BulletType, CaseType, PrimerType, PAColor

Entities: Caliber, Source, Country, Manufacturer, Headstamp

Collection Items: Load, Date, Variation, Box

Sources: HeadstampSource, LoadSource, DateSource, VariationSource, BoxSource

