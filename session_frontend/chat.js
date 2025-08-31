document.addEventListener('DOMContentLoaded', () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const statusIndicator = document.getElementById('status-indicator');

    const interviewId = Date.now().toString();
    const ws = new WebSocket(`ws://localhost:8002/api/v1/ws/${interviewId}`);
    const apiBase = 'http://localhost:8003';

    function addMessage(sender, text) {
        const message = document.createElement('div');
        message.classList.add('message', sender);
        message.innerHTML = marked.parse(text);
        chatLog.appendChild(message);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    async function getContextFromSamplesIfNeeded() {
        const jd = (sessionStorage.getItem('job_description') || '').trim();
        const resume = (sessionStorage.getItem('candidate_resume') || '').trim();
        if (jd && resume) {
            return { job_description: jd, candidate_resume: resume };
        }
        try {
            const resp = await fetch(`${apiBase}/samples`);
            const data = await resp.json();
            const items = data.items || [];
            if (items.length === 0) {
                return { job_description: jd, candidate_resume: resume };
            }
            const key = items[0].key;
            const itemResp = await fetch(`${apiBase}/samples/${encodeURIComponent(key)}`);
            const item = await itemResp.json();
            return {
                job_description: item.job_description || jd || '',
                candidate_resume: item.resume || resume || ''
            };
        } catch (e) {
            console.error('Failed to load samples', e);
            return { job_description: jd, candidate_resume: resume };
        }
    }

    ws.onopen = async () => {
        statusIndicator.textContent = 'Starting interview...';
        const context = await getContextFromSamplesIfNeeded();
        ws.send(JSON.stringify({
            event: 'join_session',
            payload: context
        }));
    };

    ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        switch (msg.event) {
            case 'session_started':
                statusIndicator.textContent = 'Connected';
                chatInput.disabled = false;
                sendButton.disabled = false;
                break;
            case 'topics':
                addMessage('interviewer', 'Topics: ' + (msg.payload.topics || []).join(', '));
                break;
            case 'new_question':
                statusIndicator.textContent = 'Connected';
                addMessage('interviewer', msg.payload.question_text);
                break;
            case 'interviewer_typing':
                statusIndicator.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>AI is thinking...';
                break;
        }
    };

    ws.onerror = () => {
        statusIndicator.textContent = 'Connection error';
    };

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());

    function sendMessage() {
        const messageText = chatInput.value.trim();
        if (messageText === '') return;
        addMessage('candidate', messageText);
        chatInput.value = '';
        statusIndicator.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>AI is thinking...';
        ws.send(JSON.stringify({ event: 'send_answer', payload: { answer_text: messageText } }));
    }
});
