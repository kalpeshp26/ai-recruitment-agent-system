import sqlite3

conn = sqlite3.connect('data/recruitment.db')
cur = conn.cursor()

def q(sql):
    try:
        cur.execute(sql)
        res = cur.fetchone()
        return res[0] if res else 0
    except Exception as e:
        print(f"Error for {sql}: {e}")
        return 0

total_applicants = q("SELECT COUNT(*) FROM candidates")
shortlisted = q("SELECT COUNT(*) FROM candidates WHERE LOWER(status) NOT IN ('new', 'parsed', 'uploaded', 'duplicate', 'rejected')")

outreach_sent = q("SELECT COUNT(DISTINCT candidate_id) FROM communications")
if outreach_sent == 0:
    outreach_sent = q("SELECT COUNT(*) FROM candidates WHERE LOWER(status) IN ('outreach_sent', 'prescreening', 'prescreened', 'interview', 'selected', 'offered', 'accepted', 'joined')")
    
prescreening_passed = q("SELECT COUNT(DISTINCT candidate_id) FROM chatbot_sessions WHERE LOWER(status) IN ('completed', 'done', 'pass')")
if prescreening_passed == 0:
    prescreening_passed = q("SELECT COUNT(*) FROM candidates WHERE LOWER(status) IN ('prescreened', 'interview', 'selected', 'offered', 'accepted', 'joined')")
    
interviewed = q("SELECT COUNT(DISTINCT candidate_id) FROM interview_sessions")
if interviewed == 0:
    interviewed = q("SELECT COUNT(*) FROM candidates WHERE LOWER(status) IN ('interview', 'selected', 'offered', 'accepted', 'joined')")
    
selected = q("SELECT COUNT(DISTINCT candidate_id) FROM interview_sessions WHERE LOWER(status) IN ('complete', 'completed')")
if selected == 0:
    selected = q("SELECT COUNT(*) FROM candidates WHERE LOWER(status) IN ('selected', 'offered', 'accepted', 'joined')")
    
offered = q("SELECT COUNT(*) FROM offers")
accepted = q("SELECT COUNT(*) FROM offers WHERE LOWER(status)='accepted'")
joined = q("SELECT COUNT(*) FROM onboarding WHERE LOWER(status) IN ('it_provisioned', 'completed', 'joined')")

stages = [
    ("Applicants", total_applicants),
    ("Shortlisted", shortlisted),
    ("Outreach Sent", outreach_sent),
    ("Pre-screening Passed", prescreening_passed),
    ("Interviewed", interviewed),
    ("Selected", selected),
    ("Offered", offered),
    ("Accepted", accepted),
    ("Joined", joined),
]

logical_stages = []
prev_count = None
for stage_name, count in stages:
    if prev_count is not None:
        count = min(count, prev_count)
    logical_stages.append((stage_name, count))
    prev_count = count

print("=== RAW METRICS ===")
for k, v in stages:
    print(f"{k:25}: {v}")

print("\n=== CASCADING LOGICAL FUNNEL ===")
for k, v in logical_stages:
    print(f"{k:25}: {v}")

conn.close()
