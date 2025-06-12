"""
JavaScript Certificate Generator Backend API
Provides data and template endpoints for client-side certificate generation
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Optional
from datetime import datetime
import base64
import tempfile
import os
from pathlib import Path

from models.student import Student
from dependencies.auth import require_student_login, get_current_student
from utils.db_operations import DatabaseOperations
from utils.email_service import EmailService
from utils.template_context import get_template_context

router = APIRouter(prefix="/client/api")
email_service = EmailService()


@router.post("/certificate-data")
async def get_certificate_data(
    request: Request,
    student: Student = Depends(require_student_login)
):
    """
    Get certificate data for JavaScript generation
    Validates eligibility and returns all necessary data for PDF generation
    """
    try:
        # Parse request body
        body = await request.json()
        event_id = body.get("event_id")
        enrollment_no = body.get("enrollment_no") or student.enrollment_no

        print(f"DEBUG: Getting certificate data for event {event_id}, student {enrollment_no}")

        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            return {"success": False, "message": "Event not found"}

        # Check if event qualifies for certificate generation
        if not _is_eligible_event(event):
            registration_type = event.get("registration_type", "unknown")
            registration_mode = event.get("registration_mode", "unknown")
            return {
                "success": False,
                "message": f"Certificate generation is not yet supported for {registration_type.title()} {registration_mode.title()} events. Currently supports Individual and Team events (Free or Paid)."
            }

        # Get student details
        student_data = await DatabaseOperations.find_one(
            "students", {"enrollment_no": enrollment_no}
        )
        if not student_data:
            return {"success": False, "message": "Student not found"}

        # Validate participation requirements
        is_valid, error_msg = await _validate_participation(student_data, event_id)
        if not is_valid:
            return {"success": False, "message": error_msg}

        # Get student details from participation data
        participation = student_data.get("event_participations", {}).get(event_id, {})
        student_info = participation.get("student_data", {})
        full_name = student_info.get("full_name", student_data.get("full_name", enrollment_no))
        department = student_data.get("department", "Unknown Department")

        # Get team name for team events
        team_name = None
        if event.get("registration_mode", "").lower() == "team":
            # Check if this is a team registration
            team_name = student_info.get("team_name")
            
            # If not found in participation data, try to get from team registration ID
            if not team_name:
                team_registration_id = participation.get("team_registration_id")
                if team_registration_id:
                    # Get team details from event data
                    event_doc = await DatabaseOperations.find_one("events", {"event_id": event_id})
                    if event_doc:
                        team_registrations = event_doc.get("team_registrations", {})
                        team_details = team_registrations.get(team_registration_id, {})
                        team_name = team_details.get("team_name")

        print(f"DEBUG: Student details - Name: {full_name}, Department: {department}, Team: {team_name or 'N/A'}")

        # Prepare certificate data
        certificate_data = {
            "event_id": event_id,
            "participant_name": full_name,
            "department_name": department,
            "event_name": event.get("event_name", "Unknown Event"),
            "event_date": _format_event_date(event),
            "issue_date": datetime.now().strftime("%B %d, %Y"),
            "student_email": student_info.get("email") or student_data.get("email"),
            "enrollment_no": enrollment_no
        }

        # Add team name for team events
        if team_name:
            certificate_data["team_name"] = team_name

        return {
            "success": True,
            "data": certificate_data,
            "message": "Certificate data retrieved successfully"
        }

    except Exception as e:
        print(f"DEBUG: Exception in get_certificate_data: {str(e)}")
        return {"success": False, "message": f"Error retrieving certificate data: {str(e)}"}


@router.get("/certificate-template/{event_id}")
async def get_certificate_template(event_id: str):
    """
    Get the HTML certificate template for an event
    Returns the raw template with placeholders intact
    """
    try:
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Get certificate template path
        certificate_template = event.get("certificate_template")
        if not certificate_template:
            raise HTTPException(status_code=404, detail="No certificate template found for this event")

        # Convert Windows backslashes to proper path handling
        template_path = Path(certificate_template.replace("\\", "/"))

        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Certificate template file not found")

        # Read and return template content
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        return HTMLResponse(content=template_content)

    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error getting certificate template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading certificate template: {str(e)}")


@router.post("/send-certificate-email")
async def send_certificate_email(
    request: Request,
    student: Student = Depends(require_student_login)
):
    """
    Send certificate email with PDF attachment from JavaScript
    """
    try:
        # Parse request body
        body = await request.json()
        certificate_data = body.get("certificate_data", {})
        pdf_base64 = body.get("pdf_base64", "")
        filename = body.get("filename", "certificate.pdf")

        if not pdf_base64:
            return {"success": False, "message": "No PDF data provided"}

        student_email = certificate_data.get("student_email")
        if not student_email:
            return {"success": False, "message": "No email address available"}

        print(f"DEBUG: Sending certificate email to {student_email}")

        # Convert base64 PDF to bytes
        try:
            pdf_bytes = base64.b64decode(pdf_base64)
        except Exception as e:
            return {"success": False, "message": f"Invalid PDF data: {str(e)}"}

        # Create temporary file for email attachment
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as temp_file:
                temp_file.write(pdf_bytes)
                temp_file_path = temp_file.name

            # Send email with attachment
            email_success = await email_service.send_certificate_notification(
                student_email=student_email,
                student_name=certificate_data.get("participant_name", "Student"),
                event_title=certificate_data.get("event_name", "Event"),
                certificate_url="",  # Not needed for direct attachment
                event_date=certificate_data.get("event_date"),
                certificate_pdf_path=temp_file_path
            )

            if email_success:
                print(f"DEBUG: Certificate email sent successfully to {student_email}")
                return {"success": True, "message": "Certificate email sent successfully"}
            else:
                print(f"DEBUG: Failed to send certificate email")
                return {"success": False, "message": "Failed to send certificate email"}

        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

    except Exception as e:
        print(f"DEBUG: Exception in send_certificate_email: {str(e)}")
        return {"success": False, "message": f"Error sending email: {str(e)}"}


def _is_eligible_event(event: Dict) -> bool:
    """Check if event is eligible for certificate generation"""
    registration_type = event.get("registration_type", "").lower()
    registration_mode = event.get("registration_mode", "").lower()

    # Support both free and paid events for both individual and team modes
    return (
        registration_mode in ["individual", "team"] and 
        registration_type in ["free", "paid"]
    )


async def _validate_participation(student: Dict, event_id: str) -> tuple[bool, str]:
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


def _format_event_date(event: Dict) -> str:
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
