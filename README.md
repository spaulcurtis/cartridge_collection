# cartridge_collection
Web application for the display and management of a cartridge collection.

This is a [Django](https://www.djangoproject.com/) based web application for a cartridge collection management through a standard browser. The program includes an SQL database as well as views and templates to display and manipulate the data.  This is actually the 4th (and hopefully final) version of the program.  It originated from Lewis Curtis's original (memory and keystroke constrained) Turbo Pascal program from the 1980s.  In early 2020's it was rewritten as a Python/SQLite/tkinter program by Paul Curtis while learning Python for the first time.  Leveraging AI LLMs, Paul rewrote this as a backwards-compatible Django web abb.  In this final version we are also leveraging LLMs, but we're giving up on complete backwads compatibility and rebuilding from the ground up.  It should maintain a very similar UI/UX to the previous web app, but the database schema and infrastructure will be modern and brand new.

## Development Notes

### To Do

notes are squished up against the Notes: line above (at least in dates)

#### Logging

Add logging for debug.

#### Recently viewed

Update Dashboard recently to be latest edits.
Maybe compress Dashboard.

#### Robustly handling unique constrain violations

 (two man codes in same country, for example)

#### Manage sources

You can add headstampsource, but not a new source.
Where do we do this?  It's own screen, or when editing any other record?

#### Country Description

Add country description that can be used to clarify what records are under this country from the historical perspective of the country.

#### Tests


