/**
 * Enhanced Certificate Generator - JavaScript Integration V2 FINAL
 * Uses JavaScript-based PDF generation with preloaded libraries
 * Eliminates OS dependencies and timeout errors for certificate generation
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
        // Generate certificate using JavaScript V2
        await certificateGeneratorJS.generateCertificate(eventId, enrollmentNo);

    } catch (error) {
        console.error('Certificate download error:', error);
        certificateGeneratorJS.showError(`Unexpected error: ${error.message}`);
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
