import sqlite3

def main():
    conn = sqlite3.connect('data/recruitment.db')
    cur = conn.cursor()
    
    # Delete candidates starting with "Test"
    cur.execute("DELETE FROM candidates WHERE name LIKE 'Test%'")
    print(f"Deleted {cur.rowcount} candidates starting with 'Test'")
    
    # Delete applications for deleted candidates
    cur.execute("DELETE FROM applications WHERE candidate_id NOT IN (SELECT id FROM candidates)")
    print(f"Deleted {cur.rowcount} orphaned applications")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
