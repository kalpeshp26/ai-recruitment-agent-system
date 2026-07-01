"""
--- FILE: backend/prompts.py ---

Prompts library copied verbatim from docs/INTERVIEW_PROMPTS_LIBRARY.md.
All prompt strings are exported as constants and must be used by services
instead of hardcoding prompt text elsewhere.
"""

# P1: Question Generation — HR Round
P1_SYSTEM_MESSAGE = """
You are IntelliHire's HR question generator. Produce a single, role-appropriate behavioral interview question in strict JSON. Avoid asking for PII. Keep question length under 200 words. Return `difficulty` as "easy"|"medium"|"hard" and `time_limit` in seconds. Do NOT include analysis or commentary.
"""

P1_USER_TEMPLATE = """
{
  "role":"{role}",
  "difficulty_hint":"{difficulty_hint}",
  "category":"hr",
  "history":[{ "q":"{last_q}", "a_summary":"{last_a_summary}" }],
  "constraints": { "no_pii": true, "max_length": 200 }
}
"""

P1_OUTPUT_SCHEMA = """
{
  "question_text":"string",
  "difficulty":"easy|medium|hard",
  "category":"hr",
  "time_limit": 90,
  "metadata": {"source":"groq"|"fallback"}
}
"""

# P2: Question Generation — Technical Round
P2_SYSTEM_MESSAGE = """
You are IntelliHire's technical question generator. Return exactly one JSON object with keys `question_text`, `difficulty`, `category`, `time_limit`, and `expected_keywords` (array of strings). The question must be solvable within the `time_limit` and scoped to `{role}`. Do not request code execution or external resources.
"""

P2_USER_TEMPLATE = """
{
  "role":"{role}",
  "difficulty_hint":"{difficulty_hint}",
  "category":"{category}",
  "history":[{ "q":"{last_q}", "a_summary":"{last_a_summary}" }],
  "constraints":{"no_pii":true}
}
"""

P2_OUTPUT_SCHEMA = """
{
  "question_text":"string",
  "difficulty":"easy|medium|hard",
  "category":"string",
  "time_limit":120,
  "expected_keywords":["keyword1","keyword2"],
  "metadata":{"source":"groq"|"fallback"}
}
"""

# P3: Question Generation — Follow-up (incomplete answer)
P3_SYSTEM_MESSAGE = """
You are IntelliHire's focused follow-up generator. Given the candidate's answer summary, generate a clarifying follow-up question that probes the missing piece. Output strict JSON.
"""

P3_USER_TEMPLATE = """
{
  "role":"{role}",
  "original_question":"{original_q}",
  "answer_summary":"{answer_summary}",
  "missing_part":"{missing_part_hint}",
  "difficulty_hint":"{difficulty_hint}"
}
"""

P3_OUTPUT_SCHEMA = """
{
  "question_text":"string",
  "difficulty":"easy|medium|hard",
  "category":"followup",
  "time_limit":60,
  "metadata":{"followup_for":"{question_id}"}
}
"""

# P4: Question Generation — Deeper Probe
P4_SYSTEM_MESSAGE = """
You are IntelliHire's deep-probe generator. Produce one deeper probing question that requires multi-step reasoning or design. Use JSON only.
"""

P4_USER_TEMPLATE = """
{
  "role":"{role}",
  "context_summary":"{3-line_summary}",
  "difficulty_hint":"hard",
  "area":"{category}"
}
"""

P4_OUTPUT_SCHEMA = """
{
  "question_text":"string",
  "difficulty":"hard",
  "category":"{category}",
  "time_limit":180,
  "metadata":{"probe_level":"deep"}
}
"""

# P5: Answer Evaluation — Full Rubric
P5_SYSTEM_MESSAGE = """
You are IntelliHire's structured answer evaluator. Evaluate the candidate answer against four dimensions: technical, communication, confidence, problem_solving. Return numeric scores 0–10 (float allowed to one decimal) and concise feedback for each. Also return `is_correct` boolean where applicable and a short `summary`. Output EXACT JSON.
"""

P5_USER_TEMPLATE = """
{
  "question_text":"{question_text}",
  "expected_keywords":["{kw1}","{kw2}"],
  "answer_text":"{answer_text}",
  "transcript":"{transcript_if_any}",
  "time_taken_ms":{time_taken_ms},
  "role":"{role}"
}
"""

P5_OUTPUT_SCHEMA = """
{
  "technical": 0.0,
  "communication": 0.0,
  "confidence": 0.0,
  "problem_solving": 0.0,
  "total": 0.0,
  "is_correct": true|false,
  "feedback": {
    "technical":"short string",
    "communication":"short string",
    "confidence":"short string",
    "problem_solving":"short string"
  },
  "summary":"short string"
}
"""

# P6: Answer Evaluation — Quick Score Only
P6_SYSTEM_MESSAGE = """
Provide compact numeric evaluation for the four dimensions and total only. Return JSON.
"""

P6_USER_TEMPLATE = """
{
  "question_text":"{question_text}",
  "answer_text":"{answer_text}",
  "role":"{role}"
}
"""

P6_OUTPUT_SCHEMA = """
{
  "technical":number,
  "communication":number,
  "confidence":number,
  "problem_solving":number,
  "total":number
}
"""

# P7: Session Summary Generation
P7_SYSTEM_MESSAGE = """
You are IntelliHire's session summarizer. Given the session's question/answer pairs and evaluation scores, produce a short executive summary (max 300 words) and identify strengths/weaknesses bullet list. Return JSON.
"""

P7_USER_TEMPLATE = """
{
  "session_id":"{session_id}",
  "qa_summaries":[{"q":"{q}", "a_summary":"{a_summary}", "scores":{"technical":x,...}}]
}
"""

P7_OUTPUT_SCHEMA = """
{
  "summary":"string",
  "strengths":["string","string"],
  "weaknesses":["string","string"]
}
"""

# P8: Feedback Generation (candidate-facing)
P8_SYSTEM_MESSAGE = """
Compose candidate-facing feedback using constructive tone. Use per-question feedback and aggregate comments. Return plain JSON with `short_feedback` and `detailed_feedback` (array per question).
"""

P8_USER_TEMPLATE = """
{
  "session_id":"{session_id}",
  "evaluation":{"technical":x,"communication":y,"confidence":z,"problem_solving":w,"final_score":v},
  "qa_details":[{"question_index":0,"feedback":{"technical":"...","communication":"..."}}]
}
"""

P8_OUTPUT_SCHEMA = """
{
  "short_feedback":"string (1-2 sentences)",
  "detailed_feedback":[{"question_index":0,"feedback":"string"}],
  "next_steps":"string"
}
"""

# P9: Fallback Question (when Groq fails)
P9_SYSTEM_MESSAGE = """
Select a safe, generic technical question from the fallback bank matching `difficulty_hint` and `category`. Return JSON.
"""

P9_USER_TEMPLATE = """
{
  "role":"{role}",
  "difficulty_hint":"{difficulty_hint}",
  "category":"{category}"
}
"""

P9_OUTPUT_SCHEMA = """
{
  "question_text":"string",
  "difficulty":"easy|medium|hard",
  "category":"string",
  "time_limit":120,
  "metadata":{"source":"fallback"}
}
"""

# Fallback question bank (10 per difficulty)
FALLBACK_QUESTIONS = {
    "easy": [
        "Explain the difference between a list and a set in Python.",
        "What is a RESTful API? Give one example.",
        "Describe how a SQL JOIN works in basic terms.",
        "What is a hash table and when would you use it?",
        "Explain the concept of time complexity O(n) vs O(log n).",
        "How does HTTP status code 404 differ from 500?",
        "What is the purpose of unit tests?",
        "Describe the difference between GET and POST requests.",
        "What is version control and why use it?",
        "Explain what a boolean value is and give an example."
    ],
    "medium": [
        "Implement an algorithm to detect a cycle in a linked list (describe approach).",
        "Explain database indexing and when to use composite indexes.",
        "Design a simple rate limiter for an API endpoint.",
        "How would you approach debugging a memory leak in a web service?",
        "Describe CAP theorem and its implications for distributed systems.",
        "Explain how to safely perform database migrations in production.",
        "Describe the producer-consumer problem and a solution using queues.",
        "Explain differences between SQL and NoSQL databases and use-cases.",
        "How would you design an upload service that supports large files?",
        "Discuss strategies for caching frequently accessed data."
    ],
    "hard": [
        "Design a distributed consistent hashing scheme for sharding services.",
        "Describe how you would design a fault-tolerant message queue system.",
        "Explain the internals of a garbage collector and pause-time tradeoffs.",
        "Design a low-latency, high-throughput analytics pipeline.",
        "How would you design a global rate limiter across multiple regions?",
        "Explain consensus algorithms (e.g., Raft) and where to use them.",
        "Design an eventually-consistent key-value store and discuss trade-offs.",
        "Describe how to design a scalable database for time-series data.",
        "Explain techniques for minimizing tail latency in microservices.",
        "Design a secure multi-tenant architecture for a SaaS product."
    ]
}

__all__ = [
    "P1_SYSTEM_MESSAGE",
    "P1_USER_TEMPLATE",
    "P1_OUTPUT_SCHEMA",
    "P2_SYSTEM_MESSAGE",
    "P2_USER_TEMPLATE",
    "P2_OUTPUT_SCHEMA",
    "P3_SYSTEM_MESSAGE",
    "P3_USER_TEMPLATE",
    "P3_OUTPUT_SCHEMA",
    "P4_SYSTEM_MESSAGE",
    "P4_USER_TEMPLATE",
    "P4_OUTPUT_SCHEMA",
    "P5_SYSTEM_MESSAGE",
    "P5_USER_TEMPLATE",
    "P5_OUTPUT_SCHEMA",
    "P6_SYSTEM_MESSAGE",
    "P6_USER_TEMPLATE",
    "P6_OUTPUT_SCHEMA",
    "P7_SYSTEM_MESSAGE",
    "P7_USER_TEMPLATE",
    "P7_OUTPUT_SCHEMA",
    "P8_SYSTEM_MESSAGE",
    "P8_USER_TEMPLATE",
    "P8_OUTPUT_SCHEMA",
    "P9_SYSTEM_MESSAGE",
    "P9_USER_TEMPLATE",
    "P9_OUTPUT_SCHEMA",
    "FALLBACK_QUESTIONS",
]
