#!/usr/bin/env python3
"""
Comprehensive test for the JavaScript Certificate Generator V2
This creates a simple HTML test page to validate PDF generation
"""

import os
from pathlib import Path

def create_test_page():
    """Create a test HTML page for the V2 certificate generator"""
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Certificate Generator V2 Test</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen py-8">
    <div class="container mx-auto px-4 max-w-2xl">
        <div class="bg-white rounded-lg shadow-lg p-8">
            <h1 class="text-3xl font-bold text-center mb-8 text-purple-600">
                Certificate Generator V2 Test
            </h1>
            
            <div class="mb-6">
                <h2 class="text-xl font-semibold mb-4">Test Configuration</h2>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div><strong>Event ID:</strong> DIGITAL_LITERACY_WORKSHOP_2025</div>
                    <div><strong>Student:</strong> 22BEIT30043</div>
                    <div><strong>Student Name:</strong> Shivansh Ghelani</div>
                    <div><strong>Department:</strong> Information Technology</div>
                </div>
            </div>

            <div class="text-center mb-6">
                <button id="testCertificateBtn" 
                        class="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-lg transition-colors duration-200">
                    <span id="testBtnText">Generate Test Certificate</span>
                </button>
            </div>

            <div id="statusDiv" class="hidden">
                <h3 class="text-lg font-semibold mb-2">Test Status:</h3>
                <div id="statusContent" class="bg-gray-50 border rounded p-4 text-sm font-mono">
                    <!-- Status updates will appear here -->
                </div>
            </div>

            <div class="mt-8 text-center">
                <p class="text-gray-600 text-sm">
                    This test page validates the V2 certificate generator functionality
                </p>
            </div>
        </div>
    </div>

    <!-- Load the V2 Certificate Generator -->
    <script src="/static/js/certificate-generator-v2.js"></script>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const testBtn = document.getElementById('testCertificateBtn');
            const testBtnText = document.getElementById('testBtnText');
            const statusDiv = document.getElementById('statusDiv');
            const statusContent = document.getElementById('statusContent');
            
            function logStatus(message, type = 'info') {
                const timestamp = new Date().toLocaleTimeString();
                const color = {
                    'info': 'text-blue-600',
                    'success': 'text-green-600',
                    'error': 'text-red-600',
                    'warning': 'text-yellow-600'
                }[type] || 'text-gray-600';
                
                statusContent.innerHTML += `<div class="${color}">[${timestamp}] ${message}</div>`;
                statusDiv.classList.remove('hidden');
                statusContent.scrollTop = statusContent.scrollHeight;
            }
            
            testBtn.addEventListener('click', async function() {
                // Reset status
                statusContent.innerHTML = '';
                logStatus('Starting Certificate Generation Test...', 'info');
                
                // Disable button
                testBtn.disabled = true;
                testBtn.classList.remove('bg-purple-600', 'hover:bg-purple-700');
                testBtn.classList.add('bg-gray-400', 'cursor-not-allowed');
                testBtnText.textContent = 'Testing...';
                
                try {
                    // Test data
                    const eventId = 'DIGITAL_LITERACY_WORKSHOP_2025';
                    const enrollmentNo = '22BEIT30043';
                    
                    logStatus(`Testing with Event: ${eventId}`, 'info');
                    logStatus(`Testing with Student: ${enrollmentNo}`, 'info');
                    
                    // Test API endpoint
                    logStatus('Testing certificate data API...', 'info');
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
                    
                    if (!data.success) {
                        throw new Error(data.message);
                    }
                    
                    logStatus('✅ API endpoint working correctly', 'success');
                    logStatus(`Student: ${data.data.student_data.full_name}`, 'info');
                    logStatus(`Event: ${data.data.event_data.event_name}`, 'info');
                    logStatus(`Template size: ${data.data.template_html.length} chars`, 'info');
                    
                    // Test V2 certificate generation
                    logStatus('Testing V2 certificate generation...', 'info');
                    await generateCertificateV2(eventId, enrollmentNo);
                    
                    logStatus('✅ Certificate generation completed successfully!', 'success');
                    testBtnText.textContent = 'Test Completed ✅';
                    
                } catch (error) {
                    logStatus(`❌ Test failed: ${error.message}`, 'error');
                    testBtnText.textContent = 'Test Failed ❌';
                    console.error('Certificate test error:', error);
                } finally {
                    // Re-enable button after delay
                    setTimeout(() => {
                        testBtn.disabled = false;
                        testBtn.classList.remove('bg-gray-400', 'cursor-not-allowed');
                        testBtn.classList.add('bg-purple-600', 'hover:bg-purple-700');
                        testBtnText.textContent = 'Generate Test Certificate';
                    }, 5000);
                }
            });
        });
    </script>
</body>
</html>
"""
    
    # Save the test page
    test_path = Path("temp/certificate_v2_test.html")
    test_path.parent.mkdir(exist_ok=True)
    
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Test page created: {test_path}")
    print(f"🌐 You can access it at: http://localhost:8000/temp/certificate_v2_test.html")
    print("📋 This test page will:")
    print("  1. Test the certificate data API endpoint")
    print("  2. Test the V2 certificate generator")
    print("  3. Show detailed status logs")
    print("  4. Generate and download a test certificate")

if __name__ == "__main__":
    create_test_page()
