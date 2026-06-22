import sqlite3
import os
from config import DATABASE_URL

db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Clear onboarding tasks
cur.execute("DELETE FROM onboarding_tasks")
tasks_deleted = cur.rowcount

# Clear onboarding
cur.execute("DELETE FROM onboarding")
onboarding_deleted = cur.rowcount

conn.commit()
conn.close()

print(f"Cleared {onboarding_deleted} onboarding records and {tasks_deleted} onboarding tasks.")
