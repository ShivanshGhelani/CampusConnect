import warnings
import re
import logging
from fastapi import APIRouter, Request, HTTPException, Response, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from utils.db_operations import DatabaseOperations
from utils.email_service import EmailService
from models.registration import RegistrationForm
from models.student import Student
from models.attendance import AttendanceRecord
from config.database import Database
from utils.template_context import get_template_context
from utils.statistics import StatisticsManager
from dependencies.auth import require_student_login, get_current_student

# Configure logging
logger = logging.getLogger(__name__)

# Suppress bcrypt version warning
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

router = APIRouter(prefix="/client")
templates = Jinja2Templates(directory="templates")
email_service = EmailService()

@router.get("/")
async def index(request: Request):
    """Render the client homepage with upcoming and ongoing events"""
    try:
        from utils.event_status_manager import EventStatusManager

        # Get events and update their status
        upcoming_events = await EventStatusManager.get_available_events("upcoming")
        ongoing_events = await EventStatusManager.get_available_events("ongoing")
        
        # Convert datetime strings to datetime objects and sort by relevant dates
        current_date = datetime.now()
        
        # Convert and sort upcoming events
        for event in upcoming_events:
            for date_field in ["start_datetime", "end_datetime", "registration_start_date", "registration_end_date"]:
                if isinstance(event.get(date_field), str):
                    try:
                        event[date_field] = datetime.fromisoformat(event[date_field].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        event[date_field] = current_date
                elif event.get(date_field) is None:
                    event[date_field] = current_date
        
        # Convert and sort ongoing events  
        for event in ongoing_events:
            for date_field in ["start_datetime", "end_datetime", "registration_start_date", "registration_end_date"]:
                if isinstance(event.get(date_field), str):
                    try:
                        event[date_field] = datetime.fromisoformat(event[date_field].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        event[date_field] = current_date
                elif event.get(date_field) is None:
                    event[date_field] = current_date
        
        # Safe sort function
        def safe_sort_key(event, field):
            value = event.get(field, current_date)
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return current_date
            elif isinstance(value, datetime):
                return value
            else:
                return current_date
        
        upcoming_events.sort(key=lambda x: safe_sort_key(x, 'start_datetime'))
        ongoing_events.sort(key=lambda x: safe_sort_key(x, 'end_datetime'))
          # Calculate event type counts for the homepage
        all_events = upcoming_events + ongoing_events
        event_type_counts = {}
        for event in all_events:
            event_type = event.get('event_type', 'other').lower()
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        # Get real platform statistics from database
        platform_stats = await StatisticsManager.get_platform_statistics()
        
        # Format statistics for display
        formatted_stats = {
            "total_events": StatisticsManager.format_stat_number(platform_stats["total_events"]),
            "active_students": StatisticsManager.format_stat_number(platform_stats["active_students"]),
            "certificates_issued": StatisticsManager.format_stat_number(platform_stats["certificates_issued"]),
            "platform_rating": StatisticsManager.format_rating(platform_stats["platform_rating"])
        }
          
        # Get template context
        template_context = await get_template_context(request)
        
        # Convert datetime objects to ISO format strings for template
        serialized_upcoming_events = []
        for event in upcoming_events:
            serialized_event = {}
            for key, value in event.items():                
                if isinstance(value, datetime):
                    serialized_event[key] = value.isoformat()
                else:
                    serialized_event[key] = value
            serialized_upcoming_events.append(serialized_event)
            
        serialized_ongoing_events = []
        for event in ongoing_events:
            serialized_event = {}
            for key, value in event.items():
                if isinstance(value, datetime):
                    serialized_event[key] = value.isoformat()
                else:
                    serialized_event[key] = value
            serialized_ongoing_events.append(serialized_event)
        return templates.TemplateResponse(
            "client/index.html",
            {
                "request": request,
                "upcoming_events": serialized_upcoming_events,
                "ongoing_events": serialized_ongoing_events,
                "current_datetime": datetime.now(),
                "event_type_counts": event_type_counts,
                "platform_stats": formatted_stats,
                **template_context
            }
        )
    except Exception as e:
        logger.error(f"Error in client index: {str(e)}")
        return templates.TemplateResponse(
            "client/index.html",
            {
                "request": request,
                "upcoming_events": [],
                "ongoing_events": [],
                "current_datetime": datetime.now(),
                "error": str(e)
            }
        )

@router.get("/events")
async def list_events(request: Request, filter: str = "upcoming"):
    """Client-side event listing page"""
    try:
        from utils.event_status_manager import EventStatusManager
        
        # Get events based on filter - Only allow upcoming and ongoing for client side
        filter = filter.lower()
        if filter not in ["upcoming", "ongoing", "all"]:
            filter = "upcoming"  # Default to upcoming for students
        
        if filter == "all":
            # For client side, "all" means upcoming + ongoing (exclude completed)
            upcoming_events = await EventStatusManager.get_available_events("upcoming")
            ongoing_events = await EventStatusManager.get_available_events("ongoing")
            events = upcoming_events + ongoing_events
        else:
            # Get specific type of events (upcoming or ongoing only)
            events = await EventStatusManager.get_available_events(filter)        # Convert datetime strings to datetime objects for sorting and processing
        current_date = datetime.now()
        
        for i, event in enumerate(events):
            for date_field in ["start_datetime", "end_datetime", "registration_start_date", "registration_end_date"]:
                value = event.get(date_field)
                
                if isinstance(value, str):
                    try:
                        event[date_field] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, AttributeError) as e:
                        event[date_field] = current_date  # Fallback to current date
                elif value is None:
                    event[date_field] = current_date  # Handle None values        # Sort events with safe key function
        def safe_sort_key(event, field):
            value = event.get(field, current_date)
            # Always return a datetime object
            if isinstance(value, datetime):
                return value
            elif isinstance(value, str):
                try:
                    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return result
                except (ValueError, AttributeError):
                    return current_date
            else:
                return current_date
          # Sort events
        try:
            if filter in ["upcoming", "all"]:
                # For upcoming events or all events, sort by start date
                events.sort(key=lambda x: safe_sort_key(x, 'start_datetime'))
            elif filter == "ongoing":
                # For ongoing events, sort by end date
                events.sort(key=lambda x: safe_sort_key(x, 'end_datetime'))
        except Exception as sort_error:
            logger.warning(f"Error sorting events: {sort_error}")
            # Don't sort if there's an error
            pass
            
        # Get all events to calculate dynamic filter categories
        try:
            all_upcoming = await EventStatusManager.get_available_events("upcoming")
            all_ongoing = await EventStatusManager.get_available_events("ongoing")
            all_events = all_upcoming + all_ongoing
            
            # Convert datetime strings to datetime objects for all events
            for event in all_events:
                for date_field in ["start_datetime", "end_datetime", "registration_start_date", "registration_end_date"]:
                    if isinstance(event.get(date_field), str):
                        try:
                            event[date_field] = datetime.fromisoformat(event[date_field].replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            event[date_field] = current_date  # Fallback to current date
                    elif event.get(date_field) is None:
                        event[date_field] = current_date  # Handle None values
              # Calculate event type counts
            event_type_counts = {}
            for event in all_events:
                event_type = event.get('event_type', 'other').lower()
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        except Exception as counts_error:
            logger.warning(f"Error calculating event type counts: {counts_error}")
            event_type_counts = {}
            
        # Get template context
        template_context = await get_template_context(request)
          # Ensure all datetime objects in template_context are serialized
        serialized_template_context = {}
        for key, value in template_context.items():
            if isinstance(value, datetime):
                serialized_template_context[key] = value.isoformat()
            else:
                serialized_template_context[key] = value

        # Convert datetime objects to ISO format strings for template
        serialized_events = []
        for event in events:
            serialized_event = {}
            for key, value in event.items():
                try:                    
                    if isinstance(value, datetime):
                        serialized_event[key] = value.isoformat()
                    else:
                        serialized_event[key] = value
                except Exception as serialize_error:
                    serialized_event[key] = str(value)  # Fallback to string conversion
            serialized_events.append(serialized_event)
        # Ensure all template values are properly serialized
        current_datetime_str = datetime.now().isoformat()
        
        return templates.TemplateResponse(
            "client/events.html",
            {
                "request": request,
                "events": serialized_events,
                "filter": filter,
                "current_datetime": current_datetime_str,
                "event_type_counts": event_type_counts,
                **serialized_template_context
            }
        )
    except Exception as e:
        print(f"Error in client events: {str(e)}")
        # Ensure consistent datetime serialization in error case
        current_datetime_str = datetime.now().isoformat()
        return templates.TemplateResponse(
            "client/events.html",
            {
                "request": request,
                "events": [],
                "filter": filter,
                "current_datetime": current_datetime_str,
                "error": str(e)
            }
        )

@router.get("/events/{event_id}")
async def event_details(request: Request, event_id: str):
    """View details of a specific event"""
    try:
        from utils.event_status_manager import EventStatusManager
        from models.event import Event, EventSubStatus
        
        # Get event details and convert to Event model
        event_data = await DatabaseOperations.find_one(
            "events", 
            {"event_id": event_id}
        )
        if not event_data:
            raise HTTPException(status_code=404, detail="Event not found")
            
        # Convert string dates to datetime objects
        for date_field in ["start_datetime", "end_datetime", "registration_start_date", "registration_end_date",
                          "certificate_start_date", "certificate_end_date"]:
            if isinstance(event_data.get(date_field), str):
                event_data[date_field] = datetime.fromisoformat(event_data[date_field].replace('Z', '+00:00'))
          # Create Event model (status will be updated in get_event_timeline)
        event = Event(**event_data)
        
        # Get timeline (this also updates status)
        timeline = await EventStatusManager.get_event_timeline(event)
        
        # Get available forms (status already updated)
        available_forms = event.get_available_forms()
        
        # Calculate registration time remaining
        registration_time_remaining = None
        if "registration" in available_forms:
            current_date = datetime.now()
            time_diff = event.registration_end_date - current_date
            if time_diff.days > 0:
                registration_time_remaining = f"{time_diff.days} days"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                registration_time_remaining = f"{hours} hours"
            else:
                registration_time_remaining = "Less than 1 hour"
        
        # Calculate event duration
        event_duration = None
        if event.start_datetime and event.end_datetime:
            duration = event.end_datetime - event.start_datetime
            if duration.days > 0:
                event_duration = f"{duration.days} days"
            else:
                hours = duration.seconds // 3600
                minutes = (duration.seconds % 3600) // 60
                if hours > 0:
                    event_duration = f"{hours}h {minutes}m"
                else:
                    event_duration = f"{minutes} minutes"
        
        # Get registration statistics
        registration_stats = {
            "total_registrations": 0,
            "available_spots": None,
            "waiting_list": 0
        }
        
        try:
            # Use event-specific database for registrations
            event_collection = await Database.get_event_collection(event_id)
            if event_collection is not None:
                cursor = event_collection.find({})
                registrations = await cursor.to_list(length=None)
                registration_stats["total_registrations"] = len(registrations)
                
                # Calculate available spots if there's a limit
                if event_data.get('registration_limit'):
                    registration_stats["available_spots"] = max(0, event_data['registration_limit'] - registration_stats["total_registrations"])
                    if registration_stats["total_registrations"] > event_data['registration_limit']:
                        registration_stats["waiting_list"] = registration_stats["total_registrations"] - event_data['registration_limit']
        except Exception as e:
            print(f"Could not fetch registration stats: {e}")          # Check if registration is possible (FIXED: compare with .value)
        can_register = (
            event.sub_status == EventSubStatus.REGISTRATION_OPEN.value and
            (not event_data.get('registration_limit') or registration_stats["available_spots"] > 0)
        )
        
        # Determine registration status for template (FIXED: compare with .value)
        if event.sub_status == EventSubStatus.REGISTRATION_NOT_STARTED.value:
            registration_status = "not_started"
        elif event.sub_status == EventSubStatus.REGISTRATION_OPEN.value:
            registration_status = "open"
        elif event.sub_status in [EventSubStatus.REGISTRATION_CLOSED.value, EventSubStatus.EVENT_STARTED.value, EventSubStatus.EVENT_ENDED.value, EventSubStatus.CERTIFICATE_AVAILABLE.value, EventSubStatus.EVENT_COMPLETED.value]:
            registration_status = "ended"
        else:
            registration_status = "ended"  # Default fallback
        
        # Process contact information
        event_contacts = []
        if event_data.get('contacts'):
            for contact in event_data['contacts']:
                contact_info = contact.get('contact', '')
                email = phone = None
                
                if '@' in contact_info and '.' in contact_info:
                    email = contact_info
                elif any(char.isdigit() for char in contact_info):
                    cleaned_phone = ''.join(filter(str.isdigit, contact_info))
                    if len(cleaned_phone) >= 10:
                        phone = contact_info
                
                event_contacts.append({
                    'name': contact.get('name', ''),
                    'role': None,
                    'email': email,
                    'phone': phone
                })
          # Add timeline, contacts and other details to event data
        event_data.update({
            'event_contacts': event_contacts,
            'timeline': timeline,
            'available_forms': available_forms,
            'status': event.status,
            'sub_status': event.sub_status,
        })
        
        # Convert datetime objects to ISO format strings for template
        serialized_event_data = {}
        for key, value in event_data.items():
            if isinstance(value, datetime):
                serialized_event_data[key] = value.isoformat()
            else:
                serialized_event_data[key] = value
        
        return templates.TemplateResponse(
            "client/event_details.html",
            {
                "request": request,
                "event": serialized_event_data,
                "timeline": timeline,
                "available_forms": available_forms,
                "registration_time_remaining": registration_time_remaining,
                "event_duration": event_duration,
                "registration_stats": registration_stats,
                "registration_status": registration_status,
                "can_register": can_register
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in event_details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Event registration routes have been moved to event_registration.py for better organization
# and proper authentication handling

# Event registration submission has been moved to event_registration.py for better organization
# and proper authentication handling

# Student Authentication Functions
async def authenticate_student(enrollment_no: str, password: str) -> Student:
    """Authenticate student using enrollment number and password"""
    # Check if student exists in the students collection with correct password
    student = await DatabaseOperations.find_one(
        "students", 
        {
            "enrollment_no": enrollment_no,
            "is_active": True
        }
    )
    
    if student and Student.verify_password(password, student.get("password_hash", "")):
        return Student(**student)
    
    return None

# Student Login Routes
@router.get("/login")
async def student_login_page(request: Request):
    """Show student login page"""
    return templates.TemplateResponse(
        "client/student_login.html",
        {"request": request}
    )

@router.post("/login")
async def student_login(request: Request):
    """Handle student login"""
    form_data = await request.form()
    enrollment_no = form_data.get("enrollment_no")
    password = form_data.get("password")
    redirect_url = form_data.get("redirect", "/client/dashboard")
    
    # Validate required fields
    if not all([enrollment_no, password]):
        return templates.TemplateResponse(
            "client/student_login.html",
            {
                "request": request,
                "error": "Both enrollment number and password are required",
                "form_data": form_data
            },
            status_code=400
        )
    
    # Authenticate student
    student = await authenticate_student(enrollment_no, password)
    if not student:
        return templates.TemplateResponse(
            "client/student_login.html",
            {
                "request": request,
                "error": "Invalid enrollment number or password. Please try again.",
                "form_data": form_data
            },
            status_code=401
        )
    
    # Update last login time
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": enrollment_no},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Convert student data to dict and serialize datetime objects
    student_data = student.model_dump()
    for key, value in student_data.items():
        if isinstance(value, datetime):
            student_data[key] = value.isoformat()
    
    # Store student in session
    request.session["student"] = student_data
    
    # Redirect to the original URL or dashboard
    return RedirectResponse(url=redirect_url, status_code=303)

@router.get("/logout") 
async def student_logout(request: Request):
    """Handle student logout"""
    request.session.clear()
    return RedirectResponse(url="/client/events", status_code=302)

@router.get("/dashboard")
async def student_dashboard(request: Request):
    """Student dashboard showing their registrations and event history"""
    try:
        student = await get_current_student(request)
    except HTTPException:
        return RedirectResponse(url="/client/login", status_code=302)
      # Handle flash messages from URL parameters
    success_msg = request.query_params.get("success")
    error_msg = request.query_params.get("error")
    event_name = request.query_params.get("event_name", "Event")
    flash_messages = []
    if success_msg == "registration_cancelled":
        flash_messages.append(("success", f"Successfully cancelled registration for {event_name}"))
    elif error_msg == "not_registered":
        flash_messages.append(("error", "You are not registered for this event"))
    elif error_msg == "event_not_found":
        flash_messages.append(("error", "Event not found"))
    elif error_msg == "event_started":
        flash_messages.append(("error", "Cannot cancel registration - event has already started"))
    elif error_msg == "database_error":
        flash_messages.append(("error", "Database error occurred while cancelling registration"))
    elif error_msg == "registration_not_found":
        flash_messages.append(("error", "Registration record not found"))
    elif error_msg == "update_failed":
        flash_messages.append(("error", "Failed to update student record"))
    elif error_msg == "participant_cannot_cancel":
        flash_messages.append(("error", "Only team leaders can cancel team registrations. Please contact your team leader."))
    elif error_msg == "unexpected_error":
        flash_messages.append(("error", "An unexpected error occurred"))
      # Get student's registrations using the new event_participations system
    registrations = []
    
    # Get the student document from database to access event_participations
    student_doc = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
    event_participations = student_doc.get("event_participations", {}) if student_doc else {}
    
    # Fetch event details for each registered event
    for event_id, participation in event_participations.items():
        # Get event details (show all registered events regardless of published status)
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            continue  # Skip if event not found
            
        # Convert datetime objects to ISO format strings in both event and participation
        serialized_event = {}
        for key, value in event.items():
            if isinstance(value, datetime):
                serialized_event[key] = value.isoformat()
            else:
                serialized_event[key] = value
                
        serialized_participation = {}
        for key, value in participation.items():
            if isinstance(value, datetime):
                serialized_participation[key] = value.isoformat()
            else:
                serialized_participation[key] = value
                
        registrations.append({
            "event": serialized_event,
            "registration": serialized_participation,  # Use participation data instead of separate registration
            "event_id": event_id
        })
      # Convert student datetime fields to ISO format
    serialized_student = student.model_dump()
    for key, value in serialized_student.items():
        if isinstance(value, datetime):
            serialized_student[key] = value.isoformat()
    
    return templates.TemplateResponse(
        "client/dashboard.html",
        {
            "request": request,
            "student": serialized_student,
            "registrations": registrations,
            "datetime": datetime,
            "flash_messages": flash_messages
        }
    )

# Student Registration Routes
@router.get("/register")
async def student_register_page(request: Request):
    """Show student registration page"""
    return templates.TemplateResponse(
        "client/register.html",
        {"request": request}
    )

@router.post("/register")
async def student_register(request: Request):
    """Handle student registration"""
    try:
        form_data = await request.form()
          # Extract form data
        enrollment_no = form_data.get("enrollment_no", "").strip().upper()
        full_name = form_data.get("full_name", "").strip()
        email = form_data.get("email", "").strip().lower()
        mobile_no = form_data.get("mobile_no", "").strip()
        password = form_data.get("password", "")
        confirm_password = form_data.get("confirm_password", "")
        department = form_data.get("department", "").strip()
        semester = form_data.get("semester")
        gender = form_data.get("gender", "").strip()
        date_of_birth = form_data.get("date_of_birth", "").strip()
        
        # Validation
        errors = []
        
        if not enrollment_no or not re.match(r'^\d{2}[A-Z]{2,4}\d{5}$', enrollment_no):
            errors.append("Invalid enrollment number format (e.g., 21BECE40015)")
            
        if not full_name or len(full_name) < 2:
            errors.append("Valid full name is required")
            
        if not email or "@" not in email:
            errors.append("Valid email address is required")
            
        if not mobile_no or len(mobile_no) != 10 or not mobile_no.isdigit():
            errors.append("Valid 10-digit mobile number is required")
            
        # Enhanced password validation
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        if not any(c in "!@#$%^&*" for c in password):
            errors.append("Password must contain at least one special character")
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")            
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        # Gender validation
        if not gender:
            errors.append("Gender is required")
        elif gender not in ["Male", "Female", "Other", "Prefer not to say"]:
            errors.append("Please select a valid gender option")
        
        # Date of birth validation
        if not date_of_birth:
            errors.append("Date of birth is required")
        else:
            try:
                birth_date = datetime.strptime(date_of_birth, '%Y-%m-%d')
                today = datetime.now()
                age = today.year - birth_date.year
                
                # Adjust age if birthday hasn't occurred this year
                if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                    age -= 1
                
                if age < 15:
                    errors.append("You must be at least 15 years old to register")
                elif age > 100:
                    errors.append("Please enter a valid date of birth")
            except ValueError:
                errors.append("Please enter a valid date of birth")
        
        if errors:
            return templates.TemplateResponse(
                "client/register.html",
                {
                    "request": request,
                    "error": "; ".join(errors),
                    "form_data": form_data
                },
                status_code=400
            )
        
        # Check if student already exists
        existing_student = await DatabaseOperations.find_one(
            "students", 
            {"$or": [
                {"enrollment_no": enrollment_no},
                {"email": email},
                {"mobile_no": mobile_no}
            ]}
        )
        
        if existing_student:
            if existing_student.get("enrollment_no") == enrollment_no:
                errors.append("Student with this enrollment number already exists")
            elif existing_student.get("email") == email:
                errors.append("Student with this email already exists")
            elif existing_student.get("mobile_no") == mobile_no:
                errors.append("Student with this mobile number already exists")
        
        if errors:
            return templates.TemplateResponse(
                "client/register.html",
                {
                    "request": request,
                    "error": "; ".join(errors),
                    "form_data": form_data
                },
                status_code=400
            )
        
        # Hash the password
        password_hash = Student.hash_password(password)
          # Create student record
        student_data = {
            "enrollment_no": enrollment_no,
            "full_name": full_name,
            "email": email,
            "mobile_no": mobile_no,
            "password_hash": password_hash,
            "department": department if department else None,
            "semester": int(semester) if semester else None,
            "gender": gender,
            "date_of_birth": datetime.strptime(date_of_birth, '%Y-%m-%d'),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        # Save to database
        result = await DatabaseOperations.insert_one("students", student_data)
        
        if result:
            return templates.TemplateResponse(
                "client/register.html",
                {
                    "request": request,
                    "success": "Account created successfully! You can now login with your credentials."
                }
            )
        else:
            return templates.TemplateResponse(
                "client/register.html",
                {
                    "request": request,
                    "error": "Failed to create account. Please try again.",
                    "form_data": form_data
                },
                status_code=500
            )
            
    except Exception as e:
        print(f"Registration error: {e}")
        return templates.TemplateResponse(
            "client/register.html",
            {
                "request": request,
                "error": "An error occurred during registration. Please try again.",
                "form_data": form_data if 'form_data' in locals() else {}
            },
            status_code=500
        )

@router.get("/registration-not-started")
async def registration_not_started(request: Request):
    """Display registration not started page"""
    context = await get_template_context(request)
    context["request"] = request
    return templates.TemplateResponse(
        "client/registration_not_started.html",
        context
    )

@router.get("/events/{event_id}/certificate")
async def download_certificate(request: Request, event_id: str, feedback_submitted: bool = False, student: Student = Depends(require_student_login)):
    """Download certificate for completed events - requires student login and feedback submission"""
    try:
        from utils.event_status_manager import EventStatusManager
        from models.event import Event, EventSubStatus
        from fastapi.responses import FileResponse
        from pathlib import Path

        # Get event details with updated status from EventStatusManager
        event = await EventStatusManager.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if certificates are available
        if event.get('sub_status') != EventSubStatus.CERTIFICATE_AVAILABLE.value:
            raise HTTPException(
                status_code=400, 
                detail="Certificates are not available for this event at this time"
            )

        # Get student's registration and check feedback submission
        event_collection = await Database.get_event_collection(event_id)
        if event_collection is not None:
            registration = await event_collection.find_one({
                "enrollment_no": student.enrollment_no,
                "type": "registration"
            })
            
            if not registration:
                raise HTTPException(
                    status_code=400, 
                    detail="You must be registered for this event to download a certificate"
                )

            # Check if feedback is submitted
            if not feedback_submitted:
                feedback = await event_collection.find_one({
                    "registration_id": registration.get("registrar_id"),
                    "type": "feedback"
                })

                if not feedback:
                    # Redirect to feedback form if not submitted
                    return RedirectResponse(
                        url=f"/client/events/{event_id}/feedback",
                        status_code=303
                    )
        
        # Check if student is registered for this event and has attended
        db = await Database.get_database(event_id)
        if db is not None:
            registration = await db["registrations"].find_one({
                "enrollment_no": student.enrollment_no
            })
            
            if not registration:
                return templates.TemplateResponse(
                    "client/certificate_download.html",
                    {
                        "request": request,
                        "event": event,
                        "student": student,
                        "error": "You must be registered for this event to download a certificate"
                    }
                )
            
            # In a full implementation, you would also check if they attended the event
            # if not registration.get('attended'):
            #     return error about not attending

        # For now, return a temporary message since actual certificate generation is not implemented
        # In a full implementation, this would:
        # 1. Verify user registration for the event
        # 2. Generate a personalized certificate
        # 3. Return the certificate file
        
        return templates.TemplateResponse(
            "client/certificate_download.html",
            {
                "request": request,
                "event": event,
                "student": student,
                "message": "Certificate download functionality is under development. Certificates will be available soon!"
            }
        )
        
    except HTTPException as he:
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            # Redirect to login with return URL
            return RedirectResponse(
                url=f"/client/login?redirect={request.url.path}",
                status_code=302
            )
        raise he
    except Exception as e:
        print(f"Error in download_certificate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/{event_id}/mark-attendance")
async def mark_attendance_get(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Display attendance marking form for ongoing events"""
    try:
        from utils.event_status_manager import EventStatusManager
        from models.event import EventSubStatus
        
        # Use EventStatusManager to get event with updated status
        event = await EventStatusManager.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if event is currently ongoing and attendance is available
        if event.get('sub_status') != EventSubStatus.EVENT_STARTED.value:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Attendance marking is only available during the event period"
                }
            )
        
        # Check if student is registered for this event
        db = await Database.get_database(event_id)
        registration = None
        if db is not None:
            registration = await db["registrations"].find_one({
                "enrollment_no": student.enrollment_no
            })
            
            if not registration:
                return templates.TemplateResponse(
                    "client/mark_attendance.html",
                    {
                        "request": request,
                        "event": event,
                        "student": student,
                        "error": "You must be registered for this event to mark attendance"
                    }
                )
              # Check if attendance already marked
            existing_attendance = await db["attendance"].find_one({
                "registration_id": registration.get("registrar_id"),
                "event_id": event_id
            })
            
            if existing_attendance:
                return templates.TemplateResponse(
                    "client/attendance_confirmation.html",
                    {
                        "request": request,
                        "event": event,
                        "student": student,
                        "registration": registration,
                        "attendance": existing_attendance,
                        "already_marked": True
                    }
                )
        
        return templates.TemplateResponse(
            "client/mark_attendance.html",
            {
                "request": request,
                "event": event,
                "student": student,
                "registration": registration
            }
        )
        
    except HTTPException as he:
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            # Redirect to login with return URL
            return RedirectResponse(
                url=f"/client/login?redirect={request.url.path}",
                status_code=302
            )
        raise he
    except Exception as e:
        print(f"Error in mark_attendance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/{event_id}/mark-attendance")
async def mark_attendance_post(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Process attendance marking form submission"""
    try:
        from utils.event_status_manager import EventStatusManager
        from models.event import EventSubStatus
        
        # Get form data
        form_data = await request.form()
        student_name = form_data.get("student_name", "").strip()
        registration_id = form_data.get("registration_id", "").strip()
        
        # Use EventStatusManager to get event with updated status
        event = await EventStatusManager.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if event is currently ongoing
        if event.get('sub_status') != EventSubStatus.EVENT_STARTED.value:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Attendance marking is only available during the event period",
                    "form_data": {"student_name": student_name, "registration_id": registration_id}
                }
            )
        
        # Validate input
        if not student_name or not registration_id:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Please fill in all required fields",
                    "form_data": {"student_name": student_name, "registration_id": registration_id}
                }
            )
        
        # Get event collection for this event
        event_collection = await Database.get_event_collection(event_id)
        if event_collection is None:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Event collection not found",
                    "form_data": {"student_name": student_name, "registration_id": registration_id}
                }
            )
          # Find registration by registrar_id (registration ID)
        registration = await event_collection.find_one({
            "registrar_id": registration_id,
            "type": "registration"
        })
        
        if not registration:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Registration ID not found. Please check and try again.",
                    "form_data": {"student_name": student_name, "registration_id": registration_id}
                }
            )
        
        # Verify that the current student is the one registered
        if registration.get("enrollment_no") != student.enrollment_no:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "This registration ID does not belong to your account",
                    "form_data": {"student_name": student_name, "registration_id": registration_id}
                }
            )        # Verify student name matches registration
        registered_name = registration.get("full_name", "").strip().lower()  # Using 'full_name' field from registration
        provided_name = student_name.strip().lower()
        
        if registered_name != provided_name:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": f"Name mismatch. Registered name: {registration.get('full_name')}",
                    "form_data": {"student_name": student_name, "registration_id": registration_id}
                }
            )
        
        # Check if attendance already marked
        existing_attendance = await event_collection.find_one({
            "registration_id": registration_id,
            "event_id": event_id,
            "type": "attendance"
        })
        
        if existing_attendance:
            return templates.TemplateResponse(
                "client/attendance_confirmation.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "registration": registration,
                    "attendance": existing_attendance,
                    "already_marked": True
                }
            )        # Mark attendance using AttendanceRecord model
        attendance_time = datetime.now()
        
        # Create attendance record using the model
        attendance_record = AttendanceRecord(
            registration_id=registration_id,  # Store the registrar_id as registration_id in attendance
            event_id=event_id,
            enrollment_no=student.enrollment_no,
            full_name=registration.get("full_name"),  # Using 'full_name' field from registration
            email=registration.get("email"),
            mobile_no=registration.get("mobile_no"),
            department=registration.get("department"),
            semester=registration.get("semester"),
            event_name=event.get("event_name"),
            attendance_marked_at=attendance_time,
            marked_by=f"Student Self-Service ({student.enrollment_no})",
            attendance_status="present",
            type="attendance"
        )
        
        # Generate unique attendance ID 
        attendance_record.attendance_id = AttendanceRecord.generate_unique_attendance_id(
            student.enrollment_no,
            registration.get("full_name"),
            registration.get("department"),
            event_id
        )
        
        # Convert to dict for database insertion
        attendance_dict = attendance_record.dict_for_db()        # Insert attendance record
        result = await event_collection.insert_one(attendance_dict)
        
        if result.inserted_id:            # Send attendance confirmation email
            try:
                await email_service.send_attendance_confirmation(
                    student_email=registration.get("email"),
                    student_name=registration.get("full_name"),
                    event_title=event.get("event_name", event_id),
                    attendance_date=attendance_time.strftime("%Y-%m-%d %H:%M:%S"),
                    event_venue=event.get("venue", "TBD")
                )
            except Exception as e:
                print(f"Failed to send attendance confirmation email: {str(e)}")
                # Continue even if email fails
            
            # Redirect to success page
            return templates.TemplateResponse(
                "client/attendance_success.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "registration": registration,
                    "attendance": attendance_record,
                    "attendance_time": attendance_time
                }
            )
        else:
            return templates.TemplateResponse(
                "client/mark_attendance.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Failed to mark attendance. Please try again.",
                    "form_data": {"student_name": student_name, "registration_id": registration_id}
                }
            )
        
    except HTTPException as he:
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            # Redirect to login with return URL
            return RedirectResponse(
                url=f"/client/login?redirect={request.url.path}",
                status_code=302
            )
        raise he
    except Exception as e:
        print(f"Error in mark_attendance_post: {str(e)}")
        return templates.TemplateResponse(
            "client/mark_attendance.html",
            {
                "request": request,
                "event": event if 'event' in locals() else None,
                "student": student,
                "error": "An unexpected error occurred. Please try again.",
                "form_data": {"student_name": form_data.get("student_name", ""), "registration_id": form_data.get("registration_id", "")}            }
        )

# This revert_registration function has been replaced by the better 
# cancel_registration function in event_registration.py which properly 
# handles both individual and team registrations using the new event_participations structure
