import sqlite3
import os

db_path = os.path.join("data", "recruitment.db")
if not os.path.exists(db_path):
    print("Database path not found at:", db_path)
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, skills, experience_min, qualification, location FROM jobs")
    rows = cursor.fetchall()
    print("--- Current Jobs in Database ---")
    for r in rows:
        print(f"ID: {r[0]} | Title: {r[1]} | Skills: {r[2]} | Exp Min: {r[3]} | Qual: {r[4]} | Loc: {r[5]}")
    conn.close()
