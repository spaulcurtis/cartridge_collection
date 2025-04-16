# cartridge_collection
Web application for the display and management of a cartridge collection.

This is a [Django](https://www.djangoproject.com/) based web application for a cartridge collection management through a standard browser. The program includes an SQL database as well as views and templates to display and manipulate the data.  This is actually the 4th (and hopefully final) version of the program.  It originated from Lewis Curtis's original (memory and keystroke constrained) Turbo Pascal program from the 1980s.  In early 2020's it was rewritten as a Python/SQLite/tkinter program by Paul Curtis while learning Python for the first time.  Leveraging AI LLMs, Paul rewrote this as a backwards-compatible Django web abb.  In this final version we are also leveraging LLMs, but we're giving up on complete backwads compatibility and rebuilding from the ground up.  It should maintain a very similar UI/UX to the previous web app, but the database schema and infrastructure will be modern and brand new.

## Deployment
This program is current deployed on render at:
[curtis-ammo.onrender.com](https://curtis-ammo.onrender.com)

## To Do List
Extensions and improvements to the application

#### Manage sources

* The user can add existing source to records, but they must go to the Admin page to add new sources. 
Need to support a better source management interview

#### Better image management

* Automate image deletion from media directory with record delection or image removal. 
* File system management.  Limit file sizes and/or automatically resize images on upload.
* Admin view to see media directory size vs available storage on deployment platform.
* Orphaned image cleanup
* Image deduplication, and allow multiple records to point to the same file.
* Image browsing capability

#### Logging

* Add logging for debug.

