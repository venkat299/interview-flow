function initChat() {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const endButton = document.getElementById('end-button');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const statusSpinner = document.getElementById('status-spinner');

    const AI_SERVICE_URL = sessionStorage.getItem('AI_SERVICE_URL') || 'http://localhost:8003';

    const context = {
        job_description: sessionStorage.getItem('job_description') || '',
        candidate_resume: sessionStorage.getItem('candidate_resume') || ''
    };

    // Client-side interview state
    let blueprint = null;
    let currentTopic = null; // object from blueprint.topics
    let currentTopicName = '';
    let currentDifficulty = 2; // 1-5
    const history = []; // {role: 'interviewer'|'candidate', message: string}[]
    let lastQuestion = '';

    function depthToDifficulty(depth) {
        const d = (depth || '').toLowerCase();
        if (d.includes('expert')) return 5;
        if (d.includes('advanced')) return 4;
        if (d.includes('intermediate')) return 3;
        return 1; // Fundamental or unknown
    }

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

    async function fetchJSON(url, opts) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            ...opts,
        });
        if (!resp.ok) {
            const text = await resp.text();
            throw new Error(`HTTP ${resp.status}: ${text}`);
        }
        return resp.json();
    }

    async function createBlueprint() {
        const data = await fetchJSON(`${AI_SERVICE_URL}/create-blueprint`, {
            body: JSON.stringify(context),
        });
        blueprint = data;
        // Pick the first topic as starting point
        if (blueprint.topics && blueprint.topics.length) {
            currentTopic = blueprint.topics[0];
            currentTopicName = currentTopic.name;
            currentDifficulty = depthToDifficulty(currentTopic.required_depth);
        } else {
            currentTopic = null;
            currentTopicName = 'General';
            currentDifficulty = 2;
        }
    }

    async function generateQuestion() {
        const payload = {
            context,
            history,
            current_topic: currentTopicName,
            current_difficulty: currentDifficulty,
            // persona omitted to use server default
        };
        const data = await fetchJSON(`${AI_SERVICE_URL}/generate-question`, {
            body: JSON.stringify(payload),
        });
        return data.question_text || '';
    }

    async function evaluateAnswer(question, answer) {
        if (!currentTopic) return null;
        const payload = {
            question,
            answer,
            topic_blueprint: currentTopic,
        };
        const data = await fetchJSON(`${AI_SERVICE_URL}/evaluate-answer`, {
            body: JSON.stringify(payload),
        });
        return data;
    }

    async function startInterview() {
        try {
            if (statusText) statusText.textContent = 'Connecting...';
            await createBlueprint();
            setThinking(true);
            lastQuestion = await generateQuestion();
            history.push({ role: 'interviewer', message: lastQuestion });
            addMessage('interviewer', lastQuestion);
            setThinking(false);
            // Enable the end interview button once the interview has started
            if (endButton) endButton.disabled = false;
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
            const evalResult = await evaluateAnswer(lastQuestion, messageText);
            if (evalResult && typeof evalResult.score === 'number') {
                // Adjust difficulty based on score
                if (evalResult.score > 7) currentDifficulty = Math.min(5, currentDifficulty + 1);
                else if (evalResult.score > 4) currentDifficulty = Math.min(5, Math.max(currentDifficulty, 3));
                else currentDifficulty = Math.max(1, 1);
            }
            const nextQ = await generateQuestion();
            lastQuestion = nextQ;
            history.push({ role: 'interviewer', message: nextQ });
            addMessage('interviewer', nextQ);
        } catch (e) {
            console.error('Failed to send message', e);
            if (statusSpinner) statusSpinner.classList.add('d-none');
            if (statusText) statusText.textContent = 'Error contacting AI service';
        } finally {
            setThinking(false);
        }
    }

    function endInterview() {
        const confirmed = window.confirm('Are you sure you want to end the interview?');
        if (!confirmed) return;
        if (statusSpinner) statusSpinner.classList.add('d-none');
        if (statusText) statusText.textContent = 'Interview ended';
        chatInput.disabled = true;
        sendButton.disabled = true;
        if (endButton) endButton.disabled = true;
        addMessage('interviewer', 'Interview ended. Thank you for your time.');
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());
    if (endButton) endButton.addEventListener('click', endInterview);

    // Kick off
    startInterview();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}
