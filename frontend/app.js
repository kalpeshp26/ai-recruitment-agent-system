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
    stageData: {
        screeningCandidates: [],
        outreachCandidates: [],
        prescreeningSessions: [],
        offers: [],
        onboarding: [],
        analytics: null,
    },
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

function escapeHTML(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function setSelectOptions(selectId, options, placeholder = '-- All --') {
    const select = $(selectId);
    if (!select) return;
    const items = Array.isArray(options) ? options : [];
    select.innerHTML = [`<option value="">${placeholder}</option>`, ...items.map((item) => `<option value="${escapeHTML(item.value)}">${escapeHTML(item.label)}</option>`)].join('');
}

function renderCardsList(containerId, items, emptyHtml) {
    const container = $(containerId);
    if (!container) return;
    if (!items || !items.length) {
        container.innerHTML = emptyHtml || '<div class="empty-state">No records found.</div>';
        return;
    }
    container.innerHTML = items.join('');
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
    const jobs = state.jobs.length ? state.jobs : [{ id: 'demo-job', title: 'Demo Engineer Role' }];
    const options = jobs.map((job) => ({ value: job.id, label: job.title || job.name || job.id }));
    ['candidate-job-select', 'screening-job-select', 'outreach-job-filter', 'prescreening-job-filter', 'post-job-select'].forEach((id) => {
        setSelectOptions(id, options, '-- All Jobs --');
    });
}

async function loadCandidates() {
    state.candidates = state.candidates.length ? state.candidates : [];
}

function _renderJobCards(items, emptyMessage) {
    const rows = (items || []).map((item) => `
        <div class="card">
            <h3>${escapeHTML(item.title || item.job_title || item.name || item.id || 'Untitled')}</h3>
            <div class="text-muted">${escapeHTML(item.department || item.location || item.status || '')}</div>
            <div style="margin-top: 0.75rem; display: grid; gap: 0.35rem;">
                ${renderKeyValueList(Object.entries(item).slice(0, 6))}
            </div>
        </div>`);
    return rows.length ? rows : [emptyMessage || '<div class="empty-state">No records found.</div>'];
}

function _renderTableRows(items, columns, emptyColSpan = 4) {
    if (!items || !items.length) {
        return `<tr><td colspan="${emptyColSpan}" class="empty-state">No records found.</td></tr>`;
    }
    return items.map((item) => `<tr>${columns.map((column) => `<td>${column(item)}</td>`).join('')}</tr>`).join('');
}

function filterCandidates() {
    const status = $('status-filter')?.value || '';
    const rows = state.stageData.screeningCandidates.filter((item) => !status || String(item.status || '').toLowerCase() === status.toLowerCase());
    const body = $('screening-results');
    if (body) {
        body.innerHTML = rows.length ? rows.map((item) => `
            <div class="card" style="margin-bottom: 12px;">
                <h3>${escapeHTML(item.name || item.candidate_name || item.id)}</h3>
                <div class="text-muted">${escapeHTML(item.email || '')}</div>
                <div style="margin-top: 0.75rem; display: grid; gap: 0.35rem;">
                    ${renderKeyValueList([
                        ['Status', item.status || 'new'],
                        ['Score', item.score ?? 'n/a'],
                        ['Duplicate', item.is_duplicate ? 'Yes' : 'No'],
                        ['Job', item.job_title || item.job_id || 'n/a'],
                        ['Reason', item.rejection_reason || 'n/a'],
                    ])}
                </div>
            </div>`).join('') : '<div class="empty-state">No screening results yet. Run screening to see results.</div>';
    }
}

function filterOutreachCandidates() {
    const jobId = $('outreach-job-filter')?.value || '';
    const rows = state.stageData.outreachCandidates.filter((item) => !jobId || String(item.job_id || '') === jobId);
    const tableBody = $('outreach-table-body');
    if (tableBody) {
        tableBody.innerHTML = _renderTableRows(rows, [
            (item) => escapeHTML(item.name || item.id || ''),
            (item) => escapeHTML(item.email || ''),
            (item) => escapeHTML(item.job_title || item.job_id || ''),
            (item) => `<button class="btn btn-ghost btn-sm" onclick="sendOutreach('${escapeHTML(item.id)}','${escapeHTML(item.job_id)}')">Send</button>`,
        ], 4);
    }
}

function filterPrescreeningSessions() {
    const jobId = $('prescreening-job-filter')?.value || '';
    const status = $('prescreening-status-filter')?.value || '';
    const rows = state.stageData.prescreeningSessions.filter((item) => (!jobId || String(item.job_id || '') === jobId) && (!status || String(item.status || '').toUpperCase() === status.toUpperCase()));
    const tableBody = $('prescreening-table-body');
    if (tableBody) {
        tableBody.innerHTML = _renderTableRows(rows, [
            (item) => escapeHTML(item.candidate_name || item.candidate_id || ''),
            (item) => escapeHTML(item.candidate_email || ''),
            (item) => escapeHTML(item.job_title || item.job_id || ''),
            (item) => escapeHTML(item.status || ''),
            (item) => escapeHTML(String(item.answered_questions ?? 0)),
            (item) => escapeHTML(String(item.ai_score ?? item.score ?? 'n/a')),
            (item) => escapeHTML(item.verdict || item.status || 'n/a'),
            (item) => escapeHTML(item.created_at || ''),
            (item) => `<button class="btn btn-ghost btn-sm" onclick="viewPrescreeningSession('${escapeHTML(item.session_id)}')">View</button>`,
        ], 9);
    }
}

async function loadScreeningData() {
    try {
        const [stats, jobs, candidates] = await Promise.all([
            apiRequest('/screening/stats', { method: 'GET' }, API_BASE),
            apiRequest('/screening/jobs', { method: 'GET' }, API_BASE),
            apiRequest('/screening/candidates', { method: 'GET' }, API_BASE),
        ]);
        const jobList = Array.isArray(jobs) ? jobs : [];
        const jobMap = new Map(jobList.map((job) => [String(job.id), job]));
        state.stageData.screeningCandidates = (Array.isArray(candidates) ? candidates : []).map((candidate) => ({
            ...candidate,
            job_title: candidate.job_title || jobMap.get(String(candidate.job_id))?.title || '',
        }));
        setSelectOptions('screening-job-select', jobList.map((job) => ({ value: job.id, label: job.title || job.id })), '-- All Jobs --');
        setText('stat-total-candidates', stats.total_candidates ?? 0);
        setText('stat-screened', stats.screened ?? 0);
        setText('stat-shortlisted', stats.shortlisted ?? 0);
        setText('stat-rejected', stats.rejected ?? 0);
        setText('stat-duplicates', stats.duplicates ?? 0);
        setText('stat-avg-score', stats.avg_score ?? 0);
        filterCandidates();
        setStatus('Screening data loaded', 'success');
        return { stats, jobs, candidates };
    } catch (error) {
        setStatus(`Screening load failed: ${error.message}`, 'error');
        return null;
    }
}

async function loadOutreachData() {
    try {
        const [stats, jobs, candidates] = await Promise.all([
            apiRequest('/outreach/stats', { method: 'GET' }, API_BASE),
            apiRequest('/outreach/jobs', { method: 'GET' }, API_BASE),
            apiRequest('/outreach/candidates', { method: 'GET' }, API_BASE),
        ]);
        const jobList = Array.isArray(jobs) ? jobs : [];
        state.stageData.outreachCandidates = Array.isArray(candidates) ? candidates : [];
        setSelectOptions('outreach-job-filter', jobList.map((job) => ({ value: job.id, label: job.title || job.id })), '-- All Jobs --');
        setText('stat-total-shortlisted', stats.total_shortlisted ?? 0);
        setText('stat-outreach-sent', stats.outreach_sent ?? 0);
        setText('stat-opened', stats.opened ?? 0);
        setText('stat-clicked', stats.clicked ?? 0);
        setText('stat-replied', stats.replied ?? 0);
        setText('stat-unresponsive', stats.unresponsive ?? 0);
        filterOutreachCandidates();
        setStatus('Outreach data loaded', 'success');
        return { stats, jobs, candidates };
    } catch (error) {
        setStatus(`Outreach load failed: ${error.message}`, 'error');
        return null;
    }
}

async function loadPrescreeningData() {
    try {
        const [stats, jobs, sessions] = await Promise.all([
            apiRequest('/prescreening/stats', { method: 'GET' }, API_BASE),
            apiRequest('/prescreening/jobs', { method: 'GET' }, API_BASE),
            apiRequest('/prescreening/sessions', { method: 'GET' }, API_BASE),
        ]);
        const jobList = Array.isArray(jobs) ? jobs : [];
        state.stageData.prescreeningSessions = (Array.isArray(sessions) ? sessions : []).map((session) => ({
            ...session,
            verdict: session.status === 'COMPLETED' ? 'Review' : session.status,
        }));
        setSelectOptions('prescreening-job-filter', jobList.map((job) => ({ value: job.id, label: job.title || job.id })), '-- All Jobs --');
        setText('prescreening-total', stats.total_in_prescreening ?? 0);
        setText('prescreening-completed', stats.sessions_completed ?? 0);
        setText('prescreening-passed', stats.passed ?? 0);
        setText('bgv-cleared', stats.bgv_cleared ?? 0);
        filterPrescreeningSessions();
        setStatus('Prescreening data loaded', 'success');
        return { stats, jobs, sessions };
    } catch (error) {
        setStatus(`Prescreening load failed: ${error.message}`, 'error');
        return null;
    }
}

async function loadOffers() {
    try {
        const response = await apiRequest('/offer/list', { method: 'GET' }, API_BASE);
        const offers = Array.isArray(response.offers) ? response.offers : [];
        state.stageData.offers = offers;
        setText('stat-total-offers', offers.length);
        setText('stat-accepted-offers', offers.filter((offer) => offer.status === 'accepted').length);
        setText('stat-pending-offers', offers.filter((offer) => offer.status === 'pending').length);
        setText('stat-negotiations', offers.filter((offer) => offer.status === 'negotiation').length);
        renderCardsList('offers-list', _renderJobCards(offers.map((offer) => ({
            title: `Offer #${offer.id}`,
            department: offer.status || 'offer',
            application_id: offer.application_id,
            salary: offer.offered_salary,
            start_date: offer.start_date,
            status: offer.status,
            currency: offer.currency,
        })), '<div class="empty-state">No offers generated yet</div>'));
        setStatus('Offers loaded', 'success');
        return offers;
    } catch (error) {
        setStatus(`Offers load failed: ${error.message}`, 'error');
        return [];
    }
}

async function loadOnboarding() {
    try {
        const response = await apiRequest('/onboarding/list', { method: 'GET' }, API_BASE);
        const onboarding = Array.isArray(response.onboarding) ? response.onboarding : [];
        state.stageData.onboarding = onboarding;
        setText('stat-total-onboarding', onboarding.length);
        setText('stat-completed-onboarding', onboarding.filter((item) => String(item.status || '').toLowerCase() === 'completed').length);
        setText('stat-pending-docs', 0);
        setText('stat-pending-tasks', 0);
        renderCardsList('onboarding-list', _renderJobCards(onboarding.map((item) => ({
            title: item.candidate_name || `Onboarding #${item.id}`,
            department: item.job_title || item.status || '',
            candidate_id: item.candidate_id,
            offer_id: item.offer_id,
            status: item.status,
            created_at: item.created_at,
        })), '<div class="empty-state">No onboarding records yet</div>'));
        setStatus('Onboarding loaded', 'success');
        return onboarding;
    } catch (error) {
        setStatus(`Onboarding load failed: ${error.message}`, 'error');
        return [];
    }
}

async function loadAnalyticsDashboard() {
    try {
        const [dashboard, jobs, timeToHire, forecast] = await Promise.all([
            apiRequest('/analytics/dashboard', { method: 'GET' }, API_BASE),
            apiRequest('/analytics/jobs', { method: 'GET' }, API_BASE),
            apiRequest('/analytics/time-to-hire', { method: 'GET' }, API_BASE).catch(() => null),
            apiRequest('/analytics/forecast', { method: 'GET' }, API_BASE).catch(() => null),
        ]);
        state.stageData.analytics = { dashboard, jobs, timeToHire, forecast };
        const funnel = Array.isArray(dashboard?.funnel) ? dashboard.funnel : [];
        const funnelMetrics = $('funnel-metrics');
        if (funnelMetrics) {
            funnelMetrics.innerHTML = funnel.length ? funnel.map((stage) => `
                <div class="card">
                    <h3>${escapeHTML(stage.stage)}</h3>
                    <div class="text-muted">Drop-off ${escapeHTML(stage.dropoff_pct)}%</div>
                    <div style="margin-top:0.75rem;font-size:1.5rem;font-weight:700;">${escapeHTML(stage.count)}</div>
                </div>`).join('') : '<div class="empty-state">No funnel metrics available</div>';
        }
        setStatus('Analytics dashboard loaded', 'success');
        return { dashboard, jobs, timeToHire, forecast };
    } catch (error) {
        setStatus(`Analytics load failed: ${error.message}`, 'error');
        return null;
    }
}

async function loadEvents() {
    setStatus('Events refreshed', 'info');
}

async function createJob(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    const title = $('job-title')?.value?.trim() || 'Untitled Job';
    const department = $('job-dept')?.value?.trim() || '';
    const location = $('job-location')?.value?.trim() || '';
    const employmentType = $('job-type')?.value || 'full-time';
    const experienceMin = Number($('job-exp-min')?.value || 0);
    const experienceMax = Number($('job-exp-max')?.value || 0);
    const salaryMin = Number($('job-salary-min')?.value || 0);
    const salaryMax = Number($('job-salary-max')?.value || 0);
    const skills = String($('job-skills')?.value || '')
        .split(',')
        .map((skill) => skill.trim())
        .filter(Boolean);

    const button = $('btn-create-job');
    const result = $('jd-result');
    const content = $('jd-content');

    if (button) {
        button.disabled = true;
        button.dataset.originalText = button.textContent || 'Create Job with AI Description';
        button.textContent = 'Generating...';
    }
    setStatus('Generating job description...', 'info');

    try {
        const response = await apiRequest('/intake/jobs', {
            method: 'POST',
            body: JSON.stringify({
                title,
                department,
                location,
                employment_type: employmentType,
                experience_min: experienceMin,
                experience_max: experienceMax,
                salary_min: salaryMin,
                salary_max: salaryMax,
                currency: 'INR',
                skills,
                headcount: 1,
            }),
        }, API_BASE);

        const jobId = response.job_id || `job-${Date.now()}`;
        state.jobs.unshift({ id: jobId, title, description: response.description || '' });
        await loadJobsForSelect();

        if (result && content) {
            result.classList.remove('hidden');
            content.innerHTML = `
                <div style="display: grid; gap: 0.75rem;">
                    <div class="status-tag success">${response.message || 'Job created successfully'}</div>
                    <div><strong>Job ID:</strong> ${jobId}</div>
                    <div><strong>Title:</strong> ${title}</div>
                    <div><strong>Description:</strong></div>
                    <div class="markdown-content job-description-content">${response.description || 'No description returned.'}</div>
                </div>`;
        }

        setStatus('Job created and description generated', 'success');
        console.log('Job created:', response);
        return response;
    } catch (error) {
        if (result && content) {
            result.classList.remove('hidden');
            content.innerHTML = `<div class="status-tag error">Failed to generate job description: ${error.message}</div>`;
        }
        setStatus(`Job creation failed: ${error.message}`, 'error');
        console.error('Create job failed:', error);
        throw error;
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = button.dataset.originalText || 'Create Job with AI Description';
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

async function runScreening(forceRescreen = false) {
    try {
        const jobId = $('screening-job-select')?.value || null;
        const response = await apiRequest('/screening/run', {
            method: 'POST',
            body: JSON.stringify({ job_id: jobId, force_rescreen: !!forceRescreen }),
        }, API_BASE);
        setStatus(response.message || 'Screening completed', 'success');
        await loadScreeningData();
        return response;
    } catch (error) {
        setStatus(`Screening failed: ${error.message}`, 'error');
        throw error;
    }
}

async function sendOutreach(candidateId, jobId) {
    try {
        const response = await apiRequest('/outreach/send', {
            method: 'POST',
            body: JSON.stringify({ candidate_id: candidateId, job_id: jobId }),
        }, API_BASE);
        setStatus(response.message || 'Outreach queued', 'success');
        await loadOutreachData();
        return response;
    } catch (error) {
        setStatus(`Outreach send failed: ${error.message}`, 'error');
        throw error;
    }
}

async function exportShortlist() {
    const shortlisted = state.stageData.screeningCandidates.filter((item) => String(item.status || '').toLowerCase() === 'shortlisted');
    const blob = new Blob([JSON.stringify(shortlisted, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'shortlist.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

async function togglePrescreeningView() {
    const adminView = $('prescreening-admin-view');
    const candidateView = $('prescreening-candidate-view');
    if (!adminView || !candidateView) return null;
    const showingAdmin = adminView.style.display !== 'none';
    adminView.style.display = showingAdmin ? 'none' : 'block';
    candidateView.style.display = showingAdmin ? 'block' : 'none';
    return { showingAdmin: !showingAdmin };
}

async function createPrescreeningSession() {
    setStatus('Prescreening sessions are created automatically from outreach in this build.', 'info');
}

async function exportPrescreeningData() {
    const blob = new Blob([JSON.stringify(state.stageData.prescreeningSessions, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'prescreening-sessions.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

async function runBulkEvaluation() {
    await loadPrescreeningData();
    setStatus('Prescreening records refreshed', 'success');
}

async function closeSessionDetails() {
    const panel = $('session-details-panel');
    if (panel) panel.style.display = 'none';
}

async function exportAnalyticsCSV() {
    window.location.href = `${API_BASE}/analytics/export/csv`;
}

async function exportAnalyticsPDF() {
    window.location.href = `${API_BASE}/analytics/export/pdf`;
}

async function viewPrescreeningSession(sessionId) {
    const session = state.stageData.prescreeningSessions.find((item) => item.session_id === sessionId);
    const panel = $('session-details-panel');
    const content = $('session-details-content');
    if (!panel || !content) return null;
    panel.style.display = 'block';
    content.innerHTML = session ? `
        <div style="display:grid; gap:0.5rem;">
            ${renderKeyValueList([
                ['Session', session.session_id],
                ['Candidate', session.candidate_name],
                ['Job', session.job_title],
                ['Status', session.status],
                ['Questions', `${session.answered_questions || 0}/${session.total_questions || 0}`],
                ['Token', session.token || 'n/a'],
            ])}
        </div>` : '<div class="empty-state">Session not found.</div>';
}

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

// API health check for header status badge
async function checkApiHealth() {
    const el = document.getElementById('api-status');
    try {
        const r = await fetch(`${BACKEND_ORIGIN}/health`, { cache: 'no-store' });
        if (r.ok) {
            if (el) {
                el.innerHTML = '<span class="status-dot success"></span><span>Connected</span>';
                el.classList.remove('connecting');
            }
            return true;
        }
    } catch (err) {
        // ignore
    }
    if (el) {
        el.innerHTML = '<span class="status-dot"></span><span>Connecting...</span>';
        el.classList.add('connecting');
    }
    return false;
}

// Kick off periodic health checks
try {
    checkApiHealth();
    setInterval(checkApiHealth, 5000);
} catch (e) {
    // ignore in environments where the DOM is not ready yet
}

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