function initChat() {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const skipButton = document.getElementById('skip-button');
    const endButton = document.getElementById('end-button');
    const reportButton = document.getElementById('report-button');
    const statusText = document.getElementById('status-text');
    const statusSpinner = document.getElementById('status-spinner');
    const rubricBody = document.getElementById('rubric-body');
    const logBody = document.getElementById('log-body');
    const summaryBody = document.getElementById('summary-body');
    const statsBody = document.getElementById('stats-body');
    const personaSelect = document.getElementById('persona-select');
    const interviewTimerEl = document.getElementById('interview-timer');
    const wordCounterEl = document.getElementById('word-counter');
    const turnTimerEl = document.getElementById('turn-timer');
    // Auto-answer controls
    const autoToggle = document.getElementById('auto-toggle');
    const autoControls = document.getElementById('auto-controls');
    const confidenceSelect = document.getElementById('confidence-select');
    const verbositySelect = document.getElementById('verbosity-select');
    const skillMatrixContainer = document.getElementById('skill-matrix-container');
    const reloadSkillMatrixBtn = document.getElementById('reload-skill-matrix');
    const autoGenerateBtn = document.getElementById('auto-generate');
    const autoSend = document.getElementById('auto-send');

    const ORCH_BASE = sessionStorage.getItem('AI_SERVICE_URL') || 'http://localhost:8003';
    const context = {
        job_description: sessionStorage.getItem('job_description') || '',
        candidate_resume: sessionStorage.getItem('candidate_resume') || '',
        candidate_profile: sessionStorage.getItem('candidate_profile') || '',
        candidate_id: sessionStorage.getItem('candidate_id') || '',
        job_id: sessionStorage.getItem('job_id') || ''
    };

    const history = [];
    let blueprint = null;
    let currentTopicName = null;
    const topicStrength = {};
    const questionStats = {};
    let ws = null;
    let sessionId = null;
    let interviewStart = null;
    let interviewInterval = null;
    let turnStart = null;
    let turnInterval = null;
    let totalWords = 0;
    let lastQuestionText = '';
    let skillMatrixState = [];

    function updateCandidateProfileContext() {
        try {
            let prof = {};
            if (context.candidate_profile) {
                try { prof = JSON.parse(context.candidate_profile); } catch (_) { prof = {}; }
            }
            // Do not persist beyond this page; only update the in-memory context
            const copy = (Array.isArray(skillMatrixState) ? skillMatrixState.map(it => ({
                skill: it.skill,
                category: it.category,
                proficiency: it.proficiency,
            })) : []);
            prof.skill_matrix = copy;
            context.candidate_profile = JSON.stringify(prof);
            // Persist only to sessionStorage (not DB) so it survives reloads
            try { sessionStorage.setItem('candidate_profile', context.candidate_profile); } catch (_) {}
        } catch (_) {
            // If anything goes wrong, keep existing context as-is
        }
    }

    function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }

    function setSkillMatrixState(list) {
        const arr = Array.isArray(list) ? list : [];
        skillMatrixState = arr.map(it => ({
            skill: String((it && it.skill) || '').trim(),
            category: String((it && it.category) || '').trim(),
            proficiency: clamp(parseInt((it && it.proficiency), 10) || 1, 1, 10),
        })).filter(it => it.skill);
        renderSkillMatrix();
        updateCandidateProfileContext();
    }

    function renderSkillMatrix() {
        if (!skillMatrixContainer) return;
        if (!skillMatrixState.length) {
            skillMatrixContainer.innerHTML = '<div class="text-muted small">No skill matrix found in profile. Use the job selector page to generate a profile, or proceed without it.</div>';
            return;
        }
        skillMatrixContainer.innerHTML = '';
        skillMatrixState.forEach((it, idx) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'mb-2';
            const cat = it.category ? ` <span class="text-muted">(${it.category})</span>` : '';
            wrapper.innerHTML = `
                <div class="d-flex justify-content-between">
                    <label class="form-label small mb-1"><strong>${it.skill}</strong>${cat}</label>
                    <span class="small"><span id="sm-val-${idx}">${it.proficiency}</span>/10</span>
                </div>
                <input type="range" class="form-range" min="1" max="10" step="1" value="${it.proficiency}" data-index="${idx}">
            `;
            skillMatrixContainer.appendChild(wrapper);
        });
        const inputs = skillMatrixContainer.querySelectorAll('input[type="range"][data-index]');
        inputs.forEach(input => {
            input.addEventListener('input', (e) => {
                const i = parseInt(e.target.getAttribute('data-index'), 10);
                const val = clamp(parseInt(e.target.value, 10) || 1, 1, 10);
                if (skillMatrixState[i]) skillMatrixState[i].proficiency = val;
                const valEl = document.getElementById(`sm-val-${i}`);
                if (valEl) valEl.textContent = String(val);
                updateCandidateProfileContext();
            });
        });
    }

    function loadSkillMatrixFromCandidateProfile() {
        try {
            const profStr = sessionStorage.getItem('candidate_profile') || '';
            if (!profStr) { setSkillMatrixState([]); return; }
            const prof = JSON.parse(profStr);
            const sm = prof && prof.skill_matrix;
            if (Array.isArray(sm) && sm.length) setSkillMatrixState(sm);
            else setSkillMatrixState([]);
        } catch (_) {
            setSkillMatrixState([]);
        }
    }

    function toWS(url) {
        try {
            const u = new URL(url);
            u.protocol = (u.protocol === 'https:') ? 'wss:' : 'ws:';
            return u.toString().replace(/\/$/, '');
        } catch (_) {
            return url.replace(/^http/, 'ws');
        }
    }

    function setThinking(thinking, text) {
        if (thinking) {
            if (statusSpinner) statusSpinner.classList.remove('d-none');
            if (statusText) statusText.textContent = text || 'AI is thinking...';
            chatInput.disabled = true;
            sendButton.disabled = true;
            if (skipButton) skipButton.disabled = true;
        } else {
            if (statusSpinner) statusSpinner.classList.add('d-none');
            if (statusText) statusText.textContent = 'Connected';
            chatInput.disabled = false;
            sendButton.disabled = false;
            if (skipButton) skipButton.disabled = false;
            chatInput.focus();
        }
    }

    function addMessage(sender, text) {
        const message = document.createElement('div');
        message.classList.add('message', sender);
        message.innerHTML = marked.parse(text || '');
        chatLog.appendChild(message);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function updateRubric(data) {
        if (!rubricBody || !data) return;
        rubricBody.innerHTML = `
            <div><strong>Score:</strong> ${data.score}/10</div>
            <div><strong>Depth:</strong> ${data.assessed_depth}</div>
            <div><strong>Confidence:</strong> ${data.llm_confidence}</div>
            <div><strong>Truthful:</strong> ${data.is_truthful ? 'Yes' : 'No'}</div>
            <div><strong>Justification:</strong> ${data.justification}</div>
        `;
    }

    function addLog(text) {
        if (!logBody) return;
        const entry = document.createElement('div');
        entry.classList.add('small', 'text-muted');
        entry.textContent = text;
        logBody.appendChild(entry);
        logBody.scrollTop = logBody.scrollHeight;
    }

    function updateSummary() {
        if (!summaryBody) return;
        const parts = Object.entries(topicStrength).map(([topic, info]) => {
            const avg = info.count ? info.total / info.count : 0;
            const pct = Math.min(100, Math.max(0, avg * 10));
            return `
                <div class="mb-2">
                    <div><strong>${topic}</strong> (${avg.toFixed(1)}/10)</div>
                    <div class="progress">
                        <div class="progress-bar" role="progressbar" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        });
        summaryBody.innerHTML = parts.length ? parts.join('') : '<p class="text-muted mb-0">No topic evaluations yet.</p>';
    }

    function updateStatsTable() {
        if (!statsBody) return;
        const difficulties = [1,2,3,4,5];
        const rows = Object.entries(questionStats).map(([topic, counts]) => {
            const cells = difficulties.map(d => `<td>${counts[d] || 0}</td>`).join('');
            return `<tr><td>${topic}</td>${cells}</tr>`;
        }).join('');
        const table = `
            <table class="table table-sm mb-0">
                <thead><tr><th>Topic</th>${difficulties.map(d => `<th>D${d}</th>`).join('')}</tr></thead>
                <tbody>${rows || '<tr><td colspan="6" class="text-muted">No questions yet</td></tr>'}</tbody>
            </table>
        `;
        statsBody.innerHTML = table;
    }

    function initStatsFromBlueprint(bp) {
        questionStats["General"] = {1:0,2:0,3:0,4:0,5:0};
        (bp.topics || []).forEach(t => {
            questionStats[t.name] = {1:0,2:0,3:0,4:0,5:0};
            topicStrength[t.name] = { total: 0, count: 0 };
        });
        updateStatsTable();
        updateSummary();
    }

    function formatTime(sec) {
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }

    function startInterviewTimer() {
        interviewStart = Date.now();
        if (interviewInterval) clearInterval(interviewInterval);
        interviewInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - interviewStart) / 1000);
            if (interviewTimerEl) interviewTimerEl.textContent = formatTime(elapsed);
        }, 1000);
    }

    function startTurnTimer() {
        turnStart = Date.now();
        if (turnInterval) clearInterval(turnInterval);
        turnInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - turnStart) / 1000);
            if (turnTimerEl) turnTimerEl.textContent = formatTime(elapsed);
        }, 1000);
    }

    function resetTurnTimer() {
        startTurnTimer();
    }

    function stopTimers() {
        if (interviewInterval) clearInterval(interviewInterval);
        if (turnInterval) clearInterval(turnInterval);
    }

    function connectWS() {
        const wsBase = toWS(ORCH_BASE);
        sessionId = `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;
        ws = new WebSocket(`${wsBase}/api/v1/ws/${sessionId}`);

        ws.onopen = () => {
            setThinking(true, 'Starting session...');
            const persona = (personaSelect && personaSelect.value) || sessionStorage.getItem('persona') || 'friendly_mentor';
            sessionStorage.setItem('persona', persona);
            const payload = { job_description: context.job_description, candidate_resume: context.candidate_resume, persona };
            const tl = parseInt(sessionStorage.getItem('time_limit'), 10);
            const wl = parseInt(sessionStorage.getItem('word_limit'), 10);
            if (!isNaN(tl)) payload.time_limit = tl;
            if (!isNaN(wl)) payload.word_limit = wl;
            ws.send(JSON.stringify({ event: 'join_session', payload }));
        };

        ws.onclose = () => {
            setThinking(false);
            if (statusText) statusText.textContent = 'Disconnected';
            if (sendButton) sendButton.disabled = true;
            if (endButton) endButton.disabled = true;
        };

        ws.onerror = () => {
            setThinking(false);
            if (statusText) statusText.textContent = 'Connection error';
        };

        ws.onmessage = (ev) => {
            let msg = null;
            try { msg = JSON.parse(ev.data); } catch (_) { return; }
            const { event, payload } = msg || {};
            if (event === 'session_started') {
                if (statusText) statusText.textContent = 'Connected';
                chatInput.disabled = false;
                sendButton.disabled = false;
                if (skipButton) skipButton.disabled = false;
                if (endButton) endButton.disabled = false;
                startInterviewTimer();
            } else if (event === 'blueprint') {
                blueprint = payload;
                initStatsFromBlueprint(blueprint);
                addLog('Interview started');
                if (payload && Array.isArray(payload.topics)) {
                    const names = payload.topics.map(t => t.name).join(', ');
                    addLog(`Topics: ${names}`);
                }
            } else if (event === 'interviewer_typing') {
                setThinking(true);
            } else if (event === 'evaluation') {
                updateRubric(payload);
                if (currentTopicName && topicStrength[currentTopicName]) {
                    if (typeof payload.score === 'number') {
                        topicStrength[currentTopicName].total += payload.score;
                        topicStrength[currentTopicName].count += 1;
                        updateSummary();
                    }
                }
            } else if (event === 'new_question') {
                const q = (payload && payload.question_text) || '';
                const t = (payload && payload.topic) || 'General';
                const d = (payload && payload.difficulty) || 3;
                currentTopicName = t;
                if (q) {
                    history.push({ role: 'interviewer', message: q });
                    addMessage('interviewer', q);
                    addLog(`Asked question on ${t} (difficulty ${d})`);
                    if (!questionStats[t]) questionStats[t] = {1:0,2:0,3:0,4:0,5:0};
                    questionStats[t][d] = (questionStats[t][d] || 0) + 1;
                    updateStatsTable();
                }
                lastQuestionText = q || '';
                setThinking(false);
                resetTurnTimer();
                // Auto-generate answer if toggled on
                if (autoToggle && autoToggle.checked && lastQuestionText) {
                    requestAutoAnswer();
                }
            } else if (event === 'interview_ended') {
                setThinking(false);
                addMessage('interviewer', 'Interview ended. Thank you for your time.');
                addLog('Interview ended');
                chatInput.disabled = true;
                sendButton.disabled = true;
                if (skipButton) skipButton.disabled = true;
                if (endButton) endButton.disabled = true;
                if (reportButton) reportButton.disabled = false;
                if (statusText) statusText.textContent = 'Interview ended';
                stopTimers();
                fetch(`${ORCH_BASE}/api/v1/sessions/${sessionId}`).then(r => r.json()).then(data => {
                    if (data && rubricBody) {
                        const score = data.final_score != null ? data.final_score : 'N/A';
                        const summaryText = data.summary ? `<div class="mt-2">${marked.parse(data.summary)}</div>` : '';
                        rubricBody.innerHTML = `
                            <div><strong>Final Score:</strong> ${score}</div>
                            ${summaryText}
                        `;
                    }
                }).catch(() => {});
            }
        };
    }

    async function requestAutoAnswer() {
        if (!sessionId) return;
        try {
            // Collect current skill matrix from sliders
            const skill_matrix = (Array.isArray(skillMatrixState) && skillMatrixState.length) ? skillMatrixState : null;
            const confidence = (confidenceSelect && confidenceSelect.value) || 'Medium';
            const verbosity = (verbositySelect && verbositySelect.value) || 'Balanced';
            // Ensure context carries the updated profile before sending
            updateCandidateProfileContext();
            const body = {
                // New controls
                confidence,
                verbosity,
                skill_matrix,
                job_description: context.job_description || '',
                candidate_resume: context.candidate_resume || '',
                candidate_profile: context.candidate_profile || '',
                candidate_id: context.candidate_id || '',
                job_id: context.job_id || ''
            };
            addLog('Auto-generating candidate answer...');
            const resp = await fetch(`${ORCH_BASE}/api/v1/sessions/${sessionId}/auto-answer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            const answer = (data && (data.answer_text || data.text)) || '';
            if (answer) {
                chatInput.value = answer;
                addLog('Auto answer populated in input.');
                if (autoSend && autoSend.checked) {
                    // Send immediately if requested
                    sendMessage();
                }
            } else {
                addLog('Auto-answer returned empty text.');
            }
        } catch (e) {
            console.error('Auto-answer failed', e);
            addLog('Auto-answer failed');
        }
    }

    function sendMessage() {
        const messageText = chatInput.value;
        if (!messageText || !messageText.trim()) return;
        addMessage('candidate', messageText);
        history.push({ role: 'candidate', message: messageText });
        addLog(`Candidate answered: ${messageText}`);
        chatInput.value = '';
        const words = messageText.trim().split(/\s+/).filter(Boolean).length;
        totalWords += words;
        if (wordCounterEl) wordCounterEl.textContent = totalWords.toString();
        if (turnInterval) clearInterval(turnInterval);
        setThinking(true);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ event: 'send_answer', payload: { answer_text: messageText } }));
        }
    }

    function endInterview() {
        const confirmed = window.confirm('Are you sure you want to end the interview?');
        if (!confirmed) return;
        setThinking(false);
        chatInput.disabled = true;
        sendButton.disabled = true;
        if (skipButton) skipButton.disabled = true;
        if (endButton) endButton.disabled = true;
        if (statusText) statusText.textContent = 'Ending interview...';
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ event: 'end_interview' }));
        }
        stopTimers();
    }

    function skipQuestion() {
        addLog('Candidate skipped the question');
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ event: 'skip_question' }));
        }
        setThinking(true);
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());
    if (skipButton) skipButton.addEventListener('click', skipQuestion);
    if (endButton) endButton.addEventListener('click', endInterview);
    if (reportButton) reportButton.addEventListener('click', () => {
        if (!sessionId) return;
        fetch(`${ORCH_BASE}/api/v1/sessions/${sessionId}/report`).then(r => r.blob()).then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `interview_report_${sessionId}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    });

    if (personaSelect) {
        const initialPersona = sessionStorage.getItem('persona') || 'friendly_mentor';
        personaSelect.value = initialPersona;
        sessionStorage.setItem('persona', initialPersona);
        personaSelect.addEventListener('change', () => {
            const p = personaSelect.value;
            sessionStorage.setItem('persona', p);
            addLog(`Persona switched to ${p}`);
        });
    }

    // Init and bind auto-answer UI
    if (autoToggle && autoControls) {
        autoToggle.addEventListener('change', () => {
            if (autoToggle.checked) {
                autoControls.classList.remove('d-none');
                // If a question is already present and input is empty, generate now
                if (lastQuestionText && !chatInput.value) {
                    requestAutoAnswer();
                }
            } else {
                autoControls.classList.add('d-none');
            }
        });
    }
    // Prefill auto-controls from candidate_profile, if present
    try {
        const profStr = sessionStorage.getItem('candidate_profile') || '';
        if (profStr) {
            const prof = JSON.parse(profStr);
            const confStr = prof && prof.personality && prof.personality.confidence;
            const verbStr = prof && prof.personality && prof.personality.verbosity;
            if (confidenceSelect && typeof confStr === 'string') confidenceSelect.value = confStr;
            if (verbositySelect && typeof verbStr === 'string') verbositySelect.value = verbStr;
        }
    } catch (_) {}
    // Initialize skill sliders from profile
    loadSkillMatrixFromCandidateProfile();
    if (reloadSkillMatrixBtn) reloadSkillMatrixBtn.addEventListener('click', (e) => { e.preventDefault(); loadSkillMatrixFromCandidateProfile(); });
    if (autoGenerateBtn) autoGenerateBtn.addEventListener('click', (e) => {
        e.preventDefault();
        requestAutoAnswer();
    });
    // No slider labels to update anymore

    if (statusSpinner) statusSpinner.classList.remove('d-none');
    if (statusText) statusText.textContent = 'Connecting...';
    connectWS();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}
