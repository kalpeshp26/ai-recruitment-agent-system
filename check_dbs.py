import sqlite3

print("=== MAIN DATABASE ===")
conn1 = sqlite3.connect('data/recruitment.db')
c1 = conn1.cursor()
c1.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables1 = [r[0] for r in c1.fetchall()]
print("Tables:", ", ".join(tables1))

print("\n=== INTERVIEW DATABASE ===")
conn2 = sqlite3.connect('Multi-Round-Assesment (3)/Multi-Round-Assesment/data/recruitment.db')
c2 = conn2.cursor()
c2.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables2 = [r[0] for r in c2.fetchall()]
print("Tables:", ", ".join(tables2))

print("\n=== COMMON TABLES ===")
common = set(tables1) & set(tables2)
print("Common:", ", ".join(common) if common else "None")

print("\n=== MAIN ONLY ===")
main_only = set(tables1) - set(tables2)
print("Main only:", ", ".join(main_only) if main_only else "None")

print("\n=== INTERVIEW ONLY ===")
interview_only = set(tables2) - set(tables1)
print("Interview only:", ", ".join(interview_only) if interview_only else "None")
