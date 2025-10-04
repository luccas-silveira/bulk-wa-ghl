#!/usr/bin/env python3
"""
Migration runner script for executing SQL migration files
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

def get_database_connection():
    """Create a database connection from DATABASE_URL environment variable"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("Please create a .env file with DATABASE_URL=postgresql://user:password@host:port/database")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except psycopg2.Error as e:
        print(f"❌ ERROR: Failed to connect to database")
        print(f"Details: {e}")
        sys.exit(1)

def run_sql_file(conn, sql_file_path):
    """Execute a SQL file"""
    if not os.path.exists(sql_file_path):
        print(f"❌ ERROR: SQL file not found: {sql_file_path}")
        sys.exit(1)

    print(f"\n📄 Reading SQL file: {sql_file_path}")
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()

    print(f"📝 Executing migration...")
    cursor = conn.cursor()
    try:
        cursor.execute(sql_content)
        conn.commit()
        print(f"✅ Migration executed successfully!")
        return True
    except psycopg2.Error as e:
        conn.rollback()
        print(f"❌ ERROR: Migration failed")
        print(f"Details: {e}")
        return False
    finally:
        cursor.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file.sql>")
        print("\nAvailable migrations:")
        migrations_dir = Path(__file__).parent / "migrations"
        if migrations_dir.exists():
            for sql_file in sorted(migrations_dir.glob("*.sql")):
                print(f"  - {sql_file.name}")
        sys.exit(1)

    migration_file = sys.argv[1]

    # If just filename provided, look in migrations directory
    if not os.path.exists(migration_file):
        migrations_dir = Path(__file__).parent / "migrations"
        migration_file = migrations_dir / migration_file

    print("=" * 70)
    print("🚀 Database Migration Runner")
    print("=" * 70)

    conn = get_database_connection()
    print(f"✅ Connected to database: {os.getenv('DATABASE_URL').split('@')[1]}")

    success = run_sql_file(conn, str(migration_file))

    conn.close()
    print("\n" + "=" * 70)

    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
