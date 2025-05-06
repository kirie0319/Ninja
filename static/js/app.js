document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const initialQuickReplies = document.getElementById('initialQuickReplies');
    
    // Set up initial quick reply buttons
    if (initialQuickReplies) {
        setupQuickReplies(initialQuickReplies);
    }
    
    function setupQuickReplies(container) {
        const quickReplyButtons = container.querySelectorAll('.quick-reply-btn');
        quickReplyButtons.forEach(button => {
            button.addEventListener('click', function() {
                userInput.value = button.textContent;
                handleUserMessage();
            });
        });
    }
    
    function showTypingIndicator() {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'bot-message p-3 mb-4 ml-2 typing-indicator-container';
        indicatorDiv.id = 'typingIndicator';
        indicatorDiv.innerHTML = `
            <div class="typing-indicator p-2">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        `;
        chatMessages.appendChild(indicatorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function addMessage(message, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser 
            ? 'user-message p-4 mb-4 ml-auto mr-2' 
            : 'bot-message p-4 mb-4 ml-2';
        
        // Process message text with markdown parsing
        let messageText = parseMarkdown(message);
        
        messageDiv.innerHTML = `<div class="${isUser ? 'text-white' : 'text-gray-800'}">${messageText}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }

    function displayQuickReplies(quickReplies, afterElement = null) {
        removeAllQuickReplies();
        
        const container = document.createElement('div');
        container.className = 'quick-replies-container';
        
        quickReplies.forEach(reply => {
            const button = document.createElement('button');
            button.className = 'quick-reply-btn';
            button.textContent = reply;
            button.addEventListener('click', function() {
                userInput.value = reply;
                handleUserMessage();
            });
            container.appendChild(button);
        });
        
        if (afterElement && afterElement.parentNode) {
            afterElement.parentNode.insertBefore(container, afterElement.nextSibling);
        } else {
            chatMessages.appendChild(container);
        }
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return container;
    }

    function removeAllQuickReplies() {
        const containers = chatMessages.querySelectorAll('.quick-replies-container');
        containers.forEach(container => {
            if (container.id !== 'initialQuickReplies') {
                container.remove();
            }
        });
    }

    function handleUserMessage() {
        const message = userInput.value.trim();
        if (message === '') return;

        // Remove initial quick replies when user sends first message
        if (initialQuickReplies && initialQuickReplies.parentNode) {
            initialQuickReplies.remove();
        }

        removeAllQuickReplies();
        addMessage(message, true);
        userInput.value = '';
        showTypingIndicator();

        // Send to backend
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({message: message}),
        })
        .then(response => response.json())
        .then(data => {
            removeTypingIndicator();
            const botMessageElement = addMessage(data.response, false);
            
            if (data.image_urls && data.image_urls.length > 0) {
                const imageDiv = document.createElement('div');
                imageDiv.className = 'bot-message p-3 mb-4 ml-2';
                const imageContainer = document.createElement('div');
                imageContainer.className = 'flex flex-wrap gap-2 mt-2';

                data.image_urls.forEach(url => {
                    if (url) {
                        const imgWrapper = document.createElement('div');
                        imgWrapper.className = 'w-1/2 sm:w-1/3 md:w-1/4 p-1';

                        const img = document.createElement('img');
                        img.src = url;
                        img.alt = "Restaurant image";
                        img.className = "rounded-lg w-full h-32 object-cover shadow-md";

                        imgWrapper.appendChild(img);
                        imageContainer.appendChild(imgWrapper);
                    }
                });

                imageDiv.appendChild(imageContainer);
                imageDiv.innerHTML += `<p class="text-xs text-gray-500 mt-2">Restaurant images</p>`;
                chatMessages.appendChild(imageDiv);
            }
            
            const fallbackReplies = [
                "Tell me more",
                "What's the price range?",
                "Any other recommendations?",
                "How's the atmosphere?"
            ];
            
            displayQuickReplies(data.quickReplies || fallbackReplies, botMessageElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingIndicator();
            
            // Demo response
            let botResponse = "I'd be happy to help you find a great Japanese restaurant. Could you tell me what type of cuisine you're interested in?";
            if (message.toLowerCase().includes('sushi')) {
                botResponse = "Tokyo has amazing sushi restaurants! What kind of atmosphere are you looking for?";
            } else if (message.toLowerCase().includes('ramen')) {
                botResponse = "Ramen is a fantastic choice! What neighborhood will you be in?";
            }
            
            const botMessageElement = addMessage(botResponse, false);
            const fallbackReplies = [
                "I'm looking for sushi",
                "Tell me about ramen",
                "I have a budget of $50",
                "Popular Tokyo restaurants"
            ];
            displayQuickReplies(fallbackReplies, botMessageElement);
        });
    }

    function clearChat() {
        while (chatMessages.firstChild) {
            chatMessages.removeChild(chatMessages.firstChild);
        }
        
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'bot-message p-4 mb-4 ml-2';
        welcomeDiv.innerHTML = `<p class="text-gray-800">Welcome to Ninja.AI! I'm your personal guide to the best authentic Japanese restaurants in Tokyo. How can I help you discover your next unforgettable dining experience?</p>`;
        chatMessages.appendChild(welcomeDiv);
        
        const initialRepliesDiv = document.createElement('div');
        initialRepliesDiv.id = 'initialQuickReplies';
        initialRepliesDiv.className = 'quick-replies-container';
        initialRepliesDiv.innerHTML = `
            <button class="quick-reply-btn">I'm looking for sushi restaurants</button>
            <button class="quick-reply-btn">Tell me about ramen spots</button>
            <button class="quick-reply-btn">What's popular in Tokyo?</button>
            <button class="quick-reply-btn">Good places for first-time visitors?</button>
        `;
        chatMessages.appendChild(initialRepliesDiv);
        setupQuickReplies(initialRepliesDiv);
        
        fetch('/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
        .catch(error => console.error('Error clearing chat:', error));
    }

    // Event listeners
    clearChatBtn.addEventListener('click', clearChat);
    sendButton.addEventListener('click', handleUserMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleUserMessage();
        }
    });
    
    userInput.focus();
    
    userInput.addEventListener('focus', function() {
        document.querySelector('.input-container').classList.add('ring-2', 'ring-red-100');
    });
    
    userInput.addEventListener('blur', function() {
        document.querySelector('.input-container').classList.remove('ring-2', 'ring-red-100');
    });
});