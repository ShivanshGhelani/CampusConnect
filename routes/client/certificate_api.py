"""
Clean Certificate API - FastAPI Backend
Handles database operations and provides data to JavaScript frontend
Thread-safe operations for concurrent certificate generation
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import asyncio
import base64
from datetime import datetime
from models.student import Student
from dependencies.auth import require_student_login

# Create logger
logger = logging.getLogger(__name__)

# FastAPI router for certificate operations
router = APIRouter(prefix="/api", tags=["clean-certificate"])

# Pydantic models for request/response
class CertificateDataRequest(BaseModel):
    event_id: str
    enrollment_no: Optional[str] = None

class CertificateEmailRequest(BaseModel):
    event_id: str
    enrollment_no: str
    pdf_base64: str
    file_name: str

class CertificateDataResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class EmailResponse(BaseModel):
    success: bool
    message: str

@router.post("/certificate-data", response_model=CertificateDataResponse)
async def get_certificate_data(
    request: CertificateDataRequest, 
    http_request: Request,
    student: Student = Depends(require_student_login)
):
    """
    Fetch certificate data from database for JavaScript frontend
    Returns structured data with placeholders for certificate generation
    """
    try:
        event_id = request.event_id
        enrollment_no = request.enrollment_no or student.enrollment_no
        
        # Verify the logged-in student matches the requested enrollment
        if student.enrollment_no != enrollment_no:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized: You can only generate certificates for your own enrollment"
            )
        
        logger.info(f"Fetching certificate data for event: {event_id}, student: {enrollment_no}")
        
        # Fetch certificate data from database
        certificate_data = await fetch_certificate_data_from_db(event_id, enrollment_no)
        
        if not certificate_data:
            raise HTTPException(
                status_code=404,
                detail="Certificate data not found for this event and student"
            )
        
        logger.info(f"Certificate data retrieved successfully for {enrollment_no}")
        return CertificateDataResponse(
            success=True,
            data=certificate_data
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching certificate data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

@router.post("/send-certificate-email", response_model=EmailResponse)
async def send_certificate_email(
    request: CertificateEmailRequest, 
    background_tasks: BackgroundTasks,
    student: Student = Depends(require_student_login)
):
    """
    Send certificate via email using background tasks
    Non-blocking email sending for better performance
    """
    try:
        event_id = request.event_id
        enrollment_no = request.enrollment_no
        pdf_base64 = request.pdf_base64
        file_name = request.file_name
        
        # Verify the logged-in student matches the requested enrollment
        if student.enrollment_no != enrollment_no:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized: You can only send certificates for your own enrollment"
            )
        
        logger.info(f"Queuing certificate email for event: {event_id}, student: {enrollment_no}")
        
        # Add email sending to background tasks
        background_tasks.add_task(
            send_certificate_email_background,
            event_id,
            enrollment_no,
            pdf_base64,
            file_name
        )
        
        logger.info(f"Email notification queued successfully for {enrollment_no}")
        
        return EmailResponse(
            success=True,
            message="Email notification sent successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing certificate email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Email queuing failed: {str(e)}"
        )

async def fetch_certificate_data_from_db(event_id: str, enrollment_no: str) -> Dict[str, Any]:
    """
    Fetch certificate data from database
    Replace this with your actual database logic
    """
    try:
        # Import your models here
        # from models import Event, Student, Registration, Team
        
        # TODO: Replace with your actual database query logic
        # Example:
        # event = await Event.get(event_id)
        # student = await Student.get_by_enrollment(enrollment_no)
        # registration = await Registration.get_by_event_and_student(event_id, enrollment_no)
        # team = await Team.get_by_event_and_student(event_id, enrollment_no) if event.registration_mode == "team" else None
        
        # Mock data structure - replace with actual database results
        certificate_data = {
            # Event information
            "event_id": event_id,
            "event_name": "Technical Workshop 2025",
            "event_date": "2025-06-12",
            "event_type": "individual",  # or "team"
            "registration_mode": "individual",  # or "team"
            
            # Student information (for placeholders)
            "participant_name": "John Doe Smith",  # {{ participant_name }}
            "full_name": "John Doe Smith",
            "enrollment_no": enrollment_no,
            "department_name": "Computer Science & Engineering",  # {{ department_name }}
            "department": "Computer Science & Engineering",
            "email": "john.doe@university.edu",
            
            # Team information (for team events) - optional
            "team_name": None,  # {{ team_name }} - only for team events
            
            # Certificate metadata
            "certificate_title": "Certificate of Participation",
            "issued_date": datetime.now().strftime("%B %d, %Y"),
            "signature_authority": "Event Coordinator",
            
            # Template type determination
            "template_type": "individual"  # will be "team" if team_name is present
        }
        
        # Determine if it's a team event (replace with actual database logic)
        # if event.registration_mode == "team" and team:
        if event_id.lower().find("team") != -1:  # Mock logic - replace with actual
            certificate_data["registration_mode"] = "team"
            certificate_data["event_type"] = "team"
            certificate_data["team_name"] = "Alpha Developers"  # {{ team_name }}
            certificate_data["template_type"] = "team"
        
        return certificate_data
        
    except Exception as e:
        logger.error(f"Database error fetching certificate data: {str(e)}")
        return None

async def send_certificate_email_background(event_id: str, enrollment_no: str, pdf_base64: str, file_name: str):
    """
    Background task function for sending certificate emails
    """
    try:
        logger.info(f"Starting background email task for {enrollment_no}")
        
        # TODO: Replace with your actual email sending logic
        # Example:
        # import base64
        # from utils.email_service import EmailService
        # 
        # pdf_bytes = base64.b64decode(pdf_base64)
        # email_service = EmailService()
        # 
        # # Get student email from database
        # student = await Student.get_by_enrollment(enrollment_no)
        # 
        # await email_service.send_certificate_notification(
        #     student_email=student.email,
        #     student_name=student.full_name,
        #     event_title=await get_event_title(event_id),
        #     certificate_url="#",  # Optional web link
        #     certificate_pdf_bytes=pdf_bytes,
        #     file_name=file_name
        # )
        
        # Mock successful email sending
        await asyncio.sleep(1)  # Simulate email sending delay
        logger.info(f"Certificate email sent successfully to {enrollment_no}")
        
    except Exception as e:
        logger.error(f"Background email task failed for {enrollment_no}: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for clean certificate API"""
    return {
        "status": "healthy", 
        "service": "clean-certificate-api",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "javascript-pdf-generation",
            "concurrent-downloads",
            "placeholder-replacement",
            "background-email-sending",
            "temp-file-cleanup"
        ]
    }
