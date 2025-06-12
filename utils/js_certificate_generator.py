#!/usr/bin/env python3
"""
JavaScript Certificate Generator Backend
Provides data and email support for client-side certificate generation
"""

import os
import tempfile
import base64
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime

from utils.db_operations import DatabaseOperations
from utils.email_service import EmailService


class JSCertificateGenerator:
    """Backend support for JavaScript-based certificate generation"""

    def __init__(self):
        self.email_service = EmailService()
        self.templates_dir = Path("templates/certificates")

    async def get_certificate_data(
        self, event_id: str, enrollment_no: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get all data needed for certificate generation
        
        Args:
            event_id: Event ID
            enrollment_no: Student enrollment number
            
        Returns:
            Tuple of (success, message, data_dict)
        """
        try:
            print(f"DEBUG: Getting certificate data for event {event_id}, student {enrollment_no}")

            # Get event details
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            if not event:
                return False, "Event not found", None

            # Check if event qualifies for certificate generation
            if not self._is_eligible_event(event):
                registration_type = event.get("registration_type", "unknown")
                registration_mode = event.get("registration_mode", "unknown")
                return (
                    False,
                    f"Certificate generation is not yet supported for {registration_type.title()} {registration_mode.title()} events. Currently supports Individual and Team events (Free or Paid).",
                    None,
                )

            # Get student details
            student = await DatabaseOperations.find_one(
                "students", {"enrollment_no": enrollment_no}
            )
            if not student:
                return False, "Student not found", None

            # Validate participation requirements
            is_valid, error_msg = await self._validate_participation(student, event_id)
            if not is_valid:
                return False, error_msg, None

            # Get certificate template path and content
            template_path = self._get_template_path(event)
            if not template_path:
                return False, "Certificate template not found for this event", None

            # Read template content
            with open(template_path, "r", encoding="utf-8") as f:
                template_html = f.read()

            # Get student data for certificate
            participation = student.get("event_participations", {}).get(event_id, {})
            student_data_dict = participation.get("student_data", {})
            
            student_data = {
                "enrollment_no": enrollment_no,
                "full_name": student_data_dict.get("full_name", student.get("full_name", enrollment_no)),
                "department": student.get("department", "Unknown Department"),
                "email": student_data_dict.get("email") or student.get("email"),
            }

            # Get team data for team events
            team_data = None
            if event.get("registration_mode", "").lower() == "team":
                team_data = await self._get_team_data(student, event, participation)

            # Prepare event data
            event_data = {
                "event_id": event_id,
                "event_name": event.get("event_name", "Unknown Event"),
                "event_date": self._format_event_date(event),
                "registration_mode": event.get("registration_mode", "individual"),
            }

            # Return complete data package
            certificate_data = {
                "template_html": template_html,
                "student_data": student_data,
                "event_data": event_data,
                "team_data": team_data,
            }

            print(f"DEBUG: Certificate data prepared successfully")
            return True, "Certificate data retrieved successfully", certificate_data

        except Exception as e:
            print(f"DEBUG: Error getting certificate data: {str(e)}")
            return False, f"Error retrieving certificate data: {str(e)}", None

    async def send_certificate_email(
        self, event_id: str, enrollment_no: str, pdf_base64: str, file_name: str
    ) -> Tuple[bool, str]:
        """
        Send certificate email with PDF attachment
        
        Args:
            event_id: Event ID
            enrollment_no: Student enrollment number
            pdf_base64: Base64 encoded PDF data
            file_name: PDF filename
            
        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"DEBUG: Sending certificate email for {enrollment_no}")

            # Get student and event data
            student = await DatabaseOperations.find_one(
                "students", {"enrollment_no": enrollment_no}
            )
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})

            if not student or not event:
                return False, "Student or event not found"

            # Get student email
            participation = student.get("event_participations", {}).get(event_id, {})
            student_data = participation.get("student_data", {})
            student_email = student_data.get("email") or student.get("email")

            if not student_email:
                return False, f"No email address found for student {enrollment_no}"

            # Get student name
            full_name = student_data.get("full_name", student.get("full_name", enrollment_no))

            # Decode PDF from base64
            pdf_bytes = base64.b64decode(pdf_base64)

            # Save PDF to temporary file for email attachment
            temp_pdf_path = os.path.join(tempfile.gettempdir(), file_name)
            with open(temp_pdf_path, "wb") as f:
                f.write(pdf_bytes)

            print(f"DEBUG: Temporary PDF saved: {temp_pdf_path}")

            # Certificate URL (fallback)
            certificate_url = f"/client/events/{event_id}/certificate"

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
                print(f"✅ Certificate email sent successfully to {student_email}")
                return True, "Email sent successfully"
            else:
                return False, "Failed to send email"

        except Exception as e:
            print(f"⚠️ Error sending certificate email: {str(e)}")
            return False, f"Error sending email: {str(e)}"

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

    async def _get_team_data(self, student: Dict, event: Dict, participation: Dict) -> Optional[Dict]:
        """Get team data for team events"""
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

        if team_name:
            return {"team_name": team_name}
        
        return None

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


# Convenience functions for use in routes
async def get_certificate_data_for_js(
    event_id: str, enrollment_no: str
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Get certificate data for JavaScript generator
    
    Args:
        event_id: Event ID
        enrollment_no: Student enrollment number
        
    Returns:
        Tuple of (success, message, data_dict)
    """
    generator = JSCertificateGenerator()
    return await generator.get_certificate_data(event_id, enrollment_no)


async def send_certificate_email_from_js(
    event_id: str, enrollment_no: str, pdf_base64: str, file_name: str
) -> Tuple[bool, str]:
    """
    Send certificate email from JavaScript-generated PDF
    
    Args:
        event_id: Event ID
        enrollment_no: Student enrollment number
        pdf_base64: Base64 encoded PDF data
        file_name: PDF filename
        
    Returns:
        Tuple of (success, message)
    """
    generator = JSCertificateGenerator()
    return await generator.send_certificate_email(event_id, enrollment_no, pdf_base64, file_name)
