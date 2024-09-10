let sessionId = null;

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const chatForm = document.getElementById('chat-form');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');

    if (uploadForm) {
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
                } else {
                    alert(`Error: ${result.error}`);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while uploading the video.');
            }
        });
    }

    if (chatForm) {
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
    }

    function addMessage(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        messageElement.textContent = text;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
