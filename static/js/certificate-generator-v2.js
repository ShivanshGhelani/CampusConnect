/**
 * JavaScript Certificate Generator V2
 * Fixed version that generates proper PDF files
 * Eliminates OS dependencies for certificate generation
 */

class CertificateGeneratorV2 {
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

        console.log('✅ Certificate Generator V2: Libraries loaded successfully');
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

            // Step 2: Try multiple PDF generation methods
            let pdfBlob = null;
            let method = 'Unknown';

            try {
                // Method 1: Use improved HTML to canvas to PDF conversion
                const processedHtml = await this.generateProcessedHtml(certificateData.data);
                pdfBlob = await this.convertHtmlToPdfImproved(processedHtml, certificateData.data);
                method = 'Improved HTML to PDF';
            } catch (error) {
                console.log('Improved method failed, trying simple PDF...', error);
                
                // Method 2: Create a simple but valid PDF
                pdfBlob = await this.createSimplePdf(certificateData.data);
                method = 'Simple PDF';
            }

            // Step 3: Validate PDF
            await this.validatePdf(pdfBlob);
            console.log(`✅ PDF generated using ${method}:`, pdfBlob.size, 'bytes');

            // Step 4: Handle download and email
            await this.handleCertificateComplete(pdfBlob, certificateData.data);

            console.log('✅ Certificate generation completed successfully');

        } catch (error) {
            console.error('❌ Certificate generation failed:', error);
            this.showError(`Certificate generation failed: ${error.message}`);
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
        };        // Add team name for team events
        if (team_data && team_data.team_name) {
            replacements['{{team_name}}'] = team_data.team_name;
        }

        // Apply replacements
        for (const [placeholder, value] of Object.entries(replacements)) {
            processedHtml = processedHtml.replace(new RegExp(placeholder, 'g'), value);
        }

        // Handle team name visibility
        if (team_data && team_data.team_name) {
            processedHtml = processedHtml.replace('style="display: none;"', 'style="display: inline;"');
        } else {
            // Remove the team info section entirely if no team
            processedHtml = processedHtml.replace(/<span id="team-info"[^>]*>.*?<\/span>/g, '');
        }

        console.log('✅ HTML template processed successfully');
        return processedHtml;
    }

    async convertHtmlToPdfImproved(htmlContent, certificateData) {
        console.log('📄 Converting HTML to PDF (Improved Method)...');

        // Create a hidden iframe for proper CSS rendering
        const iframe = document.createElement('iframe');
        iframe.style.cssText = `
            position: fixed;
            top: -9999px;
            left: -9999px;
            width: 1123px;
            height: 794px;
            border: none;
            background: white;
            opacity: 0;
            pointer-events: none;
        `;
        
        document.body.appendChild(iframe);

        try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
              // Prepare full HTML document with proper styling
            const fullHtml = `
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <script src="https://cdn.tailwindcss.com"></script>
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&display=swap');
                        body { 
                            margin: 0; 
                            padding: 0; 
                            width: 1123px; 
                            height: 794px; 
                            background: white;
                            font-family: 'Space Grotesk', sans-serif;
                            overflow: hidden;
                        }
                        :root {
                            --primary-color: #7c3aed;
                            --secondary-color: #4338ca;
                            --accent-color: #8b5cf6;
                            --text-primary: #1f2937;
                            --text-secondary: #4b5563;
                            --border-color: rgba(124, 58, 237, 0.2);
                            --gradient-start: #7c3aed;
                            --gradient-end: #4338ca;
                        }
                        * { 
                            box-sizing: border-box; 
                        }
                        
                        /* Improved text handling for certificate */
                        .certificate-container {
                            word-wrap: break-word;
                            overflow-wrap: break-word;
                            hyphens: auto;
                        }
                        
                        .participant-name {
                            line-height: 1.2;
                            word-break: break-word;
                            hyphens: none;
                        }
                        
                        .event-title {
                            line-height: 1.3;
                            word-wrap: break-word;
                            overflow-wrap: break-word;
                            hyphens: auto;
                        }
                        
                        .department-info {
                            line-height: 1.4;
                            word-wrap: break-word;
                        }
                        
                        .team-info {
                            line-height: 1.4;
                            word-wrap: break-word;
                        }
                        
                        /* Ensure text doesn't overflow certificate boundaries */
                        .text-content {
                            max-width: 90%;
                            margin: 0 auto;
                        }
                        
                        /* Responsive font sizing for long content */
                        .auto-resize-text {
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            text-align: center;
                        }
                        
                        /* Force text to fit within bounds */
                        .fit-text {
                            max-width: 100%;
                            overflow: hidden;
                            text-overflow: ellipsis;
                            white-space: nowrap;
                        }
                        
                        /* Multi-line text handling */
                        .multi-line-text {
                            white-space: normal;
                            word-wrap: break-word;
                            overflow-wrap: break-word;
                        }
                    </style>
                </head>
                <body>
                    <div class="certificate-container">
                        ${htmlContent.replace(/^<!DOCTYPE html>[\s\S]*?<body[^>]*>/i, '').replace(/<\/body>[\s\S]*$/i, '')}
                    </div>
                </body>
                </html>
            `;
            
            // Load HTML into iframe
            iframeDoc.open();
            iframeDoc.write(fullHtml);
            iframeDoc.close();

            // Wait for everything to load
            await this.waitForIframeLoad(iframe);

            // Capture with html2canvas
            const canvas = await html2canvas(iframeDoc.body, {
                scale: 2,
                useCORS: true,
                allowTaint: false,
                backgroundColor: '#ffffff',
                width: 1123,
                height: 794,
                scrollX: 0,
                scrollY: 0,
                logging: false,
            });

            // Create PDF with proper settings
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a4',
                compress: true
            });

            // Convert canvas to high quality JPEG
            const imgData = canvas.toDataURL('image/jpeg', 0.92);
            
            // Add image to PDF with proper dimensions
            pdf.addImage(imgData, 'JPEG', 0, 0, 297, 210, '', 'FAST');

            // Return as blob
            const pdfBlob = pdf.output('blob');
            
            if (pdfBlob.size < 1000) {
                throw new Error('Generated PDF is too small');
            }

            return pdfBlob;

        } finally {
            // Clean up iframe
            document.body.removeChild(iframe);
        }
    }

    async waitForIframeLoad(iframe) {
        return new Promise(resolve => {
            const checkLoad = () => {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                if (iframeDoc.readyState === 'complete') {
                    // Extra time for fonts and images
                    setTimeout(resolve, 2000);
                } else {
                    setTimeout(checkLoad, 100);
                }
            };
            checkLoad();
        });
    }    async createSimplePdf(certificateData) {
        console.log('📄 Creating simple PDF as fallback...');
        
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF({
            orientation: 'landscape',
            unit: 'mm',
            format: 'a4',
            compress: true
        });

        const { student_data, event_data, team_data } = certificateData;

        // Background
        pdf.setFillColor(248, 250, 252); // Light gray background
        pdf.rect(0, 0, 297, 210, 'F');

        // Border
        pdf.setDrawColor(124, 58, 237);
        pdf.setLineWidth(2);
        pdf.rect(10, 10, 277, 190);

        // Inner border
        pdf.setLineWidth(0.5);
        pdf.rect(15, 15, 267, 180);

        // Title
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(28);
        pdf.setTextColor(124, 58, 237);
        pdf.text('Certificate of Completion', 148.5, 40, { align: 'center' });

        // Decorative line
        pdf.setDrawColor(139, 92, 246);
        pdf.setLineWidth(1);
        pdf.line(50, 50, 247, 50);

        // Participant name section
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(16);
        pdf.setTextColor(75, 85, 99);
        pdf.text('This is to certify that', 148.5, 70, { align: 'center' });
        
        // Student name with proper text fitting
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(24);
        pdf.setTextColor(124, 58, 237);
        
        const studentName = student_data.full_name;
        const maxNameWidth = 200; // mm
        const nameLines = this.wrapText(pdf, studentName, maxNameWidth, 24);
        
        let nameYPos = 90;
        nameLines.forEach((line, index) => {
            pdf.text(line, 148.5, nameYPos + (index * 8), { align: 'center' });
        });
        
        // Adjust subsequent positions based on name lines
        const nameHeight = nameLines.length * 8;
        let currentY = 90 + nameHeight + 10;
        
        // Event details
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(16);
        pdf.setTextColor(75, 85, 99);
        pdf.text('has successfully completed', 148.5, currentY, { align: 'center' });
        currentY += 20;
        
        // Event name with smart text wrapping
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(67, 56, 202);
        
        const eventName = event_data.event_name;
        const maxEventWidth = 220; // mm
        let eventFontSize = 20;
        
        // Reduce font size if text is too long
        while (eventFontSize > 12) {
            pdf.setFontSize(eventFontSize);
            const eventLines = this.wrapText(pdf, eventName, maxEventWidth, eventFontSize);
            
            if (eventLines.length <= 2) {
                // Text fits in 2 lines or less
                eventLines.forEach((line, index) => {
                    pdf.text(line, 148.5, currentY + (index * (eventFontSize * 0.35)), { align: 'center' });
                });
                currentY += eventLines.length * (eventFontSize * 0.35) + 10;
                break;
            }
            
            eventFontSize -= 2;
        }
        
        // Department with text wrapping
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(14);
        pdf.setTextColor(75, 85, 99);
        
        const deptText = `Department: ${student_data.department}`;
        const deptLines = this.wrapText(pdf, deptText, 180, 14);
        
        deptLines.forEach((line, index) => {
            pdf.text(line, 148.5, currentY + (index * 6), { align: 'center' });
        });
        currentY += deptLines.length * 6 + 5;
        
        // Team name (if applicable) with text wrapping
        if (team_data && team_data.team_name) {
            const teamText = `Team: ${team_data.team_name}`;
            const teamLines = this.wrapText(pdf, teamText, 180, 14);
            
            teamLines.forEach((line, index) => {
                pdf.text(line, 148.5, currentY + (index * 6), { align: 'center' });
            });
            currentY += teamLines.length * 6 + 10;
        }
        
        // Dates - positioned at bottom
        pdf.setFontSize(12);
        pdf.setTextColor(107, 114, 128);
        const bottomY = 185;
        pdf.text(`Event Date: ${this.formatDate(event_data.event_date)}`, 75, bottomY);
        pdf.text(`Issue Date: ${this.formatDate(new Date())}`, 222, bottomY, { align: 'right' });

        // Certificate ID (for authenticity)
        const certId = `CERT-${Date.now().toString(36).toUpperCase()}`;
        pdf.setFontSize(8);
        pdf.text(`Certificate ID: ${certId}`, 148.5, 195, { align: 'center' });

        return pdf.output('blob');
    }

    // Helper method for intelligent text wrapping
    wrapText(pdf, text, maxWidth, fontSize) {
        pdf.setFontSize(fontSize);
        const words = text.split(' ');
        const lines = [];
        let currentLine = '';
        
        for (let i = 0; i < words.length; i++) {
            const testLine = currentLine + (currentLine ? ' ' : '') + words[i];
            const textWidth = pdf.getTextWidth(testLine);
            
            if (textWidth <= maxWidth) {
                currentLine = testLine;
            } else {
                if (currentLine) {
                    lines.push(currentLine);
                    currentLine = words[i];
                } else {
                    // Single word is too long, split it
                    lines.push(words[i]);
                }
            }
        }
        
        if (currentLine) {
            lines.push(currentLine);
        }
        
        return lines;
    }

    async validatePdf(pdfBlob) {
        console.log('🔍 Validating PDF...');
        
        if (!pdfBlob || pdfBlob.size < 1000) {
            throw new Error('Generated PDF is too small or empty');
        }

        // Check PDF header
        const arrayBuffer = await pdfBlob.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);
        
        const pdfHeader = Array.from(uint8Array.slice(0, 5))
            .map(byte => String.fromCharCode(byte))
            .join('');
            
        if (!pdfHeader.startsWith('%PDF-')) {
            throw new Error('Generated file is not a valid PDF');
        }

        console.log('✅ PDF validation passed');
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

        try {
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
        } catch (error) {
            console.warn('⚠️ Email sending failed:', error);
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
        let loadingOverlay = document.getElementById('certificate-loading-v2');
        if (!loadingOverlay) {
            loadingOverlay = document.createElement('div');
            loadingOverlay.id = 'certificate-loading-v2';
            loadingOverlay.innerHTML = `
                <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div class="bg-white rounded-lg p-8 max-w-md mx-4">
                        <div class="flex items-center space-x-4">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Generating Certificate</h3>
                                <p class="text-sm text-gray-600">Creating your professional certificate...</p>
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
        const loadingOverlay = document.getElementById('certificate-loading-v2');
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

// Global function to trigger certificate generation V2
window.generateCertificateV2 = async function(eventId, enrollmentNo) {
    if (!window.certificateGeneratorV2) {
        window.certificateGeneratorV2 = new CertificateGeneratorV2();
    }
    
    await window.certificateGeneratorV2.generateCertificate(eventId, enrollmentNo);
};

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 Certificate Generator V2: DOM loaded');
    
    // Pre-load the certificate generator on client pages
    if (window.location.pathname.startsWith('/client')) {
        window.certificateGeneratorV2 = new CertificateGeneratorV2();
    }
});

console.log('✅ Certificate Generator V2 JavaScript loaded');
