class RAGChatbot {
    constructor() {
        this.apiUrl = 'http://localhost:8002';
        this.chatMessages = document.getElementById('chat-messages');
        this.chatForm = document.getElementById('chat-form');
        this.questionInput = document.getElementById('question-input');
        this.sendBtn = document.getElementById('send-btn');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.mobileMenuBtn = document.getElementById('mobile-menu-btn');
        this.sidebar = document.getElementById('sidebar');
        this.sidebarToggle = document.getElementById('sidebar-toggle');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.clearHistoryBtn = document.getElementById('clear-history-btn');
        this.chatHistoryContainer = document.getElementById('chat-history');
        
        this.messageCount = 0;
        this.sidebarCollapsed = false;
        this.currentChatId = null;
        this.currentChatMessages = [];
        this.maxChats = 10;
        
        this.init();
        this.setupMarkdown();
    }
    
    setupMarkdown() {
        // Configure marked options for better formatting
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true,        // Convert \n to <br>
                gfm: true,          // GitHub Flavored Markdown
                tables: true,       // Support tables
                sanitize: false,    // Allow HTML (be careful in production)
                smartypants: false  // Don't convert quotes/dashes
            });
        }
    }
    
    // Add method to process markdown
    processMarkdown(text) {
        if (typeof marked === 'undefined') {
            console.warn('Marked library not loaded, returning plain text');
            return text.replace(/\n/g, '<br>');
        }
        
        try {
            // Pre-process the text to handle common formatting issues
            let processedText = text
                // Fix table formatting - ensure proper spacing
                .replace(/\|\s*([^|]+)\s*\|/g, (match, content) => {
                    return `| ${content.trim()} |`;
                })
                // Ensure table headers have proper separator
                .replace(/(\|[^|\n]+\|)\s*\n\s*(\|[^|\n]+\|)/g, (match, header, row) => {
                    if (!row.includes('---')) {
                        // This might be a header row, add separator
                        const colCount = (header.match(/\|/g) || []).length - 1;
                        const separator = '|' + ' --- |'.repeat(colCount);
                        return header + '\n' + separator + '\n' + row;
                    }
                    return match;
                })
                // Fix bold formatting spacing
                .replace(/\*\*([^*]+)\*\*/g, '**$1**')
                // Fix italic formatting
                .replace(/\*([^*]+)\*/g, '*$1*')
                // Ensure line breaks before tables
                .replace(/([^\n])\n(\|)/g, '$1\n\n$2');
            
            return marked.parse(processedText);
        } catch (error) {
            console.error('Markdown processing error:', error);
            return text.replace(/\n/g, '<br>');
        }
    }
    
    // Update addMessage method to use markdown
    addMessage(content, type, sources = [], runtime = null) {
        this.messageCount++;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (type === 'user') {
            avatar.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/></svg>';
        } else {
            avatar.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>';
        }
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = `message-bubble ${this.getBubbleSizeClass(content)}`;
        
        // Process content based on message type
        if (type === 'bot') {
            // For bot messages, process markdown
            const markdownContent = document.createElement('div');
            markdownContent.className = 'markdown-content';
            markdownContent.innerHTML = this.processMarkdown(content);
            messageBubble.appendChild(markdownContent);
        } else {
            // For user messages, keep as plain text
            messageBubble.textContent = content;
        }
        
        messageContent.appendChild(messageBubble);
        
        // Add metadata for bot messages
        if (type === 'bot') {
            const messageMeta = document.createElement('div');
            messageMeta.className = 'message-meta';
            
            if (sources && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.innerHTML = `
                    <div class="sources-title">Sources:</div>
                    <div class="sources-list">${sources.join(', ')}</div>
                `;
                messageMeta.appendChild(sourcesDiv);
            }
            
            if (runtime) {
                const runtimeDiv = document.createElement('div');
                runtimeDiv.className = 'runtime';
                runtimeDiv.textContent = `Response time: ${runtime}ms`;
                messageMeta.appendChild(runtimeDiv);
            }
            
            messageContent.appendChild(messageMeta);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Save message to current chat
        if (this.currentChatId) {
            this.currentChatMessages.push({
                content: content,
                type: type,
                sources: sources,
                runtime: runtime,
                timestamp: new Date().toISOString()
            });
            this.saveCurrentChat();
        }
    }
    
    // Update renderMessage method for chat history
    renderMessage(messageData) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${messageData.type}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (messageData.type === 'user') {
            avatar.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/></svg>';
        } else {
            avatar.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>';
        }
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = `message-bubble ${this.getBubbleSizeClass(messageData.content)}`;
        
        // Process content based on message type
        if (messageData.type === 'bot') {
            // For bot messages, process markdown
            const markdownContent = document.createElement('div');
            markdownContent.className = 'markdown-content';
            markdownContent.innerHTML = this.processMarkdown(messageData.content);
            messageBubble.appendChild(markdownContent);
        } else {
            // For user messages, keep as plain text
            messageBubble.textContent = messageData.content;
        }
        
        messageContent.appendChild(messageBubble);
        
        // Add metadata for bot messages
        if (messageData.type === 'bot') {
            const messageMeta = document.createElement('div');
            messageMeta.className = 'message-meta';
            
            if (messageData.sources && messageData.sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.innerHTML = `
                    <div class="sources-title">Sources:</div>
                    <div class="sources-list">${messageData.sources.join(', ')}</div>
                `;
                messageMeta.appendChild(sourcesDiv);
            }
            
            if (messageData.runtime) {
                const runtimeDiv = document.createElement('div');
                runtimeDiv.className = 'runtime';
                runtimeDiv.textContent = `Response time: ${messageData.runtime}ms`;
                messageMeta.appendChild(runtimeDiv);
            }
            
            messageContent.appendChild(messageMeta);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        return messageDiv;
    }
    
    init() {
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.questionInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.questionInput.addEventListener('input', (e) => this.handleInput(e));
        this.mobileMenuBtn?.addEventListener('click', () => this.toggleMobileSidebar());
        this.sidebarToggle?.addEventListener('click', () => this.toggleSidebar());
        this.newChatBtn?.addEventListener('click', () => this.newChat());
        this.clearHistoryBtn?.addEventListener('click', () => this.clearHistory());
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && this.sidebar.classList.contains('open')) {
                if (!this.sidebar.contains(e.target) && !this.mobileMenuBtn.contains(e.target)) {
                    this.closeMobileSidebar();
                }
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                this.sidebar.classList.remove('open');
            }
        });
        
        // Initialize chat history
        this.loadChatHistory();
        this.startNewChat();
        
        // Focus input on load
        this.questionInput.focus();
    }
    
    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleSubmit(e);
        }
    }
    
    handleInput(e) {
        // Auto-resize textarea
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        const question = this.questionInput.value.trim();
        if (!question) return;
        
        // Hide welcome message if it's the first message
        if (this.messageCount === 0) {
            const welcomeMessage = document.querySelector('.welcome-message');
            if (welcomeMessage) {
                welcomeMessage.style.display = 'none';
            }
        }
        
        // Add user message
        this.addMessage(question, 'user');
        
        // Clear input and reset height
        this.questionInput.value = '';
        this.questionInput.style.height = 'auto';
        this.setLoading(true);
        
        try {
            const response = await this.queryRAG(question);
            this.addMessage(response.answer, 'bot', response.sources, response.runtime_ms);
        } catch (error) {
            this.addErrorMessage('Sorry, something went wrong. Please try again.');
            console.error('Error:', error);
        } finally {
            this.setLoading(false);
            this.questionInput.focus();
        }
    }
    
    async queryRAG(question) {
        const response = await fetch(`${this.apiUrl}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                num_chunks: 10
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    // Determine bubble size class based on content length
    getBubbleSizeClass(content) {
        const length = content.length;
        if (length < 100) return 'short';
        if (length < 300) return 'medium';
        if (length < 600) return 'long';
        return 'extra-long';
    }
    
    addErrorMessage(message) {
        this.addMessage(message, 'bot', [], null);
    }
    
    setLoading(isLoading) {
        if (isLoading) {
            this.loadingOverlay.classList.remove('hidden');
            this.sendBtn.disabled = true;
        } else {
            this.loadingOverlay.classList.add('hidden');
            this.sendBtn.disabled = false;
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    // Chat History Management
    generateChatId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    generateChatTitle(firstMessage) {
        // Generate a title from the first message (max 50 chars)
        let title = firstMessage.trim();
        if (title.length > 50) {
            title = title.substring(0, 47) + '...';
        }
        return title;
    }
    
    startNewChat() {
        // Save current chat if it has messages
        if (this.currentChatId && this.currentChatMessages.length > 0) {
            this.saveCurrentChat();
        }
        
        // Start new chat
        this.currentChatId = this.generateChatId();
        this.currentChatMessages = [];
        this.messageCount = 0;
        
        // Clear chat messages
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                        <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                        <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                    </svg>
                </div>
                <h2>Welcome to Document Assistant</h2>
                <p>I can help you find information from your documents. Ask me anything!</p>
            </div>
        `;
        
        // Update sidebar
        this.updateActiveChatInSidebar(this.currentChatId);
    }
    
    saveCurrentChat() {
        if (!this.currentChatId || this.currentChatMessages.length === 0) return;
        
        const chatData = {
            id: this.currentChatId,
            title: this.generateChatTitle(this.currentChatMessages[0].content),
            messages: this.currentChatMessages,
            timestamp: new Date().toISOString()
        };
        
        // Get existing chats
        const existingChats = this.getChatHistory();
        
        // Remove if already exists (update)
        const filteredChats = existingChats.filter(chat => chat.id !== this.currentChatId);
        
        // Add new chat at the beginning
        filteredChats.unshift(chatData);
        
        // Keep only the most recent chats
        if (filteredChats.length > this.maxChats) {
            filteredChats.splice(this.maxChats);
        }
        
        // Save to localStorage
        localStorage.setItem('ragChatHistory', JSON.stringify(filteredChats));
        
        // Update sidebar
        this.renderChatHistory();
    }
    
    getChatHistory() {
        try {
            const history = localStorage.getItem('ragChatHistory');
            return history ? JSON.parse(history) : [];
        } catch (error) {
            console.error('Error loading chat history:', error);
            return [];
        }
    }
    
    loadChat(chatId) {
        const chats = this.getChatHistory();
        const chat = chats.find(c => c.id === chatId);
        
        if (!chat) return;
        
        // Save current chat first
        if (this.currentChatId && this.currentChatMessages.length > 0) {
            this.saveCurrentChat();
        }
        
        // Load the selected chat
        this.currentChatId = chatId;
        this.currentChatMessages = chat.messages;
        this.messageCount = chat.messages.length;
        
        // Clear and rebuild chat messages
        this.chatMessages.innerHTML = '';
        
        chat.messages.forEach(messageData => {
            const messageElement = this.renderMessage(messageData);
            this.chatMessages.appendChild(messageElement);
        });
        
        this.scrollToBottom();
        this.updateActiveChatInSidebar(chatId);
        
        // Close mobile sidebar
        if (window.innerWidth <= 768) {
            this.closeMobileSidebar();
        }
    }
    
    renderChatHistory() {
        const chats = this.getChatHistory();
        this.chatHistoryContainer.innerHTML = '';
        
        if (chats.length === 0) {
            this.chatHistoryContainer.innerHTML = '<div class="history-empty">No chat history</div>';
            return;
        }
        
        // Group chats by date
        const today = new Date().toDateString();
        const yesterday = new Date(Date.now() - 86400000).toDateString();
        
        const todayChats = chats.filter(chat => new Date(chat.timestamp).toDateString() === today);
        const yesterdayChats = chats.filter(chat => new Date(chat.timestamp).toDateString() === yesterday);
        const olderChats = chats.filter(chat => {
            const chatDate = new Date(chat.timestamp).toDateString();
            return chatDate !== today && chatDate !== yesterday;
        });
        
        // Render groups
        if (todayChats.length > 0) {
            this.renderChatGroup('Today', todayChats, this.chatHistoryContainer);
        }
        
        if (yesterdayChats.length > 0) {
            this.renderChatGroup('Yesterday', yesterdayChats, this.chatHistoryContainer);
        }
        
        if (olderChats.length > 0) {
            this.renderChatGroup('Older', olderChats, this.chatHistoryContainer);
        }
    }
    
    renderChatGroup(label, chats, container) {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'history-section';
        
        const labelDiv = document.createElement('div');
        labelDiv.className = 'history-label';
        labelDiv.textContent = label;
        groupDiv.appendChild(labelDiv);
        
        chats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.className = 'history-item';
            chatItem.innerHTML = `
                <div class="history-text">${chat.title}</div>
                <button class="delete-chat-btn" onclick="chatbot.deleteChat('${chat.id}')" title="Delete chat">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            `;
            
            chatItem.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-chat-btn')) {
                    this.loadChat(chat.id);
                }
            });
            
            groupDiv.appendChild(chatItem);
        });
        
        container.appendChild(groupDiv);
    }
    
    updateActiveChatInSidebar(chatId) {
        // Remove active class from all items
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to current chat (if it exists in sidebar)
        const activeItem = document.querySelector(`.history-item[onclick*="${chatId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
    }
    
    deleteChat(chatId) {
        if (!confirm('Are you sure you want to delete this chat?')) return;
        
        const chats = this.getChatHistory();
        const filteredChats = chats.filter(chat => chat.id !== chatId);
        
        localStorage.setItem('ragChatHistory', JSON.stringify(filteredChats));
        this.renderChatHistory();
        
        // If we deleted the current chat, start a new one
        if (chatId === this.currentChatId) {
            this.startNewChat();
        }
    }
    
    clearHistory() {
        if (!confirm('Are you sure you want to clear all chat history?')) return;
        
        localStorage.removeItem('ragChatHistory');
        this.renderChatHistory();
        this.startNewChat();
    }
    
    loadChatHistory() {
        this.renderChatHistory();
    }
    
    toggleSidebar() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        this.sidebar.classList.toggle('collapsed');
        localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed.toString());
    }
    
    toggleMobileSidebar() {
        this.sidebar.classList.toggle('open');
    }
    
    closeMobileSidebar() {
        this.sidebar.classList.remove('open');
    }
    
    newChat() {
        this.startNewChat();
    }
    
    // Load saved sidebar state on init
    loadSidebarState() {
        const collapsed = localStorage.getItem('sidebarCollapsed');
        if (collapsed === 'true') {
            this.sidebarCollapsed = true;
            this.sidebar.classList.add('collapsed');
        }
    }
}

// Initialize the chatbot when the page loads
let chatbot;
document.addEventListener('DOMContentLoaded', () => {
    chatbot = new RAGChatbot();
    chatbot.loadSidebarState();
});