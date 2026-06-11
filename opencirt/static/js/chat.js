document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const sendButton = document.getElementById('sendButton');
    const incidentId = window.location.pathname.split('/')[2]; // Get the incident ID from URL

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    function sendMessage() {
        const messageText = chatInput.value.trim();
        if (messageText) {
            chatInput.value = '';
            fetch(`/api/incident/${incidentId}/send-message/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.cookie.split('csrftoken=')[1]
                },
                body: JSON.stringify({ message: messageText })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addMessage('user-message', data.message);
                } else {
                    alert('Error sending message');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }
    }

    function addMessage(type, text) {
        const wrapper = document.createElement('div');
        wrapper.className = type;

        const time = document.createElement('a');
        time.className = 'sending_time';
        const now = new Date();
        time.textContent = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');

        const bubble = document.createElement('a');
        bubble.className = 'message';
        bubble.textContent = text;

        wrapper.appendChild(time);
        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Auto-scroll to the bottom when page loads
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Function to scroll to the bottom when a new message is sent
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Attach event listener to the send button
    document.getElementById("sendButton").addEventListener("click", function () {
        setTimeout(scrollToBottom, 100); // Ensure DOM updates before scrolling
    });
});
