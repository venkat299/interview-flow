function initChat() {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const endButton = document.getElementById('end-button');
    const statusIndicator = document.getElementById('status-indicator');

    const context = {
        job_description: sessionStorage.getItem('job_description') || '',
        candidate_resume: sessionStorage.getItem('candidate_resume') || ''
    };

    const sessionId = sessionStorage.getItem('session_id') || crypto.randomUUID();
    sessionStorage.setItem('session_id', sessionId);

    const socket = new WebSocket(`ws://localhost:8002/api/v1/ws/${sessionId}`);

    function addMessage(sender, text) {
        const message = document.createElement('div');
        message.classList.add('message', sender);
        message.innerHTML = marked.parse(text);
        chatLog.appendChild(message);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    socket.onopen = () => {
        statusIndicator.textContent = 'Connected';
        socket.send(JSON.stringify({ event: 'join_session', payload: context }));
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.event) {
            case 'new_question':
                statusIndicator.textContent = 'Connected';
                addMessage('interviewer', data.payload.question_text);
                chatInput.disabled = false;
                sendButton.disabled = false;
                break;
            case 'interviewer_typing':
                statusIndicator.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>AI is thinking...';
                break;
            case 'interview_ended':
                statusIndicator.textContent = 'Interview ended';
                chatInput.disabled = true;
                sendButton.disabled = true;
                if (endButton) endButton.disabled = true;
                addMessage('interviewer', 'Interview ended. Thank you for your time.');
                break;
            default:
                break;
        }
    };

    socket.onclose = () => {
        statusIndicator.textContent = 'Disconnected';
        chatInput.disabled = true;
        sendButton.disabled = true;
        if (endButton) endButton.disabled = true;
    };

    function sendMessage() {
        const messageText = chatInput.value;
        if (messageText.trim() !== '') {
            addMessage('candidate', messageText);
            socket.send(JSON.stringify({ event: 'send_answer', payload: { answer_text: messageText } }));
            chatInput.value = '';
        }
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());

    function endInterview() {
        const confirmed = window.confirm('Are you sure you want to end the interview?');
        if (!confirmed) return;
        socket.close();
    }

    if (endButton) {
        endButton.addEventListener('click', endInterview);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}
