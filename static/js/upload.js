/**
 * File upload functionality for BrainBudget
 * Handles drag-and-drop, file validation, and upload progress with ADHD-friendly feedback
 */

class FileUploader {
    constructor(options = {}) {
        this.dropZone = document.getElementById(options.dropZone);
        this.fileInput = document.getElementById(options.fileInput);
        this.browseBtn = document.getElementById(options.browseBtn);
        this.progressContainer = document.getElementById(options.progressContainer);
        this.progressBar = document.getElementById(options.progressBar);
        this.progressText = document.getElementById(options.progressText);
        this.filePreview = document.getElementById(options.filePreview);
        this.fileName = document.getElementById(options.fileName);
        this.fileSize = document.getElementById(options.fileSize);
        this.removeBtn = document.getElementById(options.removeBtn);
        this.analyzeBtn = document.getElementById(options.analyzeBtn);
        this.dropContent = document.getElementById(options.dropContent);
        
        this.apiEndpoint = options.apiEndpoint || '/api/upload';
        this.maxFileSize = options.maxFileSize || 16 * 1024 * 1024; // 16MB
        this.allowedTypes = options.allowedTypes || ['pdf', 'jpg', 'jpeg', 'png'];
        
        this.currentFile = null;
        this.uploadInProgress = false;
        
        this.init();
    }
    
    init() {
        if (!this.dropZone) {
            console.warn('Drop zone element not found');
            return;
        }
        
        this.setupEventListeners();
        this.updateUI();
    }
    
    setupEventListeners() {
        // Drag and drop events
        this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropZone.addEventListener('dragenter', (e) => this.handleDragEnter(e));
        this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Click to browse
        this.browseBtn?.addEventListener('click', () => this.fileInput?.click());
        this.dropZone.addEventListener('click', (e) => {
            if (e.target === this.dropZone || this.dropContent?.contains(e.target)) {
                this.fileInput?.click();
            }
        });
        
        // File input change
        this.fileInput?.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Remove file
        this.removeBtn?.addEventListener('click', () => this.removeFile());
        
        // Analyze button
        this.analyzeBtn?.addEventListener('click', () => this.startAnalysis());
        
        // Prevent default drag behaviors on the document
        document.addEventListener('dragover', (e) => e.preventDefault());
        document.addEventListener('drop', (e) => e.preventDefault());
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (!this.uploadInProgress) {
            this.dropZone.classList.add('border-primary-400', 'bg-primary-50');
            this.dropZone.classList.remove('border-primary-300');
        }
    }
    
    handleDragEnter(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (!this.uploadInProgress) {
            this.dropZone.classList.add('border-primary-400', 'bg-primary-50');
        }
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // Only remove highlight if we're leaving the drop zone entirely
        if (!this.dropZone.contains(e.relatedTarget)) {
            this.dropZone.classList.remove('border-primary-400', 'bg-primary-50');
            this.dropZone.classList.add('border-primary-300');
        }
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        
        this.dropZone.classList.remove('border-primary-400', 'bg-primary-50');
        this.dropZone.classList.add('border-primary-300');
        
        if (this.uploadInProgress) {
            showErrorToast('Please wait for the current upload to finish');
            return;
        }
        
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }
    
    handleFile(file) {
        const validation = this.validateFile(file);
        
        if (!validation.valid) {
            showErrorToast(validation.errors.join('\n'));
            return;
        }
        
        this.currentFile = file;
        this.showFilePreview();
        this.enableAnalyzeButton();
        
        // Provide encouraging feedback
        showSuccessToast('Great! Your file is ready to analyze 📄');
    }
    
    validateFile(file) {
        const errors = [];
        
        // Check file size
        if (file.size > this.maxFileSize) {
            const maxSizeMB = Math.round(this.maxFileSize / (1024 * 1024));
            errors.push(`File size must be less than ${maxSizeMB}MB`);
        }
        
        // Check file type
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!this.allowedTypes.includes(fileExtension)) {
            errors.push(`File type must be: ${this.allowedTypes.join(', ')}`);
        }
        
        // Check if file is empty
        if (file.size === 0) {
            errors.push('File appears to be empty');
        }
        
        return {
            valid: errors.length === 0,
            errors: errors
        };
    }
    
    showFilePreview() {
        if (!this.currentFile || !this.filePreview) return;
        
        // Update file info
        if (this.fileName) {
            this.fileName.textContent = this.currentFile.name;
        }
        
        if (this.fileSize) {
            this.fileSize.textContent = this.formatFileSize(this.currentFile.size);
        }
        
        // Show preview
        this.filePreview.classList.remove('hidden');
        
        // Hide drop area content
        if (this.dropContent) {
            this.dropContent.classList.add('hidden');
        }
        
        // Show upload progress container (but keep it hidden initially)
        if (this.progressContainer) {
            // Don't show progress until upload starts
        }
    }
    
    removeFile() {
        this.currentFile = null;
        
        // Hide preview
        if (this.filePreview) {
            this.filePreview.classList.add('hidden');
        }
        
        // Show drop area content
        if (this.dropContent) {
            this.dropContent.classList.remove('hidden');
        }
        
        // Hide progress
        if (this.progressContainer) {
            this.progressContainer.classList.add('hidden');
        }
        
        // Reset file input
        if (this.fileInput) {
            this.fileInput.value = '';
        }
        
        // Disable analyze button
        this.disableAnalyzeButton();
        
        // Reset progress
        this.updateProgress(0, 'Select a file to begin...');
        
        showSuccessToast('File removed. You can select another one! 🗑️');
    }
    
    enableAnalyzeButton() {
        if (this.analyzeBtn) {
            this.analyzeBtn.disabled = false;
            this.analyzeBtn.classList.remove('disabled:opacity-50', 'disabled:cursor-not-allowed');
            this.analyzeBtn.classList.add('hover:bg-primary-600');
        }
    }
    
    disableAnalyzeButton() {
        if (this.analyzeBtn) {
            this.analyzeBtn.disabled = true;
            this.analyzeBtn.classList.add('disabled:opacity-50', 'disabled:cursor-not-allowed');
            this.analyzeBtn.classList.remove('hover:bg-primary-600');
        }
    }
    
    async startAnalysis() {
        if (!this.currentFile || this.uploadInProgress) {
            return;
        }
        
        try {
            this.uploadInProgress = true;
            this.disableAnalyzeButton();
            
            // Show progress
            this.showProgress();
            this.updateProgress(5, 'Preparing your statement...');
            
            // Upload the file
            const result = await this.uploadFile();
            
            if (result && result.success) {
                this.updateProgress(100, 'Analysis complete! 🎉');
                
                // Show success message
                showSuccessToast('Analysis complete! Redirecting to results...');
                
                // Redirect to results page after a short delay
                setTimeout(() => {
                    window.location.href = result.redirect_url || '/analysis';
                }, 1500);
            } else {
                throw new Error(result?.message || 'Analysis failed');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            
            // Show error with helpful message
            const friendlyMessage = this.getFriendlyErrorMessage(error.message);
            showErrorToast(friendlyMessage);
            
            // Reset UI
            this.hideProgress();
            this.enableAnalyzeButton();
        } finally {
            this.uploadInProgress = false;
        }
    }
    
    async uploadFile() {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', this.currentFile);
            
            const xhr = new XMLHttpRequest();
            
            // Track upload progress
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 70); // Reserve 30% for analysis
                    this.updateProgress(percentComplete + 5, 'Uploading your statement...');
                }
            });
            
            // Handle response
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        
                        // Simulate analysis progress
                        this.updateProgress(80, 'Analyzing with AI...');
                        
                        setTimeout(() => {
                            this.updateProgress(95, 'Generating insights...');
                            
                            setTimeout(() => {
                                resolve(response);
                            }, 1000);
                        }, 1500);
                        
                    } catch (e) {
                        reject(new Error('Invalid response from server'));
                    }
                } else {
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        reject(new Error(errorResponse.message || `Upload failed (${xhr.status})`));
                    } catch (e) {
                        reject(new Error(`Upload failed: ${xhr.statusText}`));
                    }
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Network error occurred'));
            });
            
            xhr.addEventListener('timeout', () => {
                reject(new Error('Upload timed out'));
            });
            
            xhr.timeout = 60000; // 60 seconds timeout
            xhr.open('POST', this.apiEndpoint);
            xhr.send(formData);
        });
    }
    
    showProgress() {
        if (this.progressContainer && this.dropContent) {
            this.dropContent.classList.add('hidden');
            this.progressContainer.classList.remove('hidden');
        }
    }
    
    hideProgress() {
        if (this.progressContainer && this.dropContent) {
            this.progressContainer.classList.add('hidden');
            this.dropContent.classList.remove('hidden');
        }
    }
    
    updateProgress(percent, message) {
        if (this.progressBar) {
            this.progressBar.style.width = `${Math.min(percent, 100)}%`;
        }
        
        if (this.progressText) {
            this.progressText.textContent = message;
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    getFriendlyErrorMessage(errorMessage) {
        const errorMap = {
            'Network error': 'Connection problem. Please check your internet and try again.',
            'Upload timed out': 'Upload is taking too long. Please try with a smaller file.',
            'File too large': 'This file is too big. Please try a smaller file (under 16MB).',
            'Invalid file type': 'This file type isn\'t supported. Please use PDF, JPG, or PNG files.',
            'Upload failed': 'Something went wrong with the upload. Please try again.',
            'Analysis failed': 'We couldn\'t analyze your statement. Please try again or contact support.'
        };
        
        // Find matching error message
        for (const [key, message] of Object.entries(errorMap)) {
            if (errorMessage.toLowerCase().includes(key.toLowerCase())) {
                return message;
            }
        }
        
        // Default friendly message
        return 'Something didn\'t work as expected. Please try again, or contact us if the problem continues.';
    }
    
    updateUI() {
        // Initial UI state
        this.disableAnalyzeButton();
        this.updateProgress(0, 'Select a file to begin...');
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.FileUploader = FileUploader;
}