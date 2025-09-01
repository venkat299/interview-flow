function initChat() {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const endButton = document.getElementById('end-button');
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

    const ORCH_BASE = sessionStorage.getItem('AI_SERVICE_URL') || 'http://localhost:8003';
    const context = {
        job_description: sessionStorage.getItem('job_description') || '',
        candidate_resume: sessionStorage.getItem('candidate_resume') || ''
    };

    const history = [];
    let blueprint = null;
    let currentTopicName = null;
    const topicStrength = {};
    const questionStats = {};
    let ws = null;
    let interviewStart = null;
    let interviewInterval = null;
    let turnStart = null;
    let turnInterval = null;
    let totalWords = 0;

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
        } else {
            if (statusSpinner) statusSpinner.classList.add('d-none');
            if (statusText) statusText.textContent = 'Connected';
            chatInput.disabled = false;
            sendButton.disabled = false;
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
        const sessionId = `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;
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
                if (endButton) endButton.disabled = false;
                startInterviewTimer();
            } else if (event === 'blueprint') {
                blueprint = payload;
                initStatsFromBlueprint(blueprint);
                addLog('Interview started');
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
                setThinking(false);
                resetTurnTimer();
            } else if (event === 'interview_ended') {
                setThinking(false);
                addMessage('interviewer', 'Interview ended. Thank you for your time.');
                addLog('Interview ended');
                chatInput.disabled = true;
                sendButton.disabled = true;
                if (endButton) endButton.disabled = true;
                if (statusText) statusText.textContent = 'Interview ended';
                stopTimers();
            }
        };
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
        if (endButton) endButton.disabled = true;
        if (statusText) statusText.textContent = 'Ending interview...';
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ event: 'end_interview' }));
        }
        stopTimers();
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());
    if (endButton) endButton.addEventListener('click', endInterview);

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

    if (statusSpinner) statusSpinner.classList.remove('d-none');
    if (statusText) statusText.textContent = 'Connecting...';
    connectWS();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}
