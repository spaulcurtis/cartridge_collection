# Django Database Management Guide - MacBook

This guide provides quick reference for managing PostgreSQL and SQLite databases for your Django project on macOS.

## Current Configuration

Your Django project is set up to use environment variables to determine which database to use:

1. **PostgreSQL** - Used when `USE_POSTGRES=True` is set
2. **SQLite** - Used as fallback when PostgreSQL is not configured

## PostgreSQL Management

### Starting and Stopping PostgreSQL

```bash
# Check if PostgreSQL is running
brew services list

# Start PostgreSQL
brew services start postgresql@16

# Stop PostgreSQL
brew services stop postgresql@16

# Restart PostgreSQL
brew services restart postgresql@16

# Run without auto-start (stops when computer shuts down)
pg_ctl -D /usr/local/var/postgres start
```

### PostgreSQL Connection Parameters

Your current configuration uses these parameters:
- Database: `cartridge_collection`
- User: `django_user`
- Password: [Your secure password]
- Host: `localhost`
- Port: `5432`

### Connecting to PostgreSQL Directly

```bash
# Connect to your database
psql -U django_user -d cartridge_collection

# Change password if needed
ALTER USER django_user WITH PASSWORD 'new_secure_password';
```

## Switching Between Databases

### Using PostgreSQL

1. Ensure PostgreSQL is running: `brew services list`
2. Make sure your `.env` file has:
   ```
   USE_POSTGRES=True
   DB_NAME=cartridge_collection
   DB_USER=django_user
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```
3. Run your Django app: `python manage.py runserver`

### Using SQLite

1. You can simply change your `.env` file to:
   ```
   USE_POSTGRES=False
   ```
   (or remove the `USE_POSTGRES` line entirely)

2. Run your Django app: `python manage.py runserver`

## Database Migrations

When switching between databases or making model changes:

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations to current database
python manage.py migrate

# Create a superuser if needed
python manage.py createsuperuser
```

## Security Best Practices

1. **Keep `.env` out of Git**:
   - Ensure `.env` is in your `.gitignore`
   - Use `.env.example` for structure without real credentials

2. **Change your password** if you accidentally committed it to Git

3. **For local dev only**: Consider using environment variables instead of `.env` file:
   ```bash
   USE_POSTGRES=True DB_PASSWORD=your_password python manage.py runserver
   ```

## Render Deployment

On Render, database credentials are managed through environment variables in the Render dashboard. Your Django app uses the `DATABASE_URL` environment variable that Render provides automatically.
