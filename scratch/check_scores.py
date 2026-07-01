import sqlite3
conn = sqlite3.connect('data/recruitment.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(scores)")
for row in cursor.fetchall():
    print(row)
conn.close()
