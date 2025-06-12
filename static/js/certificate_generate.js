/**
 * Clean Certificate Generator - Pure JavaScript Implementation
 * Handles concurrent certificate generation with simple placeholder replacement
 * No OS dependencies - uses only browser-based PDF libraries
 */

class CleanCertificateGenerator {
    constructor() {
        this.isGenerating = false;
        this.activeGenerations = new Map(); // Track concurrent generations
        this.tempFiles = new Set(); // Track temporary files for cleanup
        
        // Certificate templates for different event types
        this.templates = {
            individual: this.getIndividualTemplate(),
            team: this.getTeamTemplate()
        };
        
        console.log('🚀 Clean Certificate Generator initialized');
    }    /**
     * Main certificate generation function
     * Handles concurrent requests with unique identifiers
     */
    async generateCertificate(eventId, enrollmentNo = null) {
        // Create unique generation ID with enrollment and timestamp
        const generationId = `${eventId}_${enrollmentNo || 'current'}_${Date.now()}`;
        
        console.log(`🎯 Starting certificate generation [ID: ${generationId}]`);
        
        // Check if already generating for this combination
        const existingGenerationKey = `${eventId}_${enrollmentNo || 'current'}`;
        const existingGeneration = Array.from(this.activeGenerations.keys()).find(key => 
            key.startsWith(existingGenerationKey) && key !== generationId
        );
        
        if (existingGeneration) {
            console.warn('⚠️ Certificate generation already in progress for this user/event combination');
            this.showError('Certificate generation already in progress. Please wait...');
            return;
        }

        // Verify libraries are loaded
        if (!this.checkLibraries()) {
            console.warn('⚠️ PDF libraries not available, using server fallback');
            await this.generateCertificateServerFallback(eventId, enrollmentNo);
            return;
        }

        // Add to active generations with detailed tracking
        this.activeGenerations.set(generationId, {
            status: 'starting',
            timestamp: Date.now(),
            eventId: eventId,
            enrollmentNo: enrollmentNo
        });

        try {
            // Show loading state
            this.showLoadingState(generationId);
            
            // Update generation status
            this.activeGenerations.set(generationId, {
                ...this.activeGenerations.get(generationId),
                status: 'fetching_data'
            });

            // Step 1: Fetch certificate data from Python API
            const certificateData = await this.fetchCertificateData(eventId, enrollmentNo);
            
            if (!certificateData.success) {
                throw new Error(certificateData.message || 'Failed to fetch certificate data');
            }

            console.log('✅ Certificate data fetched successfully');
            
            // Update generation status
            this.activeGenerations.set(generationId, {
                ...this.activeGenerations.get(generationId),
                status: 'generating_html'
            });
            
            // Step 2: Generate HTML with replaced placeholders
            const htmlContent = this.generateCertificateHTML(certificateData.data);
            
            // Update generation status
            this.activeGenerations.set(generationId, {
                ...this.activeGenerations.get(generationId),
                status: 'converting_to_pdf'
            });
            
            // Step 3: Convert HTML to PDF
            const pdfBlob = await this.convertHTMLToPDF(htmlContent, certificateData.data);
            
            // Step 4: Create temporary file name using naming convention: studentName[0]_eventName[0]_timestamp
            const fileName = this.createTempFileName(certificateData.data);
            
            // Update generation status
            this.activeGenerations.set(generationId, {
                ...this.activeGenerations.get(generationId),
                status: 'downloading'
            });
            
            // Step 5: Download PDF
            this.downloadPDF(pdfBlob, fileName);
            
            // Update generation status
            this.activeGenerations.set(generationId, {
                ...this.activeGenerations.get(generationId),
                status: 'sending_email'
            });
            
            // Step 6: Send email (background) - don't wait for completion
            this.sendCertificateEmail(certificateData.data, pdfBlob, fileName).catch(err => {
                console.warn('Email sending failed but certificate generation succeeded:', err);
            });
            
            // Step 7: Cleanup temp file tracking
            setTimeout(() => {
                this.cleanupTempFile(fileName);
            }, 5000); // Cleanup after 5 seconds
            
            console.log(`✅ Certificate generation completed [ID: ${generationId}]`);
            this.showSuccess('Certificate generated and downloaded successfully!');

        } catch (error) {
            console.error(`❌ Certificate generation failed [ID: ${generationId}]:`, error);
            this.showError(`Certificate generation failed: ${error.message}`);
        } finally {
            // Remove from active generations
            this.activeGenerations.delete(generationId);
            this.hideLoadingState();
        }
    }

    /**
     * Check if required libraries are loaded
     */
    checkLibraries() {
        const jsPDFReady = typeof window.jsPDF !== 'undefined';
        const html2canvasReady = typeof window.html2canvas !== 'undefined';
        
        console.log(`🔍 Library check: jsPDF=${jsPDFReady}, html2canvas=${html2canvasReady}`);
        return jsPDFReady && html2canvasReady;
    }

    /**
     * Fetch certificate data from Python backend
     */
    async fetchCertificateData(eventId, enrollmentNo) {
        console.log('🔄 Fetching certificate data from Python API...');
        
        try {
            const response = await fetch('/client/api/certificate-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    event_id: eventId,
                    enrollment_no: enrollmentNo
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Certificate data received from Python API');
            return data;

        } catch (error) {
            console.error('❌ Failed to fetch certificate data:', error);
            throw new Error(`Data fetch failed: ${error.message}`);
        }
    }

    /**
     * Generate certificate HTML with placeholder replacement
     */
    generateCertificateHTML(data) {
        console.log('🎨 Generating certificate HTML with placeholder replacement...');
        
        // Determine event type
        const isTeamEvent = data.event_type === 'team' || data.team_name;
        const template = isTeamEvent ? this.templates.team : this.templates.individual;
        
        // Replace placeholders - SIMPLE replacement as requested
        let htmlContent = template;
        
        // Replace participant name placeholder
        htmlContent = htmlContent.replace(
            /\{\{\s*participant_name\s*\}\}/g, 
            data.participant_name || data.full_name || 'Participant'
        );
        
        // Replace department name placeholder
        htmlContent = htmlContent.replace(
            /\{\{\s*department_name\s*\}\}/g, 
            data.department_name || data.department || 'Department'
        );
        
        // Replace team name placeholder (only for team events)
        if (isTeamEvent) {
            htmlContent = htmlContent.replace(
                /\{\{\s*team_name\s*\}\}/g, 
                data.team_name || 'Team'
            );
        }
        
        // Replace event name and other dynamic data
        htmlContent = htmlContent.replace(/\{\{\s*event_name\s*\}\}/g, data.event_name || 'Event');
        htmlContent = htmlContent.replace(/\{\{\s*event_date\s*\}\}/g, data.event_date || 'Date');
        
        console.log('✅ HTML placeholders replaced successfully');
        return htmlContent;
    }

    /**
     * Convert HTML to PDF using JavaScript libraries
     */
    async convertHTMLToPDF(htmlContent, data) {
        console.log('📄 Converting HTML to PDF...');
        
        try {
            // Create temporary container
            const container = document.createElement('div');
            container.innerHTML = htmlContent;
            container.style.cssText = `
                position: absolute;
                top: -10000px;
                left: -10000px;
                width: 794px;
                height: 1123px;
                background: white;
                font-family: Arial, sans-serif;
                padding: 40px;
                box-sizing: border-box;
            `;
            
            document.body.appendChild(container);
            
            // Convert to canvas using html2canvas
            const canvas = await window.html2canvas(container, {
                width: 794,
                height: 1123,
                scale: 2,
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff'
            });
            
            // Remove temporary container
            document.body.removeChild(container);
            
            // Convert canvas to PDF using jsPDF
            const pdf = new window.jsPDF({
                orientation: 'portrait',
                unit: 'pt',
                format: [794, 1123]
            });
            
            const imgData = canvas.toDataURL('image/png');
            pdf.addImage(imgData, 'PNG', 0, 0, 794, 1123);
            
            // Convert to blob
            const pdfBlob = pdf.output('blob');
            
            console.log('✅ PDF conversion completed');
            return pdfBlob;
            
        } catch (error) {
            console.error('❌ PDF conversion failed:', error);
            throw new Error(`PDF conversion failed: ${error.message}`);
        }
    }

    /**
     * Create temporary file name with format: studentName[0]_eventName[0]_timestamp
     */
    createTempFileName(data) {
        const participantInitial = (data.participant_name || data.full_name || 'P').charAt(0).toUpperCase();
        const eventInitial = (data.event_name || 'E').charAt(0).toUpperCase();
        const timestamp = Date.now();
        
        const fileName = `${participantInitial}_${eventInitial}_${timestamp}.pdf`;
        
        // Add to temp files tracking
        this.tempFiles.add(fileName);
        
        console.log(`📁 Created temp file name: ${fileName}`);        return fileName;
    }

    /**
     * Check if PDF libraries are loaded and available
     */
    checkLibraries() {
        const jsPDFAvailable = typeof window.jsPDF !== 'undefined';
        const html2canvasAvailable = typeof window.html2canvas !== 'undefined';
        
        console.log(`📚 Library status - jsPDF: ${jsPDFAvailable}, html2canvas: ${html2canvasAvailable}`);
        
        return jsPDFAvailable && html2canvasAvailable;
    }

    /**
     * Convert HTML to PDF using jsPDF and html2canvas
     */
    async convertHTMLToPDF(htmlContent, data) {
        console.log('🔄 Converting HTML to PDF...');
        
        try {
            // Create a temporary container for the HTML
            const tempContainer = document.createElement('div');
            tempContainer.style.position = 'absolute';
            tempContainer.style.left = '-9999px';
            tempContainer.style.top = '-9999px';
            tempContainer.style.width = '714px';
            tempContainer.style.height = '1083px';
            tempContainer.innerHTML = htmlContent;
            
            document.body.appendChild(tempContainer);
            
            // Convert HTML to canvas
            const canvas = await window.html2canvas(tempContainer, {
                width: 714,
                height: 1083,
                scale: 2,
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff'
            });
            
            // Clean up temporary container
            document.body.removeChild(tempContainer);
            
            // Create PDF
            const { jsPDF } = window.jsPDF;
            const pdf = new jsPDF({
                orientation: 'portrait',
                unit: 'px',
                format: [714, 1083]
            });
            
            // Add the canvas as image to PDF
            const imgData = canvas.toDataURL('image/png');
            pdf.addImage(imgData, 'PNG', 0, 0, 714, 1083);
            
            // Return PDF as blob
            const pdfBlob = pdf.output('blob');
            console.log('✅ PDF conversion completed');
            
            return pdfBlob;
            
        } catch (error) {
            console.error('❌ PDF conversion failed:', error);
            throw new Error(`PDF conversion failed: ${error.message}`);
        }
    }

    /**
     * Server-side certificate generation fallback
     */
    async generateCertificateServerFallback(eventId, enrollmentNo) {
        console.log('🔄 Using server-side certificate generation fallback...');
        
        try {
            this.showLoadingState('server_fallback');
            
            const response = await fetch('/client/api/generate-certificate-server', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    event_id: eventId,
                    enrollment_no: enrollmentNo
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server generation failed: ${response.status} ${response.statusText}`);
            }
            
            // Get the PDF blob from response
            const pdfBlob = await response.blob();
            
            // Create filename
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const fileName = `certificate_${eventId}_${enrollmentNo || 'current'}_${timestamp}.pdf`;
            
            // Download the file
            await this.downloadPDF(pdfBlob, fileName);
            
            this.showSuccess('Certificate downloaded successfully using server generation!');
            console.log('✅ Server-side certificate generation completed');
            
        } catch (error) {
            console.error('❌ Server-side certificate generation failed:', error);
            this.showError(`Certificate generation failed: ${error.message}`);
        } finally {
            this.hideLoadingState();
        }
    }

    /**
     * Download PDF file
     */
    downloadPDF(pdfBlob, fileName) {
        console.log(`💾 Downloading PDF: ${fileName}`);
        
        try {
            const url = URL.createObjectURL(pdfBlob);
            const downloadLink = document.createElement('a');
            downloadLink.href = url;
            downloadLink.download = fileName;
            downloadLink.style.display = 'none';
            
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            
            // Clean up object URL after a delay
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            
            console.log('✅ PDF download initiated');
            
        } catch (error) {
            console.error('❌ PDF download failed:', error);
            throw new Error(`Download failed: ${error.message}`);
        }
    }

    /**
     * Send certificate via email (background operation)
     */
    async sendCertificateEmail(data, pdfBlob, fileName) {
        console.log('📧 Sending certificate email...');
        
        try {
            // Convert PDF blob to base64
            const pdfBase64 = await this.blobToBase64(pdfBlob);
            
            // Send to Python backend for email processing
            const response = await fetch('/client/api/send-certificate-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    event_id: data.event_id,
                    enrollment_no: data.enrollment_no,
                    pdf_base64: pdfBase64,
                    file_name: fileName
                })
            });
            
            if (!response.ok) {
                console.warn('⚠️ Email sending failed, but continuing...');
                return;
            }
            
            console.log('✅ Certificate email sent successfully');
            
        } catch (error) {
            console.warn('⚠️ Email sending failed:', error.message);
            // Don't throw error - email failure shouldn't stop certificate generation
        }
    }

    /**
     * Convert blob to base64
     */
    blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    /**
     * Clean up temporary file (remove from tracking)
     */
    cleanupTempFile(fileName) {
        console.log(`🗑️ Cleaning up temp file: ${fileName}`);
        this.tempFiles.delete(fileName);
    }

    /**
     * Show loading state
     */
    showLoadingState(generationId) {
        const button = document.getElementById('downloadCertificateBtn');
        if (button) {
            button.disabled = true;
            button.innerHTML = `
                <span class="flex items-center justify-center">
                    <svg class="w-4 h-4 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    Generating Certificate...
                </span>
            `;
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const button = document.getElementById('downloadCertificateBtn');
        if (button) {
            button.disabled = false;
            button.innerHTML = `
                <span class="flex items-center justify-center">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    Download Certificate
                </span>
            `;
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    /**
     * Show notification
     */
    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-md ${
            type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
        }`;
        notification.innerHTML = `
            <div class="flex items-center">
                <span class="mr-2">${type === 'success' ? '✅' : '❌'}</span>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white">×</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Individual event certificate template
     */
    getIndividualTemplate() {
        return `
        <div style="width: 714px; height: 1083px; padding: 40px; background: white; font-family: Arial, sans-serif; text-align: center; border: 2px solid #ccc;">
            <div style="border: 3px solid #333; padding: 30px; height: 100%; box-sizing: border-box;">
                <h1 style="font-size: 36px; color: #1a365d; margin-bottom: 20px; font-weight: bold;">CERTIFICATE OF PARTICIPATION</h1>
                
                <div style="width: 100px; height: 4px; background: linear-gradient(45deg, #3182ce, #805ad5); margin: 20px auto;"></div>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">This is to certify that</p>
                
                <h2 style="font-size: 32px; color: #2d3748; margin: 30px 0; font-weight: bold; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">{{ participant_name }}</h2>
                
                <p style="font-size: 18px; color: #4a5568; margin: 20px 0;">from the Department of</p>
                
                <h3 style="font-size: 24px; color: #3182ce; margin: 20px 0; font-weight: bold;">{{ department_name }}</h3>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">has successfully participated in</p>
                
                <h3 style="font-size: 28px; color: #805ad5; margin: 30px 0; font-weight: bold;">{{ event_name }}</h3>
                
                <p style="font-size: 16px; color: #4a5568; margin: 20px 0;">held on {{ event_date }}</p>
                
                <div style="margin-top: 60px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Event Coordinator</p>
                    </div>
                    
                    <div style="width: 80px; height: 80px; border: 2px solid #3182ce; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #3182ce; font-weight: bold;">SEAL</div>
                    
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Principal</p>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    /**
     * Team event certificate template
     */
    getTeamTemplate() {
        return `
        <div style="width: 714px; height: 1083px; padding: 40px; background: white; font-family: Arial, sans-serif; text-align: center; border: 2px solid #ccc;">
            <div style="border: 3px solid #333; padding: 30px; height: 100%; box-sizing: border-box;">
                <h1 style="font-size: 36px; color: #1a365d; margin-bottom: 20px; font-weight: bold;">CERTIFICATE OF PARTICIPATION</h1>
                
                <div style="width: 100px; height: 4px; background: linear-gradient(45deg, #3182ce, #805ad5); margin: 20px auto;"></div>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">This is to certify that</p>
                
                <h2 style="font-size: 32px; color: #2d3748; margin: 30px 0; font-weight: bold; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">{{ participant_name }}</h2>
                
                <p style="font-size: 18px; color: #4a5568; margin: 20px 0;">from the Department of</p>
                
                <h3 style="font-size: 24px; color: #3182ce; margin: 20px 0; font-weight: bold;">{{ department_name }}</h3>
                
                <p style="font-size: 18px; color: #4a5568; margin: 20px 0;">as a member of team</p>
                
                <h3 style="font-size: 26px; color: #e53e3e; margin: 20px 0; font-weight: bold; background: #fed7d7; padding: 10px; border-radius: 8px;">{{ team_name }}</h3>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">has successfully participated in</p>
                
                <h3 style="font-size: 28px; color: #805ad5; margin: 30px 0; font-weight: bold;">{{ event_name }}</h3>
                
                <p style="font-size: 16px; color: #4a5568; margin: 20px 0;">held on {{ event_date }}</p>
                
                <div style="margin-top: 50px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Event Coordinator</p>
                    </div>
                    
                    <div style="width: 80px; height: 80px; border: 2px solid #3182ce; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #3182ce; font-weight: bold;">SEAL</div>
                    
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Principal</p>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    /**
     * Get status of active generations (for debugging)
     */
    getActiveGenerations() {
        return Array.from(this.activeGenerations.entries());
    }

    /**
     * Force cleanup of all temp files (for debugging)
     */
    forceCleanup() {
        console.log('🗑️ Force cleaning up all temp files...');
        this.tempFiles.clear();
        this.activeGenerations.clear();
        console.log('✅ Cleanup completed');
    }
}

// Initialize global certificate generator
window.certificateGenerator = null;

// Initialize when libraries are ready
function initializeCertificateGenerator() {
    // Check if libraries are available
    const jsPDFAvailable = typeof window.jsPDF !== 'undefined';
    const html2canvasAvailable = typeof window.html2canvas !== 'undefined';
    
    console.log(`📚 Initializing - jsPDF: ${jsPDFAvailable}, html2canvas: ${html2canvasAvailable}`);
    
    if (!window.certificateGenerator) {
        window.certificateGenerator = new CleanCertificateGenerator();
        console.log('✅ Clean Certificate Generator initialized');
        
        if (jsPDFAvailable && html2canvasAvailable) {
            console.log('✅ All PDF libraries available - client-side generation enabled');
        } else {
            console.log('⚠️ Some PDF libraries missing - will use server fallback when needed');
        }
        
        return true;
    }
    
    return false;
}

// Global function for button clicks
function generateCertificate(eventId, enrollmentNo) {
    if (!window.certificateGenerator) {
        initializeCertificateGenerator();
    }
    
    if (window.certificateGenerator) {
        window.certificateGenerator.generateCertificate(eventId, enrollmentNo);
    } else {
        alert('Certificate generator not available. Please refresh the page and try again.');
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Try to initialize immediately
    if (!initializeCertificateGenerator()) {
        // If not ready, wait for libraries
        let attempts = 0;
        const maxAttempts = 50;
        
        const waitForLibraries = () => {
            attempts++;
            if (initializeCertificateGenerator()) {
                console.log('✅ Certificate generator initialized after waiting');
            } else if (attempts < maxAttempts) {
                setTimeout(waitForLibraries, 100);
            } else {
                console.warn('⚠️ Certificate libraries took too long to load');
            }
        };
        
        setTimeout(waitForLibraries, 100);
    }
});

// Debug functions (available in console)
window.debugCertificateGenerator = {
    getActiveGenerations: () => window.certificateGenerator?.getActiveGenerations() || [],
    forceCleanup: () => window.certificateGenerator?.forceCleanup(),
    checkLibraries: () => window.certificateGenerator?.checkLibraries() || false,
    reinitialize: () => {
        window.certificateGenerator = null;
        return initializeCertificateGenerator();
    }
};

console.log('💡 Debug functions available: window.debugCertificateGenerator');