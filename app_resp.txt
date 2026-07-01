/* AI Recruitment System dashboard */

const BACKEND_ORIGIN = 'http://127.0.0.1:8000';
const API_BASE = `${BACKEND_ORIGIN}/api`;
const INTERVIEW_API_BASE = `${BACKEND_ORIGIN}/api/v1/interview`;
const LIVE_SESSION_STORAGE_KEY = 'ai-recruitment-live-interview';

function safeStorageGet(key, fallback = '') {
    try {
        return localStorage.getItem(key) || fallback;
    } catch {
        return fallback;
    }
}

function safeStorageSet(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch {
        return;
    }
}

function safeStorageRemove(key) {
    try {
        localStorage.removeItem(key);
    } catch {
        return;
    }
}

const state = {
    jobs: [],
    candidates: [],
    events: [],
    liveInterview: {
        sessionId: '',
        token: '',
        role: '',
        answerMode: 'text',
        preferredLanguage: 'en',
        currentQuestion: null,
        questionStartedAt: 0,
        questionIndex: 0,
        status: 'idle',
    },
};

function $(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const element = $(id);
    if (element) {
        element.textContent = value;
    }
}

function setHTML(id, value) {
    const element = $(id);
    if (element) {
        element.innerHTML = value;
    }
}

function show(id) {
    const element = $(id);
    if (element) {
        element.classList.remove('hidden');
    }
}

function hide(id) {
    const element = $(id);
    if (element) {
        element.classList.add('hidden');
    }
}

function setStatus(message, kind = 'info') {
    const element = $('live-interview-status');
    if (!element) {
        return;
    }
    element.textContent = message;
    element.className = `status-tag ${kind}`;
}

function updateLiveSummary() {
    setText('live-session-id', state.liveInterview.sessionId || 'none');
    setText('live-session-status', state.liveInterview.status || 'none');
    setText('live-progress', state.liveInterview.currentQuestion ? 'in progress' : 'waiting');
    setText('live-question-count', `${state.liveInterview.questionIndex || 0} / ${Number($('live-max-questions')?.textContent || '10')}`);
}

function persistLiveSession() {
    safeStorageSet(LIVE_SESSION_STORAGE_KEY, JSON.stringify(state.liveInterview));
}

function restoreLiveSession() {
    const raw = safeStorageGet(LIVE_SESSION_STORAGE_KEY, '');
    if (!raw) {
        updateLiveSummary();
        return;
    }
    try {
        const stored = JSON.parse(raw);
        state.liveInterview = { ...state.liveInterview, ...stored };
    } catch {
        safeStorageRemove(LIVE_SESSION_STORAGE_KEY);
    }
    if (state.liveInterview.sessionId) {
        setStatus('Session restored', 'info');
    }
    updateLiveSummary();
}

function clearLiveSession() {
    state.liveInterview = {
        sessionId: '',
        token: '',
        role: '',
        answerMode: 'text',
        preferredLanguage: 'en',
        currentQuestion: null,
        questionStartedAt: 0,
        questionIndex: 0,
        status: 'idle',
    };
    safeStorageRemove(LIVE_SESSION_STORAGE_KEY);
    updateLiveSummary();
}

function getInterviewHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (state.liveInterview.token) {
        headers.Authorization = `Bearer ${state.liveInterview.token}`;
        headers['X-Session-Token'] = state.liveInterview.token;
    }
    return headers;
}

async function apiRequest(url, options = {}, base = API_BASE) {
    const response = await fetch(`${base}${url}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
    });
    const text = await response.text();
    let payload = null;
    if (text) {
        try {
            payload = JSON.parse(text);
        } catch {
            payload = text;
        }
    }
    if (!response.ok) {
        const detail = payload && typeof payload === 'object' ? JSON.stringify(payload) : String(payload || response.statusText);
        throw new Error(detail || `Request failed with ${response.status}`);
    }
    return payload;
}

function renderKeyValueList(items) {
    return items
        .map(([label, value]) => `<div><strong>${label}:</strong> ${String(value ?? '')}</div>`)
        .join('');
}

function renderInterviewResults(items) {
    const list = Array.isArray(items) ? items : [];
    const container = $('interview-results-list');
    if (!container) {
        return;
    }
    if (!list.length) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No completed interviews yet</p>
                <span style="opacity: 0.7; font-size: 0.9em;">Interview results will appear here after candidates complete their sessions</span>
            </div>`;
        return;
    }
    container.innerHTML = list.map((item) => `
        <div class="card">
            <h3>${item.session_id || item.id || 'Interview Session'}</h3>
            <div class="text-muted">${item.status || item.phase || 'completed'}</div>
            <div style="margin-top: 0.75rem; display: grid; gap: 0.35rem;">
                ${renderKeyValueList([
                    ['Score', item.final_score ?? item.overall_score ?? 'n/a'],
                    ['Technical', item.technical_score ?? 'n/a'],
                    ['Communication', item.communication_score ?? 'n/a'],
                    ['Summary', item.summary ?? item.feedback_summary ?? 'n/a'],
                ])}
            </div>
        </div>`).join('');
}

async function loadInterviewResults() {
    if (!state.liveInterview.sessionId && !state.liveInterview.token) {
        renderInterviewResults([]);
        return [];
    }
    try {
        const sessions = await apiRequest('/sessions', { method: 'GET', headers: getInterviewHeaders() }, INTERVIEW_API_BASE);
        renderInterviewResults(Array.isArray(sessions) ? sessions : sessions.sessions || []);
        return sessions;
    } catch (error) {
        renderInterviewResults([]);
        setStatus(`Results unavailable: ${error.message}`, 'error');
        return [];
    }
}

function updateCurrentQuestion(question) {
    state.liveInterview.currentQuestion = question || null;
    state.liveInterview.questionStartedAt = question ? Date.now() : 0;
    if (!question) {
        hide('live-question-panel');
        updateLiveSummary();
        return;
    }
    show('live-question-panel');
    setText('live-question-meta', `${question.question_index ?? state.liveInterview.questionIndex ?? 0} • ${question.difficulty || 'medium'}${question.category ? ` • ${question.category}` : ''}`);
    setText('live-question-text', question.question_text || 'Question loaded');
    setText('live-question-count', `${question.question_index ?? state.liveInterview.questionIndex ?? 0} / ${Number($('live-max-questions')?.textContent || '10')}`);
    setText('live-answer-feedback', '');
    updateLiveSummary();
    persistLiveSession();
}

async function startLiveInterview(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    const role = $('live-role')?.value?.trim() || 'engineer';
    const answerMode = $('live-answer-mode')?.value || 'text';
    const preferredLanguage = $('live-language')?.value?.trim() || 'en';
    setStatus('Starting session...', 'info');
    try {
        const response = await apiRequest('/start', {
            method: 'POST',
            headers: getInterviewHeaders(),
            body: JSON.stringify({ role, answer_mode: answerMode, preferred_language: preferredLanguage }),
        }, INTERVIEW_API_BASE);
        state.liveInterview = {
            ...state.liveInterview,
            sessionId: response.session_id,
            token: response.session_token,
            role,
            answerMode,
            preferredLanguage,
            status: response.status || 'started',
            questionIndex: 0,
            currentQuestion: null,
            questionStartedAt: 0,
        };
        persistLiveSession();
        updateLiveSummary();
        setStatus('Session started', 'success');
        await loadNextInterviewQuestion(true);
        return response;
    } catch (error) {
        setStatus(`Start failed: ${error.message}`, 'error');
        throw error;
    }
}

async function loadNextInterviewQuestion(force = false) {
    if (!state.liveInterview.sessionId) {
        setStatus('Start a session first', 'warning');
        return null;
    }
    try {
        const question = await apiRequest(`/session/${state.liveInterview.sessionId}/next-question`, {
            method: 'GET',
            headers: getInterviewHeaders(),
        }, INTERVIEW_API_BASE);
        state.liveInterview.questionIndex = question.question_index ?? (state.liveInterview.questionIndex + 1);
        updateCurrentQuestion(question);
            // Auto-play question using TTS when available and not in text-only mode
            try {
                if (window.ttsService && state.liveInterview.answerMode !== 'text') {
                    ttsService.speak(question.question_text || '', { lang: state.liveInterview.preferredLanguage || 'en' });
                }
            } catch (err) {
                // ignore tts failures
            }
        setStatus(force ? 'Next question loaded' : 'Question loaded', 'success');
        return question;
    } catch (error) {
        setStatus(`Question load failed: ${error.message}`, 'error');
        throw error;
    }
}

async function submitLiveAnswer(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    if (!state.liveInterview.sessionId || !state.liveInterview.currentQuestion) {
        setStatus('Load a question first', 'warning');
        return null;
    }
    let answerText = $('live-answer-text')?.value?.trim() || '';
    // If using audio/STT answer mode and no typed answer provided, attempt STT
    if (!answerText && state.liveInterview.answerMode && state.liveInterview.answerMode !== 'text') {
        setStatus('Attempting STT transcription...', 'info');
        try {
            if (window.sttService && typeof sttService.transcribeLastRecording === 'function') {
                const transcript = await sttService.transcribeLastRecording(state.liveInterview.sessionId);
                if (transcript) {
                    answerText = transcript.trim();
                    const inputEl = $('live-answer-text');
                    if (inputEl) inputEl.value = answerText;
                }
            }
        } catch (err) {
            // ignore stt errors
        }
    }
    const responseTimeMs = Math.max(0, Date.now() - (state.liveInterview.questionStartedAt || Date.now()));
    const payload = {
        question_id: state.liveInterview.currentQuestion.question_id,
        answer_text: answerText || null,
        answer_audio_url: null,
        response_time_ms: responseTimeMs,
        client_request_id: `live-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    };
    try {
        const response = await apiRequest(`/session/${state.liveInterview.sessionId}/submit-answer`, {
            method: 'POST',
            headers: getInterviewHeaders(),
            body: JSON.stringify(payload),
        }, INTERVIEW_API_BASE);
        setHTML('live-answer-feedback', `<div class="status-tag success">${response.ai_feedback || 'Answer submitted'}</div>`);
        if (response.next_question_available) {
            await loadNextInterviewQuestion(false);
        } else {
            await loadLiveInterviewResult();
        }
        setStatus('Answer submitted', 'success');
        return response;
    } catch (error) {
        setStatus(`Submit failed: ${error.message}`, 'error');
        throw error;
    }
}

async function endLiveInterview(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    if (!state.liveInterview.sessionId) {
        setStatus('No live session', 'warning');
        return null;
    }
    try {
        const response = await apiRequest(`/session/${state.liveInterview.sessionId}/end`, {
            method: 'POST',
            headers: getInterviewHeaders(),
            body: JSON.stringify({ reason: 'manual_end' }),
        }, INTERVIEW_API_BASE);
        state.liveInterview.status = response.status || 'ended';
        updateLiveSummary();
        setStatus('Session ended', 'success');
        await loadLiveInterviewResult();
        return response;
    } catch (error) {
        setStatus(`End failed: ${error.message}`, 'error');
        throw error;
    }
}

async function loadLiveInterviewResult() {
    if (!state.liveInterview.sessionId) {
        return null;
    }
    try {
        const result = await apiRequest(`/session/${state.liveInterview.sessionId}/result`, {
            method: 'GET',
            headers: getInterviewHeaders(),
        }, INTERVIEW_API_BASE);
        show('live-result-panel');
        setHTML('live-result-content', `
            <div style="display: grid; gap: 0.5rem;">
                ${renderKeyValueList([
                    ['Session', result.session_id || state.liveInterview.sessionId],
                    ['Technical Score', result.technical_score ?? 'n/a'],
                    ['Communication Score', result.communication_score ?? 'n/a'],
                    ['Confidence Score', result.confidence_score ?? 'n/a'],
                    ['Problem Solving Score', result.problem_solving_score ?? 'n/a'],
                    ['Penalty Points', result.penalty_points ?? 'n/a'],
                    ['Final Score', result.final_score ?? 'n/a'],
                    ['Summary', result.summary ?? 'n/a'],
                ])}
            </div>`);
        return result;
    } catch (error) {
        setStatus(`Result unavailable: ${error.message}`, 'error');
        return null;
    }
}

function viewAPIEndpoints() {
    show('live-result-panel');
    setHTML('live-result-content', `
        <pre style="white-space: pre-wrap; margin: 0;">${[
            'GET  /api/v1/interview/sessions',
            'POST /api/v1/interview/start',
            'GET  /api/v1/interview/session/{session_id}/status',
            'GET  /api/v1/interview/session/{session_id}/next-question',
            'POST /api/v1/interview/session/{session_id}/submit-answer',
            'POST /api/v1/interview/session/{session_id}/skip-question',
            'POST /api/v1/interview/session/{session_id}/end',
            'GET  /api/v1/interview/session/{session_id}/result',
            'GET  /api/v1/interview/session/{session_id}/report',
            'POST /api/v1/interview/session/{session_id}/proctoring-event',
            'POST /api/v1/interview/tts',
            'POST /api/v1/interview/stt',
        ].join('\n')}</pre>`);
}

async function exportInterviewData() {
    const sessions = await loadInterviewResults();
    const payload = {
        liveInterview: state.liveInterview,
        sessions: Array.isArray(sessions) ? sessions : [],
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'interview-data.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

async function loadOverviewData() {
    setStatus('Dashboard ready', 'info');
}

async function loadJobs() {
    state.jobs = state.jobs.length ? state.jobs : [{ id: 'demo-job', title: 'Demo Engineer Role' }];
    loadJobsForSelect();
}

async function loadJobsForSelect() {
    const select = $('candidate-job-select');
    if (!select) {
        return;
    }
    const jobs = state.jobs.length ? state.jobs : [{ id: 'demo-job', title: 'Demo Engineer Role' }];
    select.innerHTML = jobs.map((job) => `<option value="${job.id}">${job.title || job.name || job.id}</option>`).join('');
}

async function loadCandidates() {
    state.candidates = state.candidates.length ? state.candidates : [];
}

async function loadScreeningData() { return null; }
async function loadOutreachData() { return null; }
async function loadPrescreeningData() { return null; }
async function loadOffers() { return null; }
async function loadOnboarding() { return null; }
async function loadAnalyticsDashboard() { return null; }

async function loadEvents() {
    setStatus('Events refreshed', 'info');
}

async function createJob(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    const title = $('job-title')?.value?.trim() || 'Untitled Job';
    state.jobs.unshift({ id: `job-${Date.now()}`, title });
    await loadJobsForSelect();
    const result = $('job-form-result');
    if (result) {
        result.classList.remove('hidden');
        const content = $('job-form-content');
        if (content) {
            content.textContent = `Created local demo job: ${title}`;
        }
    }
}

async function addCandidateForm(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    const name = $('candidate-name')?.value?.trim() || 'Candidate';
    state.candidates.unshift({ name });
    const result = $('candidate-form-result');
    if (result) {
        result.classList.remove('hidden');
        const content = $('candidate-form-content');
        if (content) {
            content.textContent = `Created local demo candidate: ${name}`;
        }
    }
}

async function runScreening() { setStatus('Screening demo not connected', 'info'); }
async function exportShortlist() { setStatus('Shortlist export unavailable in demo mode', 'info'); }
async function togglePrescreeningView() { return null; }
async function createPrescreeningSession() { return null; }
async function exportPrescreeningData() { return null; }
async function runBulkEvaluation() { return null; }
async function closeSessionDetails() { return null; }
async function exportAnalyticsCSV() { return null; }
async function exportAnalyticsPDF() { return null; }

function setupUploadZone() { return null; }
function setupNavToggle() { return null; }
function setupStageHeaderLift() { return null; }

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach((button) => {
        button.classList.toggle('active', button.dataset.tab === tabId);
    });
    document.querySelectorAll('.tab-content').forEach((content) => {
        content.classList.toggle('active', content.id === `tab-${tabId}`);
    });
    switch (tabId) {
        case 'overview': loadOverviewData(); break;
        case 'stage1': loadJobs(); break;
        case 'stage2': loadCandidates(); loadJobsForSelect(); break;
        case 'stage3': loadScreeningData(); break;
        case 'stage4': loadOutreachData(); break;
        case 'stage5': loadPrescreeningData(); break;
        case 'stage6': loadInterviewResults(); break;
        case 'stage8': loadOffers(); break;
        case 'stage9': loadOnboarding(); break;
        case 'stage10': loadAnalyticsDashboard(); break;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    setupUploadZone();
    setupNavToggle();
    setupStageHeaderLift();
    restoreLiveSession();
    document.querySelectorAll('.tab-btn').forEach((button) => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });
    const liveForm = $('live-interview-form');
    if (liveForm) {
        liveForm.addEventListener('submit', startLiveInterview);
    }
    const submitButton = $('btn-submit-live-answer');
    if (submitButton) {
        submitButton.addEventListener('click', submitLiveAnswer);
    }
    // Recording controls
    const btnStart = $('btn-start-record');
    const btnStop = $('btn-stop-record');
    const btnPlay = $('btn-play-record');
    const btnTranscribe = $('btn-transcribe-record');
    const recStatus = $('recording-status');
    if (btnStart) btnStart.addEventListener('click', async () => {
        try {
            await sttService.startRecording();
            if (recStatus) recStatus.textContent = 'Recording...';
            setStatus('Recording audio...', 'info');
        } catch (err) {
            setStatus(`Record start failed: ${err.message}`, 'error');
        }
    });
    if (btnStop) btnStop.addEventListener('click', async () => {
        try {
            const blob = await sttService.stopRecording();
            if (blob) {
                if (recStatus) recStatus.textContent = `Recorded ${Math.round(blob.size/1024)} KB`;
                setStatus('Recording stopped', 'success');
            } else {
                if (recStatus) recStatus.textContent = 'No recording';
                setStatus('No recording captured', 'warning');
            }
        } catch (err) {
            setStatus(`Stop failed: ${err.message}`, 'error');
        }
    });
    if (btnPlay) btnPlay.addEventListener('click', () => {
        try {
            sttService.playLastRecording();
        } catch (err) {
            setStatus(`Play failed: ${err.message}`, 'error');
        }
    });
    if (btnTranscribe) btnTranscribe.addEventListener('click', async () => {
        try {
            setStatus('Transcribing audio...', 'info');
            const transcript = await sttService.transcribeLastRecording(state.liveInterview.sessionId);
            if (transcript) {
                const inputEl = $('live-answer-text');
                if (inputEl) inputEl.value = transcript;
                setStatus('Transcription received', 'success');
            } else {
                setStatus('No transcript returned', 'warning');
            }
        } catch (err) {
            setStatus(`Transcription failed: ${err.message}`, 'error');
        }
    });
    document.querySelectorAll('#tab-stage6 button').forEach((button) => {
        const label = button.textContent.trim();
        if (label === 'Next Question') {
            button.addEventListener('click', () => loadNextInterviewQuestion(true));
        } else if (label === 'End Session') {
            button.addEventListener('click', endLiveInterview);
        } else if (label === 'Refresh') {
            button.addEventListener('click', loadInterviewResults);
        } else if (label === 'Export Interview Data (JSON)') {
            button.addEventListener('click', exportInterviewData);
        } else if (label === 'View API Endpoints') {
            button.addEventListener('click', viewAPIEndpoints);
        } else if (label === 'Skip to Next Question') {
            button.addEventListener('click', () => loadNextInterviewQuestion(true));
        }
    });
    loadOverviewData();
    loadJobsForSelect();
});

window.switchTab = switchTab;
window.loadEvents = loadEvents;
window.loadOverviewData = loadOverviewData;
window.loadJobs = loadJobs;
window.loadJobsForSelect = loadJobsForSelect;
window.loadCandidates = loadCandidates;
window.loadScreeningData = loadScreeningData;
window.loadOutreachData = loadOutreachData;
window.loadPrescreeningData = loadPrescreeningData;
window.loadInterviewResults = loadInterviewResults;
window.loadOffers = loadOffers;
window.loadOnboarding = loadOnboarding;
window.loadAnalyticsDashboard = loadAnalyticsDashboard;
window.startLiveInterview = startLiveInterview;
window.loadNextInterviewQuestion = loadNextInterviewQuestion;
window.submitLiveAnswer = submitLiveAnswer;
window.endLiveInterview = endLiveInterview;
window.viewAPIEndpoints = viewAPIEndpoints;
window.exportInterviewData = exportInterviewData;
window.createJob = createJob;
window.addCandidateForm = addCandidateForm;
window.runScreening = runScreening;
window.exportShortlist = exportShortlist;
window.togglePrescreeningView = togglePrescreeningView;
window.createPrescreeningSession = createPrescreeningSession;
window.exportPrescreeningData = exportPrescreeningData;
window.runBulkEvaluation = runBulkEvaluation;
window.closeSessionDetails = closeSessionDetails;
window.exportAnalyticsCSV = exportAnalyticsCSV;
window.exportAnalyticsPDF = exportAnalyticsPDF;