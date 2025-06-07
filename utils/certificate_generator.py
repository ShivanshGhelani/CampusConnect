#!/usr/bin/env python3
"""
Certificate Generator Utility
Handles certificate generation for events with type "free" and mode "individual"
"""

import os
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime
import webbrowser
from urllib.parse import quote

from utils.db_operations import DatabaseOperations
from utils.email_service import EmailService


class CertificateGenerator:
    """Handles certificate generation, PDF conversion, and email delivery"""
    
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
        try:
            print(f"DEBUG: Starting certificate generation for event {event_id}, student {enrollment_no}")
            
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
            
            # Generate certificate
            success, message, pdf_path = await self._generate_certificate_pdf(
                template_path, event, student, enrollment_no
            )
            
            if not success:
                return False, message, None
            
            # Create download URL (trigger download)
            download_url = self._trigger_download(pdf_path)
            
            # Send email notification
            await self._send_certificate_email(event, student, enrollment_no)
            
            return True, "Certificate generated and downloaded successfully!", download_url
            
        except Exception as e:
            print(f"DEBUG: Exception in certificate generation: {str(e)}")
            return False, f"Error generating certificate: {str(e)}", None
    
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
            pdf_path = self._convert_to_pdf_browser(temp_html_path, full_name, event['event_name'])
            
            print(f"DEBUG: PDF conversion completed: {pdf_path}")
            
            # Clean up temporary HTML file
            os.unlink(temp_html_path)
            
            return True, "Certificate generated successfully", pdf_path
            
        except Exception as e:
            print(f"DEBUG: Error in PDF generation: {str(e)}")
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
        start_date = event.get('start_datetime')  # Updated to use correct field name
        if isinstance(start_date, str):
            try:
                date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                return date_obj.strftime("%B %d, %Y")
            except:
                return start_date
        elif hasattr(start_date, 'strftime'):
            return start_date.strftime("%B %d, %Y")
        return "Unknown Date"
    
    def _convert_to_pdf_browser(self, html_path: str, student_name: str, event_name: str) -> str:
        """Convert HTML to PDF using browser or weasyprint if available"""
        try:
            # Try to use weasyprint for better PDF generation
            try:
                import weasyprint
                
                # Generate a safe filename
                safe_student_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_event_name = "".join(c for c in event_name if c.isalnum() or c in (' ', '-', '_')).strip()
                
                # Create PDF filename in temp directory
                pdf_filename = f"Certificate_{safe_student_name}_{safe_event_name}.pdf"
                pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
                
                print(f"DEBUG: Converting HTML to PDF using weasyprint: {pdf_path}")
                
                # Convert HTML to PDF using weasyprint
                weasyprint.HTML(filename=html_path).write_pdf(pdf_path)
                
                # Open the PDF file to trigger download
                if os.path.exists(pdf_path):
                    webbrowser.open(f"file:///{pdf_path.replace(os.sep, '/')}")
                    return pdf_path
                
            except ImportError:
                print("DEBUG: weasyprint not available, using browser fallback")
                # Fallback to browser-based printing
                pass
                
        except Exception as e:
            print(f"DEBUG: Error in PDF conversion: {e}")
        
        # Fallback: Browser-based printing
        safe_student_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_event_name = "".join(c for c in event_name if c.isalnum() or c in (' ', '-', '_')).strip()
        
        filename = f"Certificate_{safe_student_name}_{safe_event_name}.pdf"
        
        # Open HTML file in browser for printing
        file_url = f"file:///{html_path.replace(os.sep, '/')}"
        webbrowser.open(file_url)
        
        return filename
    
    def _trigger_download(self, pdf_path: str) -> str:
        """Trigger automatic download (simplified for browser-based PDF)"""
        # In a real implementation, this would trigger a file download
        # For now, we return a message about the browser print dialog
        return f"Browser opened for printing. Save as: {pdf_path}"
    
    async def _send_certificate_email(self, event: Dict, student: Dict, enrollment_no: str):
        """Send certificate notification email to student"""
        try:
            print(f"DEBUG: Sending certificate email notification...")
            
            # Get student email
            participation = student.get('event_participations', {}).get(event['event_id'], {})
            student_data = participation.get('student_data', {})
            student_email = student_data.get('email') or student.get('email')
            
            if not student_email:
                print(f"⚠️ No email address found for student {enrollment_no}")
                return
            
            # Get student name
            full_name = student_data.get('full_name', student.get('full_name', enrollment_no))
            
            # Certificate URL
            certificate_url = f"/client/events/{event['event_id']}/certificate"
            
            # Send notification
            success = await self.email_service.send_certificate_notification(
                student_email=student_email,
                student_name=full_name,
                event_title=event.get('event_name', 'Unknown Event'),
                certificate_url=certificate_url,
                event_date=self._format_event_date(event)
            )
            
            if success:
                print(f"✅ Certificate notification email sent to {student_email}")
            else:
                print(f"⚠️ Failed to send certificate notification email to {student_email}")
                
        except Exception as e:
            print(f"⚠️ Error sending certificate email: {str(e)}")


# Convenience function for use in routes
async def generate_certificate_for_student(event_id: str, enrollment_no: str) -> Tuple[bool, str, Optional[str]]:
    """
    Convenience function to generate certificate for a student
    
    Args:
        event_id: Event ID
        enrollment_no: Student enrollment number
        
    Returns:
        Tuple of (success, message, download_url)
    """
    generator = CertificateGenerator()
    return await generator.generate_and_download_certificate(event_id, enrollment_no)


if __name__ == "__main__":
    # Test the certificate generator
    async def test_generator():
        success, message, download_url = await generate_certificate_for_student(
            "GREEN_INNOVATION_HACKATHON_2025", 
            "22BEIT30043"
        )
        print(f"Success: {success}")
        print(f"Message: {message}")
        print(f"Download URL: {download_url}")
    
    asyncio.run(test_generator())
