import sqlite3
import json

conn = sqlite3.connect('data/recruitment.db')
cur = conn.cursor()

def dump_table(name):
    print(f"\n=== {name} ===")
    try:
        cur.execute(f"SELECT * FROM {name}")
        cols = [description[0] for description in cur.description]
        rows = cur.fetchall()
        for r in rows[:10]:
            print(dict(zip(cols, r)))
    except Exception as e:
        print("Error:", e)

dump_table("jobs")
dump_table("candidates")
dump_table("applications")
dump_table("chatbot_sessions")
dump_table("interview_sessions")
dump_table("offers")
dump_table("onboarding")

conn.close()
