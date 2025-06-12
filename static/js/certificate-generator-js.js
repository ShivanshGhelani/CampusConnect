/**
 * JavaScript-based Certificate Generator
 * Handles PDF generation client-side using jsPDF and html2canvas
 * Avoids OS dependencies and supports concurrent downloads
 */

class CertificateGeneratorJS {
    constructor() {
        this.isGenerating = false;
        this.librariesLoaded = false;
        // Libraries are now preloaded in base.html, so check if they're available
        this.checkLibrariesAvailability();
    }

    /**
     * Check if required libraries are available (preloaded in base.html)
     */
    checkLibrariesAvailability() {
        // Check immediately since libraries should be preloaded
        if (window.jsPDF && window.html2canvas) {
            this.librariesLoaded = true;
            console.log('Certificate generation libraries are available (preloaded)');
        } else {
            console.log('Libraries not yet available, will check again when needed');
            // They might still be loading, will check again in ensureLibrariesReady
        }    }

    /**
     * Wait for specified milliseconds
     */
    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Ensure libraries are ready before proceeding (simplified since libraries are preloaded)
     * @returns {Promise<void>}
     */
    async ensureLibrariesReady() {
        const maxWait = 5000; // Reduced to 5 seconds since libraries should be preloaded
        const checkInterval = 100; // Check every 100ms
        const startTime = Date.now();

        console.log('Ensuring preloaded libraries are ready...');

        // Check if libraries are already available (should be immediate)
        if (window.jsPDF && window.html2canvas) {
            console.log('Libraries already available (preloaded)');
            this.librariesLoaded = true;
            return;
        }

        // If not immediately available, wait a short time for them to finish loading
        console.log('Waiting for preloaded libraries to become available...');
        while ((!window.jsPDF || !window.html2canvas) && (Date.now() - startTime) < maxWait) {
            await this.wait(checkInterval);
        }

        // Final check
        if (!window.jsPDF || !window.html2canvas) {
            console.error('Preloaded libraries not available. Checking what failed:');
            console.error('jsPDF available:', typeof window.jsPDF !== 'undefined');
            console.error('html2canvas available:', typeof window.html2canvas !== 'undefined');
            throw new Error('Required libraries (jsPDF, html2canvas) failed to load. The libraries should be preloaded in the base template. Please refresh the page.');
        }

        console.log('Preloaded libraries are now ready');
        this.librariesLoaded = true;
    }

    /**
     * Generate certificate for a student
     * @param {string} eventId - Event ID
     * @param {string} enrollmentNo - Student enrollment number
     * @returns {Promise<Object>} Result object with success status and data
     */
    async generateCertificate(eventId, enrollmentNo) {
        if (this.isGenerating) {
            return { success: false, message: 'Certificate generation already in progress' };
        }

        this.isGenerating = true;

        try {
            // Wait for libraries to be ready (with timeout)
            console.log('Checking library availability...');
            await this.ensureLibrariesReady();

            // Double-check libraries are available
            if (!window.jsPDF || !window.html2canvas) {
                throw new Error('Required libraries failed to load. Please refresh the page and check your internet connection.');
            }

            console.log('Libraries confirmed available, proceeding with generation');

            console.log(`Starting certificate generation for student ${enrollmentNo}, event ${eventId}`);

            // Fetch certificate data from backend
            const certificateData = await this.fetchCertificateData(eventId, enrollmentNo);
            if (!certificateData.success) {
                return certificateData;
            }

            console.log('Certificate data fetched successfully:', certificateData.data);

            // Generate PDF using the certificate data
            const pdfResult = await this.generatePDFFromTemplate(certificateData.data);
            if (!pdfResult.success) {
                return pdfResult;
            }

            console.log('PDF generated successfully');

            // Send email with certificate
            await this.sendCertificateEmail(certificateData.data, pdfResult.pdfBytes);

            // Download the certificate
            this.downloadPDF(pdfResult.pdfBytes, pdfResult.filename);

            return {
                success: true,
                message: 'Certificate generated and downloaded successfully!',
                filename: pdfResult.filename
            };

        } catch (error) {
            console.error('Certificate generation error:', error);
            return {
                success: false,
                message: `Certificate generation failed: ${error.message}`
            };
        } finally {
            this.isGenerating = false;
        }
    }    /**
     * Fetch certificate data from Python backend
     * @param {string} eventId - Event ID
     * @param {string} enrollmentNo - Student enrollment number
     * @returns {Promise<Object>} Certificate data from backend
     */
    async fetchCertificateData(eventId, enrollmentNo) {
        try {
            console.log(`Fetching certificate data for event ${eventId}, student ${enrollmentNo}`);
            
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
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('Certificate data response:', result);
            return result;

        } catch (error) {
            console.error('Error fetching certificate data:', error);
            return {
                success: false,
                message: `Failed to fetch certificate data: ${error.message}`
            };
        }
    }    /**
     * Generate PDF from certificate template and data
     * @param {Object} certificateData - Certificate data from backend
     * @returns {Promise<Object>} Generated PDF result
     */
    async generatePDFFromTemplate(certificateData) {
        try {
            console.log('Starting PDF generation from template');

            // Create a temporary HTML template with replaced placeholders
            const htmlTemplate = await this.createCertificateHTML(certificateData);
            console.log('Certificate HTML template created');
            
            // Create temporary element for rendering
            const tempContainer = document.createElement('div');
            tempContainer.innerHTML = htmlTemplate;
            tempContainer.style.position = 'absolute';
            tempContainer.style.left = '-10000px';
            tempContainer.style.top = '-10000px';
            tempContainer.style.width = '800px'; // A4 width approximation
            tempContainer.style.height = '600px';
            tempContainer.style.background = 'white';
            document.body.appendChild(tempContainer);

            console.log('Temporary container created, generating canvas...');

            // Generate canvas from HTML
            const canvas = await window.html2canvas(tempContainer.firstElementChild, {
                width: 800,
                height: 600,
                scale: 2,
                useCORS: true,
                allowTaint: false,
                backgroundColor: '#ffffff',
                logging: false
            });

            console.log('Canvas generated successfully');

            // Clean up temporary element
            document.body.removeChild(tempContainer);

            // Create PDF from canvas
            const { jsPDF } = window;
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'px',
                format: [800, 600]
            });

            const imgData = canvas.toDataURL('image/png', 1.0);
            pdf.addImage(imgData, 'PNG', 0, 0, 800, 600);

            console.log('PDF created from canvas');

            // Get PDF as bytes
            const pdfBytes = pdf.output('arraybuffer');
            
            // Generate filename
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            const safeName = certificateData.participant_name.replace(/[^a-zA-Z0-9]/g, '_');
            const filename = `Certificate_${safeName}_${timestamp}.pdf`;

            console.log(`PDF generation completed: ${filename}`);

            return {
                success: true,
                pdfBytes: pdfBytes,
                filename: filename
            };

        } catch (error) {
            console.error('PDF generation error:', error);
            return {
                success: false,
                message: `PDF generation failed: ${error.message}`
            };
        }
    }    /**
     * Create HTML template with replaced placeholders
     * @param {Object} data - Certificate data
     * @returns {Promise<string>} HTML template with placeholders replaced
     */
    async createCertificateHTML(data) {
        try {
            console.log(`Fetching certificate template for event ${data.event_id}`);
            
            // Get the template HTML from backend
            const templateResponse = await fetch(`/client/api/certificate-template/${data.event_id}`);
            if (!templateResponse.ok) {
                console.warn('Failed to fetch certificate template, using fallback');
                return this.createFallbackCertificate(data);
            }
            
            let templateHTML = await templateResponse.text();
            console.log('Certificate template fetched successfully');

            // Replace placeholders based on event type
            const placeholders = {
                '{{participant_name}}': data.participant_name,
                '{{department_name}}': data.department_name,
                '{{event_name}}': data.event_name,
                '{{event_date}}': data.event_date,
                '{{issue_date}}': data.issue_date
            };

            // Add team name placeholder for team events
            if (data.team_name) {
                placeholders['{{team_name}}'] = data.team_name;
            }

            // Replace all placeholders
            for (const [placeholder, value] of Object.entries(placeholders)) {
                templateHTML = templateHTML.replace(new RegExp(placeholder, 'g'), value || '');
            }

            console.log('Placeholders replaced in template');
            return templateHTML;

        } catch (error) {
            console.error('Template creation error:', error);
            console.log('Using fallback certificate template');
            return this.createFallbackCertificate(data);
        }
    }

    /**
     * Create a simple fallback certificate HTML
     * @param {Object} data - Certificate data
     * @returns {string} Simple certificate HTML
     */
    createFallbackCertificate(data) {
        return `
        <div style="width: 800px; height: 600px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 60px; box-sizing: border-box; font-family: 'Arial', sans-serif; color: white; 
                    display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
            
            <div style="background: rgba(255,255,255,0.1); border: 3px solid white; border-radius: 20px; 
                        padding: 40px; width: 100%; max-width: 680px;">
                
                <h1 style="font-size: 48px; margin: 0 0 20px 0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                    CERTIFICATE
                </h1>
                
                <h2 style="font-size: 24px; margin: 0 0 30px 0; font-weight: normal; opacity: 0.9;">
                    OF PARTICIPATION
                </h2>
                
                <div style="margin: 30px 0; font-size: 18px; line-height: 1.6;">
                    <p style="margin: 0 0 20px 0;">This is to certify that</p>
                    
                    <h3 style="font-size: 32px; margin: 20px 0; font-weight: bold; 
                               text-decoration: underline; text-decoration-color: rgba(255,255,255,0.7);">
                        ${data.participant_name}
                    </h3>
                    
                    <p style="margin: 20px 0 10px 0;">from <strong>${data.department_name}</strong></p>
                    
                    ${data.team_name ? `<p style="margin: 10px 0;">Team: <strong>${data.team_name}</strong></p>` : ''}
                    
                    <p style="margin: 20px 0;">has successfully participated in</p>
                    
                    <h4 style="font-size: 24px; margin: 20px 0; font-weight: bold;">
                        ${data.event_name}
                    </h4>
                    
                    <p style="margin: 20px 0 30px 0;">held on <strong>${data.event_date}</strong></p>
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 40px; 
                           font-size: 14px; opacity: 0.8;">
                    <div>Issue Date: ${data.issue_date}</div>
                    <div>University Community Group</div>
                </div>
            </div>
        </div>`;
    }

    /**
     * Wait for required libraries to load
     * @returns {Promise<void>}
     */
    async waitForLibraries() {
        const maxWait = 10000; // 10 seconds
        const startTime = Date.now();

        while ((!window.jsPDF || !window.html2canvas) && (Date.now() - startTime) < maxWait) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        if (!window.jsPDF || !window.html2canvas) {
            throw new Error('Required libraries (jsPDF, html2canvas) failed to load');
        }
    }

    /**
     * Send certificate email via backend
     * @param {Object} certificateData - Certificate data
     * @param {ArrayBuffer} pdfBytes - PDF data
     * @returns {Promise<void>}
     */
    async sendCertificateEmail(certificateData, pdfBytes) {
        try {
            // Convert ArrayBuffer to base64
            const base64PDF = this.arrayBufferToBase64(pdfBytes);

            await fetch('/client/api/send-certificate-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    certificate_data: certificateData,
                    pdf_base64: base64PDF,
                    filename: `Certificate_${certificateData.participant_name.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
                })
            });

            console.log('Certificate email sent successfully');
        } catch (error) {
            console.error('Failed to send certificate email:', error);
            // Don't fail the whole process if email fails
        }
    }

    /**
     * Convert ArrayBuffer to base64
     * @param {ArrayBuffer} buffer - Array buffer to convert
     * @returns {string} Base64 string
     */
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    /**
     * Download PDF file
     * @param {ArrayBuffer} pdfBytes - PDF data
     * @param {string} filename - File name
     */
    downloadPDF(pdfBytes, filename) {
        const blob = new Blob([pdfBytes], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // Clean up the URL object
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    /**
     * Update UI during certificate generation
     * @param {HTMLElement} button - Download button element
     * @param {string} status - Current status
     */
    updateUI(button, status) {
        const downloadText = button.querySelector('#downloadText') || button;
        
        switch (status) {
            case 'generating':
                button.disabled = true;
                button.classList.remove('bg-green-600', 'hover:bg-green-700');
                button.classList.add('bg-gray-400', 'cursor-not-allowed');
                downloadText.textContent = 'Generating Certificate...';
                break;
                
            case 'success':
                downloadText.textContent = 'Certificate Downloaded!';
                this.showSuccessMessage();
                // Reset button after delay
                setTimeout(() => {
                    button.disabled = false;
                    button.classList.remove('bg-gray-400', 'cursor-not-allowed');
                    button.classList.add('bg-green-600', 'hover:bg-green-700');
                    downloadText.textContent = 'Download Certificate';
                }, 3000);
                break;
                
            case 'error':
                downloadText.textContent = 'Download Failed';
                // Reset button after delay
                setTimeout(() => {
                    button.disabled = false;
                    button.classList.remove('bg-gray-400', 'cursor-not-allowed');
                    button.classList.add('bg-green-600', 'hover:bg-green-700');
                    downloadText.textContent = 'Download Certificate';
                }, 3000);
                break;
        }
    }

    /**
     * Show success message in UI
     */
    showSuccessMessage() {
        const successDiv = document.createElement('div');
        successDiv.className = 'bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4';
        successDiv.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                    <p class="font-medium">✓ Certificate Generated Successfully!</p>
                    <p class="text-sm text-green-600">Certificate has been downloaded to your device and emailed to you.</p>
                </div>
            </div>
        `;
        
        const certificateStatusDiv = document.querySelector('.bg-gradient-to-r.from-blue-50');
        if (certificateStatusDiv) {
            certificateStatusDiv.parentNode.insertBefore(successDiv, certificateStatusDiv);
            
            // Remove success message after 5 seconds
            setTimeout(() => {
                if (successDiv.parentNode) {
                    successDiv.parentNode.removeChild(successDiv);
                }
            }, 5000);
        }
    }

    /**
     * Show error message in UI
     * @param {string} errorMessage - Error message to display
     */
    showErrorMessage(errorMessage) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4';
        errorDiv.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <div>
                    <p class="font-medium">Certificate Generation Failed</p>
                    <p class="text-sm text-red-600">${errorMessage}</p>
                </div>
            </div>
        `;
        
        const certificateStatusDiv = document.querySelector('.bg-gradient-to-r.from-blue-50');
        if (certificateStatusDiv) {
            certificateStatusDiv.parentNode.insertBefore(errorDiv, certificateStatusDiv);
            
            // Remove error message after 8 seconds
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.parentNode.removeChild(errorDiv);
                }
            }, 8000);
        }
    }
}

// Initialize the certificate generator
const certificateGenerator = new CertificateGeneratorJS();

// Export for use in other scripts
window.CertificateGeneratorJS = CertificateGeneratorJS;
window.certificateGenerator = certificateGenerator;
