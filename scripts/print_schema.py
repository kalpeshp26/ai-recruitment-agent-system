import sqlite3
conn=sqlite3.connect('dev.db')
cur=conn.cursor()
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    name=row[0]
    print('\nTABLE:', name)
    for col in cur.execute(f"PRAGMA table_info('{name}')"):
        print(col)
conn.close()
