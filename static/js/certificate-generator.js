/**
 * Enhanced Certificate Generator - JavaScript Integration
 * Uses JavaScript-based PDF generation to avoid OS dependencies
 * Supports concurrent downloads and thread-safe operations
 */

// Global certificate generator instance
let certificateGeneratorJS = null;

/**
 * Initialize the JavaScript certificate generator
 */
function initCertificateGenerator() {
    // Wait for libraries to be available first, then initialize
    const waitForLibrariesAndInit = () => {
        if (window.jsPDF && window.html2canvas) {
            // Libraries are preloaded and available
            if (!window.CertificateGeneratorJS) {
                const script = document.createElement('script');
                script.src = '/static/js/certificate-generator-js.js';
                script.onload = () => {
                    certificateGeneratorJS = new window.CertificateGeneratorJS();
                    console.log('Certificate generator initialized with preloaded libraries');
                };
                document.head.appendChild(script);
            } else {
                certificateGeneratorJS = new window.CertificateGeneratorJS();
                console.log('Certificate generator initialized with preloaded libraries');
            }
        } else {
            // Libraries not yet loaded, wait a bit more
            console.log('Waiting for preloaded libraries...');
            setTimeout(waitForLibrariesAndInit, 100);
        }
    };
    
    waitForLibrariesAndInit();
}

/**
 * Handle certificate download using JavaScript PDF generation
 * @param {string} eventId - Event ID
 * @param {string} enrollmentNo - Student enrollment number (optional, will be fetched from session)
 */
async function downloadCertificateJS(eventId, enrollmentNo = null) {
    const downloadBtn = document.getElementById('downloadCertificateBtn');
    const downloadText = document.getElementById('downloadText');
    
    if (!downloadBtn || !certificateGeneratorJS) {
        console.error('Certificate generator not initialized or button not found');
        return;
    }

    // Prevent multiple simultaneous downloads
    if (certificateGeneratorJS.isGenerating) {
        console.log('Certificate generation already in progress');
        return;
    }

    try {
        // Update UI to show generating state
        certificateGeneratorJS.updateUI(downloadBtn, 'generating');

        // Generate certificate using JavaScript
        const result = await certificateGeneratorJS.generateCertificate(eventId, enrollmentNo);

        if (result.success) {
            // Update UI to show success
            certificateGeneratorJS.updateUI(downloadBtn, 'success');
            console.log(`Certificate generated successfully: ${result.filename}`);
        } else {
            // Update UI to show error
            certificateGeneratorJS.updateUI(downloadBtn, 'error');
            certificateGeneratorJS.showErrorMessage(result.message);
            console.error('Certificate generation failed:', result.message);
        }

    } catch (error) {
        console.error('Certificate download error:', error);
        certificateGeneratorJS.updateUI(downloadBtn, 'error');
        certificateGeneratorJS.showErrorMessage(`Unexpected error: ${error.message}`);
    }
}

/**
 * Handle certificate download click event
 */
function handleCertificateDownload() {
    // Get event ID from the page (assuming it's available in a data attribute or global variable)
    const eventId = document.querySelector('[data-event-id]')?.dataset.eventId || 
                   window.currentEventId || 
                   new URLSearchParams(window.location.search).get('event_id');

    if (!eventId) {
        console.error('Event ID not found');
        return;
    }

    downloadCertificateJS(eventId);
}

/**
 * Initialize certificate download functionality when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the certificate generator
    initCertificateGenerator();

    // Set up download button event listener
    const downloadBtn = document.getElementById('downloadCertificateBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', handleCertificateDownload);
        console.log('Certificate download button event listener attached');
    }
});

// Export functions for global access
window.downloadCertificateJS = downloadCertificateJS;
window.handleCertificateDownload = handleCertificateDownload;