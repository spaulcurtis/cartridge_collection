# Cartridge Collection - Django Application

## What This Is

A Django web application for cataloging and managing an ammunition/cartridge collection.
Originally a 1980s Turbo Pascal desktop program, modernized to Django 5.1.

## Domain Model

The data is organized in a strict hierarchy:

```
Caliber (e.g., 9mm, .45 ACP)
  → Country (country of origin)
    → Manufacturer
      → Headstamp (markings on the cartridge base, has image)
        → Load (individual cartridge, ID format: L1, L2, ...)
          ├→ Variation (Load Variation — the more common case, V1, V2, ...)
          └→ Date (date/lot variant, ID format: D1, D2, ...)
               └→ Variation (Date Variation, same model, V1, V2, ...)
```

**Variation has two parent types**: A single `Variation` model serves double duty. It has
both a `load` FK and a `date` FK — exactly one is set. Most Variations are **Load Variations**
(direct children of a Load). Less commonly, a Variation is a **Date Variation** (child of a
Date, which is itself under a Load). This means Variation-related code (views, forms, URLs,
templates) must always account for both parent paths. There are separate create URLs:
`variation_create_for_load` and `variation_create_for_date`.

**Box** is a separate special entity that can attach to any level in the hierarchy via Django's
GenericForeignKey (ContentType framework). Box IDs use format: B1, B2, ...

Cart IDs (L/D/V/B) are auto-generated and unique per caliber.

## Key Domain Terms

- **Headstamp**: the stamped markings on the base of a cartridge case
- **Load**: a specific cartridge (the primary collectible item)
- **Cart ID**: the collection catalog identifier (L1, D1, V1, B1)
- **Credibility code**: 1-5 rating of information reliability
- **Source**: a reference/information source linked to items via junction tables
- **Confidential notes**: text wrapped in `{{double braces}}` — hidden from public view

## Users

The primary user is an expert cartridge collector — one of the world's foremost authorities
on 9mm ammunition — who is elderly and not comfortable with modern computer interfaces. The
Django app was deliberately designed to mirror the drill-down workflows of his original Pascal
program (Country → Manufacturer → Headstamp → Load, etc.) because that mental model is
deeply familiar to him. **Navigation simplicity is critical** — even small UX friction points
cause real difficulty.

The planned LLM enhancements (natural language help and natural language querying) are
significantly motivated by making the app more accessible to users who find traditional
navigation challenging.

There are three user tiers:
- **Primary user**: full read/write access, authenticated
- **Credentialed users**: other collectors/researchers, authenticated, read/write access
- **Anonymous visitors**: unauthenticated, read-only browsing of the collection

## Architecture

- **Framework**: Django 5.1.7, function-based views throughout (no class-based views)
- **Frontend**: Bootstrap 5 with per-caliber theme colors (CSS variables)
- **Database**: PostgreSQL on Render (production), SQLite3 locally (default)
- **No REST API**: all views return HTML via Django templates
- **Auth**: Django built-in authentication, login required for most views

### Project Layout

```
cartridge_collection/          # Django project settings
  settings.py                  # Database switching via env vars
  urls.py                      # Root URL config (includes collection.urls)

collection/                    # Main (only) app
  models.py                    # All 23 models (~1150 lines)
  views/                       # 12 view modules, 82+ view functions
    common_views.py            # Landing, dashboard, add_artifact
    search_views.py            # All search functionality (~67KB)
    country_views.py           # Country CRUD
    manufacturer_views.py      # Manufacturer CRUD + move
    headstamp_views.py         # Headstamp CRUD + move + sources
    load_views.py              # Load CRUD + move + sources
    date_views.py              # Date CRUD + sources
    variation_views.py         # Variation CRUD + sources
    box_views.py               # Box CRUD + move + sources (GenericFK)
    import_views.py            # Bulk import (~104KB)
    ref_views.py               # Reference materials (9mm guide, highlights)
  forms/                       # 9 form modules
  templates/collection/        # 45+ templates (extends app_base.html)
  static/collection/           # CSS, images
  utils/note_utils.py          # Confidential note processing
  management/commands/          # Utility management commands

media/                         # User-uploaded images (not in git)
data_migration/                # Legacy database migration scripts
```

### URL Pattern

All collection URLs are prefixed with `<str:caliber_code>/`:
- `/<caliber>/` — dashboard
- `/<caliber>/countries/` — country list
- `/<caliber>/manufacturers/<id>/` — manufacturer detail
- `/<caliber>/loads/<id>/` — load detail
- etc.

### Database Configuration (settings.py)

Priority order:
1. `DATABASE_URL` env var → uses `dj-database-url` (Render production)
2. `USE_POSTGRES=True` env var → explicit PostgreSQL credentials
3. Default → SQLite3 at `db.sqlite3` (local development)

No `.env` file is needed for local SQLite development.

## Development Environment

- **Python**: 3.10+ required (Django 5.1 minimum)
- **Virtual environment**: `venv/` in project root (in .gitignore)
- **Activate**: `source venv/bin/activate`
- **Run server**: `python manage.py runserver`
- **Migrations**: `python manage.py migrate`
- **Dependencies**: `pip install -r requirements.txt`

## Deployment

- **Host**: Render.com
- **Config**: `render.yaml` + `build.sh`
- **Server**: Gunicorn
- **Static files**: WhiteNoise with compression
- **Media**: Persistent disk at `/opt/render/project/src/media`

## Conventions

- All views are function-based — do not introduce class-based views
- Models use abstract base classes: `BaseEntity`, `BaseCollectionItem`
- Image paths are auto-generated based on the entity's position in the hierarchy
- Templates inherit from `app_base.html` (which extends `base.html`)
- Forms are Django ModelForms in `collection/forms/`
- The `Box` model uses GenericForeignKey to attach to any parent entity type
- Lookup tables (LoadType, BulletType, etc.) have an `is_common` flag for UI filtering

## Testing

No test suite currently exists. When testing changes, run the development server
and verify manually in the browser.
