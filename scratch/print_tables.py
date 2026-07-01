import sqlite3

conn = sqlite3.connect('data/recruitment.db')
cur = conn.cursor()

def print_table(name):
    print(f"\n=== {name.upper()} ===")
    try:
        cur.execute(f"SELECT * FROM {name}")
        cols = [description[0] for description in cur.description]
        print("Columns:", cols)
        for row in cur.fetchall():
            print(dict(zip(cols, row)))
    except Exception as e:
        print(f"Error reading {name}: {e}")

print_table("applications")
print_table("offers")
print_table("onboarding")
print_table("candidates")
print_table("audit_log")

conn.close()
