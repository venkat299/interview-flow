document.addEventListener("DOMContentLoaded", () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const statusIndicator = document.getElementById('status-indicator');

    const socket = new WebSocket('ws://localhost:8002/ws/test-interview-123');

    function addMessage(sender, text) {
        const message = document.createElement('div');
        message.classList.add('message', sender);
        message.textContent = text;
        chatLog.appendChild(message);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    socket.onopen = () => {
        statusIndicator.textContent = 'Connected. Waiting for interview to start...';
        socket.send(JSON.stringify({ event: 'join_session', payload: { interview_id: 'test-interview-123' } }));
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        statusIndicator.textContent = 'Connected';
        switch (data.event) {
            case 'session_started':
                chatInput.disabled = false;
                sendButton.disabled = false;
                break;
            case 'new_question':
                addMessage('interviewer', data.payload.question_text);
                break;
            case 'interviewer_typing':
                statusIndicator.textContent = 'AI is thinking...';
                break;
            case 'session_ended':
                addMessage('interviewer', data.payload.message);
                chatInput.disabled = true;
                sendButton.disabled = true;
                break;
        }
    };

    socket.onclose = () => {
        statusIndicator.textContent = 'Connection closed.';
        chatInput.disabled = true;
        sendButton.disabled = true;
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
});
