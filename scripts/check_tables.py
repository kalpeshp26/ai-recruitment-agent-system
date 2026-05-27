import sqlite3
p='data/recruitment.db'
conn=sqlite3.connect(p)
cur=conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
rows=cur.fetchall()
print('File:', p)
print('Tables:', rows)
conn.close()
