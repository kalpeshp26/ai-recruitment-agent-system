import sqlite3
conn = sqlite3.connect('data/recruitment.db')
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("Tables:", tables)
for t in tables:
    try:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f" - {t}: {count} rows")
    except Exception as e:
        print(f" - {t}: error {e}")
conn.close()
