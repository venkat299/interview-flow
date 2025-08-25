document.addEventListener("DOMContentLoaded", () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const statusIndicator = document.getElementById('status-indicator');

    const apiBase = 'http://localhost:8003';
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
        const resp = await fetch(`${apiBase}/determine-topics`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(context)
        });
        const data = await resp.json();
        addMessage('interviewer', 'Topics: ' + data.topics.join(', '));
    }

    async function askNextQuestion() {
        const resp = await fetch(`${apiBase}/generate-question`, {
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
        } catch (err) {
            console.error(err);
            statusIndicator.textContent = 'Error contacting service';
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

    startInterview();
});
