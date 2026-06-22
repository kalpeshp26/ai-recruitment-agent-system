/* AI Recruitment System dashboard */

const BACKEND_ORIGIN = 'http://127.0.0.1:8000';
const API_BASE = `${BACKEND_ORIGIN}/api`;
const INTERVIEW_API_BASE = `${BACKEND_ORIGIN}/api/v1/interview`;
const LIVE_SESSION_STORAGE_KEY = 'ai-recruitment-live-interview';
const ACTIVE_TAB_STORAGE_KEY = 'ai-recruitment-active-tab';

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

function getOptionalText(id) {
    const value = $(id)?.value?.trim();
    return value ? value : null;
}

/**
 * Render basic Markdown to HTML.
 * Handles: ## headings, **bold**, bullet lists (- / *), blank-line paragraphs.
 */
function renderMarkdown(text) {
    if (!text) return '';
    const lines = String(text).split('\n');
    const html = [];
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
        const raw = lines[i];
        const line = raw.trimEnd();

        // Headings
        if (/^### (.+)/.test(line)) {
            if (inList) { html.push('</ul>'); inList = false; }
            html.push(`<h4>${escapeHTML(line.replace(/^### /, ''))}</h4>`);
            continue;
        }
        if (/^## (.+)/.test(line)) {
            if (inList) { html.push('</ul>'); inList = false; }
            html.push(`<h3>${escapeHTML(line.replace(/^## /, ''))}</h3>`);
            continue;
        }
        if (/^# (.+)/.test(line)) {
            if (inList) { html.push('</ul>'); inList = false; }
            html.push(`<h2>${escapeHTML(line.replace(/^# /, ''))}</h2>`);
            continue;
        }

        // Bullet list items (- or *)
        if (/^[\-\*] (.+)/.test(line)) {
            if (!inList) { html.push('<ul>'); inList = true; }
            const content = line.replace(/^[\-\*] /, '');
            html.push(`<li>${renderInlineMarkdown(content)}</li>`);
            continue;
        }

        // Blank line — close list if open
        if (line.trim() === '') {
            if (inList) { html.push('</ul>'); inList = false; }
            html.push('<br>');
            continue;
        }

        // Paragraph line
        if (inList) { html.push('</ul>'); inList = false; }
        html.push(`<p>${renderInlineMarkdown(line)}</p>`);
    }

    if (inList) html.push('</ul>');
    return html.join('');
}

/** Render bold (**text**) and italic (*text*) inline */
function renderInlineMarkdown(text) {
    return escapeHTML(text)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>');
}

function parseOptionalInt(id) {
    const value = getOptionalText(id);
    return value === null ? null : parseInt(value, 10);
}

function parseOptionalFloat(id) {
    const value = getOptionalText(id);
    return value === null ? null : parseFloat(value);
}

function formatScore(value) {
    if (value === null || value === undefined || value === '') {
        return 'n/a';
    }
    return `${(Number(value) * 100).toFixed(1)}%`;
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
    container.innerHTML = list.map((item) => {
        const scoreVal = item.final_score ?? item.overall_score;
        const displayScore = scoreVal != null ? (scoreVal > 1 ? scoreVal.toFixed(1) + '%' : (scoreVal * 100).toFixed(1) + '%') : 'n/a';
        
        const technicalVal = item.technical_score;
        const displayTech = technicalVal != null ? (technicalVal > 1 ? technicalVal.toFixed(1) + '%' : (technicalVal * 100).toFixed(1) + '%') : 'n/a';
        
        const communicationVal = item.communication_score;
        const displayComm = communicationVal != null ? (communicationVal > 1 ? communicationVal.toFixed(1) + '%' : (communicationVal * 100).toFixed(1) + '%') : 'n/a';

        return `
        <div class="card" style="margin-bottom: 1rem; padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                <h3 style="margin: 0;">${escapeHTML(item.candidate_name || 'Interview Session')}</h3>
                <span class="status-tag success">${escapeHTML(item.status || 'completed')}</span>
            </div>
            <div class="text-muted" style="margin-bottom: 0.75rem;">Job Role: ${escapeHTML(item.job_title || 'Position TBD')}</div>
            <div style="display: grid; gap: 0.35rem; font-size: 0.95rem;">
                ${renderKeyValueList([
                    ['Overall Score', displayScore],
                    ['Technical Score', displayTech],
                    ['Communication Score', displayComm],
                    ['Recommendation', item.recommendation ?? 'n/a'],
                    ['Notes', item.summary ?? item.feedback_summary ?? 'n/a'],
                ])}
            </div>
            <div style="margin-top: 1rem; display: flex; justify-content: flex-end;">
                <button class="btn btn-secondary btn-sm" onclick="downloadInterviewPDF('${escapeHTML(item.session_id)}')" title="Download Scorecard PDF" style="display: flex; align-items: center; gap: 4px;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Download PDF Report
                </button>
            </div>
        </div>`;
    }).join('');
}

function downloadInterviewPDF(sessionId) {
    if (!sessionId) {
        showToast('Invalid session ID', 'error');
        return;
    }
    window.location.href = `${API_BASE}/interview/sessions/${sessionId}/export/pdf`;
}
window.downloadInterviewPDF = downloadInterviewPDF;

async function loadInterviewResults() {
    try {
        // Fetch interview sessions from new interview API
        const response = await apiRequest('/interview/sessions', { 
            method: 'GET' 
        }, API_BASE);
        
        const sessions = Array.isArray(response.sessions) ? response.sessions : [];
        state.stageData.interviewSessions = sessions;
        
        // Update stats
        setText('stat-total-interviews', sessions.length);
        setText('stat-completed-interviews', sessions.filter(s => s.status === 'COMPLETED').length);
        setText('stat-in-progress', sessions.filter(s => s.status === 'IN_PROGRESS').length);
        
        // Calculate average score
        const completed = sessions.filter(s => s.final_score != null);
        const avgScore = completed.length > 0 
            ? ((completed.reduce((sum, s) => sum + s.final_score, 0) / completed.length) * 100).toFixed(1) + '%'
            : '0.0%';
        setText('stat-avg-score', avgScore);
        
        // Render interview cards
        renderInterviewCards(sessions);
        
        // Render completed scorecards in results list
        const completedSessions = sessions.filter(s => s.status === 'COMPLETED');
        renderInterviewResults(completedSessions);
        
        setStatus('Interview data loaded', 'success');
        return sessions;
    } catch (error) {
        console.error('Load interviews error:', error);
        setStatus(`Load interviews failed: ${error.message}`, 'error');
        return [];
    }
}

function renderInterviewCards(sessions) {
    const container = $('interview-sessions-list');
    if (!container) {
        console.warn('interview-sessions-list container not found');
        return;
    }
    
    if (sessions.length === 0) {
        container.innerHTML = '<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="48" height="48" style="opacity: 0.3; margin-bottom: 1rem;"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg><p>No interview sessions yet</p><span style="opacity: 0.7; font-size: 0.9em;">Sessions will appear here after candidates pass prescreening</span></div>';
        return;
    }
    
    const cards = sessions.map(session => {
        const statusClass = {
            'PENDING': 'info',
            'IN_PROGRESS': 'warning',
            'COMPLETED': 'success',
            'EXPIRED': 'error'
        }[session.status] || 'info';
        
        const statusLabel = session.status || 'PENDING';
        
        return `
        <div class="job-card">
            <div class="job-card-header">
                <div class="job-card-title-block">
                    <h3>${escapeHTML(session.candidate_name || 'Unknown Candidate')}</h3>
                    <div class="job-card-subtitle">${escapeHTML(session.job_title || 'Position TBD')}</div>
                </div>
                <span class="status-tag ${statusClass}">${escapeHTML(statusLabel)}</span>
            </div>
            <div class="job-card-sections">
                <div class="job-card-section">
                    <span>SESSION ID</span>
                    <strong>${escapeHTML(session.session_id.substring(5, 13))}</strong>
                </div>
                <div class="job-card-section">
                    <span>INVITED</span>
                    <strong>${session.invited_at ? new Date(session.invited_at).toLocaleDateString() : 'N/A'}</strong>
                </div>
                <div class="job-card-section">
                    <span>SCORE</span>
                    <strong>${session.final_score != null ? (session.final_score > 1 ? session.final_score.toFixed(1) + '%' : (session.final_score * 100).toFixed(1) + '%') : 'Not completed'}</strong>
                </div>
            </div>
            <div class="job-card-footer">
                <span><strong>Email:</strong> ${escapeHTML(session.candidate_email || 'N/A')}</span>
                <div class="job-card-actions">
                    <button class="btn btn-primary btn-sm" onclick="launchInterview('${escapeHTML(session.session_id)}')" title="Open interview in new window">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="margin-right: 4px;">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                        Launch Interview
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick="copyInterviewLink('${escapeHTML(session.session_id)}')" title="Copy interview link">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                        Copy Link
                    </button>
                    ${session.status === 'PENDING' || session.status === 'EXPIRED' ? 
                        `<button class="btn btn-ghost btn-sm" onclick="resendInterviewEmail('${escapeHTML(session.candidate_id)}', '${escapeHTML(session.session_id)}')" title="Resend invitation email">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                            </svg>
                            Resend Email
                        </button>` : ''}
                </div>
            </div>
        </div>`;
    }).join('');
    
    container.innerHTML = cards;
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
    await loadAnalyticsDashboard();
}

async function loadJobs() {
    try {
        const response = await apiRequest('/intake/jobs', { method: 'GET' }, API_BASE);
        state.jobs = Array.isArray(response) ? response : response.jobs || [];
    } catch (error) {
        if (!state.jobs.length) {
            state.jobs = [{ id: 'placeholder-job', title: 'Sample Role' }];
        }
        setStatus(`Jobs refresh failed: ${error.message}`, 'error');
    }

    const jobs = state.jobs.length ? state.jobs : [{ id: 'placeholder-job', title: 'Sample Role' }];
    setHTML('jobs-list', _renderJobCards(jobs, '<div class="empty-state">No jobs created yet. Use the form above to create one.</div>').join(''));
    await loadJobsForSelect();
    return jobs;
}

async function loadJobsForSelect() {
    const jobs = state.jobs.length ? state.jobs : [{ id: 'placeholder-job', title: 'Sample Role' }];
    const options = jobs.map((job) => ({ value: job.id, label: job.title || job.name || job.id }));
    ['resume-job-select', 'candidate-job-select', 'screening-job-select', 'outreach-job-filter', 'prescreening-job-filter', 'post-job-select'].forEach((id) => {
        setSelectOptions(id, options, '-- All Jobs --');
    });
}

async function loadCandidates() {
    try {
        const response = await apiRequest('/sourcing/candidates', { method: 'GET' }, API_BASE);
        state.candidates = Array.isArray(response) ? response : [];
    } catch (error) {
        if (!state.candidates.length) {
            state.candidates = [];
        }
        setStatus(`Candidates refresh failed: ${error.message}`, 'error');
    }

    const candidates = state.candidates;
    const cards = candidates.map((candidate) => {
        const skills = Array.isArray(candidate.skills)
            ? candidate.skills.join(', ')
            : String(candidate.skills || '').trim();
        const createdAt = candidate.created_at ? new Date(candidate.created_at) : null;
        const createdLabel = createdAt && !Number.isNaN(createdAt.getTime())
            ? createdAt.toLocaleString()
            : (candidate.created_at || 'n/a');
        return `
            <div class="card">
                <div class="job-card-header">
                    <div class="job-card-title-block">
                        <h3>${escapeHTML(candidate.name || candidate.candidate_name || candidate.id || 'Candidate')}</h3>
                        <div class="job-card-subtitle">${escapeHTML(candidate.current_role || candidate.location || candidate.source || 'Candidate intake record')}</div>
                    </div>
                </div>
                <div class="job-card-sections">
                    <div class="job-card-section">
                        <span>Email</span>
                        <strong>${escapeHTML(candidate.email || 'n/a')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>Phone</span>
                        <strong>${escapeHTML(candidate.phone || 'n/a')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>Experience</span>
                        <strong>${escapeHTML(candidate.experience_years ?? 'n/a')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>Created</span>
                        <strong>${escapeHTML(createdLabel)}</strong>
                    </div>
                </div>
                <div style="margin-top: 0.65rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">
                    <span class="status-tag info">${escapeHTML(candidate.source || 'manual_entry')}</span>
                    ${candidate.job_id ? `<span class="status-tag info">Job ${escapeHTML(candidate.job_id)}</span>` : ''}
                </div>
                <div style="margin-top: 0.85rem; display: grid; gap: 0.35rem;">
                    <div><strong>Skills:</strong> ${escapeHTML(skills || 'n/a')}</div>
                    ${candidate.education ? `<div><strong>Education:</strong> ${escapeHTML(candidate.education)}</div>` : ''}
                    ${candidate.location ? `<div><strong>Location:</strong> ${escapeHTML(candidate.location)}</div>` : ''}
                </div>
                <div class="job-card-footer" style="margin-top: 1rem; justify-content: flex-end;">
                    <div class="job-card-actions">
                        <button class="btn btn-ghost btn-sm job-delete-btn" onclick="deleteCandidate('${escapeHTML(candidate.id || '')}', '${escapeHTML(candidate.name || 'Candidate')}')">Delete</button>
                    </div>
                </div>
            </div>`;
    });
    renderCardsList('candidates-list', cards, '<div class="empty-state">No candidates yet. Upload a resume or enter candidate details.</div>');
    return candidates;
}

async function deleteCandidate(candidateId, candidateName = '') {
    if (!candidateId) {
        setStatus('No candidate selected for deletion', 'warning');
        return null;
    }

    const confirmed = window.confirm(`Delete candidate "${candidateName || candidateId}"? This will remove the candidate and linked records.`);
    if (!confirmed) {
        return null;
    }

    try {
        setStatus('Deleting candidate...', 'info');
        const response = await apiRequest(`/sourcing/candidates/${candidateId}`, {
            method: 'DELETE',
        }, API_BASE);
        setStatus(response.message || 'Candidate deleted', 'success');
        await loadCandidates();
        return response;
    } catch (error) {
        setStatus(`Delete failed: ${error.message}`, 'error');
        throw error;
    }
}

function _renderJobCards(items, emptyMessage) {
    const rows = (items || []).map((item) => {
        const title = item.title || item.job_title || item.name || item.id || 'Untitled';
        const subtitle = [item.department, item.location].filter(Boolean).join(' • ');
        const skills = Array.isArray(item.skills)
            ? item.skills.join(', ')
            : String(item.skills || item.required_skills || '').trim();
        const experience = item.experience_min != null || item.experience_max != null
            ? `${item.experience_min ?? '0'}-${item.experience_max ?? '?'} yrs`
            : (item.experience || 'n/a');
        const salary = item.salary_min != null || item.salary_max != null
            ? `₹${item.salary_min ?? '0'} - ₹${item.salary_max ?? '?'}`
            : (item.salary || 'n/a');
        const status = String(item.status || 'draft').toLowerCase();
        return `
        <div class="job-card">
            <div class="job-card-header">
                <div class="job-card-title-block">
                    <h3>${escapeHTML(title)}</h3>
                    <div class="job-card-subtitle">${escapeHTML(subtitle || 'No department / location')}</div>
                </div>
                <span class="status-tag ${escapeHTML(status)}">${escapeHTML(status)}</span>
            </div>
            <div class="job-card-sections">
                <div class="job-card-section">
                    <span>Skills</span>
                    <strong>${escapeHTML(skills || 'n/a')}</strong>
                </div>
                <div class="job-card-section">
                    <span>Experience</span>
                    <strong>${escapeHTML(experience)}</strong>
                </div>
                <div class="job-card-section">
                    <span>Salary</span>
                    <strong>${escapeHTML(salary)}</strong>
                </div>
            </div>
            <div class="job-card-footer">
                <span><strong>ID:</strong> ${escapeHTML(item.id || 'n/a')}</span>
                <span><strong>Type:</strong> ${escapeHTML(item.employment_type || item.type || 'n/a')}</span>
                <div class="job-card-actions">
                    <button class="btn btn-ghost btn-sm job-delete-btn" onclick="deleteJob('${escapeHTML(item.id || '')}', '${escapeHTML(title)}')">Delete</button>
                </div>
            </div>
        </div>`;
    });
    return rows.length ? rows : [emptyMessage || '<div class="empty-state">No records found.</div>'];
}

async function deleteJob(jobId, jobTitle = '') {
    if (!jobId) {
        setStatus('No job selected for deletion', 'warning');
        return null;
    }

    const confirmed = window.confirm(`Delete job "${jobTitle || jobId}"? This will remove its related records too.`);
    if (!confirmed) {
        return null;
    }

    try {
        setStatus('Deleting job...', 'info');
        const response = await apiRequest(`/intake/jobs/${jobId}`, {
            method: 'DELETE',
        }, API_BASE);
        setStatus(response.message || 'Job deleted', 'success');
        await loadJobs();
        return response;
    } catch (error) {
        setStatus(`Delete failed: ${error.message}`, 'error');
        throw error;
    }
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
        body.innerHTML = rows.length ? rows.map((item) => {
            const skills = Array.isArray(item.skills) ? item.skills.join(', ') : (item.skills || 'None');
            const statusClass = item.status === 'shortlisted' ? 'success' : item.status === 'rejected' ? 'error' : 'info';
            const statusLabel = item.status === 'shortlisted' ? 'SHORTLISTED' : item.status === 'rejected' ? 'REJECTED' : (item.status || 'NEW').toUpperCase();
            
            const job = state.jobs.find(j => j.id === item.job_id);
            const jobTitle = job ? (job.title || job.name) : (item.job_id || 'No Job Assigned');
            
            let scoreDisplay = item.score ?? 'Not scored';
            if (item.score === null || item.score === undefined) {
                if (item.is_duplicate) {
                    scoreDisplay = 'Not scored (Duplicate)';
                } else if (!item.job_id) {
                    scoreDisplay = 'Not scored (No Job)';
                } else if (item.rejection_reason && item.rejection_reason.toLowerCase().includes('no job_id')) {
                    scoreDisplay = 'Not scored (No Job)';
                } else if (item.rejection_reason && item.rejection_reason.toLowerCase().includes('duplicate')) {
                    scoreDisplay = 'Not scored (Duplicate)';
                }
            }
            
            return `
            <div class="job-card">
                <div class="job-card-header">
                    <div class="job-card-title-block">
                        <h3>${escapeHTML(item.name || 'Unknown Candidate')}</h3>
                        <div class="job-card-subtitle">${escapeHTML(item.current_role || item.email || '')}</div>
                    </div>
                    <span class="status-tag ${statusClass}">${statusLabel}</span>
                </div>
                <div style="margin-top: 0.25rem; display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0 4px;">
                    <span class="status-tag info" style="font-size: 0.68rem; padding: 2px 8px;">Job: ${escapeHTML(jobTitle)}</span>
                </div>
                <div class="job-card-sections">
                    <div class="job-card-section">
                        <span>SKILLS</span>
                        <strong>${escapeHTML(skills)}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>SCORE</span>
                        <strong>${scoreDisplay}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>EXPERIENCE</span>
                        <strong>${item.experience_years ?? 0} years</strong>
                    </div>
                </div>
                <div class="job-card-footer">
                    <span><strong>ID:</strong> ${escapeHTML(item.id.substring(0, 12))}...</span>
                    <span><strong>Source:</strong> ${escapeHTML(item.source || 'unknown')}</span>
                    ${item.rejection_reason ? `<span style="color: var(--color-error); font-size: 0.85em;"><strong>Reason:</strong> ${escapeHTML(item.rejection_reason)}</span>` : ''}
                </div>
            </div>`;
        }).join('') : '<div class="empty-state">No screening results yet. Run screening to see results.</div>';
    }
}

function filterOutreachCandidates() {
    const jobId = $('outreach-job-filter')?.value || '';
    const rows = state.stageData.outreachCandidates.filter((item) => !jobId || String(item.job_id || '') === jobId);
    const container = $('outreach-candidates');
    
    if (container) {
        if (!rows.length) {
            container.innerHTML = '<div class="empty-state">No shortlisted candidates yet. Complete screening first.</div>';
            return;
        }
        
        container.innerHTML = rows.map((item) => {
            const emailSent = item.application_status === 'OUTREACH_SENT' || item.application_status === 'PRESCREENING';
            const statusClass = emailSent ? 'success' : 'info';
            const statusLabel = emailSent ? 'EMAIL SENT' : 'READY TO CONTACT';
            
            return `
            <div class="job-card">
                <div class="job-card-header">
                    <div class="job-card-title-block">
                        <h3>${escapeHTML(item.name || 'Unknown Candidate')}</h3>
                        <div class="job-card-subtitle">${escapeHTML(item.email || 'No email')}</div>
                    </div>
                    <span class="status-tag ${statusClass}">${statusLabel}</span>
                </div>
                <div class="job-card-sections">
                    <div class="job-card-section">
                        <span>JOB</span>
                        <strong>${escapeHTML(item.job_title || 'N/A')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>PHONE</span>
                        <strong>${escapeHTML(item.phone || 'N/A')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>SCORE</span>
                        <strong>${item.score ?? 'N/A'}</strong>
                    </div>
                </div>
                <div class="job-card-footer">
                    <span><strong>Location:</strong> ${escapeHTML(item.location || 'N/A')}</span>
                    <div class="job-card-actions">
                        ${!emailSent
                            ? `<button class="btn btn-primary btn-sm" onclick="sendOutreach('${escapeHTML(item.id)}','${escapeHTML(item.job_id)}')">Send Email</button>`
                            : `<span style="color: var(--color-success); font-size: 0.9em;">✓ Email Sent</span>
                               <button class="btn btn-ghost btn-sm" onclick="resendOutreach('${escapeHTML(item.id)}','${escapeHTML(item.job_id)}')" title="Resend outreach email">
                                 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="margin-right:4px;"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                                 Resend Email
                               </button>`
                        }
                    </div>
                </div>
            </div>`;
        }).join('');
    }
}

function filterPrescreeningSessions() {
    const jobId = $('prescreening-job-filter')?.value || '';
    const rows = state.stageData.prescreeningSessions.filter((item) => !jobId || String(item.job_id || '') === jobId);
    const tableBody = $('prescreening-candidates');
    if (tableBody) {
        tableBody.innerHTML = _renderTableRows(rows, [
            (item) => escapeHTML(item.candidate_name || item.name || item.candidate_id || ''),
            (item) => escapeHTML(item.candidate_email || item.email || ''),
            (item) => escapeHTML(item.job_title || item.job_id || ''),
            (item) => escapeHTML(item.status || ''),
        ], 4);
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
            const maxCount = funnel.length ? funnel[0].count : 1;
            funnelMetrics.innerHTML = funnel.length ? `
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Stage</th>
                                <th style="text-align: right; width: 140px;">Candidates</th>
                                <th>Conversion Rate</th>
                                <th style="text-align: right; width: 180px;">Drop-off</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${funnel.map((stage, index) => {
                                const pct = maxCount > 0 ? (stage.count / maxCount * 100).toFixed(1) : 0;
                                const dropoffHtml = index > 0 && stage.dropoff_pct > 0 
                                    ? `<span class="funnel-drop-badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="11" height="11" style="margin-right: 4px;"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>${stage.dropoff_pct}% drop-off</span>` 
                                    : `<span style="opacity: 0.4;">—</span>`;
                                
                                return `
                                    <tr>
                                        <td>
                                            <div style="display: flex; align-items: center; gap: 10px;">
                                                <span class="funnel-stage-num" style="width: 24px; height: 24px; font-size: 0.75rem; box-shadow: none;">${index + 1}</span>
                                                <strong style="color: var(--text-primary); font-size: 0.95rem;">${escapeHTML(stage.stage)}</strong>
                                            </div>
                                        </td>
                                        <td style="text-align: right;">
                                            <strong style="font-size: 0.95rem; color: var(--text-primary);">${stage.count}</strong>
                                        </td>
                                        <td>
                                            <div style="display: flex; flex-direction: column; gap: 4px; max-width: 220px;">
                                                <div class="funnel-progress-bg" style="margin: 0;">
                                                    <div class="funnel-progress-fill" style="width: ${pct}%;"></div>
                                                </div>
                                                <span style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 500;">${pct}% reached</span>
                                            </div>
                                        </td>
                                        <td style="text-align: right;">
                                            ${dropoffHtml}
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<div class="empty-state">No funnel metrics available</div>';
        }
        setStatus('Analytics dashboard loaded', 'success');
        return { dashboard, jobs, timeToHire, forecast };
    } catch (error) {
        setStatus(`Analytics load failed: ${error.message}`, 'error');
        return null;
    }
}

// Stage 8 functions
async function loadOffers() {
    try {
        const response = await apiRequest('/offer/list', { method: 'GET' }, API_BASE);
        const offers = Array.isArray(response.offers) ? response.offers : [];
        state.stageData.offers = offers;
        setText('stat-total-offers', offers.length);
        setText('stat-accepted-offers', offers.filter((offer) => offer.status === 'accepted').length);
        setText('stat-pending-offers', offers.filter((offer) => offer.status === 'pending').length);
        setText('stat-negotiations', offers.filter((offer) => offer.status === 'negotiation').length);
        
        // Render offer cards
        const offerCards = offers.length ? offers.map((offer) => {
            const statusClass = offer.status === 'accepted' ? 'success' : offer.status === 'pending' ? 'info' : 'warning';
            return `
            <div class="job-card">
                <div class="job-card-header">
                    <div class="job-card-title-block">
                        <h3>Offer #${escapeHTML(offer.id.substring(6, 14))}</h3>
                        <div class="job-card-subtitle">${escapeHTML(offer.application_id || 'N/A')}</div>
                    </div>
                    <span class="status-tag ${statusClass}">${escapeHTML((offer.status || 'pending').toUpperCase())}</span>
                </div>
                <div class="job-card-sections">
                    <div class="job-card-section">
                        <span>SALARY</span>
                        <strong>${escapeHTML(offer.currency || 'USD')} ${offer.offered_salary ? offer.offered_salary.toLocaleString() : '0'}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>START DATE</span>
                        <strong>${escapeHTML(offer.start_date || 'TBD')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>OFFERED</span>
                        <strong>${offer.offered_at ? new Date(offer.offered_at).toLocaleDateString() : 'N/A'}</strong>
                    </div>
                </div>
                <div class="job-card-footer">
                    <span><strong>Offer ID:</strong> ${escapeHTML(offer.id)}</span>
                    <div class="job-card-actions">
                        ${offer.status === 'pending' ? `<button class="btn btn-primary btn-sm" onclick="acceptOffer('${escapeHTML(offer.id)}')">Accept Offer</button>` : ''}
                        ${offer.status === 'pending' ? `<button class="btn btn-ghost btn-sm" onclick="dispatchOffer('${escapeHTML(offer.id)}')">Send Email</button>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('') : '<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="48" height="48" style="opacity: 0.3; margin-bottom: 1rem;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><p>No offers generated yet</p><span style="opacity: 0.7; font-size: 0.9em;">Offers will appear here after interview completion</span></div>';
        
        const container = $('offers-list');
        if (container) container.innerHTML = offerCards;
        
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
        
        // Calculate pending tasks
        let totalPendingTasks = 0;
        for (const item of onboarding) {
            try {
                const tasksResponse = await apiRequest(`/onboarding/${item.id}/tasks`, { method: 'GET' }, API_BASE);
                const tasks = Array.isArray(tasksResponse.tasks) ? tasksResponse.tasks : [];
                totalPendingTasks += tasks.filter(t => t.status === 'pending').length;
            } catch (e) {
                // Ignore errors for task count
            }
        }
        setText('stat-pending-tasks', totalPendingTasks);
        
        // Render onboarding cards
        const onboardingCards = onboarding.length ? onboarding.map((item) => {
            const statusClass = item.status === 'completed' ? 'success' : item.status === 'pending' ? 'info' : 'warning';
            return `
            <div class="job-card">
                <div class="job-card-header">
                    <div class="job-card-title-block">
                        <h3>${escapeHTML(item.candidate_name || `Candidate #${item.candidate_id || 'Unknown'}`)}</h3>
                        <div class="job-card-subtitle">${escapeHTML(item.job_title || 'Position TBD')}</div>
                    </div>
                    <span class="status-tag ${statusClass}">${escapeHTML((item.status || 'pending').toUpperCase())}</span>
                </div>
                <div class="job-card-sections">
                    <div class="job-card-section">
                        <span>CANDIDATE ID</span>
                        <strong>${escapeHTML(item.candidate_id || 'N/A')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>OFFER ID</span>
                        <strong>${escapeHTML(item.offer_id ? item.offer_id.substring(6, 14) : 'N/A')}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>CREATED</span>
                        <strong>${item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}</strong>
                    </div>
                </div>
                <div class="job-card-footer">
                    <span><strong>Onboarding ID:</strong> ${escapeHTML(item.id)}</span>
                    <div class="job-card-actions">
                        <button class="btn btn-ghost btn-sm" onclick="displayTasksInPanel('${escapeHTML(item.id)}')">View Tasks</button>
                        <button class="btn btn-ghost btn-sm job-delete-btn" onclick="deleteOnboarding('${escapeHTML(item.id)}', '${escapeHTML(item.candidate_name || '')}')">Delete</button>
                    </div>
                </div>
            </div>`;
        }).join('') : '<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="48" height="48" style="opacity: 0.3; margin-bottom: 1rem;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><p>No onboarding records yet</p><span style="opacity: 0.7; font-size: 0.9em;">Select a candidate and generate tasks to get started</span></div>';
        
        const container = $('onboarding-list');
        if (container) container.innerHTML = onboardingCards;
        
        setStatus('Onboarding data loaded', 'success');
        return { onboarding };
    } catch (error) {
        setStatus(`Onboarding load failed: ${error.message}`, 'error');
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
        await loadJobs();

        if (result && content) {
            result.classList.remove('hidden');
            content.innerHTML = `
                <div style="display: grid; gap: 0.75rem;">
                    <div class="status-tag success">${response.message || 'Job created successfully'}</div>
                    <div><strong>Job ID:</strong> ${jobId}</div>
                    <div><strong>Title:</strong> ${title}</div>
                    <div><strong>Description:</strong></div>
                    <div class="markdown-content job-description-content">${renderMarkdown(response.description || 'No description returned.')}</div>
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

async function postJob(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }

    const jobId = $('post-job-select')?.value || '';
    const platforms = Array.from(document.querySelectorAll('input[name="platform"]:checked')).map((input) => input.value).filter(Boolean);
    const result = $('posting-result');
    const content = $('posting-content');

    if (!jobId) {
        setStatus('Select a job before posting', 'warning');
        return null;
    }

    if (!platforms.length) {
        setStatus('Select at least one platform', 'warning');
        return null;
    }

    try {
        setStatus('Posting job to selected platforms...', 'info');
        const response = await apiRequest('/intake/post-job', {
            method: 'POST',
            body: JSON.stringify({ job_id: jobId, platforms }),
        }, API_BASE);

        if (result && content) {
            result.classList.remove('hidden');
            const postingCards = (response.postings || []).map((posting) => `
                <div class="card">
                    <h3>${escapeHTML(posting.platform || 'Platform')}</h3>
                    <div class="text-muted">${escapeHTML(posting.status || 'unknown')}</div>
                    <div style="margin-top: 0.75rem; display: grid; gap: 0.35rem;">
                        ${renderKeyValueList([
                            ['External ID', posting.external_id || 'n/a'],
                            ['URL', posting.post_url || posting.manual_url || 'n/a'],
                            ['Note', posting.note || posting.error || ''],
                        ])}
                    </div>
                </div>`).join('');
            content.innerHTML = `
                <div class="status-tag success">${escapeHTML(response.message || 'Job posted')}</div>
                <div style="display:grid; gap:1rem; margin-top: 1rem;">${postingCards}</div>`;
        }

        setStatus(response.message || 'Job posted successfully', 'success');
        await loadJobs();
        return response;
    } catch (error) {
        if (result && content) {
            result.classList.remove('hidden');
            content.innerHTML = `<div class="status-tag error">Failed to post job: ${escapeHTML(error.message)}</div>`;
        }
        setStatus(`Job posting failed: ${error.message}`, 'error');
        throw error;
    }
}

async function addCandidateForm(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    const candidateName = $('candidate-name')?.value?.trim() || '';
    const candidateEmail = $('candidate-email')?.value?.trim() || '';
    const candidatePhone = $('candidate-phone')?.value?.trim() || '';
    const candidateLocation = $('candidate-location')?.value?.trim() || '';
    const candidateRole = $('candidate-role')?.value?.trim() || '';
    const experienceYears = Number.parseFloat($('candidate-experience')?.value || '0');
    const candidateEducation = $('candidate-education')?.value || '';
    const candidateSkills = ($('candidate-skills')?.value || '')
        .split(',')
        .map((skill) => skill.trim())
        .filter(Boolean);
    const sourceProfileUrl = $('candidate-linkedin')?.value?.trim() || '';
    const jobId = $('candidate-job-select')?.value || '';

    if (!candidateName || !candidateEmail || !candidatePhone || !jobId) {
        setStatus('Please fill the required candidate fields before adding.', 'warning');
        return null;
    }

    try {
        setStatus('Saving candidate...', 'info');
        const response = await apiRequest('/sourcing/add-candidate', {
            method: 'POST',
            body: JSON.stringify({
                name: candidateName,
                email: candidateEmail,
                phone: candidatePhone,
                location: candidateLocation,
                current_role: candidateRole,
                experience_years: Number.isFinite(experienceYears) ? experienceYears : 0,
                skills: candidateSkills,
                education: candidateEducation || null,
                source_profile_url: sourceProfileUrl || null,
                job_id: jobId,
            }),
        }, API_BASE);

        const form = $('candidate-form');
        if (form && typeof form.reset === 'function') {
            form.reset();
        }
        await loadJobsForSelect();
        await loadCandidates();
        await loadScreeningData();
        return response;
    } catch (error) {
        setStatus(`Candidate add failed: ${error.message}`, 'error');
        throw error;
    }
}

async function runScreening(forceRescreen = false) {
    try {
        const btn = $('btn-run-screening');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" style="animation: spin 1s linear infinite;"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Running...`;
        }
        
        const jobId = $('screening-job-select')?.value || null;
        const response = await apiRequest('/screening/run', {
            method: 'POST',
            body: JSON.stringify({ job_id: jobId, force_rescreen: !!forceRescreen }),
        }, API_BASE);
        
        showToast(response.message || 'Screening completed successfully', 'success');
        await loadScreeningData();
        
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Screening`;
        }
        
        return response;
    } catch (error) {
        const btn = $('btn-run-screening');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Screening`;
        }
        showToast(`Screening failed: ${error.message}`, 'error');
        throw error;
    }
}

// Load screening data
async function loadScreeningData() {
    try {
        const statsResponse = await apiRequest('/screening/stats', { method: 'GET' }, API_BASE);
        
        // Update stats
        setText('stat-total-candidates', statsResponse.total_candidates || 0);
        setText('stat-screened', statsResponse.screened || 0);
        setText('stat-shortlisted', statsResponse.shortlisted || 0);
        setText('stat-rejected', statsResponse.rejected || 0);
        setText('stat-duplicates', statsResponse.duplicates || 0);
        setText('stat-avg-score', (statsResponse.avg_score || 0).toFixed(1));
        
        // Load candidates with screening results - API returns array directly
        const candidatesResponse = await apiRequest('/screening/candidates', { method: 'GET' }, API_BASE);
        state.stageData.screeningCandidates = Array.isArray(candidatesResponse) ? candidatesResponse : [];
        
        // Populate job filter
        await loadJobsForSelect();
        const jobs = state.jobs.length ? state.jobs : [{ id: 'placeholder-job', title: 'Sample Role' }];
        setSelectOptions('screening-job-select', jobs.map((job) => ({ value: job.id, label: job.title || job.name || job.id })), '-- All Jobs --');
        
        // Display results
        filterCandidates();
        
        return statsResponse;
    } catch (error) {
        console.error('Failed to load screening data:', error);
        showToast(`Failed to load screening data: ${error.message}`, 'error');
    }
}

async function sendOutreach(candidateId, jobId) {
    try {
        const response = await apiRequest('/outreach/send', {
            method: 'POST',
            body: JSON.stringify({ candidate_id: candidateId, job_id: jobId }),
        }, API_BASE);
        showToast(response.message || 'Outreach sent successfully', 'success');
        await loadOutreachData();
        return response;
    } catch (error) {
        showToast(`Outreach failed: ${error.message}`, 'error');
        throw error;
    }
}

async function resendOutreach(candidateId, jobId) {
    try {
        showToast('Resending outreach email...', 'info');
        const response = await apiRequest('/outreach/resend', {
            method: 'POST',
            body: JSON.stringify({ candidate_id: candidateId, job_id: jobId }),
        }, API_BASE);
        showToast(response.message || 'Email resent successfully', 'success');
        await loadOutreachData();
        return response;
    } catch (error) {
        showToast(`Resend failed: ${error.message}`, 'error');
        throw error;
    }
}

// Load outreach data
async function loadOutreachData() {
    try {
        const response = await apiRequest('/outreach/candidates', { method: 'GET' }, API_BASE);
        state.stageData.outreachCandidates = Array.isArray(response) ? response : [];
        
        // Populate job filter
        await loadJobsForSelect();
        const jobs = state.jobs.length ? state.jobs : [{ id: 'placeholder-job', title: 'Sample Role' }];
        setSelectOptions('outreach-job-filter', jobs.map((job) => ({ value: job.id, label: job.title || job.name || job.id })), '-- All Jobs --');
        
        // Display results
        filterOutreachCandidates();
        
        return response;
    } catch (error) {
        console.error('Failed to load outreach data:', error);
        showToast(`Failed to load outreach data: ${error.message}`, 'error');
    }
}

// Load prescreening data
async function loadPrescreeningData() {
    try {
        // Fetch all candidates for the dropdown
        const candidates = await apiRequest('/prescreening/all-candidates', { method: 'GET' }, API_BASE);
        
        const dropdown = $('prescreening-candidate-select');
        if (dropdown) {
            dropdown.innerHTML = '<option value="">-- Choose a Candidate --</option>' + 
                candidates.map(c => `<option value="${escapeHTML(c.id)}">${escapeHTML(c.name)} (${escapeHTML(c.job_title)})</option>`).join('');
        }
        
        // Fetch prescreening sessions to display in table
        const sessions = await apiRequest('/prescreening/sessions', { method: 'GET' }, API_BASE);
        state.stageData.prescreeningSessions = sessions;

        // ── Update analytics stat cards ──────────────────────────────────
        const totalSessions = sessions.length;
        const completedSessions = sessions.filter(s => s.status === 'COMPLETED').length;
        const passedSessions = sessions.filter(s => s.verdict === 'PASS' || s.verdict === 'BORDERLINE').length;
        const scoredSessions = sessions.filter(s => s.avg_score != null);
        const avgScore = scoredSessions.length > 0
            ? (scoredSessions.reduce((sum, s) => sum + s.avg_score, 0) / scoredSessions.length).toFixed(1)
            : '0.0';

        setText('stat-total-sessions', totalSessions);
        setText('stat-sessions-completed', completedSessions);
        setText('stat-sessions-passed', passedSessions);
        setText('stat-avg-prescreening-score', avgScore);

        // Mini header stats
        setText('prescreening-total', totalSessions);
        setText('prescreening-completed', completedSessions);
        setText('prescreening-passed', passedSessions);
        // ─────────────────────────────────────────────────────────────────
        
        // Render sessions table
        const tableBody = $('prescreening-table-body');
        if (tableBody) {
            if (!sessions || sessions.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="9" class="empty-state">No prescreening sessions yet. Select a candidate above to start.</td></tr>';
            } else {
                tableBody.innerHTML = sessions.map(session => {
                    const statusClass = session.status === 'COMPLETED' ? 'success' : session.status === 'IN_PROGRESS' ? 'warning' : 'info';
                    const createdDate = session.created_at ? new Date(session.created_at).toLocaleDateString() : 'N/A';
                    
                    return `
                        <tr>
                            <td>${escapeHTML(session.candidate_name || 'Unknown')}</td>
                            <td>${escapeHTML(session.candidate_email || 'N/A')}</td>
                            <td>${escapeHTML(session.job_title || 'Unknown')}</td>
                            <td><span class="status-tag ${statusClass}">${escapeHTML(session.status)}</span></td>
                            <td>${session.answered_questions} / ${session.total_questions}</td>
                            <td>${session.avg_score != null ? session.avg_score.toFixed(1) : 'N/A'}</td>
                            <td>${session.verdict ? `<span class="status-tag ${session.verdict === 'PASS' ? 'success' : session.verdict === 'BORDERLINE' ? 'warning' : 'error'}">${escapeHTML(session.verdict)}</span>` : 'N/A'}</td>
                            <td>${createdDate}</td>
                            <td>
                                <button class="btn btn-ghost btn-sm" onclick="viewSessionDetails('${escapeHTML(session.session_id)}')" title="View Details">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                        <circle cx="12" cy="12" r="3"/>
                                    </svg>
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
        
        // Hide other views/success views initially
        const demoContainer = $('candidate-demo-container');
        if (demoContainer) demoContainer.style.display = 'none';
        const successContainer = $('prescreening-success-container');
        if (successContainer) successContainer.style.display = 'none';
        const loadingContainer = $('prescreening-loading');
        if (loadingContainer) loadingContainer.style.display = 'none';
        
    } catch (error) {
        console.error('Failed to load prescreening data:', error);
        showToast(`Failed to load prescreening data: ${error.message}`, 'error');
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

let currentPrescreeningSession = null;
let currentPrescreeningQuestions = [];

async function onPrescreeningCandidateChange() {
    const select = $('prescreening-candidate-select');
    const candidateId = select ? select.value : '';
    
    const demoContainer = $('candidate-demo-container');
    const successContainer = $('prescreening-success-container');
    const loadingContainer = $('prescreening-loading');
    const questionsContainer = $('demo-questions-container');
    
    if (!candidateId) {
        if (demoContainer) demoContainer.style.display = 'none';
        if (successContainer) successContainer.style.display = 'none';
        if (loadingContainer) loadingContainer.style.display = 'none';
        return;
    }
    
    // Hide containers and show loading
    if (demoContainer) demoContainer.style.display = 'none';
    if (successContainer) successContainer.style.display = 'none';
    if (loadingContainer) {
        loadingContainer.style.display = 'block';
        setText('prescreening-loading-text', 'Generating personalised questions for this role...');
    }
    
    try {
        const response = await apiRequest('/prescreening/start-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_id: candidateId })
        }, API_BASE);
        
        if (response.success) {
            currentPrescreeningSession = response.session_id;
            currentPrescreeningQuestions = response.questions.map(q => q.question);
            
            // Set header
            setText('prescreening-job-title-header', `🤖 AI Prescreening Interview — ${response.job_title}`);
            
            // Render questions
            if (questionsContainer) {
                questionsContainer.innerHTML = response.questions.map((q, index) => `
                    <div class="demo-question-card" style="background: var(--bg-surface); border: 1px solid var(--border); padding: 20px; border-radius: 8px; margin-bottom: 16px; box-shadow: var(--shadow-sm);">
                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                            <span style="background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; margin-right: 12px;">
                                ${index + 1}
                            </span>
                            <h4 style="margin: 0; font-size: 1rem; color: var(--text-primary);">${escapeHTML(q.question)}</h4>
                        </div>
                        <textarea 
                            id="demo-answer-${q.id}" 
                            placeholder="Type your answer here (minimum ${q.minChars} characters)..." 
                            style="width: 100%; min-height: 100px; padding: 12px; background: var(--bg-surface); border: 2px solid var(--border); border-radius: 6px; color: var(--text-primary); font-family: inherit; font-size: 0.95rem; resize: vertical;"
                            onkeyup="updateCharCount(${q.id}, ${q.minChars})"
                        ></textarea>
                        <div style="display: flex; justify-content: flex-end; margin-top: 8px; font-size: 0.85rem; color: var(--text-secondary);">
                            <span id="status-${q.id}"></span>
                        </div>
                    </div>
                `).join('') + `
                    <div style="margin-top: 24px; text-align: center;">
                        <button class="btn btn-primary btn-lg" onclick="submitCustomPrescreening()" style="padding: 12px 32px;">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" style="margin-right: 6px;">
                                <polyline points="20 6 9 17 4 12"/>
                            </svg>
                            Submit Prescreening Answers
                        </button>
                    </div>
                `;
            }
            
            // Show candidate view
            if (loadingContainer) loadingContainer.style.display = 'none';
            if (demoContainer) demoContainer.style.display = 'block';
        } else {
            throw new Error(response.message || 'Failed to start session');
        }
    } catch (error) {
        console.error('Failed to start prescreening session:', error);
        showToast(`Error starting prescreening: ${error.message}`, 'error');
        if (loadingContainer) loadingContainer.style.display = 'none';
    }
}

// Update character count for questions
function updateCharCount(questionId, minChars) {
    const textarea = $(`demo-answer-${questionId}`);
    const statusSpan = $(`status-${questionId}`);
    
    if (!textarea) return;
    
    const length = textarea.value.length;
    
    if (statusSpan) {
        if (length >= minChars) {
            statusSpan.textContent = '✓ Complete';
            statusSpan.style.color = '#10b981';
        } else {
            statusSpan.textContent = `${minChars - length} more needed`;
            statusSpan.style.color = '#f59e0b';
        }
    }
}

async function submitCustomPrescreening() {
    if (!currentPrescreeningSession) {
        showToast('No active session. Please select a candidate first.', 'error');
        return;
    }
    
    const answers = [];
    let allAnswered = true;
    
    for (let i = 1; i <= 6; i++) {
        const textarea = $(`demo-answer-${i}`);
        if (!textarea || textarea.value.length < 100) {
            allAnswered = false;
            break;
        }
        answers.push({
            question_index: i - 1,
            question: currentPrescreeningQuestions[i - 1],
            answer: textarea.value
        });
    }
    
    if (!allAnswered) {
        showToast('Please answer all questions with at least 100 characters', 'error');
        return;
    }
    
    const demoContainer = $('candidate-demo-container');
    const loadingContainer = $('prescreening-loading');
    const successContainer = $('prescreening-success-container');
    
    if (demoContainer) demoContainer.style.display = 'none';
    if (loadingContainer) {
        loadingContainer.style.display = 'block';
        setText('prescreening-loading-text', 'Submitting responses and running AI evaluation...');
    }
    
    try {
        const response = await apiRequest('/prescreening/submit-answers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentPrescreeningSession,
                answers: answers
            })
        }, API_BASE);
        
        if (response.success) {
            if (loadingContainer) loadingContainer.style.display = 'none';
            
            // Populate success view
            const verdictMsg = $('prescreening-verdict-msg');
            if (verdictMsg) {
                const emoji = response.verdict === 'PASS' ? '🎉' : response.verdict === 'BORDERLINE' ? '⚠️' : '❌';
                verdictMsg.textContent = `${emoji} Result: ${response.verdict}  —  Score: ${response.avg_score.toFixed(1)} / 4.0`;
            }
            
            // Show session ID box only if candidate passed
            const passDetails = $('prescreening-pass-details');
            const sessionDisplay = $('prescreening-session-id-display');
            if (passDetails && response.verdict === 'PASS' && response.interview_session_id) {
                if (sessionDisplay) sessionDisplay.textContent = response.interview_session_id;
                passDetails.style.display = 'block';
            } else if (passDetails) {
                passDetails.style.display = 'none';
            }
            
            if (successContainer) successContainer.style.display = 'block';
            showToast('Prescreening evaluation completed successfully!', 'success');
            
            // Reload the prescreening sessions table to show the new result
            await loadPrescreeningData();
        } else {
            throw new Error(response.message || 'Submission failed');
        }
    } catch (error) {
        console.error('Failed to submit answers:', error);
        showToast(`Error evaluating answers: ${error.message}`, 'error');
        if (loadingContainer) loadingContainer.style.display = 'none';
        if (demoContainer) demoContainer.style.display = 'block';
    }
}

function resetPrescreeningForm() {
    currentPrescreeningSession = null;
    currentPrescreeningQuestions = [];
    const sel = $('prescreening-candidate-select');
    if (sel) sel.value = '';
    const els = ['candidate-demo-container', 'prescreening-loading', 'prescreening-success-container', 'prescreening-pass-details'];
    els.forEach(id => { const el = $(id); if (el) el.style.display = 'none'; });
    const qc = $('demo-questions-container');
    if (qc) qc.innerHTML = '';
}

async function viewSessionDetails(sessionId) {
    try {
        const sessions = state.stageData.prescreeningSessions || [];
        const session = sessions.find(s => s.session_id === sessionId);
        
        if (!session) {
            showToast('Session not found', 'error');
            return;
        }
        
        const detailsPanel = $('session-details-panel');
        const detailsContent = $('session-details-content');
        
        if (!detailsPanel || !detailsContent) {
            showToast('Details panel not found', 'error');
            return;
        }
        
        // Build details HTML
        let html = `
            <div style="display: grid; gap: 1rem;">
                <div class="info-box">
                    <div>
                        <strong>Session ID:</strong> ${escapeHTML(session.session_id)}<br>
                        <strong>Candidate:</strong> ${escapeHTML(session.candidate_name)} (${escapeHTML(session.candidate_email)})<br>
                        <strong>Job:</strong> ${escapeHTML(session.job_title)}<br>
                        <strong>Status:</strong> <span class="status-tag ${session.status === 'COMPLETED' ? 'success' : 'warning'}">${escapeHTML(session.status)}</span><br>
                        <strong>Created:</strong> ${session.created_at ? new Date(session.created_at).toLocaleString() : 'N/A'}<br>
                        ${session.completed_at ? `<strong>Completed:</strong> ${new Date(session.completed_at).toLocaleString()}<br>` : ''}
                        ${session.verdict ? `<strong>Verdict:</strong> <span class="status-tag ${session.verdict === 'PASS' ? 'success' : session.verdict === 'BORDERLINE' ? 'warning' : 'error'}">${escapeHTML(session.verdict)}</span><br>` : ''}
                        ${session.avg_score != null ? `<strong>Score:</strong> ${session.avg_score.toFixed(1)} / 4.0<br>` : ''}
                    </div>
                </div>
                <h4>Questions (${session.total_questions})</h4>
        `;
        
        // Show questions
        if (session.questions && session.questions.length > 0) {
            session.questions.forEach((q, idx) => {
                html += `<div class="card"><strong>Q${idx + 1}:</strong> ${escapeHTML(q)}</div>`;
            });
        } else {
            html += '<div class="empty-state">No questions available</div>';
        }
        
        html += '</div>';
        
        detailsContent.innerHTML = html;
        detailsPanel.style.display = 'block';
        
    } catch (error) {
        console.error('Failed to view session details:', error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

function closeSessionDetails() {
    const panel = $('session-details-panel');
    if (panel) panel.style.display = 'none';
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

// ══════════════════════════════════════════════════════════════════
// Stage 6: Interview & Evaluation Functions
// ══════════════════════════════════════════════════════════════════

async function submitInterviewData(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    
    const candidateId = $('interview-candidate-select')?.value;
    const phase = $('interview-phase')?.value;
    const finalScore = parseOptionalFloat('interview-final-score');
    
    if (!candidateId) {
        showToast('Please select a candidate', 'error');
        return;
    }
    
    if (finalScore === null || finalScore < 0 || finalScore > 1) {
        showToast('Final score must be between 0.0 and 1.0', 'error');
        return;
    }
    
    const contentScore = parseOptionalFloat('interview-content-score');
    const behaviorScore = parseOptionalFloat('interview-behavior-score');
    if ((contentScore !== null && (contentScore < 0 || contentScore > 1)) ||
        (behaviorScore !== null && (behaviorScore < 0 || behaviorScore > 1))) {
        showToast('Content and behavior scores must be between 0.0 and 1.0', 'error');
        return;
    }

    const behavioralSnapshotRaw = $('interview-behavioral-snapshot')?.value?.trim();
    let behavioralSnapshot = null;
    if (behavioralSnapshotRaw) {
        try {
            behavioralSnapshot = JSON.parse(behavioralSnapshotRaw);
        } catch {
            showToast('Behavioral snapshot must be valid JSON', 'error');
            return;
        }
    }
    
    const payload = {
        candidate_id: candidateId,
        session_id: getOptionalText('interview-session-id'),
        interview_id: getOptionalText('interview-id'),
        phase,
        current_turn: parseOptionalInt('interview-current-turn'),
        total_turns: parseOptionalInt('interview-total-turns'),
        turn_number: parseOptionalInt('interview-turn-number'),
        question_text: getOptionalText('interview-question-text'),
        question_difficulty: getOptionalText('interview-question-difficulty'),
        candidate_response: getOptionalText('interview-candidate-response'),
        response_time_sec: parseOptionalFloat('interview-response-time'),
        content_score: contentScore,
        behavior_score: behaviorScore,
        final_score: finalScore,
        intent: getOptionalText('interview-intent'),
        behavioral_snapshot: behavioralSnapshot,
        is_followup: Boolean($('interview-is-followup')?.checked),
        followup_number: parseOptionalInt('interview-followup-number') || 0,
        interviewer_name: getOptionalText('interview-interviewer'),
        interview_date: getOptionalText('interview-date'),
        evaluator_notes: getOptionalText('interview-evaluator-notes'),
        recommendation: getOptionalText('interview-recommendation')
    };
    
    const submitBtn = $('btn-submit-interview');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading"></span> Submitting...';
    }
    
    try {
        const response = await apiRequest('/evaluation/submit-interview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }, API_BASE);
        
        showToast('Interview evaluation submitted successfully!', 'success');
        
        // Reset form
        $('interview-data-form')?.reset();
        
        // Reload evaluation results
        await loadEvaluationResults();
        
    } catch (error) {
        console.error('Failed to submit interview data:', error);
        showToast(`Submission failed: ${error.message}`, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                    <path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/>
                </svg>
                Submit & Generate Evaluation
            `;
        }
    }
}

async function loadEvaluationResults() {
    try {
        const response = await apiRequest('/evaluation/results', { method: 'GET' }, API_BASE);
        const evaluations = Array.isArray(response) ? response : response.evaluations || [];
        
        // Update stats
        const totalEvals = evaluations.length;
        const passed = evaluations.filter(e => Number(e.final_score || 0) >= 0.6).length;
        const failed = totalEvals - passed;
        const avgScore = totalEvals > 0 
            ? ((evaluations.reduce((sum, e) => sum + Number(e.final_score || 0), 0) / totalEvals) * 100).toFixed(1)
            : '0.0';
        
        setText('stat-total-evaluations', totalEvals);
        setText('stat-passed-interviews', passed);
        setText('stat-failed-interviews', failed);
        setText('stat-eval-avg-score', avgScore);
        
        // Render evaluation cards
        const container = $('evaluation-results-list');
        if (!container) return;
        
        if (evaluations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="48" height="48" style="opacity: 0.3; margin-bottom: 1rem;">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    <p>No evaluation results yet</p>
                    <span style="opacity: 0.7; font-size: 0.9em;">Submit interview data above to generate evaluation reports</span>
                </div>
            `;
            return;
        }
        
        const cards = evaluations.map(evaluation => {
            const passStatus = evaluation.final_score >= 240 ? 'PASS' : 'FAIL';
            const statusClass = passStatus === 'PASS' ? 'success' : 'error';
            const percentage = ((evaluation.final_score / 400) * 100).toFixed(1);
            const createdDate = evaluation.created_at ? new Date(evaluation.created_at).toLocaleDateString() : 'N/A';
            
            return `
                <div class="job-card">
                    <div class="job-card-header">
                        <div class="job-card-title-block">
                            <h3>${escapeHTML(evaluation.candidate_name || 'Unknown Candidate')}</h3>
                            <div class="job-card-subtitle">${escapeHTML(evaluation.job_title || '')} — ${escapeHTML(evaluation.phase || 'Interview')}</div>
                        </div>
                        <span class="status-tag ${statusClass}">${passStatus}</span>
                    </div>
                    <div class="job-card-sections">
                        <div class="job-card-section">
                            <span>FINAL SCORE</span>
                            <strong>${evaluation.final_score} / 400 (${percentage}%)</strong>
                        </div>
                        <div class="job-card-section">
                            <span>TECHNICAL</span>
                            <strong>${evaluation.technical_score}/100</strong>
                        </div>
                        <div class="job-card-section">
                            <span>COMMUNICATION</span>
                            <strong>${evaluation.communication_score}/100</strong>
                        </div>
                        <div class="job-card-section">
                            <span>CONFIDENCE</span>
                            <strong>${evaluation.confidence_score}/100</strong>
                        </div>
                        <div class="job-card-section">
                            <span>PROBLEM SOLVING</span>
                            <strong>${evaluation.problem_solving_score}/100</strong>
                        </div>
                        <div class="job-card-section">
                            <span>PENALTIES</span>
                            <strong>-${evaluation.penalty_points}</strong>
                        </div>
                    </div>
                    ${evaluation.summary ? `
                        <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-surface); border-radius: 8px; border-left: 3px solid var(--accent-blue);">
                            <strong style="display: block; margin-bottom: 0.5rem; font-size: 0.9rem; opacity: 0.8;">Summary:</strong>
                            <p style="margin: 0; line-height: 1.5; white-space: pre-wrap;">${escapeHTML(evaluation.summary)}</p>
                        </div>
                    ` : ''}
                    <div class="job-card-footer">
                        <span><strong>Date:</strong> ${createdDate}</span>
                        ${evaluation.interviewer_name ? `<span><strong>Interviewer:</strong> ${escapeHTML(evaluation.interviewer_name)}</span>` : ''}
                        <div class="job-card-actions">
                            <button class="btn btn-ghost btn-sm" onclick="viewEvaluationDetails('${escapeHTML(evaluation.id)}')" title="View Full Report">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                    <circle cx="12" cy="12" r="3"/>
                                </svg>
                                View Details
                            </button>
                            <button class="btn btn-ghost btn-sm" onclick="downloadInterviewPDF('${escapeHTML(evaluation.session_id)}')" title="Download PDF Report">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                    <polyline points="14 2 14 8 20 8"/>
                                    <line x1="16" y1="13" x2="8" y2="13"/>
                                    <line x1="16" y1="17" x2="8" y2="17"/>
                                    <polyline points="10 9 9 9 8 9"/>
                                </svg>
                                PDF
                            </button>
                            <button class="btn btn-ghost btn-sm" onclick="downloadEvaluationReport('${escapeHTML(evaluation.id)}')" title="Download JSON Report">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                                </svg>
                                Export
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = cards;
        
    } catch (error) {
        console.error('Failed to load evaluation results:', error);
        showToast(`Failed to load evaluations: ${error.message}`, 'error');
    }
}

async function viewEvaluationDetails(evaluationId) {
    try {
        const report = await apiRequest(`/evaluation/report/${evaluationId}`, { method: 'GET' }, API_BASE);
        const output = report.interview_output || {};
        const recommendation = report.report?.recommendation || output.recommendation || 'n/a';
        const recClass = ['STRONG_HIRE', 'HIRE'].includes(recommendation.toUpperCase()) ? 'success'
            : recommendation.toUpperCase() === 'HOLD' ? 'warning' : 'error';
        const finalPct = report.report?.score_percent ?? output.final_score_percent;
        const riskFlags = (report.report?.risk_flags || []).filter(Boolean);

        // Build a modal/toast-style summary
        const summaryHTML = `
            <div style="max-width:640px;margin:0 auto;display:grid;gap:1rem;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;">
                    <div style="padding:.9rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;">
                        <div style="font-size:0.72rem;text-transform:uppercase;opacity:.55;margin-bottom:.3rem;">Candidate</div>
                        <div style="font-weight:600;">${escapeHTML(report.candidate?.name || 'Unknown')}</div>
                        <div style="font-size:0.82rem;opacity:.65;">${escapeHTML(report.candidate?.email || 'n/a')}</div>
                    </div>
                    <div style="padding:.9rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;">
                        <div style="font-size:0.72rem;text-transform:uppercase;opacity:.55;margin-bottom:.3rem;">Position</div>
                        <div style="font-weight:600;">${escapeHTML(report.job?.title || 'Unknown')}</div>
                        <div style="font-size:0.82rem;opacity:.65;">Phase: ${escapeHTML(output.phase || 'n/a')}</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:.75rem;">
                    <div style="padding:.9rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <div style="font-size:1.6rem;font-weight:700;color:var(--accent-blue);">${finalPct != null ? finalPct + '%' : 'n/a'}</div>
                        <div style="font-size:0.72rem;opacity:.55;">Overall Score</div>
                    </div>
                    <div style="padding:.9rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <div style="font-size:1.6rem;font-weight:700;color:var(--accent-purple);">${formatScore(output.content_score)}</div>
                        <div style="font-size:0.72rem;opacity:.55;">Technical</div>
                    </div>
                    <div style="padding:.9rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <div style="font-size:1.6rem;font-weight:700;color:var(--accent-green);">${formatScore(output.behavior_score)}</div>
                        <div style="font-size:0.72rem;opacity:.55;">Behavioral</div>
                    </div>
                    <div style="padding:.9rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <span class="status-tag ${recClass}" style="font-size:0.85rem;">${escapeHTML(recommendation.replace('_', ' '))}</span>
                        <div style="font-size:0.72rem;opacity:.55;margin-top:.4rem;">Recommendation</div>
                    </div>
                </div>
                ${riskFlags.length ? `<div style="padding:.7rem 1rem;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);border-radius:8px;">
                    <div style="font-weight:600;font-size:0.82rem;color:#ef4444;margin-bottom:.3rem;">⚠ Risk Flags</div>
                    ${riskFlags.map(f => `<div style="font-size:0.82rem;">• ${escapeHTML(f)}</div>`).join('')}
                </div>` : ''}
            </div>`;

        // Try to show in the detail panel if it exists; otherwise alert
        const detail = $('evaluation-detail-content');
        if (detail) {
            detail.innerHTML = summaryHTML;
            show('evaluation-detail-panel');
            $('evaluation-detail-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            showToast(`${report.candidate?.name || 'Candidate'} — Score: ${finalPct != null ? finalPct + '%' : 'n/a'} — ${recommendation}`, 'info');
        }
    } catch (error) {
        console.error('Failed to load evaluation report:', error);
        showToast(`Failed to load report: ${error.message}`, 'error');
    }
}

async function downloadEvaluationReport(evaluationId) {
    try {
        const response = await fetch(`${API_BASE}/evaluation/report/${evaluationId}`, {
            method: 'GET'
        });
        
        if (!response.ok) {
            throw new Error('Failed to download report');
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `evaluation_${evaluationId}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        
        showToast('Report downloaded successfully', 'success');
    } catch (error) {
        console.error('Failed to download report:', error);
        showToast(`Download failed: ${error.message}`, 'error');
    }
}

async function loadInterviewCandidates() {
    try {
        // Load candidates who have passed prescreening
        const response = await apiRequest('/prescreening/sessions?status=COMPLETED', { method: 'GET' }, API_BASE);
        const sessions = Array.isArray(response) ? response : [];
        
        // Filter for those who passed
        const passedCandidates = sessions.filter(s => s.verdict === 'PASS');
        
        const dropdown = $('interview-candidate-select');
        if (dropdown) {
            dropdown.innerHTML = '<option value="">-- Select Candidate --</option>' + 
                passedCandidates.map(s => `<option value="${escapeHTML(s.candidate_id)}">${escapeHTML(s.candidate_name)} - ${escapeHTML(s.job_title)}</option>`).join('');
        }
    } catch (error) {
        console.error('Failed to load interview candidates:', error);
    }
}

// Load interview sessions created from prescreening
async function loadInterviewSessions() {
    const tbody = $('interview-sessions-table-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">Loading sessions...</td></tr>';

    try {
        const response = await apiRequest('/interview/sessions', { method: 'GET' }, API_BASE);
        const sessions = response?.sessions || [];

        if (!sessions.length) {
            tbody.innerHTML = `<tr><td colspan="8" class="empty-state">
                No interview sessions yet — sessions are created automatically when candidates pass prescreening.
            </td></tr>`;
            return;
        }

        const statusBadge = (s) => {
            const map = { PENDING: '#f59e0b', IN_PROGRESS: '#3b82f6', COMPLETED: '#10b981', EXPIRED: '#ef4444', TERMINATED: '#ef4444' };
            const color = map[s] || '#6b7280';
            return `<span style="background:${color}22;color:${color};padding:2px 10px;border-radius:20px;font-size:0.8rem;font-weight:600;">${s||'PENDING'}</span>`;
        };

        tbody.innerHTML = sessions.map(s => {
            const created = s.invited_at || s.created_at ? new Date(s.invited_at || s.created_at).toLocaleDateString() : '—';
            const scoreStr = s.prescreening_score != null ? `${parseFloat(s.prescreening_score).toFixed(1)} / 4.0` : '—';
            const sid = escapeHTML(s.session_id || '');
            return `<tr>
                <td style="font-weight:600;">${escapeHTML(s.candidate_name || '—')}</td>
                <td style="opacity:0.75;">${escapeHTML(s.candidate_email || '—')}</td>
                <td>${escapeHTML(s.job_title || '—')}</td>
                <td>
                    <div style="display:flex;align-items:center;gap:0.4rem;">
                        <code style="background:rgba(102,126,234,0.15);color:#a5b4fc;padding:2px 8px;border-radius:5px;font-size:0.82rem;">${sid}</code>
                        <button onclick="navigator.clipboard.writeText('${sid}');showToast('Session ID copied!','success')" class="btn btn-ghost btn-sm" style="padding:0.2rem 0.4rem;" title="Copy">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                        </button>
                    </div>
                </td>
                <td>${scoreStr}</td>
                <td>${statusBadge(s.status)}</td>
                <td style="opacity:0.7;font-size:0.88rem;">${created}</td>
                <td>
                    <a href="http://localhost:5173" target="_blank" class="btn btn-primary btn-sm" style="text-decoration:none;font-size:0.82rem;padding:0.3rem 0.8rem;">
                        Launch
                    </a>
                </td>
            </tr>`;
        }).join('');

    } catch (err) {
        console.error('Failed to load interview sessions:', err);
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state">Failed to load sessions. Make sure the server is running.</td></tr>';
    }
}

async function loadPrescreeningInterviewSessions() {
    const container = $('prescreening-interview-sessions-list');
    if (!container) return;
    
    try {
        container.innerHTML = '<div class="empty-state">Loading interview sessions...</div>';
        
        // Fetch interview sessions from Stage 6 API
        const response = await apiRequest('/interview/sessions', { method: 'GET' }, API_BASE);
        
        if (!response.success || !response.sessions || response.sessions.length === 0) {
            container.innerHTML = '<div class="empty-state">No interview sessions created yet. They will appear automatically when candidates pass prescreening.</div>';
            return;
        }
        
        const sessions = response.sessions;
        
        // Render session cards
        const sessionCards = sessions.map(session => {
            const statusColors = {
                'PENDING': 'warning',
                'IN_PROGRESS': 'info',
                'COMPLETED': 'success',
                'EXPIRED': 'error',
                'TERMINATED': 'error'
            };
            
            const statusColor = statusColors[session.status] || 'info';
            const invitedDate = session.invited_at ? new Date(session.invited_at).toLocaleDateString() : 'N/A';
            const startedDate = session.started_at ? new Date(session.started_at).toLocaleDateString() : '-';
            const completedDate = session.completed_at ? new Date(session.completed_at).toLocaleDateString() : '-';
            
            // Generate interview URL
            const interviewUrl = `http://localhost:5173/interview/session/${session.session_id}`;
            
            return `
                <div class="candidate-card" style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div>
                            <h4 style="margin: 0 0 4px 0; font-size: 1.1rem;">${session.candidate_name || 'Unknown'}</h4>
                            <p style="margin: 0; opacity: 0.7; font-size: 0.9rem;">${session.candidate_email || 'No email'}</p>
                        </div>
                        <span class="badge badge-${statusColor}">${session.status || 'PENDING'}</span>
                    </div>
                    
                    <div style="margin: 12px 0; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                        <p style="margin: 0 0 4px 0; font-size: 0.9rem;"><strong>Job:</strong> ${session.job_title || 'Not specified'}</p>
                        <p style="margin: 0 0 4px 0; font-size: 0.9rem;"><strong>Session ID:</strong> <code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; font-size: 0.85rem;">${session.session_id}</code></p>
                        <p style="margin: 0 0 4px 0; font-size: 0.9rem;"><strong>Invited:</strong> ${invitedDate}</p>
                        <p style="margin: 0 0 4px 0; font-size: 0.9rem;"><strong>Started:</strong> ${startedDate}</p>
                        <p style="margin: 0; font-size: 0.9rem;"><strong>Completed:</strong> ${completedDate}</p>
                    </div>
                    
                    <div style="display: flex; gap: 8px; margin-top: 12px;">
                        <button class="btn btn-primary btn-sm" onclick="window.open('${interviewUrl}', '_blank')" style="flex: 1;">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                                <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                            </svg>
                            Launch Interview
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="copyInterviewLink('${interviewUrl}')" style="flex: 1;">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>
                            Copy Link
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = sessionCards;
        
        showToast(`Loaded ${sessions.length} interview session(s)`, 'success');
        
    } catch (error) {
        console.error('Failed to load interview sessions:', error);
        container.innerHTML = `<div class="empty-state" style="color: #f87171;">Failed to load interview sessions: ${error.message}</div>`;
    }
}

// Copy interview link to clipboard
function copyInterviewLink(url) {
    navigator.clipboard.writeText(url).then(() => {
        showToast('Interview link copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy link', 'error');
    });
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

// Setup upload zone functionality
function setupUploadZone() {
    const uploadZone = $('upload-zone');
    const fileInput = $('resume-file');
    
    if (!uploadZone || !fileInput) return;

    // Click to upload
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change handler
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // Drag and drop handlers
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
}

// Handle file upload
async function handleFileUpload(file) {
    if (!file) return;

    const progressDiv = $('upload-progress');
    const resultDiv = $('parse-result');
    const statusSpan = $('upload-status');
    const progressFill = $('progress-fill');
    
    try {
        // Show progress
        show('upload-progress');
        hide('parse-result');
        
        if (statusSpan) statusSpan.textContent = 'Uploading...';
        if (progressFill) progressFill.style.width = '20%';

        // Get selected job
        const jobId = $('resume-job-select')?.value || null;
        
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        if (jobId) formData.append('job_id', jobId);

        // Upload file
        const response = await fetch(`${API_BASE}/sourcing/upload-resume`, {
            method: 'POST',
            body: formData
        });

        if (progressFill) progressFill.style.width = '60%';
        if (statusSpan) statusSpan.textContent = 'Processing...';

        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || result.message || 'Upload failed');
        }

        if (progressFill) progressFill.style.width = '100%';
        if (statusSpan) statusSpan.textContent = 'Parsing resume...';

        // Wait for parsing to complete (give it a few seconds)
        showToast('Resume uploaded! Parsing in progress...', 'success');
        
        // Poll for parsed candidate data
        const candidateId = result.candidate_id;
        let attempts = 0;
        const maxAttempts = 10;
        
        const pollParsing = async () => {
            attempts++;
            try {
                const candidateData = await apiRequest(`/sourcing/candidates/${candidateId}`, { method: 'GET' }, API_BASE);
                
                // Check if parsing is complete
                if (candidateData.status === 'parsed' || attempts >= maxAttempts) {
                    hide('upload-progress');
                    show('parse-result');
                    
                    const parseContent = $('parse-content');
                    if (parseContent) {
                        const skills = Array.isArray(candidateData.skills) ? candidateData.skills : [];
                        const education = Array.isArray(candidateData.education) ? candidateData.education[0] : candidateData.education;
                        
                        parseContent.innerHTML = `
                            <div class="parse-result-card">
                                <h4>${escapeHTML(candidateData.name || 'Unknown Candidate')}</h4>
                                <div class="parse-details">
                                    <p><strong>Email:</strong> ${escapeHTML(candidateData.email || 'Not found')}</p>
                                    <p><strong>Phone:</strong> ${escapeHTML(candidateData.phone || 'Not found')}</p>
                                    <p><strong>Experience:</strong> ${candidateData.experience_years || 0} years</p>
                                    <p><strong>Skills:</strong> ${skills.join(', ') || 'None detected'}</p>
                                    <p><strong>Education:</strong> ${escapeHTML(education || 'Not specified')}</p>
                                    <p><strong>Status:</strong> ${escapeHTML(candidateData.status || 'uploaded')}</p>
                                </div>
                                <div class="parse-actions">
                                    <button class="btn btn-primary" onclick="loadCandidates()">
                                        View in Candidates List
                                    </button>
                                </div>
                            </div>
                        `;
                    }

                    // Refresh candidates list
                    await loadCandidates();
                    
                    if (candidateData.status === 'parsed') {
                        showToast('Resume uploaded and parsed successfully!', 'success');
                    } else {
                        showToast('Resume uploaded (parsing may take longer)', 'info');
                    }
                } else {
                    // Not parsed yet, poll again
                    if (attempts < maxAttempts) {
                        setTimeout(pollParsing, 1000);
                    }
                }
            } catch (error) {
                console.error('Poll error:', error);
                if (attempts >= maxAttempts) {
                    hide('upload-progress');
                    showToast('Resume uploaded but parsing status unknown', 'warning');
                } else {
                    setTimeout(pollParsing, 1000);
                }
            }
        };
        
        setTimeout(pollParsing, 1500); // Start polling after 1.5 seconds

    } catch (error) {
        hide('upload-progress');
        showToast(`Upload failed: ${error.message}`, 'error');
        console.error('Upload error:', error);
    }
}
function setupNavToggle() {
    const navToggle = $('nav-toggle');
    const navOverlay = $('nav-overlay');
    const navClose = $('nav-close');
    const body = document.body;
    
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            body.classList.toggle('nav-open');
        });
    }
    
    if (navOverlay) {
        navOverlay.addEventListener('click', () => {
            body.classList.remove('nav-open');
        });
    }
    
    if (navClose) {
        navClose.addEventListener('click', () => {
            body.classList.remove('nav-open');
        });
    }
}

function setupStageHeaderLift() {
    // Add scroll-based header effects
    window.addEventListener('scroll', () => {
        const scrolled = window.scrollY > 20;
        document.body.classList.toggle('scrolled', scrolled);
    });
}

function switchTab(tabId) {
    if (!tabId || !document.getElementById(`tab-${tabId}`)) {
        tabId = 'overview';
    }
    safeStorageSet(ACTIVE_TAB_STORAGE_KEY, tabId);
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
        case 'stage6': loadEvaluationResults(); loadInterviewCandidates(); break;
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
    
    // Load jobs on page load so dropdowns are populated
    loadJobs().catch(err => console.error('Initial jobs load failed:', err));
    
    const initialTab = safeStorageGet(ACTIVE_TAB_STORAGE_KEY, 'overview');
    document.querySelectorAll('.tab-btn').forEach((button) => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });
    const candidateForm = $('candidate-form');
    if (candidateForm) {
        candidateForm.addEventListener('submit', addCandidateForm);
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
    switchTab(initialTab);
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
// Open the Multi-Round Assessment React app
function openInterviewApp() {
    const interviewUrl = 'http://localhost:5173/login';
    const win = window.open(interviewUrl, '_blank');
    if (!win) {
        showToast('Please allow popups to open the interview interface', 'warning');
        setTimeout(() => {
            if (confirm('Popup blocked. Open interview interface in current tab?')) {
                window.location.href = interviewUrl;
            }
        }, 500);
    } else {
        showToast('Interview interface opened in new tab', 'success');
    }
}

// Submit manual interview results
async function submitManualInterview(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    
    // Gather form data
    const payload = {
        session_id: parseInt($('manual-session-id').value),
        phase: $('manual-phase').value,
        current_turn: parseInt($('manual-current-turn').value),
        total_turns: parseInt($('manual-total-turns').value),
        behavioral_score: parseFloat($('manual-behavioral-score').value),
        confidence_score: parseFloat($('manual-confidence-score').value),
        technical_score: parseFloat($('manual-technical-score').value),
        transcript: $('manual-transcript').value || null,
        rl_state: {}
    };
    
    // Validation
    if (!payload.session_id || payload.session_id <= 0) {
        showToast('Please enter a valid Assessment Session ID', 'error');
        return;
    }
    
    if (payload.behavioral_score < 0 || payload.behavioral_score > 1) {
        showToast('Behavioral score must be between 0 and 1', 'error');
        return;
    }
    
    if (payload.confidence_score < 0 || payload.confidence_score > 1) {
        showToast('Confidence score must be between 0 and 1', 'error');
        return;
    }
    
    if (payload.technical_score < 0 || payload.technical_score > 1) {
        showToast('Technical score must be between 0 and 1', 'error');
        return;
    }
    
    try {
        showToast('Saving interview results...', 'info');
        
        const response = await fetch('http://localhost:8001/api/v1/interview/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save interview results');
        }
        
        const result = await response.json();
        
        showToast('Interview results saved successfully!', 'success');
        
        // Reset form
        $('manual-interview-form').reset();
        hide('manual-interview-preview');
        
        // Show success message with result ID
        setTimeout(() => {
            showToast(`Interview ID: ${result.id || result.interview_id || 'saved'}`, 'info');
        }, 1000);
        
    } catch (error) {
        showToast(`Save failed: ${error.message}`, 'error');
        console.error('Submit manual interview error:', error);
    }
}

// Preview manual interview data
function previewManualInterview() {
    const payload = {
        session_id: parseInt($('manual-session-id').value) || null,
        phase: $('manual-phase').value || null,
        current_turn: parseInt($('manual-current-turn').value) || null,
        total_turns: parseInt($('manual-total-turns').value) || null,
        behavioral_score: parseFloat($('manual-behavioral-score').value) || null,
        confidence_score: parseFloat($('manual-confidence-score').value) || null,
        technical_score: parseFloat($('manual-technical-score').value) || null,
        transcript: $('manual-transcript').value || null,
        notes: $('manual-notes').value || null,
        interviewer_name: $('manual-interviewer-name').value || null,
        interview_date: $('manual-interview-date').value || null,
        candidate_name_ref: $('manual-candidate-name').value || '(not saved)',
    };
    
    const previewPanel = $('manual-interview-preview');
    const previewContent = $('manual-interview-preview-content');
    
    if (previewContent) {
        previewContent.textContent = JSON.stringify(payload, null, 2);
    }
    
    show('manual-interview-preview');
    showToast('Preview generated', 'info');
}

function updateSelectedInterviewSessionDetails() {
    const select = $('interview-session-select');
    const option = select?.selectedOptions?.[0];
    const name = $('interview-candidate-name');
    const email = $('interview-candidate-email');
    const job = $('interview-job-title');
    if (name) name.value = option?.dataset?.candidateName || '';
    if (email) email.value = option?.dataset?.candidateEmail || '';
    if (job) job.value = option?.dataset?.jobTitle || '';
}

async function submitInterviewData(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }

    const select = $('interview-session-select');
    const option = select?.selectedOptions?.[0];
    const sessionId = select?.value;
    const candidateId = option?.dataset?.candidateId;
    const jobId = option?.dataset?.jobId;
    const finalScore = parseOptionalFloat('interview-final-score');
    const contentScore = parseOptionalFloat('interview-content-score');
    const behaviorScore = parseOptionalFloat('interview-behavior-score');

    if (!sessionId || !candidateId) {
        showToast('Please select a generated candidate session ID', 'error');
        return;
    }

    if (finalScore === null || finalScore < 0 || finalScore > 1) {
        showToast('Final score must be between 0.0 and 1.0 (e.g. 0.75 = 75%)', 'error');
        return;
    }

    if ((contentScore !== null && (contentScore < 0 || contentScore > 1)) ||
        (behaviorScore !== null && (behaviorScore < 0 || behaviorScore > 1))) {
        showToast('Content and behavior scores must be between 0.0 and 1.0 (e.g. 0.85 = 85%)', 'error');
        return;
    }

    const payload = {
        candidate_id: candidateId,
        job_id: jobId || null,
        session_id: sessionId,
        phase: getOptionalText('interview-phase') || 'HR',
        content_score: contentScore,
        behavior_score: behaviorScore,
        final_score: finalScore,
        interview_date: getOptionalText('interview-date'),
        recommendation: getOptionalText('interview-recommendation')
    };

    const submitBtn = $('btn-submit-interview');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading"></span> Submitting...';
    }

    try {
        await apiRequest('/evaluation/submit-interview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }, API_BASE);

        showToast('Interview evaluation submitted successfully!', 'success');
        $('interview-data-form')?.reset();
        updateSelectedInterviewSessionDetails();
        await loadEvaluationResults();
        await loadOverviewData();
    } catch (error) {
        console.error('Failed to submit interview data:', error);
        showToast(`Submission failed: ${error.message}`, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                    <path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/>
                </svg>
                Submit & Generate Evaluation
            `;
        }
    }
}

async function loadEvaluationResults() {
    try {
        const response = await apiRequest('/evaluation/results', { method: 'GET' }, API_BASE);
        const evaluations = Array.isArray(response) ? response : response.evaluations || [];
        const totalEvals = evaluations.length;
        const passed = evaluations.filter((item) => Number(item.final_score || 0) >= 0.6).length;
        const failed = totalEvals - passed;
        const avgScore = totalEvals > 0
            ? ((evaluations.reduce((sum, item) => sum + Number(item.final_score || 0), 0) / totalEvals) * 100).toFixed(1)
            : '0.0';

        setText('stat-total-evaluations', totalEvals);
        setText('stat-passed-interviews', passed);
        setText('stat-failed-interviews', failed);
        setText('stat-eval-avg-score', avgScore);

        const container = $('evaluation-results-list');
        if (!container) return;

        if (!evaluations.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No evaluation results yet</p>
                    <span style="opacity: 0.7; font-size: 0.9em;">Submit interview data above to generate evaluation reports</span>
                </div>
            `;
            return;
        }

        container.innerHTML = evaluations.map((evaluation) => {
            const recommendation = evaluation.recommendation || (Number(evaluation.final_score || 0) >= 0.6 ? 'HIRE' : 'REJECT');
            const statusClass = ['STRONG_HIRE', 'HIRE'].includes(recommendation) ? 'success' : (recommendation === 'HOLD' ? 'warning' : 'error');
            const percentage = Number(evaluation.final_score_percent ?? (Number(evaluation.final_score || 0) * 100)).toFixed(1);
            const createdDate = evaluation.created_at ? new Date(evaluation.created_at).toLocaleDateString() : 'N/A';
            const subtitle = [
                evaluation.job_title || '',
                evaluation.phase || 'Interview',
                evaluation.session_id ? `Session ${evaluation.session_id}` : '',
            ].filter(Boolean).join(' - ');

            return `
                <div class="job-card">
                    <div class="job-card-header">
                        <div class="job-card-title-block">
                            <h3>${escapeHTML(evaluation.candidate_name || 'Unknown Candidate')}</h3>
                            <div class="job-card-subtitle">${escapeHTML(subtitle)}</div>
                        </div>
                        <span class="status-tag ${statusClass}">${escapeHTML(recommendation.replace('_', ' '))}</span>
                    </div>
                    <div class="job-card-sections">
                        <div class="job-card-section"><span>FINAL SCORE</span><strong>${percentage}%</strong></div>
                        <div class="job-card-section"><span>CONTENT</span><strong>${formatScore(evaluation.content_score)}</strong></div>
                        <div class="job-card-section"><span>BEHAVIOR</span><strong>${formatScore(evaluation.behavior_score)}</strong></div>
                        <div class="job-card-section"><span>SESSION</span><strong>${escapeHTML(evaluation.session_id || 'n/a')}</strong></div>
                        <div class="job-card-section"><span>ROUND</span><strong>${escapeHTML(evaluation.phase || 'n/a')}</strong></div>
                    </div>
                    <div class="job-card-footer">
                        <span><strong>Date:</strong> ${createdDate}</span>
                        <div class="job-card-actions">
                            <button class="btn btn-ghost btn-sm" onclick="viewEvaluationDetails('${escapeHTML(evaluation.id)}')" title="View Full Report">
                                View Details
                            </button>
                            <button class="btn btn-ghost btn-sm" onclick="downloadInterviewPDF('${escapeHTML(evaluation.session_id)}')" title="Download PDF Report">
                                PDF
                            </button>
                            <button class="btn btn-ghost btn-sm" onclick="downloadEvaluationReport('${escapeHTML(evaluation.id)}')" title="Download JSON Report">
                                JSON
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load evaluation results:', error);
        showToast(`Failed to load evaluations: ${error.message}`, 'error');
    }
}

async function viewEvaluationDetails(evaluationId) {
    try {
        const report = await apiRequest(`/evaluation/report/${evaluationId}`, { method: 'GET' }, API_BASE);
        const output = report.interview_output || {};
        const detail = $('evaluation-detail-content');
        if (!detail) return;

        const recommendation = report.report?.recommendation || output.recommendation || 'n/a';
        const recClass = ['STRONG_HIRE', 'HIRE'].includes(recommendation.toUpperCase()) ? 'success'
            : recommendation.toUpperCase() === 'HOLD' ? 'warning' : 'error';
        const finalPct = report.report?.score_percent ?? output.final_score_percent;
        const riskFlags = (report.report?.risk_flags || []).filter(Boolean);

        detail.innerHTML = `
            <div style="display:grid;gap:1.25rem;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                    <div style="padding:1rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;">
                        <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:.06em;opacity:.6;margin-bottom:.4rem;">Candidate</div>
                        <div style="font-weight:600;font-size:1.05rem;">${escapeHTML(report.candidate?.name || 'Unknown')}</div>
                        <div style="font-size:0.85rem;opacity:.7;margin-top:.2rem;">${escapeHTML(report.candidate?.email || 'n/a')}</div>
                    </div>
                    <div style="padding:1rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;">
                        <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:.06em;opacity:.6;margin-bottom:.4rem;">Position</div>
                        <div style="font-weight:600;font-size:1.05rem;">${escapeHTML(report.job?.title || 'Unknown')}</div>
                        <div style="font-size:0.85rem;opacity:.7;margin-top:.2rem;">Phase: ${escapeHTML(output.phase || 'n/a')}</div>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:0.75rem;">
                    <div style="padding:1rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <div style="font-size:1.8rem;font-weight:700;color:var(--accent-blue);">${finalPct != null ? finalPct + '%' : 'n/a'}</div>
                        <div style="font-size:0.75rem;opacity:.6;margin-top:.25rem;">Overall Score</div>
                    </div>
                    <div style="padding:1rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <div style="font-size:1.8rem;font-weight:700;color:var(--accent-purple);">${formatScore(output.content_score)}</div>
                        <div style="font-size:0.75rem;opacity:.6;margin-top:.25rem;">Technical / Content</div>
                    </div>
                    <div style="padding:1rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <div style="font-size:1.8rem;font-weight:700;color:var(--accent-green);">${formatScore(output.behavior_score)}</div>
                        <div style="font-size:0.75rem;opacity:.6;margin-top:.25rem;">Behavioral</div>
                    </div>
                    <div style="padding:1rem;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;text-align:center;">
                        <span class="status-tag ${recClass}" style="font-size:0.9rem;padding:.4rem .9rem;">${escapeHTML(recommendation.replace('_', ' '))}</span>
                        <div style="font-size:0.75rem;opacity:.6;margin-top:.5rem;">Recommendation</div>
                    </div>
                </div>

                ${riskFlags.length ? `
                <div style="padding:.75rem 1rem;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);border-radius:8px;">
                    <div style="font-weight:600;font-size:0.85rem;color:#ef4444;margin-bottom:.4rem;">⚠ Risk Flags</div>
                    ${riskFlags.map(f => `<div style="font-size:0.85rem;opacity:.85;">• ${escapeHTML(f)}</div>`).join('')}
                </div>` : ''}

                <div style="font-size:0.8rem;opacity:.5;text-align:right;">Session: ${escapeHTML(output.session_id || 'n/a')} &nbsp;|&nbsp; Evaluation ID: ${escapeHTML(report.evaluation_id || 'n/a')}</div>
            </div>
        `;
        show('evaluation-detail-panel');
        $('evaluation-detail-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
        console.error('Failed to load evaluation report:', error);
        showToast(`Failed to load report: ${error.message}`, 'error');
    }
}

async function downloadEvaluationReport(evaluationId) {
    try {
        const report = await apiRequest(`/evaluation/report/${evaluationId}`, { method: 'GET' }, API_BASE);
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `evaluation_${evaluationId}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        showToast('JSON report downloaded successfully', 'success');
    } catch (error) {
        console.error('Failed to download report:', error);
        showToast(`Download failed: ${error.message}`, 'error');
    }
}

function closeEvaluationDetails() {
    hide('evaluation-detail-panel');
}

async function loadInterviewCandidates() {
    const dropdown = $('interview-session-select');
    if (!dropdown) return;

    try {
        const response = await apiRequest('/interview/sessions', { method: 'GET' }, API_BASE);
        const sessions = Array.isArray(response?.sessions) ? response.sessions : [];

        dropdown.innerHTML = '<option value="">-- Select candidate who passed prescreening --</option>' +
            sessions
                .filter((session) => session.session_id && session.candidate_id)
                .map((session) => {
                    const label = [
                        session.candidate_name || 'Unknown Candidate',
                        `(ID: ${session.candidate_id})`,
                        session.job_title ? `- ${session.job_title}` : ''
                    ].filter(Boolean).join(' ');
                    return `<option value="${escapeHTML(session.session_id)}"
                        data-candidate-id="${escapeHTML(session.candidate_id)}"
                        data-candidate-name="${escapeHTML(session.candidate_name || '')}"
                        data-candidate-email="${escapeHTML(session.candidate_email || '')}"
                        data-job-id="${escapeHTML(session.job_id || '')}"
                        data-job-title="${escapeHTML(session.job_title || '')}">
                        ${escapeHTML(label)}
                    </option>`;
                }).join('');
        dropdown.onchange = updateSelectedInterviewSessionDetails;
        updateSelectedInterviewSessionDetails();
    } catch (error) {
        console.error('Failed to load interview sessions:', error);
        showToast(`Failed to load generated sessions: ${error.message}`, 'error');
    }
}

window.loadEvents = loadEvents;
window.loadOverviewData = loadOverviewData;
window.loadJobs = loadJobs;
window.loadJobsForSelect = loadJobsForSelect;
window.loadCandidates = loadCandidates;
window.loadScreeningData = loadScreeningData;
window.loadOutreachData = loadOutreachData;
window.loadPrescreeningData = loadPrescreeningData;
window.loadInterviewResults = loadInterviewResults;
window.loadEvaluationResults = loadEvaluationResults;
window.submitInterviewData = submitInterviewData;
window.viewEvaluationDetails = viewEvaluationDetails;
window.downloadEvaluationReport = downloadEvaluationReport;
window.closeEvaluationDetails = closeEvaluationDetails;
window.loadInterviewCandidates = loadInterviewCandidates;
window.loadOffers = loadOffers;
window.loadOnboarding = loadOnboarding;
window.loadAnalyticsDashboard = loadAnalyticsDashboard;
window.openInterviewApp = openInterviewApp;
window.submitManualInterview = submitManualInterview;
window.previewManualInterview = previewManualInterview;
window.startLiveInterview = startLiveInterview;
window.loadNextInterviewQuestion = loadNextInterviewQuestion;
window.submitLiveAnswer = submitLiveAnswer;
window.endLiveInterview = endLiveInterview;
window.viewAPIEndpoints = viewAPIEndpoints;
window.exportInterviewData = exportInterviewData;
window.createJob = createJob;
window.postJob = postJob;
window.deleteJob = deleteJob;
window.addCandidateForm = addCandidateForm;
window.runScreening = runScreening;
window.exportShortlist = exportShortlist;
window.togglePrescreeningView = togglePrescreeningView;
window.createPrescreeningSession = createPrescreeningSession;
window.exportPrescreeningData = exportPrescreeningData;
window.runBulkEvaluation = runBulkEvaluation;
window.closeSessionDetails = closeSessionDetails;
window.viewSessionDetails = viewSessionDetails;
window.exportAnalyticsCSV = exportAnalyticsCSV;
window.exportAnalyticsPDF = exportAnalyticsPDF;


// Export helper functions
window.handleFileUpload = handleFileUpload;
window.autoFillCandidateForm = autoFillCandidateForm;
window.updateCharCount = updateCharCount;
window.submitPrescreening = submitPrescreening;
window.loadCandidateDemoQuestions = loadCandidateDemoQuestions;

// Add toast notification system
function showToast(message, type = 'info') {
    const container = $('toast-container') || document.body;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span>${escapeHTML(message)}</span>
        <button onclick="this.parentElement.remove()" style="margin-left: 12px; background: none; border: none; color: inherit; cursor: pointer; font-size: 1.2rem; opacity: 0.7;">×</button>
    `;
    container.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

window.showToast = showToast;


// Export missing window functions
window.loadScreeningData = loadScreeningData;
window.loadOutreachData = loadOutreachData;
window.loadPrescreeningData = loadPrescreeningData;
window.sendOutreach = sendOutreach;
window.resendOutreach = resendOutreach;
window.filterCandidates = filterCandidates;
window.filterOutreachCandidates = filterOutreachCandidates;
window.filterPrescreeningSessions = filterPrescreeningSessions;

// Add spin animation CSS if not already present
if (!document.querySelector('#spin-animation-style')) {
    const style = document.createElement('style');
    style.id = 'spin-animation-style';
    style.textContent = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}


// Stage 8: Offer Management Functions
async function acceptOffer(offerId) {
    try {
        setStatus('Accepting offer...', 'info');
        const response = await apiRequest(`/offer/accept/${offerId}`, { method: 'POST' }, API_BASE);
        setStatus(response.message || 'Offer accepted! Onboarding initiated.', 'success');
        await loadOffers();
        await loadOnboarding();
        return response;
    } catch (error) {
        setStatus(`Accept offer failed: ${error.message}`, 'error');
        return null;
    }
}

async function dispatchOffer(offerId) {
    try {
        setStatus('Sending offer email...', 'info');
        const response = await apiRequest(`/offer/dispatch/${offerId}`, { method: 'POST' }, API_BASE);
        setStatus(response.message || 'Offer email sent!', 'success');
        await loadOffers();
        return response;
    } catch (error) {
        setStatus(`Dispatch offer failed: ${error.message}`, 'error');
        return null;
    }
}

// Stage 9: Onboarding Functions
async function viewOnboardingTasks(onboardingId) {
    try {
        setStatus('Loading tasks...', 'info');
        const response = await apiRequest(`/onboarding/${onboardingId}/tasks`, { method: 'GET' }, API_BASE);
        const tasks = Array.isArray(response.tasks) ? response.tasks : [];
        
        // Display tasks in modal
        const modal = $('onboarding-tasks-modal');
        const modalTitle = $('modal-title');
        const modalBody = $('modal-body');
        
        if (modal && modalTitle && modalBody) {
            modalTitle.textContent = `Onboarding Tasks - ${onboardingId}`;
            
            if (tasks.length === 0) {
                modalBody.innerHTML = '<p style="text-align: center; padding: 2rem;">No tasks found for this onboarding record.</p>';
            } else {
                // Group tasks by phase
                const phases = {};
                tasks.forEach(task => {
                    if (!phases[task.phase]) phases[task.phase] = [];
                    phases[task.phase].push(task);
                });
                
                let html = '<div style="display: flex; flex-direction: column; gap: 1.5rem;">';
                
                for (const [phase, phaseTasks] of Object.entries(phases)) {
                    const phaseLabel = phase.replace('_', ' ').toUpperCase();
                    html += `
                        <div>
                            <h4 style="margin-bottom: 0.75rem; color: var(--primary);">${phaseLabel}</h4>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                ${phaseTasks.map(task => `
                                    <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; background: var(--bg-tertiary); border-radius: 0.5rem;">
                                        <input type="checkbox" ${task.status === 'completed' ? 'checked' : ''} 
                                            onchange="toggleTaskStatus('${task.id}', this.checked)" 
                                            style="width: 18px; height: 18px; cursor: pointer;">
                                        <div style="flex: 1;">
                                            <div style="font-weight: 500;">${escapeHTML(task.task)}</div>
                                            <div style="font-size: 0.85em; opacity: 0.7;">Due: ${escapeHTML(task.due_date)}</div>
                                        </div>
                                        <span class="status-tag ${task.status === 'completed' ? 'success' : 'info'}" style="font-size: 0.75rem;">
                                            ${task.status || 'pending'}
                                        </span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
                
                html += '</div>';
                modalBody.innerHTML = html;
            }
            
            modal.style.display = 'flex';
        }
        
        setStatus('Tasks loaded', 'success');
        return tasks;
    } catch (error) {
        setStatus(`Load tasks failed: ${error.message}`, 'error');
        return null;
    }
}

async function toggleTaskStatus(taskId, isComplete) {
    try {
        const response = await apiRequest('/onboarding/task/complete', {
            method: 'POST',
            body: JSON.stringify({ task_id: taskId })
        }, API_BASE);
        setStatus(response.message || 'Task status updated', 'success');
    } catch (error) {
        setStatus(`Failed to update task: ${error.message}`, 'error');
    }
}

function closeOnboardingModal() {
    const modal = $('onboarding-tasks-modal');
    if (modal) modal.style.display = 'none';
}

async function loadCompletedCandidates() {
    const select = $('candidate-select');
    const dateInput = $('joining-date');
    
    if (!select || !dateInput) return;
    
    // Set default joining date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    dateInput.value = tomorrow.toISOString().split('T')[0];
    
    // Load candidates who completed interviews/evaluations
    try {
        setStatus('Loading candidates...', 'info');
        const response = await apiRequest('/interview/completed-candidates', { method: 'GET' }, API_BASE);
        const candidates = Array.isArray(response.candidates) ? response.candidates : [];
        
        if (candidates.length === 0) {
            select.innerHTML = '<option value="">-- No candidates found --</option>';
            setStatus('No candidates with completed interviews found', 'warning');
        } else {
            select.innerHTML = '<option value="">-- Choose a Candidate --</option>' +
                candidates.map(c => `<option value="${c.session_id}" data-candidate-id="${c.candidate_id}" data-job-id="${c.job_id}" data-candidate-name="${c.candidate_name}" data-job-title="${c.job_title}">${escapeHTML(c.candidate_name)} - ${escapeHTML(c.job_title)}</option>`).join('');
            setStatus(`Loaded ${candidates.length} candidates`, 'success');
        }
    } catch (error) {
        setStatus(`Failed to load candidates: ${error.message}`, 'error');
        select.innerHTML = '<option value="">-- Failed to load candidates --</option>';
    }
}

function onCandidateSelected() {
    const select = $('candidate-select');
    if (!select) return;
    
    const selectedOption = select.selectedOptions[0];
    if (selectedOption && selectedOption.value) {
        const candidateName = selectedOption.dataset.candidateName;
        const jobTitle = selectedOption.dataset.jobTitle;
        setStatus(`Selected: ${candidateName} - ${jobTitle}`, 'info');
    }
}

function closeTasksPanel() {
    const panel = $('tasks-panel');
    if (panel) panel.style.display = 'none';
}

async function generateTasksForCandidate() {
    const select = $('candidate-select');
    const dateInput = $('joining-date');
    
    if (!select || !dateInput) return;
    
    const selectedOption = select.selectedOptions[0];
    if (!selectedOption || !selectedOption.value) {
        setStatus('Please select a candidate', 'error');
        return;
    }
    
    const candidateId = selectedOption.dataset.candidateId;
    const jobId = selectedOption.dataset.jobId;
    const candidateName = selectedOption.dataset.candidateName;
    const jobTitle = selectedOption.dataset.jobTitle;
    const joiningDate = dateInput.value;
    
    if (!joiningDate) {
        setStatus('Please select a joining date', 'error');
        return;
    }
    
    try {
        setStatus('Creating onboarding and generating tasks...', 'info');
        
        // Create onboarding with AI-generated tasks
        const response = await apiRequest('/onboarding/from-interview', {
            method: 'POST',
            body: JSON.stringify({
                candidate_id: candidateId,
                job_id: jobId,
                joining_date: joiningDate
            })
        }, API_BASE);
        
        setStatus(`Onboarding created for ${candidateName} - ${jobTitle}`, 'success');
        
        // Refresh onboarding list
        await loadOnboarding();
        
        // Show the tasks in the tasks panel
        if (response.onboarding_id) {
            await displayTasksInPanel(response.onboarding_id);
        }
        
        return response;
    } catch (error) {
        setStatus(`Failed to create onboarding: ${error.message}`, 'error');
        return null;
    }
}

async function displayTasksInPanel(onboardingId) {
    try {
        setStatus('Loading tasks...', 'info');
        const response = await apiRequest(`/onboarding/${onboardingId}/tasks`, { method: 'GET' }, API_BASE);
        const tasks = Array.isArray(response.tasks) ? response.tasks : [];
        
        const panel = $('tasks-panel');
        const display = $('tasks-display');
        
        if (panel && display) {
            panel.style.display = 'block';
            
            if (tasks.length === 0) {
                display.innerHTML = '<p style="text-align: center; padding: 2rem;">No tasks found for this onboarding record.</p>';
            } else {
                // Group tasks by phase
                const phases = {};
                tasks.forEach(task => {
                    if (!phases[task.phase]) phases[task.phase] = [];
                    phases[task.phase].push(task);
                });
                
                let html = '<div style="display: flex; flex-direction: column; gap: 1.5rem;">';
                
                for (const [phase, phaseTasks] of Object.entries(phases)) {
                    const phaseLabel = phase.replace('_', ' ').toUpperCase();
                    html += `
                        <div>
                            <h4 style="margin-bottom: 0.75rem; color: var(--primary);">${phaseLabel}</h4>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                ${phaseTasks.map(task => `
                                    <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; background: var(--bg-tertiary); border-radius: 0.5rem;">
                                        <input type="checkbox" ${task.status === 'completed' ? 'checked' : ''} 
                                            onchange="toggleTaskStatus('${task.id}', this.checked)" 
                                            style="width: 18px; height: 18px; cursor: pointer;">
                                        <div style="flex: 1;">
                                            <div style="font-weight: 500;">${escapeHTML(task.task)}</div>
                                            <div style="font-size: 0.85em; opacity: 0.7;">Due: ${escapeHTML(task.due_date)}</div>
                                        </div>
                                        <span class="status-tag ${task.status === 'completed' ? 'success' : 'info'}" style="font-size: 0.75rem;">
                                            ${task.status || 'pending'}
                                        </span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
                
                html += '</div>';
                display.innerHTML = html;
            }
        }
        
        setStatus('Tasks loaded', 'success');
        return tasks;
    } catch (error) {
        setStatus(`Load tasks failed: ${error.message}`, 'error');
        return null;
    }
}


// Make functions available globally
window.acceptOffer = acceptOffer;
window.dispatchOffer = dispatchOffer;
window.viewOnboardingTasks = viewOnboardingTasks;

window.closeOnboardingModal = closeOnboardingModal;
window.loadCompletedCandidates = loadCompletedCandidates;
window.onCandidateSelected = onCandidateSelected;
window.closeTasksPanel = closeTasksPanel;
window.generateTasksForCandidate = generateTasksForCandidate;
window.displayTasksInPanel = displayTasksInPanel;
window.toggleTaskStatus = toggleTaskStatus;


// ════════════════════════════════════════════════════════════════════
// Stage 6: Interview Management Functions
// ════════════════════════════════════════════════════════════════════

async function launchInterview(sessionId) {
    /**
     * Launch interview directly with session ID
     * Opens to session validation → resume upload → interview
     */
    const url = `http://localhost:5173/interview/session/${sessionId}`;
    window.open(url, '_blank', 'width=1200,height=800');
    setStatus('Interview launched in new window', 'info');
}

async function copyInterviewLink(sessionId) {
    /**
     * Copy interview link to clipboard for sharing with candidate
     */
    const url = `http://localhost:5173/interview/session/${sessionId}`;
    try {
        await navigator.clipboard.writeText(url);
        setStatus('Interview link copied to clipboard!', 'success');
    } catch (e) {
        // Fallback for browsers that don't support clipboard API
        prompt('Copy this interview link:', url);
    }
}

async function resendInterviewEmail(candidateId, sessionId) {
    /**
     * Resend interview invitation email to candidate
     */
    try {
        setStatus('Resending interview email...', 'info');
        const response = await apiRequest(`/interview/resend/${sessionId}`, { 
            method: 'POST' 
        }, API_BASE);
        setStatus(response.message || 'Interview email resent successfully!', 'success');
        return response;
    } catch (error) {
        setStatus(`Failed to resend email: ${error.message}`, 'error');
        return null;
    }
}

// Make functions globally available
window.launchInterview = launchInterview;
window.copyInterviewLink = copyInterviewLink;
window.resendInterviewEmail = resendInterviewEmail;

async function deleteOnboarding(onboardingId, candidateName = '') {
    if (!onboardingId) return;
    const confirmed = window.confirm(`Delete onboarding record for "${candidateName || onboardingId}"? This will remove the onboarding tasks too.`);
    if (!confirmed) return;
    
    try {
        setStatus('Deleting onboarding record...', 'info');
        const response = await apiRequest(`/onboarding/${onboardingId}`, {
            method: 'DELETE'
        }, API_BASE);
        setStatus(response.message || 'Onboarding deleted', 'success');
        
        closeTasksPanel();
        await loadOnboarding();
        return response;
    } catch (error) {
        setStatus(`Delete failed: ${error.message}`, 'error');
        throw error;
    }
}
window.deleteOnboarding = deleteOnboarding;
