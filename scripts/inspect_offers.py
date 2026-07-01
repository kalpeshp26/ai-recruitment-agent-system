import sqlite3
conn=sqlite3.connect('data/recruitment.db')
cur=conn.cursor()
rows=list(cur.execute("PRAGMA table_info('offers')"))
print(rows)
conn.close()
