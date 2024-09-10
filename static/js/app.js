let sessionId = null;

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const chatForm = document.getElementById('chat-form');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sessionList = document.getElementById('session-list');

    loadPreviousSessions();

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(uploadForm);
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (response.ok) {
                sessionId = result.session_id;
                alert('Video uploaded successfully. You can now start chatting!');
                document.getElementById('chat-section').style.display = 'block';
                loadPreviousSessions();
            } else {
                alert(`Error: ${result.error}`);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while uploading the video.');
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        addMessage('user', message);
        userInput.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: sessionId, message: message }),
            });
            const result = await response.json();
            
            if (response.ok) {
                addMessage('ai', result.response);
            } else {
                addMessage('ai', `Error: ${result.error}`);
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('ai', 'An error occurred while processing your message.');
        }
    });

    function addMessage(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        messageElement.textContent = text;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function loadPreviousSessions() {
        try {
            const response = await fetch('/get_sessions');
            const sessions = await response.json();
            
            sessionList.innerHTML = '';
            sessions.forEach(session => {
                const li = document.createElement('li');
                li.textContent = `Session ${session.id} - ${new Date(session.created_at).toLocaleString()}`;
                li.addEventListener('click', () => loadSession(session.session_id));
                sessionList.appendChild(li);
            });
        } catch (error) {
            console.error('Error loading previous sessions:', error);
        }
    }

    async function loadSession(selectedSessionId) {
        sessionId = selectedSessionId;
        chatMessages.innerHTML = '';
        document.getElementById('chat-section').style.display = 'block';

        try {
            const response = await fetch(`/get_session_messages/${sessionId}`);
            const messages = await response.json();
            
            messages.forEach(message => {
                addMessage(message.role === 'user' ? 'user' : 'ai', message.content);
            });
        } catch (error) {
            console.error('Error loading session messages:', error);
        }
    }
});
