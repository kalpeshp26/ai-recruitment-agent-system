import sqlite3
conn=sqlite3.connect('data/recruitment.db')
cur=conn.cursor()
rows=list(cur.execute("PRAGMA table_info('applications')"))
print(rows)
conn.close()
