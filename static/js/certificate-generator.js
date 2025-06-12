/**
 * JavaScript Certificate Generator
 * Handles client-side PDF generation using browser APIs
 * Eliminates OS dependencies for certificate generation
 */

class CertificateGenerator {
    constructor() {
        this.isGenerating = false;
        this.loadLibraries();
    }

    async loadLibraries() {
        // Load jsPDF library dynamically
        if (typeof window.jspdf === 'undefined') {
            await this.loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js');
        }

        // Load html2canvas for HTML to image conversion
        if (typeof html2canvas === 'undefined') {
            await this.loadScript('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js');
        }

        console.log('✅ Certificate Generator: Libraries loaded successfully');
    }

    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async generateCertificate(eventId, enrollmentNo) {
        if (this.isGenerating) {
            console.log('⚠️ Certificate generation already in progress');
            return;
        }

        this.isGenerating = true;
        console.log(`🎯 Starting certificate generation for event: ${eventId}, student: ${enrollmentNo}`);

        try {
            // Show loading state
            this.showLoadingState();

            // Step 1: Fetch certificate data from Python backend
            const certificateData = await this.fetchCertificateData(eventId, enrollmentNo);
            
            if (!certificateData.success) {
                throw new Error(certificateData.message);
            }

            console.log('✅ Certificate data received:', certificateData.data);

            // Step 2: Generate processed HTML
            const processedHtml = await this.generateProcessedHtml(certificateData.data);

            // Step 3: Convert HTML to PDF
            const pdfBlob = await this.convertHtmlToPdf(processedHtml, certificateData.data);

            // Step 4: Handle download and email
            await this.handleCertificateComplete(pdfBlob, certificateData.data);

            console.log('✅ Certificate generation completed successfully');

        } catch (error) {
            console.error('❌ Certificate generation failed:', error);
            this.showError(error.message);
        } finally {
            this.isGenerating = false;
            this.hideLoadingState();
        }
    }

    async fetchCertificateData(eventId, enrollmentNo) {
        console.log('📡 Fetching certificate data from backend...');
        
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

        const data = await response.json();
        console.log('📡 Backend response:', data);
        
        return data;
    }

    async generateProcessedHtml(certificateData) {
        console.log('🔄 Processing HTML template...');
        
        const { template_html, student_data, event_data, team_data } = certificateData;
        
        // Replace placeholders in HTML
        let processedHtml = template_html;
        
        const replacements = {
            '{{participant_name}}': student_data.full_name,
            '{{department_name}}': student_data.department,
            '{{event_name}}': event_data.event_name,
            '{{event_date}}': this.formatDate(event_data.event_date),
            '{{issue_date}}': this.formatDate(new Date()),
        };

        // Add team name for team events
        if (team_data && team_data.team_name) {
            replacements['{{team_name}}'] = team_data.team_name;
        }

        // Apply replacements
        for (const [placeholder, value] of Object.entries(replacements)) {
            processedHtml = processedHtml.replace(new RegExp(placeholder, 'g'), value);
        }

        console.log('✅ HTML template processed successfully');
        return processedHtml;
    }

    async convertHtmlToPdf(htmlContent, certificateData) {
        console.log('📄 Converting HTML to PDF...');

        // Create a temporary container for rendering
        const tempContainer = document.createElement('div');
        tempContainer.innerHTML = htmlContent;
        tempContainer.style.cssText = `
            position: fixed;
            top: -9999px;
            left: -9999px;
            width: 297mm;
            height: 210mm;
            background: white;
            z-index: -1;
        `;
        
        document.body.appendChild(tempContainer);

        try {
            // Convert HTML to canvas using html2canvas
            const canvas = await html2canvas(tempContainer, {
                scale: 2, // High DPI for quality
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff',
                width: 1123, // A4 width in pixels at 96 DPI
                height: 794,  // A4 height in pixels at 96 DPI
            });

            // Create PDF using jsPDF
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a4'
            });

            // Calculate dimensions
            const imgWidth = 297; // A4 landscape width in mm
            const imgHeight = 210; // A4 landscape height in mm

            // Add image to PDF
            const imgData = canvas.toDataURL('image/png');
            pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight);

            // Convert to blob
            const pdfBlob = pdf.output('blob');

            console.log('✅ PDF generated successfully:', pdfBlob.size, 'bytes');
            return pdfBlob;

        } finally {
            // Clean up temporary container
            document.body.removeChild(tempContainer);
        }
    }

    async handleCertificateComplete(pdfBlob, certificateData) {
        console.log('🎉 Handling certificate completion...');

        // Generate filename
        const fileName = this.generateFileName(certificateData);

        // Download the PDF
        this.downloadPdf(pdfBlob, fileName);

        // Send email notification (optional)
        try {
            await this.sendEmailNotification(pdfBlob, certificateData);
        } catch (error) {
            console.warn('⚠️ Email notification failed:', error.message);
            // Don't fail the whole process if email fails
        }

        // Show success message
        this.showSuccess('Certificate generated and downloaded successfully!');
    }

    downloadPdf(pdfBlob, fileName) {
        console.log('💾 Starting PDF download...');
        
        const url = URL.createObjectURL(pdfBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        a.style.display = 'none';
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // Clean up the URL object
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        
        console.log('✅ PDF download initiated');
    }

    async sendEmailNotification(pdfBlob, certificateData) {
        console.log('📧 Sending email notification...');

        // Convert blob to base64 for sending
        const pdfBase64 = await this.blobToBase64(pdfBlob);

        const response = await fetch('/client/api/send-certificate-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                event_id: certificateData.event_data.event_id,
                enrollment_no: certificateData.student_data.enrollment_no,
                pdf_base64: pdfBase64,
                file_name: this.generateFileName(certificateData)
            })
        });

        const result = await response.json();
        if (result.success) {
            console.log('✅ Email notification sent successfully');
        } else {
            throw new Error(result.message);
        }
    }

    // Utility functions
    formatDate(date) {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    generateFileName(certificateData) {
        const safeName = certificateData.student_data.full_name
            .replace(/[^a-zA-Z0-9]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
        
        const safeEvent = certificateData.event_data.event_name
            .replace(/[^a-zA-Z0-9]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');

        const timestamp = new Date().toISOString().slice(0, 10);
        
        return `Certificate_${safeName}_${safeEvent}_${timestamp}.pdf`;
    }

    blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const dataUrl = reader.result;
                const base64 = dataUrl.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    // UI feedback methods
    showLoadingState() {
        // Create or show loading overlay
        let loadingOverlay = document.getElementById('certificate-loading');
        if (!loadingOverlay) {
            loadingOverlay = document.createElement('div');
            loadingOverlay.id = 'certificate-loading';
            loadingOverlay.innerHTML = `
                <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div class="bg-white rounded-lg p-8 max-w-md mx-4">
                        <div class="flex items-center space-x-4">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Generating Certificate</h3>
                                <p class="text-sm text-gray-600">Please wait while we prepare your certificate...</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(loadingOverlay);
        }
        loadingOverlay.style.display = 'block';
    }

    hideLoadingState() {
        const loadingOverlay = document.getElementById('certificate-loading');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white transform transition-all duration-300 translate-x-full`;
        
        const bgColor = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        }[type] || 'bg-blue-500';

        notification.classList.add(bgColor);
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }
}

// Global function to trigger certificate generation
window.generateCertificate = async function(eventId, enrollmentNo) {
    if (!window.certificateGenerator) {
        window.certificateGenerator = new CertificateGenerator();
    }
    
    await window.certificateGenerator.generateCertificate(eventId, enrollmentNo);
};

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 Certificate Generator: DOM loaded');
    
    // Pre-load the certificate generator on client pages
    if (window.location.pathname.startsWith('/client')) {
        window.certificateGenerator = new CertificateGenerator();
    }
});

console.log('✅ Certificate Generator JavaScript loaded');
