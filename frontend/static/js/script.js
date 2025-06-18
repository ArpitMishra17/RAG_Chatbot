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
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    }
    
    // Determine bubble size class based on content length
    getBubbleSizeClass(content) {
        const length = content.length;
        
        if (length < 50) {
            return 'short';
        } else if (length < 200) {
            return 'medium';
        } else if (length < 500) {
            return 'long';
        } else {
            return 'extra-long';
        }
    }
    
    addMessage(content, type, sources = [], runtime = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        // Create avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = type === 'user' ? 'You' : 'AI';
        
        // Create content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Create message bubble with dynamic sizing
        const bubble = document.createElement('div');
        const sizeClass = this.getBubbleSizeClass(content);
        bubble.className = `message-bubble ${sizeClass}`;
        bubble.textContent = content;
        
        contentDiv.appendChild(bubble);
        
        // Add sources if available
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources';
            
            const sourcesTitle = document.createElement('div');
            sourcesTitle.className = 'sources-title';
            sourcesTitle.textContent = 'Sources';
            
            const sourcesList = document.createElement('div');
            sourcesList.className = 'sources-list';
            sourcesList.textContent = sources.join(', ');
            
            sourcesDiv.appendChild(sourcesTitle);
            sourcesDiv.appendChild(sourcesList);
            contentDiv.appendChild(sourcesDiv);
        }
        
        // Add metadata
        if (runtime) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            metaDiv.textContent = `${runtime}ms`;
            contentDiv.appendChild(metaDiv);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        
        this.chatMessages.appendChild(messageDiv);
        this.messageCount++;
        
        // Store message in current chat
        const messageData = {
            content,
            type,
            sources,
            runtime,
            timestamp: new Date().toISOString()
        };
        this.currentChatMessages.push(messageData);
        
        // Save current chat to localStorage
        this.saveCurrentChat();
        
        this.scrollToBottom();
    }
    
    addErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        this.chatMessages.appendChild(errorDiv);
        this.scrollToBottom();
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
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    // Chat History Management
    generateChatId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    generateChatTitle(firstMessage) {
        // Generate a title from the first user message (max 30 chars)
        if (!firstMessage || firstMessage.length === 0) return 'New Chat';
        
        let title = firstMessage.trim();
        if (title.length > 30) {
            title = title.substring(0, 27) + '...';
        }
        return title;
    }
    
    startNewChat() {
        this.currentChatId = this.generateChatId();
        this.currentChatMessages = [];
        this.messageCount = 0;
    }
    
    saveCurrentChat() {
        if (this.currentChatMessages.length === 0) return;
        
        const chatData = {
            id: this.currentChatId,
            title: this.generateChatTitle(this.currentChatMessages[0]?.content),
            messages: this.currentChatMessages,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        
        // Get existing chats
        let chats = this.getChatHistory();
        
        // Update existing chat or add new one
        const existingIndex = chats.findIndex(chat => chat.id === this.currentChatId);
        if (existingIndex !== -1) {
            chats[existingIndex] = chatData;
        } else {
            chats.unshift(chatData); // Add to beginning
        }
        
        // Keep only last 10 chats
        if (chats.length > this.maxChats) {
            chats = chats.slice(0, this.maxChats);
        }
        
        // Save to localStorage
        localStorage.setItem('ragChatHistory', JSON.stringify(chats));
        
        // Update UI
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
        
        // Clear current messages
        this.chatMessages.innerHTML = '';
        
        // Set current chat
        this.currentChatId = chatId;
        this.currentChatMessages = [...chat.messages];
        this.messageCount = chat.messages.length;
        
        // Render messages
        chat.messages.forEach(msg => {
            this.renderMessage(msg);
        });
        
        // Update active chat in sidebar
        this.updateActiveChatInSidebar(chatId);
        
        this.scrollToBottom();
        this.questionInput.focus();
    }
    
    renderMessage(messageData) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${messageData.type}-message`;
        
        // Create avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = messageData.type === 'user' ? 'You' : 'AI';
        
        // Create content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Create message bubble with dynamic sizing
        const bubble = document.createElement('div');
        const sizeClass = this.getBubbleSizeClass(messageData.content);
        bubble.className = `message-bubble ${sizeClass}`;
        bubble.textContent = messageData.content;
        
        contentDiv.appendChild(bubble);
        
        // Add sources if available
        if (messageData.sources && messageData.sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources';
            
            const sourcesTitle = document.createElement('div');
            sourcesTitle.className = 'sources-title';
            sourcesTitle.textContent = 'Sources';
            
            const sourcesList = document.createElement('div');
            sourcesList.className = 'sources-list';
            sourcesList.textContent = messageData.sources.join(', ');
            
            sourcesDiv.appendChild(sourcesTitle);
            sourcesDiv.appendChild(sourcesList);
            contentDiv.appendChild(sourcesDiv);
        }
        
        // Add metadata
        if (messageData.runtime) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            metaDiv.textContent = `${messageData.runtime}ms`;
            contentDiv.appendChild(metaDiv);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        
        this.chatMessages.appendChild(messageDiv);
    }
    
    renderChatHistory() {
        const chats = this.getChatHistory();
        
        // Clear existing history (except clear button)
        const historyContainer = this.chatHistoryContainer;
        historyContainer.innerHTML = '';
        
        if (chats.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'history-empty';
            emptyState.innerHTML = `
                <p>No chat history yet</p>
                <p>Start a conversation to see your chats here</p>
            `;
            historyContainer.appendChild(emptyState);
            return;
        }
        
        // Group chats by date
        const today = new Date().toDateString();
        const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toDateString();
        
        const groupedChats = {
            today: [],
            yesterday: [],
            older: []
        };
        
        chats.forEach(chat => {
            const chatDate = new Date(chat.createdAt).toDateString();
            if (chatDate === today) {
                groupedChats.today.push(chat);
            } else if (chatDate === yesterday) {
                groupedChats.yesterday.push(chat);
            } else {
                groupedChats.older.push(chat);
            }
        });
        
        // Render groups
        if (groupedChats.today.length > 0) {
            this.renderChatGroup('Today', groupedChats.today, historyContainer);
        }
        
        if (groupedChats.yesterday.length > 0) {
            this.renderChatGroup('Yesterday', groupedChats.yesterday, historyContainer);
        }
        
        if (groupedChats.older.length > 0) {
            this.renderChatGroup('Previous 7 days', groupedChats.older, historyContainer);
        }
    }
    
    renderChatGroup(label, chats, container) {
        const section = document.createElement('div');
        section.className = 'history-section';
        
        const labelDiv = document.createElement('div');
        labelDiv.className = 'history-label';
        labelDiv.textContent = label;
        section.appendChild(labelDiv);
        
        chats.forEach(chat => {
            const item = document.createElement('div');
            item.className = `history-item ${chat.id === this.currentChatId ? 'active' : ''}`;
            item.dataset.chatId = chat.id;
            
            item.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M21 15A2 2 0 0 1 19 17H7A2 2 0 0 1 5 15V5A2 2 0 0 1 7 3H19A2 2 0 0 1 21 5Z" stroke="currentColor" stroke-width="2"/>
                    <path d="M16 3V7L14 5L12 7V3" stroke="currentColor" stroke-width="2"/>
                </svg>
                <span class="history-text">${chat.title}</span>
                <button class="delete-chat-btn" data-chat-id="${chat.id}" title="Delete chat">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </button>
            `;
            
            // Add click listener for loading chat
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-chat-btn')) {
                    this.loadChat(chat.id);
                }
            });
            
            // Add delete listener
            const deleteBtn = item.querySelector('.delete-chat-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteChat(chat.id);
            });
            
            section.appendChild(item);
        });
        
        container.appendChild(section);
    }
    
    updateActiveChatInSidebar(chatId) {
        const items = this.chatHistoryContainer.querySelectorAll('.history-item');
        items.forEach(item => {
            if (item.dataset.chatId === chatId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    deleteChat(chatId) {
        if (confirm('Are you sure you want to delete this chat?')) {
            let chats = this.getChatHistory();
            chats = chats.filter(chat => chat.id !== chatId);
            
            localStorage.setItem('ragChatHistory', JSON.stringify(chats));
            
            // If deleted chat is current, start new chat
            if (chatId === this.currentChatId) {
                this.newChat();
            } else {
                this.renderChatHistory();
            }
        }
    }
    
    clearHistory() {
        if (confirm('Are you sure you want to clear all chat history? This action cannot be undone.')) {
            localStorage.removeItem('ragChatHistory');
            this.renderChatHistory();
            this.newChat();
        }
    }
    
    loadChatHistory() {
        this.renderChatHistory();
    }
    
    toggleSidebar() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        
        if (this.sidebarCollapsed) {
            this.sidebar.classList.add('collapsed');
            // Update toggle button icon for collapsed state
            const toggleBtn = this.sidebarToggle.querySelector('svg');
            if (toggleBtn) {
                toggleBtn.innerHTML = `
                    <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                `;
            }
        } else {
            this.sidebar.classList.remove('collapsed');
            // Update toggle button icon for expanded state
            const toggleBtn = this.sidebarToggle.querySelector('svg');
            if (toggleBtn) {
                toggleBtn.innerHTML = `
                    <path d="M3 8L21 8M3 16L21 16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                `;
            }
        }
        
        // Save state to localStorage
        localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed);
    }
    
    toggleMobileSidebar() {
        this.sidebar.classList.toggle('open');
    }
    
    closeMobileSidebar() {
        this.sidebar.classList.remove('open');
    }
    
    newChat() {
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
                <h2>Welcome to RAG Assistant</h2>
                <p>I can help you find information from your documents. Ask me anything!</p>
            </div>
        `;
        
        // Start new chat
        this.startNewChat();
        
        // Update sidebar
        this.renderChatHistory();
        
        this.questionInput.focus();
    }
    
    // Load saved sidebar state on init
    loadSidebarState() {
        const saved = localStorage.getItem('sidebarCollapsed');
        if (saved === 'true') {
            this.sidebarCollapsed = true;
            this.sidebar.classList.add('collapsed');
        }
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const chatbot = new RAGChatbot();
    chatbot.loadSidebarState();
});