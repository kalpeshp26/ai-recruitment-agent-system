import requests

# 1. Start prescreening session
print("Starting session...")
r = requests.post('http://localhost:8000/api/prescreening/start-session', json={'candidate_id': 'dba79514-664'})
res = r.json()
print("Start Session Response:", res)
session_id = res['session_id']
questions = res['questions']

# 2. Submit answers to PASS prescreening
print("Submitting answers...")
answers = []
sample_answers = [
    'I want to join as a Web Developer since I love creating responsive and fast web applications.',
    'My recent project was a recruitment portal UI built with React and integrated with FastAPI.',
    'I regularly read articles on Medium, dev.to, and follow JavaScript Weekly newsletter.',
    'I organize my work by breaking down tasks and keeping the team updated with daily updates.',
    'My salary expectation is standard, about 80,000 INR per month, matching my experience.',
    'I am ready to start immediately since I have already completed my current project.'
]
for i, q in enumerate(questions):
    answers.append({
        'question_index': i,
        'question': q['question'],
        'answer': sample_answers[i]
    })

r2 = requests.post('http://localhost:8000/api/prescreening/submit-answers', json={
    'session_id': session_id,
    'answers': answers
})
res2 = r2.json()
print('Submit Answers Result:', res2)
