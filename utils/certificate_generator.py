#!/usr/bin/env python3
"""
Certificate Generator
Handles certificate generation with multiple PDF generation fallbacks
"""

import os
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime
import base64

from fastapi.responses import StreamingResponse
from utils.db_operations import DatabaseOperations
from utils.email_service import EmailService


class CertificateGenerator:
    """Handles certificate generation with reliable PDF conversion"""

    def __init__(self):
        self.email_service = EmailService()
        self.templates_dir = Path("templates/certificates")

    async def generate_and_download_certificate(
        self, event_id: str, enrollment_no: str
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
            print(
                f"DEBUG: Starting robust certificate generation for event {event_id}, student {enrollment_no}"
            )

            # Get event details
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            if not event:
                return False, "Event not found", None

            print(f"DEBUG: Event found: {event.get('event_name', 'Unknown')}")            # Check if event qualifies for certificate generation
            if not self._is_eligible_event(event):
                registration_type = event.get("registration_type", "unknown")
                registration_mode = event.get("registration_mode", "unknown")
                return (
                    False,
                    f"Certificate generation is not yet supported for {registration_type.title()} {registration_mode.title()} events. Currently supports Individual and Team events (Free or Paid).",
                    None,
                )

            print(f"DEBUG: Event is eligible for certificate generation")

            # Get student details
            student = await DatabaseOperations.find_one(
                "students", {"enrollment_no": enrollment_no}
            )
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
            success, message, pdf_bytes = await self._generate_certificate_pdf(
                template_path, event, student, enrollment_no
            )

            if not success:
                return False, message, None

            print(f"DEBUG: PDF generated successfully: {len(pdf_bytes)} bytes")

            # Send email with PDF attachment
            email_success = await self._send_certificate_email_with_attachment(
                event, student, enrollment_no, pdf_bytes
            )

            if email_success:
                print(f"DEBUG: Email with PDF attachment sent successfully")
            else:
                print(f"DEBUG: Email sending failed, but continuing with download")            # Return PDF data for client download
            return True, "Certificate generated and emailed successfully!", pdf_bytes

        except Exception as e:
            print(f"DEBUG: Exception in certificate generation: {str(e)}")
            return False, f"Error generating certificate: {str(e)}", None

    def _is_eligible_event(self, event: Dict) -> bool:
        """Check if event is eligible for certificate generation"""
        registration_type = event.get("registration_type", "").lower()
        registration_mode = event.get("registration_mode", "").lower()

        # Support both free and paid events for both individual and team modes
        return (
            registration_mode in ["individual", "team"] and 
            registration_type in ["free", "paid"]
        )

    async def _validate_participation(
        self, student: Dict, event_id: str
    ) -> Tuple[bool, str]:
        """Validate that student has completed all requirements"""
        participations = student.get("event_participations", {})
        participation = participations.get(event_id)

        if not participation:
            return False, "Student not registered for this event"

        if not participation.get("registration_id"):
            return False, "Invalid registration - missing registration ID"

        if not participation.get("attendance_id"):
            return False, "Student did not attend the event"

        if not participation.get("feedback_id"):
            return False, "Student has not submitted feedback"

        return True, "All requirements validated"

    def _get_template_path(self, event: Dict) -> Optional[Path]:
        """Get the certificate template path for the event"""
        certificate_template = event.get("certificate_template")
        if not certificate_template:
            print(f"DEBUG: No certificate_template field found in event")
            return None

        print(f"DEBUG: Raw certificate_template: {certificate_template}")

        # The certificate_template field contains the full path from project root
        # Convert Windows backslashes to proper path handling
        template_path = Path(certificate_template.replace("\\", "/"))

        print(f"DEBUG: Computed template_path: {template_path}")
        print(f"DEBUG: Template path exists: {template_path.exists()}")

        if not template_path.exists():
            return None

        return template_path

    async def _generate_certificate_pdf(
        self, template_path: Path, event: Dict, student: Dict, enrollment_no: str
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Generate PDF certificate from HTML template using multiple fallbacks"""
        temp_html_path = None
        try:
            print(f"DEBUG: Generating PDF certificate...")

            # Read template content
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            print(
                f"DEBUG: Template content loaded, length: {len(template_content)} characters"
            )            # Get student details
            participation = student.get("event_participations", {}).get(
                event["event_id"], {}
            )
            student_data = participation.get("student_data", {})
            full_name = student_data.get(
                "full_name", student.get("full_name", enrollment_no)
            )
            department = student.get("department", "Unknown Department")            # Get team name for team events
            team_name = None
            if event.get("registration_mode", "").lower() == "team":
                # Check if this is a team registration
                student_data_in_participation = participation.get("student_data", {})
                team_name = student_data_in_participation.get("team_name")
                
                # If not found in participation data, try to get from team registration ID
                if not team_name:
                    team_registration_id = participation.get("team_registration_id")
                    if team_registration_id:
                        # Get team details from event data
                        event_doc = await DatabaseOperations.find_one("events", {"event_id": event["event_id"]})
                        if event_doc:
                            team_registrations = event_doc.get("team_registrations", {})
                            team_details = team_registrations.get(team_registration_id, {})
                            team_name = team_details.get("team_name")

            print(
                f"DEBUG: Student details - Name: {full_name}, Department: {department}, Team: {team_name or 'N/A'}"
            )

            # Replace placeholders
            processed_content = self._replace_placeholders(
                template_content, full_name, department, event, team_name
            )

            print(f"DEBUG: Placeholders replaced")

            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(processed_content)
                temp_html_path = temp_file.name

            print(f"DEBUG: Temporary HTML file created: {temp_html_path}")            # Try multiple PDF generation methods
            pdf_bytes = await self._convert_html_to_pdf_multiple_methods(
                temp_html_path,
                processed_content,
                full_name,
                event.get("event_name", "Event"),
                event,
                team_name,
            )

            print(f"DEBUG: PDF conversion completed: {len(pdf_bytes)} bytes")

            # Clean up temporary HTML file
            if temp_html_path and os.path.exists(temp_html_path):
                os.unlink(temp_html_path)
                print(f"DEBUG: Cleaned up temporary HTML file: {temp_html_path}")

            return True, "Certificate generated successfully", pdf_bytes

        except Exception as e:
            print(f"DEBUG: Error in PDF generation: {str(e)}")
            # Clean up temp HTML file on error
            if temp_html_path and os.path.exists(temp_html_path):
                try:                os.unlink(temp_html_path)
                except:
                    pass
            return False, f"Error generating PDF: {str(e)}", None

    async def _convert_html_to_pdf_multiple_methods(
        self, html_path: str, html_content: str, student_name: str, event_name: str, event: Dict = None, team_name: str = None
    ) -> bytes:
        """Try multiple PDF generation methods with fallbacks"""

        # Method 1: Try WeasyPrint
        try:
            import weasyprint

            print("DEBUG: Trying WeasyPrint for PDF generation...")
            pdf_bytes = weasyprint.HTML(filename=html_path).write_pdf()
            print(f"DEBUG: WeasyPrint successful, generated {len(pdf_bytes)} bytes")
            return pdf_bytes
        except ImportError:
            print("DEBUG: WeasyPrint not available")
        except Exception as e:
            print(f"DEBUG: WeasyPrint failed: {e}")

        # Method 2: Try pdfkit (requires wkhtmltopdf)
        try:
            import pdfkit

            print("DEBUG: Trying pdfkit for PDF generation...")
            options = {
                "page-size": "A4",
                "margin-top": "0.75in",
                "margin-right": "0.75in",
                "margin-bottom": "0.75in",
                "margin-left": "0.75in",
                "encoding": "UTF-8",
                "no-outline": None,
                "enable-local-file-access": None,
            }
            pdf_bytes = pdfkit.from_file(html_path, False, options=options)
            print(f"DEBUG: pdfkit successful, generated {len(pdf_bytes)} bytes")
            return pdf_bytes
        except ImportError:
            print("DEBUG: pdfkit not available")
        except Exception as e:
            print(f"DEBUG: pdfkit failed: {e}")        # Method 3: All HTML-to-PDF methods failed
            error_message = (
                "Certificate generation failed: Unable to convert HTML template to PDF. "
                "This requires either WeasyPrint or wkhtmltopdf (pdfkit) to be properly installed and configured. "
                "Please install the required dependencies:\n"
                "- WeasyPrint: pip install weasyprint\n"
                "- OR wkhtmltopdf: Download from https://wkhtmltopdf.org/ and ensure it's in PATH\n"
                "Professional certificates require HTML-to-PDF conversion to maintain template styling."
            )
            print(f"ERROR: {error_message}")
            raise Exception(error_message)    
    def _replace_placeholders(
        self, template_content: str, full_name: str, department: str, event: Dict, team_name: str = None
    ) -> str:
        """Replace placeholders in template with actual values"""
        replacements = {
            "{{participant_name}}": full_name,
            "{{department_name}}": department,
            "{{event_name}}": event.get("event_name", "Unknown Event"),
            "{{event_date}}": self._format_event_date(event),
            "{{issue_date}}": datetime.now().strftime("%B %d, %Y"),
        }

        # Add team name placeholder for team events
        if team_name:
            replacements["{{team_name}}"] = team_name

        processed_content = template_content
        for placeholder, value in replacements.items():
            processed_content = processed_content.replace(placeholder, value)

        return processed_content

    def _format_event_date(self, event: Dict) -> str:
        """Format event date for certificate"""
        start_date = event.get("start_datetime")
        if isinstance(start_date, str):
            try:
                date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                return date_obj.strftime("%B %d, %Y")
            except:
                return start_date
        elif hasattr(start_date, "strftime"):
            return start_date.strftime("%B %d, %Y")
        return "Unknown Date"

    async def _send_certificate_email_with_attachment(
        self, event: Dict, student: Dict, enrollment_no: str, pdf_bytes: bytes
    ) -> bool:
        """Send certificate email with PDF attachment"""
        try:
            print(f"DEBUG: Sending certificate email with PDF attachment...")

            # Get student email
            participation = student.get("event_participations", {}).get(
                event["event_id"], {}
            )
            student_data = participation.get("student_data", {})
            student_email = student_data.get("email") or student.get("email")

            if not student_email:
                print(f"⚠️ No email address found for student {enrollment_no}")
                return False

            # Get student name
            full_name = student_data.get(
                "full_name", student.get("full_name", enrollment_no)
            )

            # Save PDF to temporary file for email attachment
            safe_student_name = "".join(
                c for c in full_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            safe_event_name = "".join(
                c
                for c in event.get("event_name", "Event")
                if c.isalnum() or c in (" ", "-", "_")
            ).strip()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = (
                f"Certificate_{safe_student_name}_{safe_event_name}_{timestamp}.pdf"
            )
            temp_pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)

            # Write PDF bytes to file
            with open(temp_pdf_path, "wb") as f:
                f.write(pdf_bytes)

            print(f"DEBUG: Temporary PDF saved: {temp_pdf_path}")

            # Certificate URL (fallback)
            certificate_url = f"/client/events/{event['event_id']}/certificate"

            # Send notification with PDF attachment
            success = await self.email_service.send_certificate_notification(
                student_email=student_email,
                student_name=full_name,
                event_title=event.get("event_name", "Unknown Event"),
                certificate_url=certificate_url,
                event_date=self._format_event_date(event),
                certificate_pdf_path=temp_pdf_path,
            )

            if success:
                print(
                    f"✅ Certificate email with PDF attachment sent to {student_email}"
                )
            else:
                print(f"⚠️ Failed to send certificate email to {student_email}")

            # Clean up temporary PDF file after a delay
            asyncio.create_task(
                self._delayed_cleanup([temp_pdf_path], delay_seconds=60)
            )

            return success

        except Exception as e:
            print(f"⚠️ Error sending certificate email: {str(e)}")
            return False

    async def _delayed_cleanup(self, file_paths: list, delay_seconds: int = 60):
        """Clean up temporary files after a delay"""
        await asyncio.sleep(delay_seconds)
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    print(f"DEBUG: Cleaned up temp file: {file_path}")
            except Exception as e:
                print(f"DEBUG: Error cleaning up {file_path}: {e}")

    def create_certificate_download_response(
        self, pdf_bytes: bytes, file_name: str
    ) -> StreamingResponse:
        """Create a streaming response for certificate PDF download"""
        from fastapi import Response

        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Type": "application/pdf",
        }

        return Response(
            content=pdf_bytes, media_type="application/pdf", headers=headers
        )


# Convenience functions for use in routes
async def generate_certificate_for_student(
    event_id: str, enrollment_no: str
) -> Tuple[bool, str, Optional[bytes]]:
    """
    Generate certificate for a student

    Args:
        event_id: Event ID
        enrollment_no: Student enrollment number

    Returns:
        Tuple of (success, message, pdf_bytes)
    """
    generator = CertificateGenerator()
    return await generator.generate_and_download_certificate(event_id, enrollment_no)


def create_certificate_download_response(
    pdf_bytes: bytes, filename: str
) -> StreamingResponse:
    """
    Create download response for certificate PDF

    Args:
        pdf_bytes: PDF file bytes
        filename: Filename for download

    Returns:
        StreamingResponse for download
    """
    try:
        # Create streaming response
        def generate():
            yield pdf_bytes

        response = StreamingResponse(
            generate(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            },
        )

        return response

    except Exception as e:
        print(f"DEBUG: Error creating download response: {e}")
        raise


if __name__ == "__main__":
    # Test the certificate generator
    async def test_generator():
        success, message, pdf_bytes = await generate_certificate_for_student(
            "GREEN_INNOVATION_HACKATHON_2025", "22BEIT30043"
        )
        print(f"Success: {success}")
        print(f"Message: {message}")
        if pdf_bytes:
            print(f"PDF Size: {len(pdf_bytes)} bytes")
            # Save test PDF
            with open("test_certificate.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("Test PDF saved as 'test_certificate.pdf'")

    asyncio.run(test_generator())
