"""
Run Interview Status Migration
Adds interview_status and timestamp columns to interview_sessions table
"""
import sqlite3
import os
from pathlib import Path

# Get database path from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/recruitment.db")
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

# Also migrate the interview app database if using shared DB
INTERVIEW_DB_PATH = "Multi-Round-Assesment (3)/Multi-Round-Assesment/data/recruitment.db"

def run_migration(db_path: str):
    """Run the migration on a database file."""
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n📊 Migrating database: {db_path}")
        
        # Check if interview_sessions table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='interview_sessions'
        """)
        
        if not cursor.fetchone():
            print("⚠️  interview_sessions table does not exist yet")
            conn.close()
            return False
        
        # Add interview_status column
        try:
            cursor.execute("""
                ALTER TABLE interview_sessions 
                ADD COLUMN interview_status VARCHAR(20) DEFAULT 'PENDING'
            """)
            print("✅ Added interview_status column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓  interview_status column already exists")
            else:
                raise
        
        # Add invited_at column
        try:
            cursor.execute("""
                ALTER TABLE interview_sessions 
                ADD COLUMN invited_at DATETIME
            """)
            print("✅ Added invited_at column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓  invited_at column already exists")
            else:
                raise
        
        # Add started_at column
        try:
            cursor.execute("""
                ALTER TABLE interview_sessions 
                ADD COLUMN started_at DATETIME
            """)
            print("✅ Added started_at column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("✓  started_at column already exists")
            else:
                raise
        
        # Update existing records to set invited_at from created_at
        cursor.execute("""
            UPDATE interview_sessions 
            SET invited_at = created_at 
            WHERE invited_at IS NULL AND created_at IS NOT NULL
        """)
        updated = cursor.rowcount
        if updated > 0:
            print(f"✅ Updated {updated} existing records with invited_at")
        
        # Create indexes
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_interview_status 
                ON interview_sessions(interview_status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_interview_candidate 
                ON interview_sessions(candidate_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_interview_job 
                ON interview_sessions(job_id)
            """)
            print("✅ Created indexes")
        except Exception as e:
            print(f"⚠️  Index creation: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Migration completed successfully for {db_path}\n")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed for {db_path}: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Interview Status Migration")
    print("=" * 60)
    
    success_count = 0
    
    # Migrate main database
    if run_migration(DB_PATH):
        success_count += 1
    
    # Migrate interview app database if it exists
    if Path(INTERVIEW_DB_PATH).exists():
        if run_migration(INTERVIEW_DB_PATH):
            success_count += 1
    else:
        print(f"ℹ️  Interview app database not found: {INTERVIEW_DB_PATH}")
    
    print("=" * 60)
    if success_count > 0:
        print(f"✅ Migration completed successfully on {success_count} database(s)")
    else:
        print("❌ Migration failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
