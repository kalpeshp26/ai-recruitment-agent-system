// Minimal AI service wrapper (frontend). Provides a mock evaluate function and
// a thin proxy to backend AI endpoints if available.
(function () {
    const BACKEND_ORIGIN = 'http://127.0.0.1:8000';
    const INTERVIEW_API_BASE = `${BACKEND_ORIGIN}/api/v1/interview`;

    async function evaluateAnswer(sessionId, questionText, answerText, timeTakenMs = 0) {
        const url = `${INTERVIEW_API_BASE}/session/${sessionId}/ai/evaluate`;
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question_text: questionText, answer_text: answerText, time_taken_ms: timeTakenMs }),
        });
        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error(txt || resp.statusText);
        }
        return resp.json();
    }

    window.aiService = { evaluateAnswer };
})();
