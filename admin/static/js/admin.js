class RAGAdmin {
    constructor() {
        this.uploadApiUrl = 'http://localhost:8004';
        this.fileInput = document.getElementById('file-input');
        this.uploadBtn = document.getElementById('upload-btn');
        this.uploadArea = document.getElementById('upload-area');
        this.uploadQueue = document.getElementById('upload-queue');
        this.queueItems = document.getElementById('queue-items');
        this.processingStatus = document.getElementById('processing-status');
        this.statusItems = document.getElementById('status-items');
        this.startAllBtn = document.getElementById('start-all-btn');
        this.clearQueueBtn = document.getElementById('clear-queue-btn');
        
        this.fileQueue = [];
        this.processingTasks = new Map();
        
        this.init();
    }
    
    init() {
        // File input events
        this.uploadBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop events
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Queue actions
        this.startAllBtn.addEventListener('click', () => this.processAllFiles());
        this.clearQueueBtn.addEventListener('click', () => this.clearQueue());
    }
    
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.addFilesToQueue(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.addFilesToQueue(files);
        e.target.value = ''; // Reset input
    }
    
    addFilesToQueue(files) {
        const validFiles = files.filter(file => {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                this.showNotification(`${file.name} is not a PDF file`, 'error');
                return false;
            }
            if (file.size > 50 * 1024 * 1024) {
                this.showNotification(`${file.name} is too large (max 50MB)`, 'error');
                return false;
            }
            return true;
        });
        
        validFiles.forEach(file => {
            const fileId = this.generateFileId();
            this.fileQueue.push({
                id: fileId,
                file: file,
                status: 'queued'
            });
        });
        
        if (validFiles.length > 0) {
            this.renderQueue();
            this.showNotification(`Added ${validFiles.length} file(s) to queue`, 'success');
        }
    }
    
    generateFileId() {
        return 'file_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    renderQueue() {
        if (this.fileQueue.length === 0) {
            this.uploadQueue.style.display = 'none';
            return;
        }
        
        this.uploadQueue.style.display = 'block';
        this.queueItems.innerHTML = '';
        
        this.fileQueue.forEach(item => {
            const queueItem = document.createElement('div');
            queueItem.className = 'queue-item';
            queueItem.innerHTML = `
                <div class="item-info">
                    <div class="item-icon">PDF</div>
                    <div class="item-details">
                        <h4>${item.file.name}</h4>
                        <p>${this.formatFileSize(item.file.size)} • ${item.status}</p>
                    </div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-danger btn-small" onclick="admin.removeFromQueue('${item.id}')">
                        Remove
                    </button>
                </div>
            `;
            this.queueItems.appendChild(queueItem);
        });
    }
    
    removeFromQueue(fileId) {
        this.fileQueue = this.fileQueue.filter(item => item.id !== fileId);
        this.renderQueue();
    }
    
    clearQueue() {
        if (confirm('Are you sure you want to clear the upload queue?')) {
            this.fileQueue = [];
            this.renderQueue();
        }
    }
    
    async processAllFiles() {
        if (this.fileQueue.length === 0) {
            this.showNotification('No files in queue', 'warning');
            return;
        }
        
        this.startAllBtn.disabled = true;
        this.startAllBtn.textContent = 'Processing...';
        
        // Show processing status section
        this.processingStatus.style.display = 'block';
        
        // Process each file
        for (const item of this.fileQueue) {
            await this.processFile(item);
        }
        
        // Clear queue after processing
        this.fileQueue = [];
        this.renderQueue();
        
        this.startAllBtn.disabled = false;
        this.startAllBtn.textContent = 'Process All Files';
        
        this.showNotification('All files processed', 'success');
    }
    
    async processFile(item) {
        const formData = new FormData();
        formData.append('file', item.file);
        
        // Create status item
        const statusItem = this.createStatusItem(item);
        this.statusItems.appendChild(statusItem);
        
        try {
            // Upload file
            this.updateStatusItem(statusItem, 'Uploading...', 0);
            
            const response = await fetch(`${this.uploadApiUrl}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Start polling for status
                this.processingTasks.set(item.id, result.task_id);
                await this.pollFileStatus(item.id, result.task_id, statusItem);
            } else {
                this.updateStatusItem(statusItem, 'Upload failed: ' + result.message, 0, 'error');
            }
        } catch (error) {
            this.updateStatusItem(statusItem, 'Upload failed: ' + error.message, 0, 'error');
        }
    }
    
    createStatusItem(item) {
        const statusItem = document.createElement('div');
        statusItem.className = 'status-item';
        statusItem.id = `status-${item.id}`;
        statusItem.innerHTML = `
            <div class="item-info">
                <div class="item-icon">PDF</div>
                <div class="item-details">
                    <h4>${item.file.name}</h4>
                    <p class="status-text">Preparing...</p>
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                </div>
            </div>
        `;
        return statusItem;
    }
    
    updateStatusItem(statusItem, message, progress, status = 'processing') {
        const statusText = statusItem.querySelector('.status-text');
        const progressFill = statusItem.querySelector('.progress-fill');
        
        statusText.textContent = message;
        statusText.className = `status-text ${status}`;
        progressFill.style.width = progress + '%';
        progressFill.className = `progress-fill ${status}`;
    }
    
    async pollFileStatus(fileId, taskId, statusItem) {
        try {
            const response = await fetch(`${this.uploadApiUrl}/status/${taskId}`);
            const status = await response.json();
            
            if (status.status === 'processing') {
                let percentage = 50;
                if (status.progress) {
                    const match = status.progress.match(/(\d+)%/);
                    if (match) {
                        percentage = parseInt(match[1]);
                    }
                }
                this.updateStatusItem(statusItem, status.message, percentage);
                
                // Continue polling
                setTimeout(() => this.pollFileStatus(fileId, taskId, statusItem), 2000);
            } else if (status.status === 'completed') {
                this.updateStatusItem(statusItem, status.message, 100, 'success');
                this.processingTasks.delete(fileId);
            } else if (status.status === 'failed') {
                this.updateStatusItem(statusItem, status.message, 0, 'error');
                this.processingTasks.delete(fileId);
            }
        } catch (error) {
            this.updateStatusItem(statusItem, 'Status check failed: ' + error.message, 0, 'error');
            this.processingTasks.delete(fileId);
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: var(--radius);
            color: white;
            font-weight: 500;
            z-index: 1000;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        `;
        
        // Set background color based on type
        const colors = {
            success: '#22c55e',
            error: '#dc2626',
            warning: '#f59e0b',
            info: '#2563eb'
        };
        notification.style.background = colors[type] || colors.info;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 5000);
    }
}

// Initialize admin when page loads
let admin;
document.addEventListener('DOMContentLoaded', () => {
    admin = new RAGAdmin();
});