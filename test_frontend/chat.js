document.addEventListener("DOMContentLoaded", () => {
    const chatLog = document.getElementById('chat-log');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const statusIndicator = document.getElementById('status-indicator');

    const wsUrl = 'ws://localhost:8002/api/v1/ws/test-interview-123';
    console.log('Connecting to WebSocket:', wsUrl);
    const socket = new WebSocket(wsUrl);
    const jobDescription = sessionStorage.getItem('job_description') || '';
    const resume = sessionStorage.getItem('candidate_resume') || '';

    function addMessage(sender, text) {
        const message = document.createElement('div');
        message.classList.add('message', sender);
        message.innerHTML = marked.parse(text);
        chatLog.appendChild(message);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    socket.onopen = () => {
        statusIndicator.textContent = 'Connected. Waiting for interview to start...';
        const joinPayload = {
            event: 'join_session',
            payload: {
                interview_id: 'test-interview-123',
                job_description: jobDescription,
                candidate_resume: resume,
            },
        };
        console.log('>>', joinPayload);
        socket.send(JSON.stringify(joinPayload));
    };

    socket.onmessage = (event) => {
        console.log('<<', event.data);
        const data = JSON.parse(event.data);
        statusIndicator.textContent = 'Connected';
        switch (data.event) {
            case 'session_started':
                chatInput.disabled = false;
                sendButton.disabled = false;
                break;
            case 'topics':
                addMessage('interviewer', 'Topics: ' + data.payload.topics.join(', '));
                break;
            case 'new_question':
                addMessage('interviewer', data.payload.question_text);
                break;
            case 'interviewer_typing':
                statusIndicator.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>AI is thinking...';
                break;
            case 'session_ended':
                addMessage('interviewer', data.payload.message);
                chatInput.disabled = true;
                sendButton.disabled = true;
                statusIndicator.textContent = 'Interview ended';
                break;
        }
    };

    socket.onclose = (event) => {
        console.log('WebSocket closed:', event);
        statusIndicator.textContent = 'Connection closed.';
        chatInput.disabled = true;
        sendButton.disabled = true;
    };
    socket.onerror = (event) => {
        console.error('WebSocket error:', event);
    };

    function sendMessage() {
        const messageText = chatInput.value;
        if (messageText.trim() !== '') {
            addMessage('candidate', messageText);
            const messagePayload = { event: 'send_answer', payload: { answer_text: messageText } };
            console.log('>>', messagePayload);
            socket.send(JSON.stringify(messagePayload));
            chatInput.value = '';
        }
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());
});
