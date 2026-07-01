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

function parseMarkdown(text) {
    if (!text) return '';
    let html = escapeHTML(text);
    
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    const lines = html.split('\n');
    let inList = false;
    const processedLines = lines.map(line => {
        const trimmed = line.trim();
        if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
            const content = trimmed.substring(2);
            if (!inList) {
                inList = true;
                return '<ul><li>' + content + '</li>';
            }
            return '<li>' + content + '</li>';
        } else {
            if (inList) {
                inList = false;
                return '</ul>' + (trimmed ? `<p>${trimmed}</p>` : '');
            }
            return trimmed ? `<p>${trimmed}</p>` : '';
        }
    });
    if (inList) {
        processedLines.push('</ul>');
    }
    return processedLines.join('\n');
}


function getOptionalText(id) {
    const value = $(id)?.value?.trim();
    return value ? value : null;
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
            ? (completed.reduce((sum, s) => sum + s.final_score, 0) / completed.length).toFixed(1)
            : '0.0';
        setText('stat-avg-score', avgScore);
        
        // Render interview cards
        renderInterviewCards(sessions);
        
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
        const recommendationTag = session.recommendation ? 
            `<span class="status-tag ${session.recommendation.toLowerCase() === 'reject' ? 'error' : 'success'}" style="margin-left: 8px;">${escapeHTML(session.recommendation)}</span>` : '';
        
        return `
        <div class="job-card">
            <div class="job-card-header">
                <div class="job-card-title-block">
                    <h3>${escapeHTML(session.candidate_name || 'Unknown Candidate')} ${recommendationTag}</h3>
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
                    <strong>${session.final_score != null ? session.final_score.toFixed(1) + '%' : 'Not completed'}</strong>
                </div>
            </div>
            <div class="job-card-footer">
                <span><strong>Email:</strong> ${escapeHTML(session.candidate_email || 'N/A')}</span>
                <div class="job-card-actions">
                    ${session.status !== 'COMPLETED' && session.status !== 'completed' && session.status !== 'TERMINATED' && session.status !== 'terminated' ? `
                    <button class="btn btn-primary btn-sm" onclick="launchInterview('${escapeHTML(session.session_id)}')" title="Open interview in new window">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="margin-right: 4px;">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                        Launch Interview
                    </button>
                    ` : ''}
                    ${session.status === 'COMPLETED' || session.status === 'completed' || session.status === 'TERMINATED' || session.status === 'terminated' ? `
                    <button class="btn btn-secondary btn-sm" onclick="viewDetailedInterviewReport('${escapeHTML(session.session_id)}', this)" title="View detailed evaluation scorecard">
                        View Report
                    </button>
                    ` : ''}
                    <button class="btn btn-ghost btn-sm" onclick="copyInterviewLink('${escapeHTML(session.session_id)}')" title="Copy interview link">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                        Copy Link
                    </button>
                    ${session.status === 'PENDING' || session.status === 'EXPIRED' || session.status === 'FAILED' || session.status === 'COMPLETED' || session.status === 'completed' || session.status === 'TERMINATED' || session.status === 'terminated' ? 
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

async function viewDetailedInterviewReport(sessionId, btn) {
    const modal = $('interview-results-modal');
    const modalBody = $('interview-modal-body');
    if (!modal || !modalBody) return;

    let originalHtml = '';
    if (btn) {
        btn.disabled = true;
        originalHtml = btn.innerHTML;
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="margin-right: 4px; animation: spin 1s linear infinite;"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Loading...`;
    }

    modalBody.innerHTML = '<div class="loading-spinner" style="text-align: center; padding: 2rem;">Loading detailed scorecard...</div>';
    modal.style.display = 'flex';
    show('interview-results-modal');

    try {
        const response = await apiRequest(`/interview/session/${sessionId}/turns`, { method: 'GET' }, API_BASE);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
        if (!response || !response.success) {
            modalBody.innerHTML = '<div class="alert alert-error">Failed to retrieve interview report data.</div>';
            return;
        }

        const evalData = response.evaluation || {};
        const turns = response.turns || [];

        let turnsHtml = '';
        if (turns.length === 0) {
            turnsHtml = '<p class="text-muted">No individual turns recorded for this session.</p>';
        } else {
            turnsHtml = turns.map(t => {
                const isDec = t.content_score <= 1.0;
                const cs = (isDec ? t.content_score * 100 : t.content_score).toFixed(0);
                const bs = (isDec ? t.behavior_score * 100 : t.behavior_score).toFixed(0);
                const fs = (isDec ? t.final_score * 100 : t.final_score).toFixed(0);
                return `
                <div style="border-bottom: 1px solid var(--border); padding: 1rem 0;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                        <span style="font-weight: 600; color: var(--text-primary);">Turn ${t.turn_number} ${t.is_followup ? '(Follow-up)' : ''}</span>
                        <span class="status-tag info">${escapeHTML(t.difficulty || 'medium')}</span>
                    </div>
                    <div style="margin-bottom: 0.5rem;">
                        <strong style="font-size: 0.9em; color: var(--text-secondary);">Question:</strong>
                        <p style="margin: 0.25rem 0; line-height: 1.4;">${escapeHTML(t.question_text)}</p>
                    </div>
                    <div style="margin-bottom: 0.5rem; background: var(--bg-primary); padding: 0.75rem; border-radius: 8px;">
                        <strong style="font-size: 0.9em; color: var(--text-secondary);">Response:</strong>
                        <p style="margin: 0.25rem 0; line-height: 1.4; font-style: italic;">"${escapeHTML(t.response || 'No response recorded')}"</p>
                    </div>
                    <div style="display: flex; gap: 1rem; font-size: 0.85em; color: var(--text-secondary);">
                        <span><strong>Content Score:</strong> ${cs}%</span>
                        <span><strong>Behavior Score:</strong> ${bs}%</span>
                        <span><strong>Final Score:</strong> ${fs}%</span>
                    </div>
                </div>
                `;
            }).join('');
        }

        modalBody.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem;">
                <div>
                    <h4 style="margin-bottom: 0.5rem; font-family: var(--font-display); color: var(--text-primary); font-size: 1.25rem;">Candidate Information</h4>
                    <p style="margin: 0.25rem 0;"><strong>Name:</strong> ${escapeHTML(response.candidate_name)}</p>
                    <p style="margin: 0.25rem 0;"><strong>Email:</strong> ${escapeHTML(response.candidate_email)}</p>
                    <p style="margin: 0.25rem 0;"><strong>Job Role:</strong> ${escapeHTML(response.job_title)}</p>
                    <div style="margin-top: 1rem; font-size: 0.8em; opacity: 0.8; border-top: 1px dashed var(--border); padding-top: 0.5rem;">
                        <p style="margin: 0.15rem 0;"><strong>AI Generated:</strong> ${evalData.ai_generated_at ? new Date(evalData.ai_generated_at).toLocaleString() : 'N/A'}</p>
                        <p style="margin: 0.15rem 0;"><strong>Reviewed At:</strong> ${evalData.recruiter_reviewed_at ? new Date(evalData.recruiter_reviewed_at).toLocaleString() : 'Not reviewed'}</p>
                    </div>
                </div>
                <div style="background: var(--bg-primary); padding: 1rem; border-radius: 12px;">
                    <h4 style="margin-bottom: 0.5rem; font-family: var(--font-display); color: var(--text-primary); font-size: 1.1rem;">AI Evaluation Scorecard (Read-only)</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9em;">
                        <span><strong>Technical:</strong> ${evalData.content_score != null ? evalData.content_score.toFixed(1) + '%' : 'N/A'}</span>
                        <span><strong>Behavioral:</strong> ${evalData.behavior_score != null ? evalData.behavior_score.toFixed(1) + '%' : 'N/A'}</span>
                        <span><strong>Communication:</strong> ${evalData.communication_score != null ? evalData.communication_score.toFixed(1) + '%' : 'N/A'}</span>
                        <span><strong>Confidence:</strong> ${evalData.confidence_score != null ? evalData.confidence_score.toFixed(1) + '%' : 'N/A'}</span>
                        <span style="grid-column: span 2; font-size: 1.05em; margin-top: 0.25rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.25rem;"><strong>Overall AI Score:</strong> ${evalData.final_score != null ? evalData.final_score.toFixed(1) + '%' : 'N/A'}</span>
                        <span style="grid-column: span 2;"><strong>AI Recommendation:</strong> <span class="status-tag ${evalData.ai_recommendation && evalData.ai_recommendation.toLowerCase() !== 'reject' ? 'success' : 'error'}">${escapeHTML(evalData.ai_recommendation || 'N/A')}</span></span>
                    </div>
                </div>
            </div>

            <!-- Recruiter Override Section -->
            <div style="margin-bottom: 1.5rem; background: rgba(var(--accent-rgb), 0.03); border: 1px solid var(--border); padding: 1.25rem; border-radius: 12px;">
                <h4 style="margin-bottom: 0.75rem; font-family: var(--font-display); color: var(--text-primary); font-size: 1.25rem;">Recruiter Decision Override</h4>
                <div class="form-grid" style="display: grid; grid-template-columns: 1fr 2fr; gap: 1rem; margin-bottom: 1rem;">
                    <div class="form-group">
                        <label for="override-decision" style="font-weight: 600; display: block; margin-bottom: 0.25rem; font-size: 0.9rem;">Hiring Decision</label>
                        <select id="override-decision" style="width: 100%; padding: 0.5rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-primary);">
                            <option value="" ${!evalData.recruiter_decision ? 'selected' : ''}>-- Use Advisory AI --</option>
                            <option value="STRONG_HIRE" ${evalData.recruiter_decision === 'STRONG_HIRE' ? 'selected' : ''}>Strong Hire</option>
                            <option value="HIRE" ${evalData.recruiter_decision === 'HIRE' ? 'selected' : ''}>Hire</option>
                            <option value="HOLD" ${evalData.recruiter_decision === 'HOLD' ? 'selected' : ''}>Hold</option>
                            <option value="REJECT" ${evalData.recruiter_decision === 'REJECT' ? 'selected' : ''}>Reject</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="override-notes" style="font-weight: 600; display: block; margin-bottom: 0.25rem; font-size: 0.9rem;">Audit Notes / Justification</label>
                        <textarea id="override-notes" rows="2" style="width: 100%; padding: 0.5rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-primary);" placeholder="Add override reason, reviewed strengths/weaknesses comments...">${escapeHTML(evalData.recruiter_notes || '')}</textarea>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="submitRecruiterOverride('${escapeHTML(evalData.id)}')" style="padding: 0.5rem 1rem;">Save Overrides</button>
            </div>
            
            <div style="margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                <div>
                    <h5 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600; color: var(--text-primary);">Key Strengths</h5>
                    <p style="line-height: 1.4; font-size: 0.9em; color: var(--text-secondary); white-space: pre-wrap;">${escapeHTML(evalData.strengths || 'No key strengths extracted.')}</p>
                </div>
                <div>
                    <h5 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600; color: var(--text-primary);">Key Weaknesses</h5>
                    <p style="line-height: 1.4; font-size: 0.9em; color: var(--text-secondary); white-space: pre-wrap;">${escapeHTML(evalData.weaknesses || 'No key weaknesses extracted.')}</p>
                </div>
            </div>

            <div style="margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem;">
                <h4 style="margin-bottom: 0.5rem; font-family: var(--font-display); color: var(--text-primary); font-size: 1.25rem;">Evaluation Summary</h4>
                <p style="line-height: 1.5; color: var(--text-secondary);">${escapeHTML(evalData.evaluator_notes || 'No summary notes generated.')}</p>
            </div>

            <div>
                <h4 style="margin-bottom: 1rem; font-family: var(--font-display); color: var(--text-primary); font-size: 1.25rem;">Turns & Responses</h4>
                <div style="max-height: 350px; overflow-y: auto; padding-right: 0.5rem;">
                    ${turnsHtml}
                </div>
            </div>
        `;

    } catch (error) {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
        console.error('Fetch interview report error:', error);
        modalBody.innerHTML = `<div class="alert alert-error">An error occurred loading detailed evaluation scorecard: ${escapeHTML(error.message)}</div>`;
    }
}

function closeInterviewResultsModal() {
    hide('interview-results-modal');
    const modal = $('interview-results-modal');
    if (modal) {
        modal.style.display = 'none';
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

let radarChartInstance = null;
let barChartInstance = null;

function filterCandidates() {
    const status = $('status-filter')?.value || '';
    const jobId = $('screening-job-select')?.value || '';
    
    const rows = state.stageData.screeningCandidates.filter((item) => {
        const matchesStatus = !status || String(item.status || '').toLowerCase() === status.toLowerCase();
        const matchesJob = !jobId || String(item.job_id || '') === jobId;
        return matchesStatus && matchesJob;
    });
    
    const body = $('screening-results');
    if (body) {
        body.innerHTML = rows.length ? rows.map((item) => {
            const skills = Array.isArray(item.skills) ? item.skills.join(', ') : (item.skills || 'None');
            const currentStage = (item.status || 'new').toLowerCase();
            
            let statusClass = 'info';
            if (currentStage === 'prescreening' || currentStage === 'shortlisted') {
                statusClass = 'success';
            } else if (currentStage === 'rejected') {
                statusClass = 'error';
            } else if (currentStage === 'interview') {
                statusClass = 'warning';
            }
            
            const validTransitions = {
                "new": ["prescreening", "interview", "rejected"],
                "prescreening": ["interview", "rejected"],
                "interview": ["rejected"],
                "rejected": ["prescreening", "interview"]
            };
            const allowed = validTransitions[currentStage] || [];
            
            const renderOption = (val, label) => {
                const isSelected = currentStage === val || (currentStage === 'shortlisted' && val === 'prescreening');
                const isDisabled = !isSelected && !allowed.includes(val);
                return `<option value="${val}" ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}>${label}</option>`;
            };

            const dropdownHtml = `
            <div class="pipeline-selector-wrapper" style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                <span style="font-size: 0.7em; color: var(--color-text-muted); text-transform: uppercase; font-weight: bold; letter-spacing: 0.05em;">Pipeline Stage</span>
                <select class="pipeline-stage-select ${statusClass}" onchange="changeCandidateStage('${escapeHTML(item.id)}', '${currentStage}', this.value)" style="padding: 4px 8px; font-size: 0.85em; border-radius: 6px; font-weight: 500; cursor: pointer; border: 1px solid var(--color-border); background-color: var(--color-card); color: var(--color-text);">
                    ${renderOption('new', 'New')}
                    ${renderOption('prescreening', 'Prescreening')}
                    ${renderOption('interview', 'Interview')}
                    ${renderOption('rejected', 'Rejected')}
                </select>
            </div>`;
            
            return `
            <div class="job-card">
                <div class="job-card-header">
                    <div class="job-card-title-block">
                        <h3>${escapeHTML(item.name || 'Unknown Candidate')}</h3>
                        <div class="job-card-subtitle">${escapeHTML(item.current_role || item.email || '')}</div>
                    </div>
                    ${dropdownHtml}
                </div>
                <div class="job-card-sections">
                    <div class="job-card-section">
                        <span>SKILLS</span>
                        <strong>${escapeHTML(skills)}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>SCORE</span>
                        <strong>${item.score ?? 'Not scored'}</strong>
                    </div>
                    <div class="job-card-section">
                        <span>EXPERIENCE</span>
                        <strong>${item.experience_years ?? 0} years</strong>
                    </div>
                </div>
                <div class="job-card-footer" style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                    <div>
                        <span><strong>ID:</strong> ${escapeHTML(item.id.substring(0, 12))}...</span>
                        <span><strong>Source:</strong> ${escapeHTML(item.source || 'unknown')}</span>
                        ${item.rejection_reason ? `<br><span style="color: var(--color-error); font-size: 0.85em;"><strong>Reason:</strong> ${escapeHTML(item.rejection_reason)}</span>` : ''}
                    </div>
                    <button class="btn btn-ghost btn-sm" onclick="deleteCandidate('${escapeHTML(item.id)}')" style="color: var(--color-error); border: 1px solid rgba(239, 68, 68, 0.2); padding: 4px 8px; font-size: 0.8em; display: flex; align-items: center; gap: 4px; border-radius: 4px;" title="Delete Candidate">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                        Delete
                    </button>
                </div>
            </div>`;
        }).join('') : '<div class="empty-state">No resume screening results yet. Run resume screening to see results.</div>';
    }
    
    // Dynamically update KPI aggregates and Chart.js visuals
    updateScreeningStatsAndCharts(rows);
    updateSkillsComparison(jobId);
}

function updateScreeningStatsAndCharts(candidates) {
    const totalScreenedEl = $('stats-total-screened');
    const qualifiedCandidatesEl = $('stats-qualified-candidates');
    const averageScoreEl = $('stats-average-score');
    const highestScoreEl = $('stats-highest-score');
    const radarEmptyState = $('radar-empty-state');
    const barEmptyState = $('bar-empty-state');
    const radarCanvas = $('screening-radar-chart');
    const barCanvas = $('screening-bar-chart');

    const screenedCandidates = candidates.filter(c => c.score !== null && c.score !== undefined);
    const totalScreened = screenedCandidates.length;

    // Reset KPI cards if empty
    if (totalScreened === 0) {
        if (totalScreenedEl) totalScreenedEl.textContent = '0';
        if (qualifiedCandidatesEl) qualifiedCandidatesEl.textContent = '0';
        if (averageScoreEl) averageScoreEl.textContent = '0%';
        if (highestScoreEl) highestScoreEl.textContent = '0%';

        if (radarEmptyState) radarEmptyState.style.display = 'block';
        if (barEmptyState) barEmptyState.style.display = 'block';
        if (radarCanvas) radarCanvas.style.display = 'none';
        if (barCanvas) barCanvas.style.display = 'none';

        if (radarChartInstance) { radarChartInstance.destroy(); radarChartInstance = null; }
        if (barChartInstance) { barChartInstance.destroy(); barChartInstance = null; }
        return;
    }

    // Hide empty states and show canvases
    if (radarEmptyState) radarEmptyState.style.display = 'none';
    if (barEmptyState) barEmptyState.style.display = 'none';
    if (radarCanvas) radarCanvas.style.display = 'block';
    if (barCanvas) barCanvas.style.display = 'block';

    // Calculate KPIs
    const scores = screenedCandidates.map(c => Number(c.score));
    const avgScore = (scores.reduce((a, b) => a + b, 0) / totalScreened).toFixed(1);
    const highestScore = Math.max(...scores).toFixed(0);
    const qualifiedCount = screenedCandidates.filter(c => c.score >= 70).length;

    if (totalScreenedEl) totalScreenedEl.textContent = totalScreened;
    if (qualifiedCandidatesEl) qualifiedCandidatesEl.textContent = qualifiedCount;
    if (averageScoreEl) averageScoreEl.textContent = `${avgScore}%`;
    if (highestScoreEl) highestScoreEl.textContent = `${highestScore}%`;

    // 1. Radar Chart Data (Dynamic Score Normalization)
    const paramTotals = {
        skills: { score: 0.0, max_score: 0.0 },
        experience: { score: 0.0, max_score: 0.0 },
        education: { score: 0.0, max_score: 0.0 },
        location: { score: 0.0, max_score: 0.0 },
        title_relevance: { score: 0.0, max_score: 0.0 }
    };

    screenedCandidates.forEach(c => {
        const breakdown = c.score_breakdown_normalized;
        if (breakdown) {
            Object.keys(paramTotals).forEach(key => {
                if (breakdown[key]) {
                    paramTotals[key].score += Number(breakdown[key].score || 0);
                    paramTotals[key].max_score += Number(breakdown[key].max_score || 0);
                }
            });
        }
    });

    const radarLabels = ["Skills", "Experience", "Education", "Location", "Title Match"];
    const radarData = radarLabels.map((label, index) => {
        const key = ["skills", "experience", "education", "location", "title_relevance"][index];
        const data = paramTotals[key];
        return data.max_score > 0 ? Number(((data.score / data.max_score) * 100).toFixed(1)) : 0;
    });

    // Destroy existing radar chart if active
    if (radarChartInstance) {
        radarChartInstance.destroy();
    }

        radarChartInstance = new Chart(radarCanvas, {
            type: 'radar',
            data: {
                labels: radarLabels,
                datasets: [{
                    label: 'Average Parameter Match (%)',
                    data: radarData,
                    backgroundColor: 'rgba(99, 102, 241, 0.35)',
                    borderColor: '#818cf8',
                    pointBackgroundColor: '#818cf8',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#818cf8',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255,255,255,0.25)' },
                        grid: { color: 'rgba(255,255,255,0.25)' },
                        pointLabels: { color: '#ffffff', font: { size: 11, weight: 'bold' } },
                        ticks: { color: '#ffffff', backdropColor: 'rgba(15, 23, 42, 0.85)', font: { weight: 'bold' } },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });

    // 2. Bar Chart Data (Score Distribution)
    const buckets = { under_50: 0, "50-60": 0, "60-70": 0, "70-80": 0, "80-90": 0, "90+": 0 };
    screenedCandidates.forEach(c => {
        const score = Number(c.score);
        if (score < 50) buckets.under_50++;
        else if (score < 60) buckets["50-60"]++;
        else if (score < 70) buckets["60-70"]++;
        else if (score < 80) buckets["70-80"]++;
        else if (score < 90) buckets["80-90"]++;
        else buckets["90+"]++;
    });

    const barLabels = ["< 50", "50-60", "60-70", "70-80", "80-90", "90+"];
    const barData = barLabels.map(label => buckets[label === "< 50" ? "under_50" : label]);

    // Destroy existing bar chart if active
    if (barChartInstance) {
        barChartInstance.destroy();
    }

    if (barCanvas) {
        barChartInstance = new Chart(barCanvas, {
            type: 'bar',
            data: {
                labels: barLabels,
                datasets: [{
                    label: 'Candidate Count',
                    data: barData,
                    backgroundColor: [
                        'rgba(239, 68, 68, 0.6)',  // Red
                        'rgba(245, 158, 11, 0.6)', // Amber
                        'rgba(59, 130, 246, 0.6)', // Blue
                        'rgba(16, 185, 129, 0.6)', // Emerald
                        'rgba(99, 102, 241, 0.6)', // Indigo
                        'rgba(139, 92, 246, 0.6)'  // Violet
                    ],
                    borderColor: [
                        'rgba(239, 68, 68, 1)',
                        'rgba(245, 158, 11, 1)',
                        'rgba(59, 130, 246, 1)',
                        'rgba(16, 185, 129, 1)',
                        'rgba(99, 102, 241, 1)',
                        'rgba(139, 92, 246, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.15)' },
                        ticks: { color: '#ffffff', font: { weight: 'bold' } }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.15)' },
                        ticks: { color: '#ffffff', stepSize: 1, font: { weight: 'bold' } }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

async function updateSkillsComparison(jobId) {
    const panel = $('skills-comparison-panel');
    const tbody = $('skills-comparison-tbody');
    if (!panel || !tbody) return;
    
    if (!jobId) {
        panel.style.display = 'none';
        return;
    }
    
    try {
        const response = await apiRequest(`/screening/stats/details?job_id=${jobId}`, { method: 'GET' }, API_BASE);
        const comparison = response.skills_comparison || [];
        
        if (comparison.length === 0) {
            panel.style.display = 'none';
            return;
        }
        
        panel.style.display = 'block';
        
        let html = '';
        comparison.forEach(item => {
            if (!item.skills_breakdown || item.skills_breakdown.length === 0) return;
            
            // Loop through each required skill for this candidate
            item.skills_breakdown.forEach((skillData, idx) => {
                const recency = skillData.recency;
                
                // Color badges depending on recency
                let badgeClass = 'info';
                let priorityText = 'Medium';
                if (recency === 'Recent (Current Role)') {
                    badgeClass = 'success';
                    priorityText = '🔥 High Priority';
                } else if (recency === 'Past Experience') {
                    badgeClass = 'warning';
                    priorityText = 'Medium Priority';
                } else if (recency === 'Mentioned (Profile)') {
                    badgeClass = 'info';
                    priorityText = 'Low Priority';
                } else {
                    badgeClass = 'secondary';
                    priorityText = 'No Priority';
                }
                
                html += `
                <tr style="border-bottom: 1px solid var(--border); background: rgba(255,255,255,0.02); text-align: left;">
                    ${idx === 0 ? `<td rowspan="${item.skills_breakdown.length}" style="padding: 1rem; font-weight: bold; border-right: 1px solid var(--border); vertical-align: middle; color: var(--text-primary);">${escapeHTML(item.candidate_name)}</td>` : ''}
                    <td style="padding: 0.75rem 1rem; vertical-align: middle;">
                        <span style="background: rgba(99, 102, 241, 0.15); color: #818cf8; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85rem;">
                            ${escapeHTML(skillData.skill)}
                        </span>
                    </td>
                    <td style="padding: 0.75rem 1rem; text-align: center; font-weight: bold; vertical-align: middle; color: ${skillData.frequency > 0 ? '#10b981' : 'var(--text-primary)'};">
                        ${skillData.frequency} times
                    </td>
                    <td style="padding: 0.75rem 1rem; vertical-align: middle;">
                        <span class="status-tag ${badgeClass}" style="margin-right: 8px;">
                            ${escapeHTML(recency)}
                        </span>
                        <strong style="color: ${badgeClass === 'success' ? '#10b981' : 'var(--text-primary)'}; font-size: 0.85rem;">
                            ${priorityText}
                        </strong>
                    </td>
                </tr>
                `;
            });
        });
        
        tbody.innerHTML = html || '<tr><td colspan="4" style="text-align: center; padding: 2rem; opacity: 0.7;">No skill comparison metrics available.</td></tr>';
    } catch (error) {
        console.error('Failed to load skills comparison:', error);
        panel.style.display = 'none';
    }
}

async function downloadScreeningPDF() {
    try {
        const jobId = $('screening-job-select')?.value || '';
        showToast('Generating screening PDF report...', 'info');
        window.location.href = `${API_BASE}/screening/export/pdf${jobId ? '?job_id=' + jobId : ''}`;
        showToast('PDF download initiated.', 'success');
    } catch (error) {
        console.error('Failed to download screening PDF:', error);
        showToast(`Failed to generate PDF: ${error.message}`, 'error');
    }
}

function filterOutreachCandidates() {
    const jobId = $('outreach-job-filter')?.value || '';
    const rows = state.stageData.outreachCandidates.filter((item) => !jobId || String(item.job_id || '') === jobId);
    const container = $('outreach-candidates');
    
    if (container) {
        if (!rows.length) {
            container.innerHTML = '<div class="empty-state">No shortlisted candidates yet. Complete resume screening first.</div>';
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
                    <div class="job-card-actions" style="display: flex; gap: 8px; align-items: center;">
                        ${!emailSent 
                            ? `<button class="btn btn-primary btn-sm" onclick="sendOutreach('${escapeHTML(item.id)}','${escapeHTML(item.job_id)}')">Send Email</button>` 
                            : `<span style="color: var(--color-success); font-size: 0.9em; margin-right: 8px;">✓ Email Sent</span>
                               <button class="btn btn-ghost btn-sm" onclick="resendOutreach('${escapeHTML(item.id)}','${escapeHTML(item.job_id)}')">Resend Email</button>`
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
                        ${item.status === 'pending' ? `<button class="btn btn-primary btn-sm" onclick="triggerBGV('${escapeHTML(item.id)}')">Trigger BGV</button>` : ''}
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
                    <div class="markdown-content job-description-content">${parseMarkdown(response.description) || 'No description returned.'}</div>
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
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Resume Screening`;
        }
        
        return response;
    } catch (error) {
        const btn = $('btn-run-screening');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Resume Screening`;
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
        setStatus('Resending outreach email...', 'info');
        const response = await apiRequest('/outreach/resend', {
            method: 'POST',
            body: JSON.stringify({ candidate_id: candidateId, job_id: jobId }),
        }, API_BASE);
        showToast(response.message || 'Outreach email resent successfully', 'success');
        await loadOutreachData();
        return response;
    } catch (error) {
        showToast(`Resend failed: ${error.message}`, 'error');
        throw error;
    }
}

async function deleteCandidate(candidateId) {
    if (!confirm('Are you sure you want to delete this candidate and all of their related data? This cannot be undone.')) {
        return;
    }
    try {
        setStatus('Deleting candidate...', 'info');
        const response = await apiRequest(`/screening/delete/${candidateId}`, {
            method: 'DELETE',
        }, API_BASE);
        showToast(response.message || 'Candidate deleted successfully', 'success');
        await loadScreeningData();
    } catch (error) {
        showToast(`Deletion failed: ${error.message}`, 'error');
    } finally {
        clearStatus();
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
        
        // Fetch and update prescreening stats
        try {
            const stats = await apiRequest('/prescreening/stats', { method: 'GET' }, API_BASE);
            setText('prescreening-total', stats.total_in_prescreening || 0);
            setText('prescreening-completed', stats.sessions_completed || 0);
            setText('prescreening-passed', stats.passed || 0);
            setText('bgv-cleared', stats.bgv_cleared || 0);

            setText('stat-total-sessions', stats.sessions_created || 0);
            setText('stat-sessions-completed', stats.sessions_completed || 0);
            setText('stat-sessions-passed', stats.passed || 0);

            let avgScore = 0.0;
            const scoredSessions = sessions.filter(s => s.avg_score != null);
            if (scoredSessions.length > 0) {
                avgScore = scoredSessions.reduce((sum, s) => sum + s.avg_score, 0) / scoredSessions.length;
            }
            setText('stat-avg-prescreening-score', avgScore.toFixed(1));
        } catch (statsError) {
            console.error('Failed to load prescreening stats:', statsError);
        }
        
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
                                ${session.status === 'COMPLETED' 
                                    ? `<button class="btn btn-ghost btn-sm" onclick="viewPrescreeningResults('${escapeHTML(session.session_id)}')" title="View Results">
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                                <polyline points="14 2 14 8 20 8"/>
                                                <line x1="16" y1="13" x2="8" y2="13"/>
                                                <line x1="16" y1="17" x2="8" y2="17"/>
                                                <polyline points="10 9 9 9 8 9"/>
                                            </svg>
                                       </button>`
                                    : `<button class="btn btn-ghost btn-sm" onclick="viewSessionDetails('${escapeHTML(session.session_id)}')" title="View Details">
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                                <circle cx="12" cy="12" r="3"/>
                                            </svg>
                                       </button>`
                                }
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
        
        // Hide other views initially
        const managementPanel = $('prescreening-management-panel');
        if (managementPanel) managementPanel.style.display = 'none';
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

async function onPrescreeningCandidateChange() {
    const select = $('prescreening-candidate-select');
    const candidateId = select ? select.value : '';
    
    const managementPanel = $('prescreening-management-panel');
    const loadingContainer = $('prescreening-loading');
    
    if (!candidateId) {
        if (managementPanel) managementPanel.style.display = 'none';
        if (loadingContainer) loadingContainer.style.display = 'none';
        return;
    }
    
    if (managementPanel) managementPanel.style.display = 'none';
    if (loadingContainer) {
        loadingContainer.style.display = 'block';
        setText('prescreening-loading-text', 'Loading prescreening status...');
    }
    
    try {
        const response = await apiRequest(`/prescreening/candidates/${candidateId}/session`, { method: 'GET' }, API_BASE);
        
        if (loadingContainer) loadingContainer.style.display = 'none';
        if (managementPanel) managementPanel.style.display = 'block';
        
        const candidateOption = select.options[select.selectedIndex];
        const candidateName = candidateOption ? candidateOption.text : 'Candidate';
        
        setText('recruiter-prescreening-candidate-header', `🤖 ${candidateName}`);
        
        if (response && response.exists) {
            currentPrescreeningSession = response.session_id;
            setText('recruiter-prescreening-job-header', `${response.job_title} Position`);
            
            const statusBadge = $('recruiter-session-status-badge');
            if (statusBadge) {
                let progressText = response.status.toUpperCase();
                let badgeClass = 'info';
                if (response.status === 'COMPLETED') {
                    progressText = '✓ Completed';
                    badgeClass = 'success';
                } else if (response.status === 'EXPIRED') {
                    progressText = '✕ Expired';
                    badgeClass = 'error';
                } else if (response.status === 'IN_PROGRESS') {
                    if (response.answered_questions > 0) {
                        progressText = '◐ In Progress';
                        badgeClass = 'warning';
                    } else {
                        progressText = '○ Not Started';
                        badgeClass = 'info';
                    }
                }
                statusBadge.textContent = progressText;
                statusBadge.className = `status-tag ${badgeClass}`;
            }
            
            setText('recruiter-session-sent-time', response.invitation_sent_at ? new Date(response.invitation_sent_at).toLocaleString() : 'Not sent');
            setText('recruiter-session-completed-time', response.completed_at ? new Date(response.completed_at).toLocaleString() : '—');
            
            const linkContainer = $('recruiter-assessment-link-container');
            const linkInput = $('recruiter-assessment-link-input');
            if (linkContainer && linkInput) {
                linkContainer.style.display = 'block';
                linkInput.value = response.assessment_url;
            }
            
            const generateBtn = $('btn-generate-send-invite');
            const resendBtn = $('btn-resend-invite');
            
            if (generateBtn) generateBtn.style.display = 'none';
            if (resendBtn) resendBtn.style.display = 'block';
        } else {
            currentPrescreeningSession = null;
            setText('recruiter-prescreening-job-header', 'No active prescreening session');
            
            const statusBadge = $('recruiter-session-status-badge');
            if (statusBadge) {
                statusBadge.textContent = 'PENDING';
                statusBadge.className = 'status-tag info';
            }
            
            setText('recruiter-session-sent-time', 'Never');
            setText('recruiter-session-completed-time', '—');
            
            const linkContainer = $('recruiter-assessment-link-container');
            if (linkContainer) linkContainer.style.display = 'none';
            
            const generateBtn = $('btn-generate-send-invite');
            const resendBtn = $('btn-resend-invite');
            
            if (generateBtn) generateBtn.style.display = 'block';
            if (resendBtn) resendBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to load candidate prescreening status:', error);
        showToast('Error loading prescreening status', 'error');
        if (loadingContainer) loadingContainer.style.display = 'none';
    }
}

async function generateAndSendInvite() {
    const select = $('prescreening-candidate-select');
    const candidateId = select ? select.value : '';
    if (!candidateId) return;
    
    const generateBtn = $('btn-generate-send-invite');
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating & Sending Invite...';
    }
    
    try {
        const response = await apiRequest('/prescreening/start-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_id: candidateId })
        }, API_BASE);
        
        if (response.success) {
            showToast('Prescreening invite generated and email sent successfully!', 'success');
            await onPrescreeningCandidateChange();
            await loadPrescreeningData();
        } else {
            showToast('Failed to generate invite', 'error');
        }
    } catch (error) {
        console.error('Invite generation error:', error);
        showToast(`Failed to generate invite: ${error.message}`, 'error');
    } finally {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate & Send Invite';
        }
    }
}

async function resendInviteEmail() {
    const select = $('prescreening-candidate-select');
    const candidateId = select ? select.value : '';
    if (!candidateId) return;
    
    const resendBtn = $('btn-resend-invite');
    if (resendBtn) {
        resendBtn.disabled = true;
        resendBtn.textContent = 'Resending Invitation...';
    }
    
    try {
        const response = await apiRequest('/outreach/resend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_id: candidateId, job_id: 'auto' })
        }, API_BASE);
        
        showToast('Prescreening email invitation resent successfully!', 'success');
        await onPrescreeningCandidateChange();
    } catch (error) {
        console.error('Email resend error:', error);
        showToast(`Failed to resend invite: ${error.message}`, 'error');
    } finally {
        if (resendBtn) {
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend Email Invite';
        }
    }
}

function copyAssessmentLink() {
    const input = $('recruiter-assessment-link-input');
    if (input && input.value) {
        navigator.clipboard.writeText(input.value)
            .then(() => showToast('Assessment link copied to clipboard!', 'success'))
            .catch(() => showToast('Failed to copy link', 'error'));
    }
}

async function viewPrescreeningResults(sessionId) {
    const modal = $('prescreening-results-modal');
    const modalBody = $('prescreening-modal-body');
    if (!modal || !modalBody) return;
    
    modalBody.innerHTML = '<div style="text-align:center;padding:2rem;"><div class="spinner" style="display:inline-block;width:30px;height:30px;border:3px solid rgba(255,255,255,0.05);border-top-color:var(--accent-blue);border-radius:50%;animation:spin 0.8s linear infinite;"></div><p style="margin-top:10px;opacity:0.7;">Loading assessment responses...</p></div>';
    modal.style.display = 'block';
    
    try {
        const res = await apiRequest(`/prescreening/session/${sessionId}/results`, { method: 'GET' }, API_BASE);
        
        if (res && res.success) {
            const verdictClass = res.evaluation.verdict === 'PASS' ? 'success' : res.evaluation.verdict === 'BORDERLINE' ? 'warning' : 'error';
            
            const answersHtml = res.answers.map(ans => `
                <div style="margin-bottom:20px;padding:16px;background:rgba(255,255,255,0.02);border:1px solid var(--border);border-radius:8px;">
                    <div style="font-weight:600;margin-bottom:8px;font-size:0.95rem;color:var(--text-primary);">Q${ans.question_index + 1}: ${escapeHTML(ans.question)}</div>
                    <div style="margin-bottom:12px;font-style:italic;color:var(--text-secondary);font-size:0.9rem;white-space:pre-wrap;">"${escapeHTML(ans.answer)}"</div>
                    <div style="display:flex;gap:12px;font-size:0.82rem;border-top:1px solid rgba(255,255,255,0.05);padding-top:8px;">
                        <span><strong>Score:</strong> <span class="status-tag ${ans.ai_score === 'Excellent' ? 'success' : ans.ai_score === 'Good' ? 'success' : ans.ai_score === 'Average' ? 'warning' : 'error'}">${ans.ai_score}</span></span>
                        <span><strong>AI Feedback:</strong> ${escapeHTML(ans.ai_feedback)}</span>
                    </div>
                </div>
            `).join('');
            
            modalBody.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.03);padding:16px;border-radius:8px;margin-bottom:20px;border:1px solid var(--border);">
                    <div>
                        <h4 style="margin:0;font-size:1.1rem;color:var(--text-primary);">${escapeHTML(res.candidate_name)}</h4>
                        <span style="font-size:0.85rem;color:var(--text-secondary);">${escapeHTML(res.job_title)} Application</span>
                    </div>
                    <div style="text-align:right;">
                        <span class="status-tag ${verdictClass}" style="font-size:1rem;padding:6px 12px;font-weight:700;">${res.evaluation.verdict}</span>
                        <div style="font-size:0.82rem;margin-top:4px;color:var(--text-secondary);">Avg Rating: <strong>${res.evaluation.score} / 4.0</strong></div>
                    </div>
                </div>
                <div style="margin-bottom:20px;">
                    <h5 style="margin:0 0 8px 0;font-size:0.9rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;">AI Summary Feedback</h5>
                    <p style="margin:0;font-size:0.95rem;line-height:1.5;color:var(--text-primary);">${escapeHTML(res.evaluation.feedback)}</p>
                </div>
                <div>
                    <h5 style="margin:0 0 12px 0;font-size:0.9rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;">Assessment Responses</h5>
                    ${answersHtml}
                </div>
            `;
        } else {
            modalBody.innerHTML = '<div class="empty-state">Failed to load results.</div>';
        }
    } catch (err) {
        console.error('Failed to load results:', err);
        modalBody.innerHTML = `<div class="empty-state" style="color:var(--color-error);">Error loading results: ${err.message}</div>`;
    }
}

function closePrescreeningResultsModal() {
    const modal = $('prescreening-results-modal');
    if (modal) modal.style.display = 'none';
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

// (Legacy duplicate code removed - active implementation is at the bottom of the file)

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
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files);
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
            handleFileUpload(files);
        }
    });
}

// Handle file upload (supports single or multiple files)
async function handleFileUpload(files) {
    const fileList = files instanceof FileList || Array.isArray(files) ? files : [files];
    if (fileList.length === 0) return;

    const progressDiv = $('upload-progress');
    const resultDiv = $('parse-result');
    const statusSpan = $('upload-status');
    const progressFill = $('progress-fill');
    
    try {
        // Show progress
        show('upload-progress');
        hide('parse-result');
        
        if (statusSpan) statusSpan.textContent = `Uploading ${fileList.length} files...`;
        if (progressFill) progressFill.style.width = '20%';

        // Get selected job
        const jobId = $('resume-job-select')?.value || null;
        
        // Create form data
        const formData = new FormData();
        for (let i = 0; i < fileList.length; i++) {
            formData.append('files', fileList[i]);
        }
        if (jobId) formData.append('job_id', jobId);

        // Upload files using bulk endpoint
        const response = await fetch(`${API_BASE}/sourcing/upload-resume-bulk`, {
            method: 'POST',
            body: formData
        });

        if (progressFill) progressFill.style.width = '60%';
        if (statusSpan) statusSpan.textContent = 'Processing files...';

        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || result.message || 'Upload failed');
        }

        if (progressFill) progressFill.style.width = '100%';
        if (statusSpan) statusSpan.textContent = 'Parsing resumes...';

        showToast(`Successfully queued ${result.uploaded_count} resumes! Parsing in progress...`, 'success');
        
        // Refresh candidates list immediately
        await loadCandidates();
        
        // Wait a few seconds to let first files parse, then hide progress and show details
        setTimeout(async () => {
            hide('upload-progress');
            show('parse-result');
            
            const parseContent = $('parse-content');
            if (parseContent) {
                let parsedHTML = `
                    <div class="parse-result-card">
                        <h4>Bulk Upload Status</h4>
                        <div class="parse-details">
                            <p><strong>Successfully Queued:</strong> ${result.uploaded_count} candidates</p>
                            <p><strong>Failed Uploads:</strong> ${result.failed.length}</p>
                        </div>
                `;
                
                if (result.failed.length > 0) {
                    parsedHTML += `
                        <div class="failed-uploads-list" style="margin-top: 10px; color: var(--error-color);">
                            <h5>Errors:</h5>
                            <ul style="padding-left: 20px;">
                                ${result.failed.map(f => `<li><strong>${escapeHTML(f.filename)}:</strong> ${escapeHTML(f.reason)}</li>`).join('')}
                            </ul>
                        </div>
                    `;
                }
                
                parsedHTML += `
                        <div class="parse-actions" style="margin-top: 15px;">
                            <button class="btn btn-primary" onclick="loadCandidates()">
                                Refresh Candidates List
                            </button>
                        </div>
                    </div>
                `;
                
                parseContent.innerHTML = parsedHTML;
            }
            await loadCandidates();
        }, 3000);

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

let fallbackSyncInterval = null;

function switchTab(tabId) {
    if (!tabId || !document.getElementById(`tab-${tabId}`)) {
        tabId = 'overview';
    }
    
    // Clear any active fallback synchronization interval
    if (fallbackSyncInterval) {
        clearInterval(fallbackSyncInterval);
        fallbackSyncInterval = null;
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
        case 'stage6': 
            loadEvaluationResults(); 
            loadInterviewResults(); 
            loadInterviewCandidates(); 
            // Enable fallback synchronization polling every 5 seconds for stage 6
            fallbackSyncInterval = setInterval(() => {
                loadInterviewResults();
                loadEvaluationResults();
            }, 5000);
            break;
        case 'stage8': loadOffers(); break;
        case 'stage9': loadOnboarding(); loadCompletedCandidates(); break;
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
    const recordedInterviewUrl = getOptionalText('interview-recording-url');

    if (!sessionId || !candidateId) {
        showToast('Please select a generated candidate session ID', 'error');
        return;
    }

    if (finalScore === null || finalScore < 0 || finalScore > 100) {
        showToast('Final score must be between 0 and 100', 'error');
        return;
    }

    if ((contentScore !== null && (contentScore < 0 || contentScore > 100)) ||
        (behaviorScore !== null && (behaviorScore < 0 || behaviorScore > 100))) {
        showToast('Content and behavior scores must be between 0 and 100', 'error');
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
        recommendation: getOptionalText('interview-recommendation'),
        recorded_interview_url: recordedInterviewUrl
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
        const passed = evaluations.filter((item) => {
            const s = Number(item.final_score || 0);
            return s >= 60 || (s >= 0.6 && s <= 1.0);
        }).length;
        const failed = totalEvals - passed;
        const avgScore = totalEvals > 0
            ? (evaluations.reduce((sum, item) => {
                const s = Number(item.final_score || 0);
                const val = s <= 1.0 ? s * 100 : s;
                return sum + val;
              }, 0) / totalEvals).toFixed(1)
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

        const feedbackSummary = report.report?.feedback_summary || output.evaluator_notes || '';
        let strengthsHTML = '<li>No specific strengths recorded.</li>';
        let weaknessesHTML = '<li>No specific weaknesses recorded.</li>';

        if (feedbackSummary) {
            const strengthsMatch = feedbackSummary.match(/(?:strengths|pros|positives):\s*([\s\S]*?)(?=(?:weaknesses|cons|negatives|recommendation|overall|$))/i);
            const weaknessesMatch = feedbackSummary.match(/(?:weaknesses|cons|negatives):\s*([\s\S]*?)(?=(?:strengths|pros|positives|recommendation|overall|$))/i);

            if (strengthsMatch && strengthsMatch[1]) {
                const list = strengthsMatch[1].split('\n').map(s => s.trim().replace(/^-\s*|\*\s*/, '')).filter(Boolean);
                if (list.length) strengthsHTML = list.map(s => `<li>${escapeHTML(s)}</li>`).join('');
            }
            if (weaknessesMatch && weaknessesMatch[1]) {
                const list = weaknessesMatch[1].split('\n').map(w => w.trim().replace(/^-\s*|\*\s*/, '')).filter(Boolean);
                if (list.length) weaknessesHTML = list.map(w => `<li>${escapeHTML(w)}</li>`).join('');
            }
        }

        const recommendation = report.report?.recommendation || output.recommendation || 'n/a';
        const statusClass = ['STRONG_HIRE', 'HIRE'].includes(recommendation) ? 'success' : (recommendation === 'HOLD' ? 'warning' : 'error');
        const finalScore = report.report?.score_percent ?? output.final_score_percent ?? 'n/a';

        detail.innerHTML = `
            <div style="background: var(--bg-surface); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); box-shadow: var(--shadow-md); display: grid; gap: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 1rem;">
                    <div>
                        <h3 style="margin: 0; font-size: 1.5rem; color: var(--text-primary);">${escapeHTML(report.candidate?.name || 'Unknown Candidate')}</h3>
                        <p style="margin: 0.25rem 0 0 0; opacity: 0.7; font-size: 0.9rem;">Job: ${escapeHTML(report.job?.title || 'Unknown Position')} (${escapeHTML(output.phase || 'Interview')})</p>
                    </div>
                    <span class="status-tag ${statusClass}" style="font-size: 1rem; padding: 0.5rem 1rem;">${escapeHTML(recommendation.replace('_', ' '))}</span>
                </div>

                ${output.recorded_interview_url ? `
                <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); padding: 1rem; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
                    <span style="display: flex; align-items: center; gap: 8px; font-size: 0.95rem; color: var(--text-primary);">
                        🎥 <strong>Recorded Interview:</strong> <span style="opacity: 0.8; font-size: 0.9rem; margin-left: 4px; word-break: break-all;">${escapeHTML(output.recorded_interview_url)}</span>
                    </span>
                    <a href="${escapeHTML(output.recorded_interview_url)}" target="_blank" class="btn btn-primary btn-sm" style="text-decoration: none; display: inline-flex; align-items: center; gap: 4px; padding: 0.4rem 0.8rem; flex-shrink: 0;">
                        Watch Recording
                    </a>
                </div>
                ` : ''}

                <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; margin: 0;">
                    <div class="stat-card" style="padding: 1rem; text-align: center; box-shadow: none; border: 1px solid var(--border);">
                        <span style="font-size: 0.8rem; opacity: 0.7; display: block; margin-bottom: 0.25rem;">Overall Score</span>
                        <strong style="font-size: 1.6rem; color: var(--accent-blue);">${finalScore}%</strong>
                    </div>
                    <div class="stat-card" style="padding: 1rem; text-align: center; box-shadow: none; border: 1px solid var(--border);">
                        <span style="font-size: 0.8rem; opacity: 0.7; display: block; margin-bottom: 0.25rem;">Technical</span>
                        <strong style="font-size: 1.6rem; color: var(--text-primary);">${output.content_score ?? 'n/a'}%</strong>
                    </div>
                    <div class="stat-card" style="padding: 1rem; text-align: center; box-shadow: none; border: 1px solid var(--border);">
                        <span style="font-size: 0.8rem; opacity: 0.7; display: block; margin-bottom: 0.25rem;">Behavioral</span>
                        <strong style="font-size: 1.6rem; color: var(--text-primary);">${output.behavior_score ?? 'n/a'}%</strong>
                    </div>
                    <div class="stat-card" style="padding: 1rem; text-align: center; box-shadow: none; border: 1px solid var(--border);">
                        <span style="font-size: 0.8rem; opacity: 0.7; display: block; margin-bottom: 0.25rem;">Communication</span>
                        <strong style="font-size: 1.6rem; color: var(--text-primary);">${output.behavior_score ?? 'n/a'}%</strong>
                    </div>
                    <div class="stat-card" style="padding: 1rem; text-align: center; box-shadow: none; border: 1px solid var(--border);">
                        <span style="font-size: 0.8rem; opacity: 0.7; display: block; margin-bottom: 0.25rem;">Confidence</span>
                        <strong style="font-size: 1.6rem; color: var(--text-primary);">${output.behavior_score ?? 'n/a'}%</strong>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 0.5rem;">
                    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 1.25rem; border-radius: 8px;">
                        <h4 style="margin: 0 0 0.75rem 0; color: #10b981; display: flex; align-items: center; gap: 6px;">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16"><polyline points="20 6 9 17 4 12"/></svg>
                            Key Strengths
                        </h4>
                        <ul style="margin: 0; padding-left: 1.25rem; line-height: 1.6; color: var(--text-primary);">${strengthsHTML}</ul>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); padding: 1.25rem; border-radius: 8px;">
                        <h4 style="margin: 0 0 0.75rem 0; color: #ef4444; display: flex; align-items: center; gap: 6px;">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                            Areas for Development
                        </h4>
                        <ul style="margin: 0; padding-left: 1.25rem; line-height: 1.6; color: var(--text-primary);">${weaknessesHTML}</ul>
                    </div>
                </div>

                <div style="background: var(--bg-tertiary); padding: 1.25rem; border-radius: 8px; border-left: 4px solid var(--accent-purple);">
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; opacity: 0.85;">Feedback Summary</h4>
                    <p style="margin: 0; line-height: 1.6; font-size: 0.95rem; white-space: pre-wrap;">${escapeHTML(feedbackSummary || 'No evaluation notes provided.')}</p>
                </div>

                <div style="display: flex; gap: 1rem; font-size: 0.85rem; opacity: 0.75; border-top: 1px solid var(--border); padding-top: 0.75rem;">
                    <span><strong>Email:</strong> ${escapeHTML(report.candidate?.email || 'n/a')}</span>
                    <span><strong>Session ID:</strong> ${escapeHTML(output.session_id || 'n/a')}</span>
                    <span><strong>Status:</strong> COMPLETED</span>
                </div>
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
window.deleteCandidate = deleteCandidate;
window.exportShortlist = exportShortlist;
window.createPrescreeningSession = createPrescreeningSession;
window.exportPrescreeningData = exportPrescreeningData;
window.runBulkEvaluation = runBulkEvaluation;
window.closeSessionDetails = closeSessionDetails;
window.viewSessionDetails = viewSessionDetails;
window.exportAnalyticsCSV = exportAnalyticsCSV;
window.exportAnalyticsPDF = exportAnalyticsPDF;
window.downloadScreeningPDF = downloadScreeningPDF;


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
    
    const btn = $('btn-generate-onboarding');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" style="animation: spin 1s linear infinite; margin-right: 8px; display: inline-block; vertical-align: middle;"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Generating Tasks...`;
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
        
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Generate Tasks & Create Onboarding';
        }
        return response;
    } catch (error) {
        setStatus(`Failed to create onboarding: ${error.message}`, 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Generate Tasks & Create Onboarding';
        }
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

async function triggerBGV(onboardingId) {
    try {
        setStatus('Triggering BGV...', 'info');
        const response = await apiRequest(`/onboarding/${onboardingId}/bgv`, { method: 'POST' }, API_BASE);
        setStatus(response.message || 'BGV triggered!', 'success');
        await loadOnboarding();
        return response;
    } catch (error) {
        setStatus(`Trigger BGV failed: ${error.message}`, 'error');
        return null;
    }
}

// Make functions available globally
window.acceptOffer = acceptOffer;
window.dispatchOffer = dispatchOffer;
window.viewOnboardingTasks = viewOnboardingTasks;
window.triggerBGV = triggerBGV;
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
    try {
        setStatus('Resending interview email...', 'info');
        const response = await apiRequest(`/interview/resend/${sessionId}`, { 
            method: 'POST' 
        }, API_BASE);
        setStatus(response.message || 'Interview email resent successfully!', 'success');
        await loadInterviewResults();
        return response;
    } catch (error) {
        setStatus(`Failed to resend email: ${error.message}`, 'error');
        await loadInterviewResults();
        return null;
    }
}

async function submitRecruiterOverride(evaluationId) {
    const decision = $('override-decision').value;
    const notes = $('override-notes').value;
    
    if (!decision) {
        showToast('Please select a recruiter decision override', 'error');
        return;
    }
    
    try {
        const response = await apiRequest(`/evaluation/override/${evaluationId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recruiter_decision: decision,
                recruiter_notes: notes
            })
        }, API_BASE);
        
        if (response && response.success) {
            showToast('Recruiter overrides saved successfully!', 'success');
            closeInterviewResultsModal();
            await loadEvaluationResults(); // Refresh list to display updated recruiter decisions
        } else {
            showToast('Failed to save recruiter overrides', 'error');
        }
    } catch (err) {
        console.error('Error submitting override:', err);
        showToast(`Error: ${err.message}`, 'error');
    }
}

// Make functions globally available
window.launchInterview = launchInterview;
window.copyInterviewLink = copyInterviewLink;
window.resendInterviewEmail = resendInterviewEmail;
window.submitRecruiterOverride = submitRecruiterOverride;
window.resendOutreach = resendOutreach;
window.changeCandidateStage = changeCandidateStage;
window.generateAndSendInvite = generateAndSendInvite;
window.resendInviteEmail = resendInviteEmail;
window.copyAssessmentLink = copyAssessmentLink;
window.viewPrescreeningResults = viewPrescreeningResults;
window.closePrescreeningResultsModal = closePrescreeningResultsModal;


async function changeCandidateStage(candidateId, currentStage, newStage) {
    if (currentStage === newStage) return;
    
    const currentLabel = currentStage.charAt(0).toUpperCase() + currentStage.slice(1);
    const newLabel = newStage.charAt(0).toUpperCase() + newStage.slice(1);
    
    const confirmMessage = `Are you sure you want to transition this candidate's Pipeline Stage from "${currentLabel}" to "${newLabel}"?\n\n` + 
        (newStage === 'interview' ? '⚠️ This will make the candidate directly eligible for Interview (bypassing Prescreening).\n\n' : '') +
        (newStage === 'rejected' ? '⚠️ This will reject the candidate and remove them from outreach/interview pipelines.\n\n' : '') +
        'Confirm transition?';
        
    if (!confirm(confirmMessage)) {
        await loadScreeningData();
        return;
    }
    
    try {
        const response = await apiRequest(`/screening/candidates/${candidateId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStage })
        });
        
        if (response && response.success) {
            showToast(`Candidate successfully moved to ${newLabel}`, 'success');
            await loadScreeningData();
            // Immediate UI update for Stage 6 active lists & selectors
            await loadInterviewResults();
            await loadEvaluationResults();
            await loadInterviewCandidates();
        } else {
            showToast('Failed to update pipeline stage', 'error');
            await loadScreeningData();
        }
    } catch (err) {
        console.error('Error updating stage:', err);
        showToast(err.message || 'Error updating pipeline stage', 'error');
        await loadScreeningData();
    }
}

