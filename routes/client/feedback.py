"""Event feedback and certificate routes."""
from fastapi import APIRouter, Request, HTTPException, Response, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime
from models.student import Student
from models.feedback import EventFeedback
from config.database import Database
from utils.db_operations import DatabaseOperations
from utils.email_service import EmailService
from dependencies.auth import require_student_login
from utils.event_status_manager import EventStatusManager
from models.event import EventSubStatus
from utils.id_generator import generate_feedback_id

router = APIRouter(prefix="/client")
templates = Jinja2Templates(directory="templates")
email_service = EmailService()

@router.get("/events/{event_id}/feedback")
async def show_feedback_form(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Display the feedback form for an event before certificate collection"""
    try:
        # Get event details with updated status from EventStatusManager
        event = await EventStatusManager.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if certificates are available
        if event.get('sub_status') != EventSubStatus.CERTIFICATE_AVAILABLE.value:
            raise HTTPException(
                status_code=400, 
                detail="Feedback collection is not available for this event at this time"
            )
        
        # Check if student is registered and attended
        event_collection = await Database.get_event_collection(event_id)
        if event_collection is not None:
            registration = await event_collection.find_one({
                "enrollment_no": student.enrollment_no
            })
            if not registration:
                # Show not registered error page
                return templates.TemplateResponse(
                    "client/not_registered.html",
                    {
                        "request": request,
                        "event": event,
                        "student": student
                    }
                )

            # Check if student already submitted feedback
            feedback = await event_collection.find_one({
                "registration_id": registration.get("registrar_id")
            })

            if feedback:
                # Show confirmation page with existing feedback
                return templates.TemplateResponse(
                    "client/feedback_confirmation.html",
                    {
                        "request": request,
                        "event": event,
                        "student": student,
                        "registration": registration,
                        "feedback": feedback
                    }
                )

            # Check attendance record
            attendance = await event_collection.find_one({
                "registration_id": registration.get("registrar_id")
            })

            if not attendance:
                return templates.TemplateResponse(
                    "client/feedback_form.html",
                    {
                        "request": request,
                        "event": event,
                        "student": student,
                        "error": "Event attendance record not found"
                    }
                )

            return templates.TemplateResponse(
                "client/feedback_form.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "registration": registration,
                    "attendance": attendance
                }
            )

    except HTTPException as he:
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(
                url=f"/client/login?redirect={request.url.path}",
                status_code=302
            )
        raise he
    except Exception as e:
        print(f"Error in show_feedback_form: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/{event_id}/feedback")
async def submit_feedback(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Handle feedback form submission"""
    try:
        # Get form data
        form_data = await request.form()
        
        # Get event details
        event = await EventStatusManager.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event_collection = await Database.get_event_collection(event_id)
        if event_collection is None:
            raise HTTPException(status_code=500, detail="Event collection not found")

        # Get registration record
        registration = await event_collection.find_one({
            "enrollment_no": student.enrollment_no
        })
        if not registration:
            # Show not registered error page for POST requests as well
            return templates.TemplateResponse(
                "client/not_registered.html",
                {
                    "request": request,
                    "event": event,
                    "student": student
                },
                status_code=400
            )        # Generate feedback ID using the utility function
        feedback_id = generate_feedback_id(student.enrollment_no, event_id)

        # Create feedback record
        feedback_data = {
            "feedback_id": feedback_id,
            "registration_id": registration.get("registrar_id"),
            "event_id": event_id,
            "enrollment_no": student.enrollment_no,
            "name": registration.get("full_name"),
            "email": registration.get("email"),
            "overall_satisfaction": int(form_data.get("overall_satisfaction", 0)),
            "event_organization": int(form_data.get("event_organization", 0)),
            "venue_facilities": int(form_data.get("venue_facilities", 0)),
            "speaker_quality": int(form_data.get("speaker_quality", 0)),
            "time_management": int(form_data.get("time_management", 0)),
            "met_expectations": form_data.get("met_expectations") == "yes",
            "event_usefulness": int(form_data.get("event_usefulness", 0)),
            "would_recommend": form_data.get("would_recommend") == "yes",
            "liked_most": form_data.get("liked_most", ""),
            "areas_for_improvement": form_data.get("areas_for_improvement", ""),
            "additional_comments": form_data.get("additional_comments", ""),
            "submitted_at": datetime.now()
        }        # Save feedback
        result = await event_collection.insert_one(feedback_data)
        
        if result.inserted_id:
            # Update student's event participation record with feedback_id
            await DatabaseOperations.update_one(
                "students",
                {"enrollment_no": student.enrollment_no},
                {"$set": {f"event_participations.{event_id}.feedback_id": feedback_id}}
            )
              # Send feedback confirmation email
            try:
                await email_service.send_feedback_confirmation(
                    student_email=registration.get("email"),
                    student_name=registration.get("full_name"),
                    event_title=event.get("event_name", event_id),
                    event_date=event.get("start_date")
                )
            except Exception as e:
                print(f"Failed to send feedback confirmation email: {str(e)}")
                # Continue even if email fails
            
            # Show success page
            return templates.TemplateResponse(
                "client/feedback_success.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "registration": registration,
                    "feedback": feedback_data
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save feedback")

    except HTTPException as he:
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(
                url=f"/client/login?redirect={request.url.path}",
                status_code=302
            )
        raise he
    except ValueError as ve:
        return templates.TemplateResponse(
            "client/feedback_form.html",
            {
                "request": request,
                "event": event if 'event' in locals() else None,
                "student": student,
                "error": str(ve),
                "form_data": form_data if 'form_data' in locals() else {}
            },
            status_code=422
        )
    except Exception as e:
        print(f"Error in submit_feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/{event_id}/feature-development")
async def show_feature_development(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Display the feature under development page"""
    try:
        # Get event details
        event = await EventStatusManager.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get registration record
        event_collection = await Database.get_event_collection(event_id)
        if event_collection is None:
            raise HTTPException(status_code=500, detail="Event collection not found")

        registration = await event_collection.find_one({
            "enrollment_no": student.enrollment_no
        })
        
        if not registration:
            return templates.TemplateResponse(
                "client/not_registered.html",
                {
                    "request": request,
                    "event": event,
                    "student": student
                }
            )

        return templates.TemplateResponse(
            "client/feature_development.html",
            {
                "request": request,
                "event": event,
                "student": student,
                "registration": registration
            }
        )

    except HTTPException as he:
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(
                url=f"/client/login?redirect={request.url.path}",
                status_code=302
            )
        raise he
    except Exception as e:
        print(f"Error in show_feature_development: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
