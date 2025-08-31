function initChat() {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const endButton = document.getElementById('end-button');
    const statusIndicator = document.getElementById('status-indicator');

    // Base URL of the AI orchestration service
    const AI_SERVICE_URL = 'http://localhost:8003';
    const context = {
        job_description: sessionStorage.getItem('job_description') || '',
        candidate_resume: sessionStorage.getItem('candidate_resume') || ''
    };
    let history = [];

    function addMessage(sender, text) {
        const message = document.createElement('div');
        message.classList.add('message', sender);
        message.innerHTML = marked.parse(text);
        chatLog.appendChild(message);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    async function determineTopics() {
        const resp = await fetch(`${AI_SERVICE_URL}/determine-topics`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(context)
        });
        const data = await resp.json();
        addMessage('interviewer', 'Topics: ' + data.topics.join(', '));
    }

    async function askNextQuestion() {
        const resp = await fetch(`${AI_SERVICE_URL}/generate-question`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ context, history })
        });
        const data = await resp.json();
        addMessage('interviewer', data.question_text);
        history.push({ role: 'interviewer', message: data.question_text });
    }

    async function startInterview() {
        statusIndicator.textContent = 'Starting interview...';
        try {
            await determineTopics();
            await askNextQuestion();
            statusIndicator.textContent = 'Connected';
            chatInput.disabled = false;
            sendButton.disabled = false;
            if (endButton) endButton.disabled = false; // redundant but explicit
        } catch (err) {
            console.error(err);
            statusIndicator.textContent = 'Error contacting service';
            // Still allow ending the interview even if the service failed
            if (endButton) endButton.disabled = false;
        }
    }

    async function sendMessage() {
        const messageText = chatInput.value;
        if (messageText.trim() !== '') {
            addMessage('candidate', messageText);
            history.push({ role: 'candidate', message: messageText });
            chatInput.value = '';
            statusIndicator.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>AI is thinking...';
            try {
                await askNextQuestion();
                statusIndicator.textContent = 'Connected';
            } catch (err) {
                console.error(err);
                statusIndicator.textContent = 'Error contacting service';
            }
        }
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());

    function endInterview() {
        const confirmed = window.confirm('Are you sure you want to end the interview?');
        if (!confirmed) return;
        chatInput.disabled = true;
        sendButton.disabled = true;
        if (endButton) endButton.disabled = true;
        statusIndicator.textContent = 'Interview ended by you';
        addMessage('interviewer', 'Interview ended. Thank you for your time.');
    }

    if (endButton) {
        endButton.addEventListener('click', endInterview);
    }

    // Ensure the End Interview button is always available
    if (endButton) {
        endButton.disabled = false;
        endButton.removeAttribute('disabled');
    }
    startInterview();
}

// Run immediately if DOM already loaded, otherwise wait
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}
