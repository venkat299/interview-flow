document.addEventListener('DOMContentLoaded', () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const statusIndicator = document.getElementById('status-indicator');

    const interviewId = Date.now().toString();
    const ws = new WebSocket(`ws://localhost:8002/api/v1/ws/${interviewId}`);

    function addMessage(sender, text) {
        const message = document.createElement('div');
        message.classList.add('message', sender);
        message.innerHTML = marked.parse(text);
        chatLog.appendChild(message);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    ws.onopen = () => {
        statusIndicator.textContent = 'Starting interview...';
        ws.send(JSON.stringify({
            event: 'join_session',
            payload: {
                job_description: sessionStorage.getItem('job_description') || '',
                candidate_resume: sessionStorage.getItem('candidate_resume') || ''
            }
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
