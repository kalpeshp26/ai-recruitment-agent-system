import sqlite3
conn = sqlite3.connect('data/recruitment.db')
cur = conn.cursor()

cur.execute("SELECT candidate_id FROM applications WHERE id='47f0f664-16c8-4de7-a66b-8adee27ba32b'")
print("App Candidate ID:", cur.fetchone())

cur.execute("SELECT name FROM candidates WHERE id IN (SELECT candidate_id FROM applications WHERE id='47f0f664-16c8-4de7-a66b-8adee27ba32b')")
print("Candidate Name:", cur.fetchone())

conn.close()
