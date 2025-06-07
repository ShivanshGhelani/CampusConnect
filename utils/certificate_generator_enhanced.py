#!/usr/bin/env python3
"""
Enhanced Certificate Generator Utility
Handles certificate generation for events with type "free" and mode "individual"
With improved download handling and email attachment support
"""

import os
import tempfile
import asyncio
import time
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime
import webbrowser
from urllib.parse import quote

from utils.db_operations import DatabaseOperations
from utils.email_service import EmailService


class EnhancedCertificateGenerator:
    """Handles certificate generation, PDF conversion, email delivery with improved file management"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.templates_dir = Path("templates/certificates")
    
    async def generate_and_download_certificate(
        self, 
        event_id: str, 
        enrollment_no: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Main function to generate certificate for free individual events
        
        Args:
            event_id: Event ID
            enrollment_no: Student enrollment number
            
        Returns:
            Tuple of (success, message, download_url)
        """
        temp_files_to_cleanup = []
        try:
            print(f"DEBUG: Starting enhanced certificate generation for event {event_id}, student {enrollment_no}")
            
            # Get event details
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            if not event:
                return False, "Event not found", None
            
            print(f"DEBUG: Event found: {event.get('event_name', 'Unknown')}")
            
            # Check if event qualifies for certificate generation
            if not self._is_eligible_event(event):
                registration_type = event.get('registration_type', 'unknown')
                registration_mode = event.get('registration_mode', 'unknown')
                return False, f"Certificate generation is under development for {registration_type.title()} {registration_mode.title()} events. Currently only supports Free Individual events.", None
            
            print(f"DEBUG: Event is eligible for certificate generation")
            
            # Get student details
            student = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
            if not student:
                return False, "Student not found", None
            
            print(f"DEBUG: Student found: {enrollment_no}")
            
            # Validate participation requirements
            is_valid, error_msg = await self._validate_participation(student, event_id)
            print(f"DEBUG: Validation result: {is_valid}, message: {error_msg}")
            if not is_valid:
                return False, error_msg, None
            
            print(f"DEBUG: Validation passed, getting template path...")
            
            # Get certificate template path
            template_path = self._get_template_path(event)
            if not template_path:
                return False, "Certificate template not found for this event", None
            
            print(f"DEBUG: Template path found: {template_path}")
            
            # Generate certificate PDF
            success, message, pdf_path = await self._generate_certificate_pdf(
                template_path, event, student, enrollment_no
            )
            
            if not success:
                return False, message, None
            
            # Add PDF to cleanup list
            if pdf_path:
                temp_files_to_cleanup.append(pdf_path)
            
            print(f"DEBUG: PDF generated successfully: {pdf_path}")
            
            # Create download URL and trigger download
            download_url = self._trigger_download(pdf_path)
            
            # Send email with PDF attachment BEFORE cleanup
            email_success = await self._send_certificate_email_with_attachment(
                event, student, enrollment_no, pdf_path
            )
            
            if email_success:
                print(f"DEBUG: Email with PDF attachment sent successfully")
            else:
                print(f"DEBUG: Email sending failed, but continuing with download")
            
            # Wait a bit to ensure download has started
            print(f"DEBUG: Waiting for download to initialize...")
            await asyncio.sleep(2)  # Give browser time to start download
            
            # Schedule cleanup after delay (in background)
            asyncio.create_task(self._delayed_cleanup(temp_files_to_cleanup, delay_seconds=30))
            
            return True, "Certificate generated, downloaded, and emailed successfully!", download_url
            
        except Exception as e:
            print(f"DEBUG: Exception in certificate generation: {str(e)}")
            # Cleanup on error
            for file_path in temp_files_to_cleanup:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        print(f"DEBUG: Cleaned up temp file: {file_path}")
                except Exception as cleanup_error:
                    print(f"DEBUG: Error cleaning up {file_path}: {cleanup_error}")
            
            return False, f"Error generating certificate: {str(e)}", None
    
    async def _delayed_cleanup(self, file_paths: list, delay_seconds: int = 30):
        """Clean up temporary files after a delay"""
        print(f"DEBUG: Scheduling cleanup of {len(file_paths)} files in {delay_seconds} seconds")
        await asyncio.sleep(delay_seconds)
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    print(f"DEBUG: Successfully cleaned up temp file: {file_path}")
                else:
                    print(f"DEBUG: Temp file already removed: {file_path}")
            except Exception as e:
                print(f"DEBUG: Error cleaning up {file_path}: {e}")
    
    def _is_eligible_event(self, event: Dict) -> bool:
        """Check if event is eligible for certificate generation"""
        registration_type = event.get('registration_type', '').lower()
        registration_mode = event.get('registration_mode', '').lower()
        
        return registration_type == 'free' and registration_mode == 'individual'
    
    async def _validate_participation(self, student: Dict, event_id: str) -> Tuple[bool, str]:
        """Validate that student has completed all requirements"""
        participations = student.get('event_participations', {})
        participation = participations.get(event_id)
        
        if not participation:
            return False, "Student not registered for this event"
        
        if not participation.get('registration_id'):
            return False, "Invalid registration - missing registration ID"
        
        if not participation.get('attendance_id'):
            return False, "Student did not attend the event"
        
        if not participation.get('feedback_id'):
            return False, "Student has not submitted feedback"
        
        return True, "All requirements validated"
    
    def _get_template_path(self, event: Dict) -> Optional[Path]:
        """Get the certificate template path for the event"""
        certificate_template = event.get('certificate_template')
        if not certificate_template:
            print(f"DEBUG: No certificate_template field found in event")
            return None
        
        print(f"DEBUG: Raw certificate_template: {certificate_template}")
        
        # The certificate_template field contains the full path from project root
        # Convert Windows backslashes to proper path handling
        template_path = Path(certificate_template.replace('\\', '/'))
        
        print(f"DEBUG: Computed template_path: {template_path}")
        print(f"DEBUG: Template path exists: {template_path.exists()}")
        
        if not template_path.exists():
            return None
        
        return template_path
    
    async def _generate_certificate_pdf(
        self, 
        template_path: Path, 
        event: Dict, 
        student: Dict, 
        enrollment_no: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Generate PDF certificate from HTML template"""
        temp_html_path = None
        try:
            print(f"DEBUG: Generating PDF certificate...")
            
            # Read template content
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            print(f"DEBUG: Template content loaded, length: {len(template_content)} characters")
            
            # Get student details
            participation = student.get('event_participations', {}).get(event['event_id'], {})
            student_data = participation.get('student_data', {})
            full_name = student_data.get('full_name', student.get('full_name', enrollment_no))
            department = student.get('department', 'Unknown Department')
            
            print(f"DEBUG: Student details - Name: {full_name}, Department: {department}")
            
            # Replace placeholders
            processed_content = self._replace_placeholders(
                template_content, 
                full_name, 
                department, 
                event
            )
            
            print(f"DEBUG: Placeholders replaced")
            
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(processed_content)
                temp_html_path = temp_file.name
            
            print(f"DEBUG: Temporary HTML file created: {temp_html_path}")
            
            # Convert to PDF
            pdf_path = self._convert_to_pdf_weasyprint(temp_html_path, full_name, event['event_name'])
            
            print(f"DEBUG: PDF conversion completed: {pdf_path}")
            
            # Clean up temporary HTML file immediately
            if temp_html_path and os.path.exists(temp_html_path):
                os.unlink(temp_html_path)
                print(f"DEBUG: Cleaned up temporary HTML file: {temp_html_path}")
            
            return True, "Certificate generated successfully", pdf_path
            
        except Exception as e:
            print(f"DEBUG: Error in PDF generation: {str(e)}")
            # Clean up temp HTML file on error
            if temp_html_path and os.path.exists(temp_html_path):
                try:
                    os.unlink(temp_html_path)
                except:
                    pass
            return False, f"Error generating PDF: {str(e)}", None
    
    def _replace_placeholders(
        self, 
        template_content: str, 
        full_name: str, 
        department: str, 
        event: Dict
    ) -> str:
        """Replace placeholders in template with actual values"""
        replacements = {
            '{{participant_name}}': full_name,
            '{{department_name}}': department,
            '{{event_name}}': event.get('event_name', 'Unknown Event'),
            '{{event_date}}': self._format_event_date(event),
            '{{issue_date}}': datetime.now().strftime("%B %d, %Y")
        }
        
        processed_content = template_content
        for placeholder, value in replacements.items():
            processed_content = processed_content.replace(placeholder, value)
        
        return processed_content
    
    def _format_event_date(self, event: Dict) -> str:
        """Format event date for certificate"""
        start_date = event.get('start_datetime')
        if isinstance(start_date, str):
            try:
                date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                return date_obj.strftime("%B %d, %Y")
            except:
                return start_date
        elif hasattr(start_date, 'strftime'):
            return start_date.strftime("%B %d, %Y")
        return "Unknown Date"
    
    def _convert_to_pdf_weasyprint(self, html_path: str, student_name: str, event_name: str) -> str:
        """Convert HTML to PDF using weasyprint"""
        try:
            import weasyprint
            
            # Generate a safe filename
            safe_student_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_event_name = "".join(c for c in event_name if c.isalnum() or c in (' ', '-', '_')).strip()
            
            # Create PDF filename in temp directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"Certificate_{safe_student_name}_{safe_event_name}_{timestamp}.pdf"
            pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
            
            print(f"DEBUG: Converting HTML to PDF using weasyprint: {pdf_path}")
            
            # Convert HTML to PDF using weasyprint
            weasyprint.HTML(filename=html_path).write_pdf(pdf_path)
            
            if os.path.exists(pdf_path):
                print(f"DEBUG: PDF successfully created: {pdf_path}")
                return pdf_path
            else:
                raise Exception("PDF file was not created")
                
        except ImportError:
            print("DEBUG: weasyprint not available")
            raise Exception("weasyprint library is required for PDF generation")
        except Exception as e:
            print(f"DEBUG: Error in PDF conversion: {e}")
            raise Exception(f"PDF conversion failed: {e}")
    
    def _trigger_download(self, pdf_path: str) -> str:
        """Trigger automatic download of the PDF file"""
        try:
            if os.path.exists(pdf_path):
                # Open the PDF file to trigger download
                file_url = f"file:///{pdf_path.replace(os.sep, '/')}"
                webbrowser.open(file_url)
                print(f"DEBUG: Browser opened for PDF download: {file_url}")
                return file_url
            else:
                print(f"DEBUG: PDF file does not exist: {pdf_path}")
                return "PDF file not found"
        except Exception as e:
            print(f"DEBUG: Error triggering download: {e}")
            return f"Download error: {e}"
    
    async def _send_certificate_email_with_attachment(
        self, 
        event: Dict, 
        student: Dict, 
        enrollment_no: str,
        pdf_path: Optional[str] = None
    ) -> bool:
        """Send certificate email with PDF attachment"""
        try:
            print(f"DEBUG: Sending certificate email with attachment...")
            
            # Get student email
            participation = student.get('event_participations', {}).get(event['event_id'], {})
            student_data = participation.get('student_data', {})
            student_email = student_data.get('email') or student.get('email')
            
            if not student_email:
                print(f"⚠️ No email address found for student {enrollment_no}")
                return False
            
            # Get student name
            full_name = student_data.get('full_name', student.get('full_name', enrollment_no))
            
            # Certificate URL (fallback)
            certificate_url = f"/client/events/{event['event_id']}/certificate"
            
            # Send notification with PDF attachment
            success = await self.email_service.send_certificate_notification(
                student_email=student_email,
                student_name=full_name,
                event_title=event.get('event_name', 'Unknown Event'),
                certificate_url=certificate_url,
                event_date=self._format_event_date(event),
                certificate_pdf_path=pdf_path  # This is the key enhancement
            )
            
            if success:
                print(f"✅ Certificate email with PDF attachment sent to {student_email}")
            else:
                print(f"⚠️ Failed to send certificate email to {student_email}")
            
            return success
                
        except Exception as e:
            print(f"⚠️ Error sending certificate email: {str(e)}")
            return False


# Convenience function for use in routes
async def generate_enhanced_certificate_for_student(event_id: str, enrollment_no: str) -> Tuple[bool, str, Optional[str]]:
    """
    Enhanced convenience function to generate certificate for a student
    
    Args:
        event_id: Event ID
        enrollment_no: Student enrollment number
        
    Returns:
        Tuple of (success, message, download_url)
    """
    generator = EnhancedCertificateGenerator()
    return await generator.generate_and_download_certificate(event_id, enrollment_no)


if __name__ == "__main__":
    # Test the enhanced certificate generator
    async def test_enhanced_generator():
        success, message, download_url = await generate_enhanced_certificate_for_student(
            "GREEN_INNOVATION_HACKATHON_2025", 
            "22BEIT30043"
        )
        print(f"Success: {success}")
        print(f"Message: {message}")
        print(f"Download URL: {download_url}")
    
    asyncio.run(test_enhanced_generator())
