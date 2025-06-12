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
from fastapi.responses import Response
import jinja2
import pdfkit
import tempfile
import os

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

class ServerCertificateRequest(BaseModel):
    event_id: str
    enrollment_no: Optional[str] = None

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

@router.post("/generate-certificate-server")
async def generate_certificate_server(
    request: ServerCertificateRequest,
    http_request: Request,
    student: Student = Depends(require_student_login)
):
    """
    Server-side certificate generation fallback
    Generates PDF using server-side libraries when client libraries fail
    """
    try:
        logger.info(f"🔄 Server-side certificate generation for event {request.event_id}, student {request.enrollment_no}")
        
        # Use enrollment_no from request or current student
        enrollment_no = request.enrollment_no or student.enrollment_no
        
        # Fetch certificate data using existing function
        certificate_data = await fetch_certificate_data_from_db(request.event_id, enrollment_no)
        
        if not certificate_data["success"]:
            raise HTTPException(status_code=404, detail=certificate_data["message"])
        
        data = certificate_data["data"]
        
        # Generate HTML content
        html_content = generate_certificate_html_server(data)
        
        # Convert HTML to PDF using server-side library
        pdf_content = await generate_pdf_from_html(html_content)
        
        # Create filename
        participant_name = data.get("participant_name", data.get("full_name", "participant"))
        event_name = data.get("event_name", "event")
        
        participant_initial = participant_name[0].upper() if participant_name else "P"
        event_initial = event_name[0].upper() if event_name else "E"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"{participant_initial}_{event_initial}_{timestamp}.pdf"
        
        logger.info(f"✅ Server-side certificate generated: {filename}")
        
        # Return PDF as response
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Server-side certificate generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server certificate generation failed: {str(e)}")

async def fetch_certificate_data_from_db(event_id: str, enrollment_no: str) -> Dict[str, Any]:
    """
    Fetch real certificate data from database for JavaScript frontend
    Returns structured data with actual database values for placeholders
    """
    try:
        from utils.db_operations import DatabaseOperations
        
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            logger.error(f"Event {event_id} not found")
            return None
            
        # Get student details
        student = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        if not student:
            logger.error(f"Student {enrollment_no} not found")
            return None
            
        # Get student's participation in this event
        event_participations = student.get('event_participations', {})
        participation = event_participations.get(event_id)
        
        if not participation:
            logger.error(f"No participation record found for student {enrollment_no} in event {event_id}")
            return None
            
        # Extract student data from participation or student record
        student_data = participation.get('student_data', {})
        participant_name = student_data.get('full_name') or student.get('full_name', 'Unknown Participant')
        department_name = student_data.get('department') or student.get('department', 'Unknown Department')
        
        # Build certificate data structure
        certificate_data = {
            # Event information
            "event_id": event_id,
            "event_name": event.get("event_name", "Event"),
            "event_date": event.get("start_date", datetime.now()).strftime("%B %d, %Y") if event.get("start_date") else datetime.now().strftime("%B %d, %Y"),
            "event_type": event.get("registration_mode", "individual"),
            "registration_mode": event.get("registration_mode", "individual"),
            
            # Student information for placeholders
            "participant_name": participant_name,  # {{ participant_name }}
            "full_name": participant_name,
            "enrollment_no": enrollment_no,
            "department_name": department_name,  # {{ department_name }}
            "department": department_name,
            "email": student_data.get('email') or student.get('email', ''),
            
            # Team information (for team events) - optional
            "team_name": None,  # {{ team_name }} - only for team events
            
            # Certificate metadata
            "certificate_title": "Certificate of Participation",
            "issued_date": datetime.now().strftime("%B %d, %Y"),
            "signature_authority": "Event Coordinator",
            
            # Template type determination
            "template_type": "individual"  # will be "team" if team_name is present
        }
        
        # Check if this is a team event and get team information
        if event.get("registration_mode") == "team":
            # Get team name from student's participation data
            team_name = student_data.get("team_name")
            
            # If team name not in student data, try to get from team registration
            if not team_name:
                team_registration_id = participation.get("team_registration_id")
                if team_registration_id:
                    team_registrations = event.get("team_registrations", {})
                    team_details = team_registrations.get(team_registration_id, {})
                    team_name = team_details.get("team_name")
            
            if team_name:
                certificate_data["registration_mode"] = "team"
                certificate_data["event_type"] = "team"
                certificate_data["team_name"] = team_name  # {{ team_name }}
                certificate_data["template_type"] = "team"
        
        logger.info(f"Certificate data prepared for {enrollment_no} in {event_id} - Type: {certificate_data['template_type']}")
        return certificate_data
        
    except Exception as e:
        logger.error(f"Database error fetching certificate data: {str(e)}")
        return None

async def send_certificate_email_background(event_id: str, enrollment_no: str, pdf_base64: str, file_name: str):
    """
    Background task function for sending certificate emails with real data
    """
    try:
        logger.info(f"Starting background email task for {enrollment_no}")
        
        # Get student and event data
        from utils.db_operations import DatabaseOperations
        
        student = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        
        if not student or not event:
            logger.error(f"Student or event not found for email sending: {enrollment_no}, {event_id}")
            return
            
        # Get student email
        participation = student.get("event_participations", {}).get(event_id, {})
        student_data = participation.get("student_data", {})
        student_email = student_data.get("email") or student.get("email")
        student_name = student_data.get("full_name") or student.get("full_name", "Student")
        
        if not student_email:
            logger.warning(f"No email address found for student {enrollment_no}")
            return
            
        # Send email using your email service
        try:
            from utils.email_service import EmailService
            import base64
            
            pdf_bytes = base64.b64decode(pdf_base64)
            email_service = EmailService()
            
            await email_service.send_certificate_notification(
                student_email=student_email,
                student_name=student_name,
                event_title=event.get("event_name", "Event"),
                certificate_url=f"/client/events/{event_id}/certificate",  # Web link to certificate page
                certificate_pdf_bytes=pdf_bytes,
                file_name=file_name,
                event_date=event.get("start_date")
            )
            
            logger.info(f"Certificate email sent successfully to {student_email}")
            
        except Exception as email_error:
            logger.error(f"Failed to send certificate email: {str(email_error)}")
        
    except Exception as e:
        logger.error(f"Background email task failed for {enrollment_no}: {str(e)}")

def generate_certificate_html_server(data: Dict[str, Any]) -> str:
    """
    Generate certificate HTML on server side
    """
    # Determine if it's a team event
    is_team_event = data.get("event_type") == "team" or data.get("team_name")
    
    # Base template
    if is_team_event:
        template_content = """
        <div style="width: 714px; height: 1083px; padding: 40px; background: white; font-family: Arial, sans-serif; text-align: center; border: 2px solid #ccc;">
            <div style="border: 3px solid #333; padding: 30px; height: 100%; box-sizing: border-box;">
                <h1 style="font-size: 36px; color: #1a365d; margin-bottom: 20px; font-weight: bold;">CERTIFICATE OF PARTICIPATION</h1>
                
                <div style="width: 100px; height: 4px; background: linear-gradient(45deg, #3182ce, #805ad5); margin: 20px auto;"></div>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">This is to certify that</p>
                
                <h2 style="font-size: 32px; color: #2d3748; margin: 30px 0; font-weight: bold; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">{{ participant_name }}</h2>
                
                <p style="font-size: 18px; color: #4a5568; margin: 20px 0;">from the Department of</p>
                
                <h3 style="font-size: 24px; color: #3182ce; margin: 20px 0; font-weight: bold;">{{ department_name }}</h3>
                
                <p style="font-size: 18px; color: #4a5568; margin: 20px 0;">as a member of team</p>
                
                <h3 style="font-size: 26px; color: #e53e3e; margin: 20px 0; font-weight: bold; background: #fed7d7; padding: 10px; border-radius: 8px;">{{ team_name }}</h3>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">has successfully participated in</p>
                
                <h3 style="font-size: 28px; color: #805ad5; margin: 30px 0; font-weight: bold;">{{ event_name }}</h3>
                
                <p style="font-size: 16px; color: #4a5568; margin: 20px 0;">held on {{ event_date }}</p>
                
                <div style="margin-top: 50px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Event Coordinator</p>
                    </div>
                    
                    <div style="width: 80px; height: 80px; border: 2px solid #3182ce; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #3182ce; font-weight: bold;">SEAL</div>
                    
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Principal</p>
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        template_content = """
        <div style="width: 714px; height: 1083px; padding: 40px; background: white; font-family: Arial, sans-serif; text-align: center; border: 2px solid #ccc;">
            <div style="border: 3px solid #333; padding: 30px; height: 100%; box-sizing: border-box;">
                <h1 style="font-size: 36px; color: #1a365d; margin-bottom: 20px; font-weight: bold;">CERTIFICATE OF PARTICIPATION</h1>
                
                <div style="width: 100px; height: 4px; background: linear-gradient(45deg, #3182ce, #805ad5); margin: 20px auto;"></div>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">This is to certify that</p>
                
                <h2 style="font-size: 32px; color: #2d3748; margin: 30px 0; font-weight: bold; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">{{ participant_name }}</h2>
                
                <p style="font-size: 18px; color: #4a5568; margin: 20px 0;">from the Department of</p>
                
                <h3 style="font-size: 24px; color: #3182ce; margin: 20px 0; font-weight: bold;">{{ department_name }}</h3>
                
                <p style="font-size: 18px; color: #4a5568; margin: 30px 0;">has successfully participated in</p>
                
                <h3 style="font-size: 28px; color: #805ad5; margin: 30px 0; font-weight: bold;">{{ event_name }}</h3>
                
                <p style="font-size: 16px; color: #4a5568; margin: 20px 0;">held on {{ event_date }}</p>
                
                <div style="margin-top: 60px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Event Coordinator</p>
                    </div>
                    
                    <div style="width: 80px; height: 80px; border: 2px solid #3182ce; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #3182ce; font-weight: bold;">SEAL</div>
                    
                    <div style="text-align: center;">
                        <div style="width: 150px; height: 2px; background: #2d3748; margin-bottom: 5px;"></div>
                        <p style="font-size: 14px; color: #4a5568;">Principal</p>
                    </div>
                </div>
            </div>
        </div>
        """
    
    # Replace placeholders
    html_content = template_content.replace(
        "{{ participant_name }}", 
        data.get("participant_name", data.get("full_name", "Participant"))
    )
    html_content = html_content.replace(
        "{{ department_name }}", 
        data.get("department_name", data.get("department", "Department"))
    )
    html_content = html_content.replace(
        "{{ event_name }}", 
        data.get("event_name", "Event")
    )
    html_content = html_content.replace(
        "{{ event_date }}", 
        data.get("event_date", "Date")
    )
    
    if is_team_event:
        html_content = html_content.replace(
            "{{ team_name }}", 
            data.get("team_name", "Team")
        )
    
    return html_content

async def generate_pdf_from_html(html_content: str) -> bytes:
    """
    Generate PDF from HTML using server-side library
    """
    try:
        # Try using weasyprint first (better CSS support)
        try:
            from weasyprint import HTML, CSS
            from io import BytesIO
            
            html_doc = HTML(string=html_content)
            pdf_buffer = BytesIO()
            html_doc.write_pdf(pdf_buffer)
            return pdf_buffer.getvalue()
            
        except ImportError:
            logger.warning("WeasyPrint not available, trying pdfkit...")
            
            # Fallback to pdfkit
            try:
                import pdfkit
                
                options = {
                    'page-size': 'A4',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                    'no-outline': None,
                    'enable-local-file-access': None
                }
                
                pdf_content = pdfkit.from_string(html_content, False, options=options)
                return pdf_content
                
            except Exception as e:
                logger.error(f"pdfkit failed: {e}")
                raise Exception("Server-side PDF generation not available. Please install weasyprint or wkhtmltopdf.")
                
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise Exception(f"PDF generation failed: {str(e)}")

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
