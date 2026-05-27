import sqlite3, json
conn=sqlite3.connect('data/recruitment.db')
cur=conn.cursor()
rows = list(cur.execute("PRAGMA table_info('interviews')"))
print(rows)
conn.close()
