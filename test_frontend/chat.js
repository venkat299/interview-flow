function initChat() {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const endButton = document.getElementById('end-button');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const statusSpinner = document.getElementById('status-spinner');

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
        const data = await postJSON('/evaluate-answer', req).catch((e) => {
            console.warn('Evaluation failed', e);
            return null;
        });
        if (data && typeof data.score === 'number') {
            // Light-touch difficulty adjustment
            if (data.score >= 8 && currentDifficulty < 5) currentDifficulty += 1;
            if (data.score <= 3 && currentDifficulty > 1) currentDifficulty -= 1;
        }
        return data;
    }

    async function start() {
        try {
            await createBlueprint();
            if (statusText) statusText.textContent = 'Connected';
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
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());
    if (endButton) endButton.addEventListener('click', endInterview);

    // Kick off
    if (statusSpinner) statusSpinner.classList.remove('d-none');
    start();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}
