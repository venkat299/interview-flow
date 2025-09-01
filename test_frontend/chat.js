function initChat() {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const endButton = document.getElementById('end-button');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const statusSpinner = document.getElementById('status-spinner');
    const rubricBody = document.getElementById('rubric-body');
    const logBody = document.getElementById('log-body');
    const summaryBody = document.getElementById('summary-body');
    const statsBody = document.getElementById('stats-body');
    const personaSelect = document.getElementById('persona-select');

    // HTTP base for the AI Orchestration Service
    const ORCH_BASE = sessionStorage.getItem('AI_SERVICE_URL') || 'http://localhost:8003';
    const HTTP_TIMEOUT_MS = Number(sessionStorage.getItem('AI_HTTP_TIMEOUT')) || 60000;

    const context = {
        job_description: sessionStorage.getItem('job_description') || '',
        candidate_resume: sessionStorage.getItem('candidate_resume') || ''
    };

    // Client-side interview state
    const history = []; // { role: 'interviewer' | 'candidate', message: string }
    let blueprint = null;
    let topicIndex = 0;
    let currentDifficulty = 3; // 1-5 scale
    let lastQuestion = '';
    let started = false;
    const topicStrength = {}; // { topic: { total, count } }
    const questionStats = {}; // { topic: {1:0,2:0,3:0,4:0,5:0} }

    function setThinking(thinking) {
        if (thinking) {
            if (statusSpinner) statusSpinner.classList.remove('d-none');
            if (statusText) statusText.textContent = 'AI is thinking...';
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
        message.innerHTML = marked.parse(text);
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

    function depthToDifficulty(depth) {
        const s = String(depth || '').toLowerCase();
        if (s === 'fundamental' || s === 'beginner' || s === 'basic') return 1;
        if (s === 'intermediate') return 3;
        if (s === 'advanced') return 4;
        if (s === 'expert') return 5;
        return 3;
    }

    async function postJSON(path, body) {
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);
        try {
            const resp = await fetch(`${ORCH_BASE}${path}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: controller.signal,
            });
            if (!resp.ok) {
                const txt = await resp.text().catch(() => '');
                throw new Error(`HTTP ${resp.status}: ${txt || resp.statusText}`);
            }
            return await resp.json();
        } finally {
            clearTimeout(t);
        }
    }

    function currentTopic() {
        if (!blueprint || !Array.isArray(blueprint.topics) || blueprint.topics.length === 0) return null;
        return blueprint.topics[Math.max(0, Math.min(topicIndex, blueprint.topics.length - 1))];
    }

    async function createBlueprint() {
        if (statusText) statusText.textContent = 'Loading blueprint...';
        const data = await postJSON('/create-blueprint', context);
        blueprint = data;
        // Initialize difficulty from the first topic
        const t = currentTopic();
        currentDifficulty = t ? depthToDifficulty(t.required_depth) : 3;
        if (blueprint && Array.isArray(blueprint.topics)) {
            blueprint.topics.forEach((tp) => {
                topicStrength[tp.name] = { total: 0, count: 0 };
                questionStats[tp.name] = {1:0,2:0,3:0,4:0,5:0};
            });
            updateSummary();
            updateStatsTable();
        }
        if (endButton) endButton.disabled = false;
        started = true;
    }

    async function generateQuestion() {
        const t = currentTopic();
        const req = {
            context,
            history,
            current_topic: t ? t.name : 'General',
            current_difficulty: currentDifficulty,
            persona: sessionStorage.getItem('persona') || 'friendly_mentor',
        };
        const data = await postJSON('/generate-question', req);
        const q = data && data.question_text ? String(data.question_text) : '';
        lastQuestion = q;
        if (q) {
            history.push({ role: 'interviewer', message: q });
            addMessage('interviewer', q);
            addLog(`Asked question on ${t ? t.name : 'General'} (difficulty ${currentDifficulty})`);
            if (t && questionStats[t.name]) {
                questionStats[t.name][currentDifficulty] += 1;
                updateStatsTable();
            }
        }
    }

    async function evaluateAnswer(answerText) {
        const t = currentTopic();
        if (!t || !lastQuestion) return null;
        const req = {
            question: lastQuestion,
            answer: answerText,
            topic_blueprint: t,
        };
        const prevDifficulty = currentDifficulty;
        const data = await postJSON('/evaluate-answer', req).catch((e) => {
            console.warn('Evaluation failed', e);
            return null;
        });
        if (data && typeof data.score === 'number') {
            // Light-touch difficulty adjustment
            if (data.score >= 8 && currentDifficulty < 5) currentDifficulty += 1;
            if (data.score <= 3 && currentDifficulty > 1) currentDifficulty -= 1;
            updateRubric(data);
            addLog(`Answer scored ${data.score}/10`);
            if (currentDifficulty !== prevDifficulty) {
                addLog(`Difficulty changed from ${prevDifficulty} to ${currentDifficulty}`);
            }
            if (t && topicStrength[t.name]) {
                topicStrength[t.name].total += data.score;
                topicStrength[t.name].count += 1;
                updateSummary();
            }
        }
        return data;
    }

    async function start() {
        try {
            await createBlueprint();
            if (statusText) statusText.textContent = 'Connected';
            addLog('Interview started');
            await generateQuestion();
            setThinking(false);
        } catch (e) {
            console.error('Failed to start interview', e);
            if (statusSpinner) statusSpinner.classList.add('d-none');
            if (statusText) statusText.textContent = 'Error starting interview';
        }
    }

    async function sendMessage() {
        const messageText = chatInput.value;
        if (!messageText || !messageText.trim()) return;
        addMessage('candidate', messageText);
        history.push({ role: 'candidate', message: messageText });
        addLog(`Candidate answered: ${messageText}`);
        chatInput.value = '';
        setThinking(true);
        try {
            await evaluateAnswer(messageText);
        } catch (e) {
            // Non-fatal; continue to next question
            console.warn('Evaluation error', e);
        }
        try {
            await generateQuestion();
        } catch (e) {
            console.error('Failed to get next question', e);
            if (statusSpinner) statusSpinner.classList.add('d-none');
            if (statusText) statusText.textContent = 'Error getting next question';
        } finally {
            setThinking(false);
        }
    }

    function endInterview() {
        const confirmed = window.confirm('Are you sure you want to end the interview?');
        if (!confirmed) return;
        setThinking(false);
        chatInput.disabled = true;
        sendButton.disabled = true;
        if (endButton) endButton.disabled = true;
        if (statusText) statusText.textContent = 'Interview ended';
        addMessage('interviewer', 'Interview ended. Thank you for your time.');
        addLog('Interview ended');
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

    // Kick off
    if (statusSpinner) statusSpinner.classList.remove('d-none');
    start();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}
