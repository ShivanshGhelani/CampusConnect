"""Event registration routes."""
import warnings
import re
from fastapi import APIRouter, Request, HTTPException, Response, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from utils.db_operations import DatabaseOperations
from utils.event_status_manager import EventStatusManager
from utils.email_service import EmailService
from models.registration import RegistrationForm
from models.team_registration import TeamRegistrationForm, TeamParticipant, TeamValidationResult
from models.student import Student, EventParticipation
from models.event import TeamRegistration
from config.database import Database
from utils.template_context import get_template_context
from utils.id_generator import generate_registration_id, generate_team_registration_id, generate_attendance_id, generate_feedback_id, generate_certificate_id
from dependencies.auth import require_student_login

router = APIRouter()
templates = Jinja2Templates(directory="templates")
email_service = EmailService()

# Template utility functions
def format_datetime(dt, format_type="full"):
    """Format datetime for templates"""
    if not dt:
        return "TBD"
    
    # Convert string to datetime if needed
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00') if 'Z' in dt else dt)
        except ValueError:
            return dt
    
    if not isinstance(dt, datetime):
        return str(dt)
    
    if format_type == "date_only":
        return dt.strftime("%B %d, %Y")
    elif format_type == "time_only":
        return dt.strftime("%I:%M %p")
    else:
        return dt.strftime("%B %d, %Y at %I:%M %p")

def format_venue(venue):
    """Format venue for templates"""
    if not venue:
        return "TBD"
    return venue

# Register template filters
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_venue"] = format_venue


async def validate_team_participants(enrollment_numbers: list) -> TeamValidationResult:
    """Validate team participants by checking if they exist in the students database"""
    result = TeamValidationResult()
    
    for enrollment_no in enrollment_numbers:
        if not enrollment_no.strip():  # Skip empty enrollment numbers
            continue
            
        # Find student in database
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        
        if student_data:
            # Valid participant - add their details
            participant_info = {
                "enrollment_no": enrollment_no,
                "full_name": student_data.get("full_name", ""),
                "email": student_data.get("email", ""),
                "department": student_data.get("department", ""),
                "semester": student_data.get("semester", "")
            }
            result.valid_participants.append(participant_info)
        else:
            # Invalid participant
            result.invalid_enrollments.append(enrollment_no)
            result.error_messages.append(f"Student with enrollment number {enrollment_no} not found in system")
    
    result.is_valid = len(result.invalid_enrollments) == 0
    return result


async def check_team_registration_conflicts(event_id: str, team_enrollment_numbers: list) -> list:
    """Check if any team members are already registered for this event using new approach"""
    conflicts = []
    
    # Check each enrollment number in student data
    for enrollment_no in team_enrollment_numbers:
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        if student_data:
            event_participations = student_data.get('event_participations', {})
            if event_id in event_participations:
                conflicts.append(enrollment_no)
    
    return conflicts


async def check_student_registration_conflicts(enrollment_no: str) -> dict:
    """Check if a student is already registered for any event using the new approach"""
    conflicts = {
        "has_conflicts": False,
        "individual_registrations": [],
        "team_registrations": []
    }
    
    # Get student data
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    if not student_data:
        return conflicts
    
    event_participations = student_data.get('event_participations', {})
    
    if event_participations:
        # Get all events to get event names
        all_events = await DatabaseOperations.find_many("events", {})
        event_names = {event['event_id']: event.get('event_name', event['event_id']) for event in all_events}
        
        for event_id, participation in event_participations.items():
            event_name = event_names.get(event_id, event_id)
            
            if participation.get('registration_type') == 'individual':
                conflicts["individual_registrations"].append({
                    "event_id": event_id,
                    "event_name": event_name,
                    "registration_id": participation.get('registration_id')
                })
                conflicts["has_conflicts"] = True
            elif participation.get('registration_type') in ['team_leader', 'team_participant']:
                conflicts["team_registrations"].append({
                    "event_id": event_id,
                    "event_name": event_name,
                    "role": participation.get('registration_type'),
                    "registration_id": participation.get('registration_id'),
                    "team_registration_id": participation.get('team_registration_id')
                })
                conflicts["has_conflicts"] = True
    
    return conflicts


async def check_team_participation_conflicts(enrollment_no: str) -> dict:
    """Legacy function - now redirects to the new approach"""
    return await check_student_registration_conflicts(enrollment_no)

@router.get("/events/{event_id}/register")
async def show_registration_form(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Display the registration form for an event - requires student login"""
    try:
        # Fetch event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")        # Check if student has already registered for this event using event-specific collection
        event_collection = await Database.get_event_collection(event_id)
        if event_collection is not None:
            existing_registration = await event_collection.find_one({"enrollment_no": student.enrollment_no})
            if existing_registration:
                # Student has already registered - show existing registration
                # Get participation data from student's event_participations
                student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
                if student_data:
                    event_participations = student_data.get('event_participations', {})
                    if event_id in event_participations:
                        existing_participation = event_participations[event_id]
                        
                        # Convert datetime objects to ISO format strings for template
                        serialized_event = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in event.items()}
                        
                        return templates.TemplateResponse("client/existing_registration.html", {
                            "request": request,
                            "event": serialized_event,
                            "student": student,
                            "registration": {
                                "registrar_id": existing_participation.get('registration_id'), 
                                "registration_type": existing_participation.get('registration_type', 'individual'),
                                "registration_datetime": existing_participation.get('registration_date'),
                                "enrollment_no": student.enrollment_no
                            },
                            "datetime": datetime,
                            "is_student_logged_in": True,
                            "student_data": student.model_dump()
                        })
        
        # Get current status using Event Status Manager
        current_time = datetime.now()
        status, sub_status = await EventStatusManager._calculate_event_status(event, current_time)
        
        # Check if registration is allowed
        if sub_status == "registration_not_started":
            registration_start = event.get('registration_start_date')
            if isinstance(registration_start, str):
                registration_start = datetime.fromisoformat(registration_start.replace('Z', '+00:00'))
            
            return templates.TemplateResponse(
                "client/event_registration.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Registration has not started yet",
                    "start_date": registration_start,
                    "datetime": datetime,
                    "is_student_logged_in": True,
                    "student_data": student.model_dump()
                }
            )
        elif sub_status != "registration_open":
            # Registration is closed or event has started/ended
            return templates.TemplateResponse(
                "client/event_registration.html",
                {
                    "request": request,
                    "event": event,
                    "student": student,
                    "error": "Registration deadline has passed",
                    "datetime": datetime,
                    "is_student_logged_in": True,
                    "student_data": student.model_dump()
                }
            )        # Registration is open - show the form with pre-filled student data
        # Check registration mode and add event constraints to template context
        template_context = {
            "request": request,
            "event": event,
            "student": student,
            "datetime": datetime,
            "is_team_registration": event.get('registration_mode') == 'team',
            "team_size_min": event.get('team_size_min', 2),
            "team_size_max": event.get('team_size_max', 5),
            "is_student_logged_in": True,
            "student_data": student.model_dump()
        }        # Check if student is already registered for THIS specific event (both individual and team)
        # Students should be allowed to register for multiple different events but not duplicate registration for the same event
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
        if student_data:
            event_participations = student_data.get('event_participations', {})
            if event_id in event_participations:
                # Student is already registered for THIS event - show existing registration
                existing_participation = event_participations[event_id]
                
                # For team registrations, also get team information
                team_info = None
                if existing_participation.get('registration_type') in ['team_leader', 'team_participant']:
                    team_registration_id = existing_participation.get('team_registration_id')
                    if team_registration_id:
                        # Get team details from event data
                        team_registrations = event.get('team_registrations', {})
                        team_data = team_registrations.get(team_registration_id, {})
                        
                        if team_data:
                            # Get team leader information
                            leader_enrollment = team_data.get('team_leader_enrollment')
                            leader_data = None
                            if leader_enrollment:
                                leader_data = await DatabaseOperations.find_one("students", {"enrollment_no": leader_enrollment})
                            
                            # Get team participants information
                            participants = []
                            for participant_enrollment in team_data.get('participants', []):
                                participant_data = await DatabaseOperations.find_one("students", {"enrollment_no": participant_enrollment})
                                if participant_data:
                                    participants.append({
                                        'full_name': participant_data.get('full_name', 'N/A'),
                                        'enrollment_no': participant_enrollment,
                                        'department': participant_data.get('department', 'N/A')
                                    })
                            
                            team_info = {
                                "team_name": team_data.get('team_name', 'Unknown Team'),
                                "team_registration_id": team_registration_id,
                                "participant_count": len(team_data.get('participants', [])) + 1,  # +1 for leader
                                "leader_name": leader_data.get('full_name', 'Unknown') if leader_data else 'Unknown',
                                "leader_enrollment": leader_enrollment,
                                "participants": participants
                            }
                
                # Convert datetime objects to ISO format strings for template
                serialized_event = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in event.items()}
                return templates.TemplateResponse("client/existing_registration.html", {
                    "request": request,
                    "event": serialized_event,
                    "student": student,
                    "registration": {
                        "registrar_id": existing_participation.get('registration_id'), 
                        "registration_type": existing_participation.get('registration_type', 'individual'),
                        "registration_datetime": existing_participation.get('registration_date'),
                        "enrollment_no": student.enrollment_no,
                        "payment_status": existing_participation.get('payment_status', 'pending'),
                        "payment_completed_datetime": existing_participation.get('payment_completed_datetime')
                    },
                    "team_info": team_info,
                    "datetime": datetime,
                    "is_student_logged_in": True,
                    "student_data": student.model_dump()
                })
        
        return templates.TemplateResponse(
            "client/event_registration.html",
            template_context
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
        print(f"Error in show_registration_form: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/{event_id}/register")
async def submit_registration(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Handle registration form submission - supports both individual and team registration"""
    try:
        # Get the form data
        form_data = dict(await request.form())
        print(f"Received form data: {form_data}")

        # Get event details first to check registration mode
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Check if it's team or individual registration
        is_team_registration = event.get('registration_mode') == 'team'
        
        # Create template context for error responses
        template_context = {
            "request": request,
            "event": event,
            "student": student,
            "form_data": form_data,
            "datetime": datetime,
            "is_team_registration": is_team_registration,
            "team_size_min": event.get('team_size_min', 2),
            "team_size_max": event.get('team_size_max', 5),
            "is_student_logged_in": True,
            "student_data": student.model_dump()
        }

        # Use authenticated student's data to pre-fill/validate enrollment number
        if form_data.get('enrollment_no') != student.enrollment_no:
            template_context["error"] = "Enrollment number doesn't match logged-in student"
            return templates.TemplateResponse("client/event_registration.html", template_context, status_code=400)

        if is_team_registration:
            # Handle team registration
            return await handle_team_registration(form_data, event_id, event, student, template_context)
        else:
            # Handle individual registration
            return await handle_individual_registration(form_data, event_id, event, student, template_context)

    except HTTPException as he:
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url=f"/client/login?redirect={request.url.path}", status_code=302)
        raise he
    except Exception as e:
        print(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.")


async def handle_individual_registration(form_data: dict, event_id: str, event: dict, student, template_context: dict):
    """Handle individual registration submission"""
    # Validate required fields for individual registration
    required_fields = ['full_name', 'enrollment_no', 'email', 'mobile_no', 'department', 'semester', 'gender', 'date_of_birth']
    missing_fields = [field for field in required_fields if field not in form_data or not form_data[field]]
    if missing_fields:
        template_context["error"] = f"Missing required fields: {', '.join(missing_fields)}"
        return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)

    try:
        # Convert and validate data
        form_data = await process_common_form_data(form_data)
        
        # Create and validate registration model
        registration = RegistrationForm(**form_data)
          # Save individual registration
        return await save_individual_registration(registration, event_id, event, student, template_context["request"])

    except ValueError as ve:
        template_context["error"] = str(ve)
        return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)


async def handle_team_registration(form_data: dict, event_id: str, event: dict, student, template_context: dict):
    """Handle team registration submission"""
    # Validate required fields for team registration
    team_required_fields = ['full_name', 'enrollment_no', 'email', 'mobile_no', 'department', 'semester', 'gender', 'date_of_birth', 'team_name']
    missing_fields = [field for field in team_required_fields if field not in form_data or not form_data[field]]
    if missing_fields:
        template_context["error"] = f"Missing required fields: {', '.join(missing_fields)}"
        return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)

    try:
        # Convert and validate common data
        form_data = await process_common_form_data(form_data)
        
        # Extract team participants from form data
        team_participants = []
        participant_index = 1
        
        while f'participant_{participant_index}_enrollment' in form_data:
            enrollment_no = form_data[f'participant_{participant_index}_enrollment'].strip()
            if enrollment_no:  # Only add non-empty enrollment numbers
                team_participants.append(TeamParticipant(enrollment_no=enrollment_no))
            participant_index += 1

        # Validate team size constraints
        total_team_size = len(team_participants) + 1  # +1 for leader
        team_size_min = event.get('team_size_min', 2)
        team_size_max = event.get('team_size_max', 5)
        
        if total_team_size < team_size_min:
            template_context["error"] = f"Team size must be at least {team_size_min} members (including leader)"
            return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)
        
        if total_team_size > team_size_max:
            template_context["error"] = f"Team size cannot exceed {team_size_max} members (including leader)"
            return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)

        # Validate all team participants exist in database
        participant_enrollments = [p.enrollment_no for p in team_participants]
        validation_result = await validate_team_participants(participant_enrollments)
        
        if not validation_result.is_valid:
            error_msg = "Invalid team participants:\n" + "\n".join(validation_result.error_messages)
            template_context["error"] = error_msg
            return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)        # Check for registration conflicts (already registered participants)
        all_team_enrollments = [student.enrollment_no] + participant_enrollments
        conflicts = await check_team_registration_conflicts(event_id, all_team_enrollments)
        
        if conflicts:
            template_context["error"] = f"The following team members are already registered for this event: {', '.join(conflicts)}"
            return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)
          # Note: Multiple event registrations are now allowed
        # Students can register for different events simultaneously
        # Only prevent duplicate registrations for the same event (already checked above)

        # Fill participant details from validation result
        for i, participant in enumerate(team_participants):
            if i < len(validation_result.valid_participants):
                valid_participant = validation_result.valid_participants[i]
                participant.full_name = valid_participant['full_name']
                participant.email = valid_participant['email']
                participant.department = valid_participant['department']
                participant.semester = valid_participant['semester']

        # Create team registration form
        team_form_data = {
            **form_data,
            'team_participants': team_participants
        }
        
        team_registration = TeamRegistrationForm(**team_form_data)
          # Save team registration
        return await save_team_registration(team_registration, event_id, event, student, validation_result.valid_participants, template_context["request"])

    except ValueError as ve:
        template_context["error"] = str(ve)
        return templates.TemplateResponse("client/event_registration.html", template_context, status_code=422)


async def process_common_form_data(form_data: dict) -> dict:
    """Process common form data for both individual and team registration"""
    # Convert semester to integer
    if 'semester' in form_data:
        form_data['semester'] = int(form_data['semester'])
    
    # Handle date of birth
    if 'date_of_birth' in form_data:
        date_str = form_data['date_of_birth']
        try:
            if 'T' in date_str:  # ISO format
                form_data['date_of_birth'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:  # YYYY-MM-DD format
                form_data['date_of_birth'] = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError as e:
            raise ValueError(f"Invalid date format: {str(e)}")
    
    # Normalize gender value
    if 'gender' in form_data:
        gender_mapping = {
            'Male': 'male',
            'Female': 'female', 
            'Other': 'other',
            'Prefer not to say': 'other'
        }
        form_data['gender'] = gender_mapping.get(form_data['gender'], form_data['gender'].lower())
    
    return form_data


async def save_individual_registration(registration: RegistrationForm, event_id: str, event: dict, student, request: Request):
    """Save individual registration to database"""
    # Check for existing registration in student data
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
    if not student_data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    event_participations = student_data.get('event_participations', {})
      
    # Check if already registered for this event
    if event_id in event_participations:
        existing_participation = event_participations[event_id]
        # Return existing registration view with the registration ID
        serialized_event = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in event.items()}
        return templates.TemplateResponse("client/existing_registration.html", {
            "request": request,
            "event": serialized_event,
            "student": student,
            "registration": {
                "registrar_id": existing_participation.get('registration_id'),
                "registration_type": existing_participation.get('registration_type', 'individual'),
                "registration_datetime": existing_participation.get('registration_date'),
                "enrollment_no": student.enrollment_no
            },
            "datetime": datetime,
            "is_student_logged_in": True,
            "student_data": student.model_dump()
        })

    # Generate only registration ID at registration time
    registration_id = generate_registration_id(student.enrollment_no, event_id, registration.full_name)
    registration.registration_datetime = datetime.now()

    # Create individual participation with only registration_id, all other IDs as None
    individual_participation = EventParticipation(
        registration_id=registration_id,
        attendance_id=None,
        feedback_id=None,
        certificate_id=None,
        registration_type="individual",
        registration_datetime=registration.registration_datetime,
        student_data={
            "full_name": registration.full_name,
            "email": registration.email,
            "mobile_no": registration.mobile_no,
            "department": registration.department,
            "semester": registration.semester,
            "gender": registration.gender,
            "date_of_birth": registration.date_of_birth
        }
    )

    # Store participation in student's event_participations
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": student.enrollment_no},
        {"$set": {f"event_participations.{event_id}": individual_participation.model_dump()}}
    )    # Update event registrations mapping
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$set": {f"registrations.{registration_id}": student.enrollment_no}}
    )    # Check if event is paid
    if event.get('registration_type') == 'paid' and event.get('registration_fee', 0) > 0:
        # Redirect to payment page
        return templates.TemplateResponse("client/payment_page.html", {
            "request": request,
            "event": event,
            "registrar_id": registration_id,
            "total_amount": event.get('registration_fee', 0),
            "student_name": registration.full_name,
            "enrollment_no": registration.enrollment_no,
            "is_team_registration": False,
            "is_student_logged_in": True,
            "student_data": student.model_dump()
        })    # Send registration confirmation email for free events
    try:        # Format start_datetime from separate date and time fields
        start_date = event.get("start_date", "")
        start_time = event.get("start_time", "")
          # Ensure we have proper date/time values
        if not start_date or start_date == "":
            start_date = "Date to be announced" 
            
        # Format with validation
        if start_date and start_date != "Date to be announced" and start_time:
            start_datetime = f"{start_date} {start_time}"
        else:
            start_datetime = start_date
        
        await email_service.send_registration_confirmation(
            student_email=registration.email,
            student_name=registration.full_name,
            event_title=event.get("event_name", event_id),
            start_datetime=start_datetime.strftime("%Y-%m-%d %H:%M AM/PM") if isinstance(start_datetime, datetime) else start_datetime,
            venue=event.get("venue"),
            registration_id=registration_id
        )
    except Exception as e:
        print(f"Failed to send registration confirmation email: {str(e)}")
        # Continue with the response even if email fails

    # Return success response
    return templates.TemplateResponse("client/registration_success.html", {
        "request": request,
        "registrar_id": registration_id,
        "event_name": event.get("event_name", event_id),
        "is_team_registration": False,
        "is_student_logged_in": True,
        "student_data": student.model_dump()
    })

async def save_team_registration(team_registration: TeamRegistrationForm, event_id: str, event: dict, student, valid_participants: list, request: Request):
    """Save team registration using new relational mapping approach"""    
    # Generate team registration ID
    team_registration_id = generate_team_registration_id(student.enrollment_no, event_id, team_registration.team_name)
    team_registration.registration_datetime = datetime.now()

    # Create team registration record for event data
    team_reg_data = TeamRegistration(
        team_registration_id=team_registration_id,
        team_name=team_registration.team_name,
        team_leader_enrollment=team_registration.enrollment_no,
        participants=[p.enrollment_no for p in team_registration.team_participants],
        registration_date=team_registration.registration_datetime
    )

    # Update event data with team registration
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$set": {f"team_registrations.{team_registration_id}": team_reg_data.model_dump()}}
    )

    # Generate and store leader registration
    leader_registration_id = generate_registration_id(student.enrollment_no, event_id, team_registration.full_name)

    # Create leader participation with only registration_id
    leader_participation = EventParticipation(
        registration_id=leader_registration_id,
        attendance_id=None,
        feedback_id=None,
        certificate_id=None,
        registration_type="team_leader",
        team_registration_id=team_registration_id,
        registration_datetime=team_registration.registration_datetime,
        student_data={
            "full_name": team_registration.full_name,
            "email": team_registration.email,
            "mobile_no": team_registration.mobile_no,
            "department": team_registration.department,
            "semester": team_registration.semester,
            "gender": team_registration.gender,
            "date_of_birth": team_registration.date_of_birth,
            "team_name": team_registration.team_name
        }
    )

    # Store leader participation
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": student.enrollment_no},
        {"$set": {f"event_participations.{event_id}": leader_participation.model_dump()}}
    )

    # Add leader to event registrations mapping
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$set": {f"registrations.{leader_registration_id}": student.enrollment_no}}
    )

    # Process each team participant
    for participant in team_registration.team_participants:
        # Generate only registration ID for participant
        participant_registration_id = generate_registration_id(participant.enrollment_no, event_id, participant.full_name)

        # Create participant participation with only registration_id
        participant_participation = EventParticipation(
            registration_id=participant_registration_id,
            attendance_id=None,
            feedback_id=None,
            certificate_id=None,
            registration_type="team_participant",
            team_registration_id=team_registration_id,
            registration_datetime=team_registration.registration_datetime,
            student_data={
                "full_name": participant.full_name,
                "email": participant.email,
                "mobile_no": getattr(participant, 'mobile_no', ''),
                "department": participant.department,
                "semester": participant.semester,
                "gender": getattr(participant, 'gender', ''),
                "date_of_birth": getattr(participant, 'date_of_birth', None),
                "team_name": team_registration.team_name
            }
        )

        # Store participant participation
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": participant.enrollment_no},
            {"$set": {f"event_participations.{event_id}": participant_participation.model_dump()}}
        )

        # Add participant to event registrations mapping
        await DatabaseOperations.update_one(
            "events",
            {"event_id": event_id},
            {"$set": {f"registrations.{participant_registration_id}": participant.enrollment_no}}
        )
        
    # Check if event is paid
    if event.get('registration_type') == 'paid' and event.get('registration_fee', 0) > 0:
        # Calculate total amount for team (fee per member)
        total_amount = event.get('registration_fee', 0) * team_registration.total_team_size
        
        # Redirect to payment page
        return templates.TemplateResponse("client/payment_page.html", {
            "request": request,
            "event": event,
            "registrar_id": team_registration_id,
            "total_amount": total_amount,
            "student_name": team_registration.full_name,
            "enrollment_no": team_registration.enrollment_no,
            "is_team_registration": True,
            "team_info": {
                "team_name": team_registration.team_name,
                "participant_count": team_registration.total_team_size,
                "leader_name": team_registration.full_name,
                "leader_enrollment": team_registration.enrollment_no,
                "participants": valid_participants
            },
            "is_student_logged_in": True,
            "student_data": student.model_dump()        })    
    
    # Send registration confirmation emails for free team events
    try:
        # Prepare team member data for email
        team_members_for_email = [
            {
                'full_name': team_registration.full_name,
                'enrollment_no': team_registration.enrollment_no,
                'email': team_registration.email,
                'department': team_registration.department,
                'role': 'Team Leader'
            }
        ]
        
        # Add participants to team members list
        for participant in valid_participants:
            team_members_for_email.append({
                'full_name': participant['full_name'],
                'enrollment_no': participant['enrollment_no'],
                'email': participant['email'],
                'department': participant['department'],
                'role': 'Team Member'
            })
        
        # Send team registration confirmation to all team members
        await email_service.send_team_registration_confirmation(
            team_members=team_members_for_email,
            event_title=event.get("event_name", event_id),
            event_date=event.get("start_datetime", "TBD"),
            event_venue=event.get("venue", "TBD"),
            team_name=team_registration.team_name,
            team_registration_id=team_registration_id,
            event_url=f"{request.base_url}client/events/{event_id}",
            payment_required=False,
            payment_amount=None
        )
        print(f"Team registration confirmation emails sent for team: {team_registration.team_name}")
        
        # Send emails to team participants
        for participant in team_registration.team_participants:
            if participant.email:  # Only send if email is available                # Format start_datetime from separate date and time fields
                start_date = event.get("start_date", "")
                start_time = event.get("start_time", "")
                  # Ensure we have proper date/time values
                if not start_date or start_date == "":
                    start_date = "Date to be announced" 
                    
                # Format with validation
                if start_date and start_date != "Date to be announced" and start_time:
                    start_datetime = f"{start_date} {start_time}"
                else:
                    start_datetime = start_date
                
                await email_service.send_registration_confirmation(
                    student_email=participant.email,
                    student_name=participant.full_name,
                    event_title=event.get("event_name", event_id),
                    start_datetime=start_datetime,
                    venue=event.get("venue"),
                    registration_id=team_registration_id
                )
                
    except Exception as e:
        print(f"Failed to send team registration confirmation emails: {str(e)}")
        # Continue with the response even if email fails

    # For free events, show success page directly
    return templates.TemplateResponse("client/registration_success.html", {
        "request": request,
        "registrar_id": team_registration_id,
        "event_name": event.get("event_name", event_id),
        "is_team_registration": True,
        "is_student_logged_in": True,
        "student_data": student.model_dump()
    })

@router.get("/api/validate-participant")
async def validate_participant_api(enrollment: str, event_id: str = None, team_id: str = None):
    """API endpoint to validate a team participant by enrollment number"""
    try:
        if not enrollment or not enrollment.strip():
            return {"success": False, "message": "Enrollment number is required"}
        
        enrollment = enrollment.strip().upper()
          # Validate enrollment format with improved pattern and better error message
        enrollment_pattern = r'^\d{2}[A-Z]{2,4}\d{5}$'
        if not re.match(enrollment_pattern, enrollment):
            return {"success": False, "message": "Invalid enrollment number format. Expected format: 22BEIT30043"}
          # Find student in database
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment})
        if not student_data:
            return {"success": False, "message": "Student not found in system. Please verify the enrollment number."}
            
        # If event_id and team_id are provided, check team size limits
        if event_id and team_id:
            # Get event details to check team size limits
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            if not event:
                return {"success": False, "message": "Event not found"}
                
            # Get current team details
            team_details = event.get('team_registrations', {}).get(team_id, {})
            if not team_details:
                return {"success": False, "message": "Team not found"}
                
            # Check team size limit
            current_team_size = len(team_details.get('participants', [])) + 1  # +1 for team leader
            max_team_size = event.get('team_size_max', 5)
            
            if current_team_size >= max_team_size:
                return {"success": False, "message": f"Team size cannot exceed the maximum limit of {max_team_size} participants"}
            
            # Check if student is already part of this team
            if enrollment in team_details.get('participants', []) or enrollment == team_details.get('team_leader_enrollment'):
                return {"success": False, "message": "This student is already part of your team"}
                
        # Check if student is already registered for this specific event
        if event_id:
            event_participations = student_data.get('event_participations', {})
            if event_id in event_participations:
                return {"success": False, "message": "This student is already registered for this event"}
        
        # Get student details for display
        formatted_student = {
            "full_name": student_data.get("full_name", ""),
            "enrollment_no": student_data.get("enrollment_no", ""),
            "email": student_data.get("email", ""),
            "mobile_no": student_data.get("mobile_no", ""),
            "department": student_data.get("department", ""),
            "semester": str(student_data.get("semester", "")),
            "gender": student_data.get("gender", ""),
            "profile_image": student_data.get("profile_image", "")
        }
        
        # Return detailed student data for confirmation
        response_data = {
            "success": True,
            "student": formatted_student,
            "can_add": True,
            "message": "Student details retrieved successfully. Please review and confirm to add to your team."
        }
        
        return response_data
        
    except Exception as e:
        print(f"Error in validate_participant_api: {str(e)}")
        return {"success": False, "message": f"Internal server error: {str(e)}"}

@router.get("/api/validate-registration")
async def validate_registration(request: Request, registration_id: str, event_id: str):
    """API endpoint to validate a registration ID and return student details for auto-filling the attendance form"""
    try:
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            return {"success": False, "message": "Event not found"}
        
        # Check if the registration exists for this event
        registration_found = False
        student_enrollment = None
        
        # Check in registrations dictionary
        registrations = event.get("registrations", {})
        if isinstance(registrations, dict):
            for reg_id, enrolled_id in registrations.items():
                if reg_id == registration_id:
                    registration_found = True
                    student_enrollment = enrolled_id
                    break
        
        if not registration_found:
            return {"success": False, "message": "Registration ID not found for this event"}
        
        if not student_enrollment:
            return {"success": False, "message": "Student information not found for this registration"}
        
        # Get student details from database
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student_enrollment})
        if not student_data:
            return {"success": False, "message": "Student not found in system"}
        
        # Get participation details for this registration
        event_participations = student_data.get('event_participations', {})
        participation = event_participations.get(event_id, {})
        registration_type = participation.get('registration_type', 'individual')
        
        # Prepare student response data
        student_response = {
            "full_name": student_data.get("full_name", ""),
            "enrollment_no": student_data.get("enrollment_no", ""),
            "email": student_data.get("email", ""),
            "mobile_no": student_data.get("mobile_no", ""),
            "department": student_data.get("department", ""),
            "semester": student_data.get("semester", ""),
            "registration_type": registration_type
        }
        
        return {
            "success": True, 
            "message": "Registration validated successfully", 
            "student": student_response
        }
        
    except Exception as e:
        print(f"Error in validate_registration: {str(e)}")
        return {"success": False, "message": f"Error validating registration: {str(e)}"}

@router.post("/events/{event_id}/payment/confirm")
async def confirm_payment(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Handle payment confirmation submission - Updated for new relational mapping system"""
    try:
        # Get
        form_data = dict(await request.form())
        registration_id = form_data.get('registration_id')
        
        # Validate required fields
        if not registration_id:
            raise HTTPException(status_code=400, detail="Missing registration ID")
        
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Find registration using new relational mapping approach
        # Check if registration ID exists in event's registration mapping
        event_registrations = event.get('registrations', {})
        if registration_id not in event_registrations:
            raise HTTPException(status_code=404, detail="Registration not found")
        
        # Get the enrollment number associated with this registration
        enrollment_no = event_registrations[registration_id]
        
        # Verify the logged-in student owns this registration
        if enrollment_no != student.enrollment_no:
            raise HTTPException(status_code=403, detail="You can only confirm payment for your own registration")
        
        # Get student data to access participation details
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        if not student_data:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get the event participation for this registration
        event_participations = student_data.get('event_participations', {})
        if event_id not in event_participations:
            raise HTTPException(status_code=404, detail="Registration not found")        
        participation = event_participations[event_id]
        
        # Update payment status in student's event participation
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": enrollment_no},
            {
                "$set": {
                    f"event_participations.{event_id}.payment_status": "completed",
                    f"event_participations.{event_id}.payment_completed_datetime": datetime.now()
                }
            }
        )
        
        # Determine if it's team registration and prepare team info
        is_team_registration = participation.get('registration_type') in ['team_leader', 'team_participant']
        team_info = None
        
        if is_team_registration:
            # For team registrations, get team information
            team_registration_id = participation.get('team_registration_id')
            if team_registration_id:
                # Get team registration details from event data
                event_team_registrations = event.get('team_registrations', {})
                team_reg_data = event_team_registrations.get(team_registration_id, {})
                
                if team_reg_data:
                    # Build team info for success page
                    participants = []
                    team_participants = team_reg_data.get('participants', [])
                    
                    # Get participant details from student records
                    for participant_enrollment in team_participants:
                        participant_data = await DatabaseOperations.find_one("students", {"enrollment_no": participant_enrollment})
                        if participant_data:
                            participants.append({
                                'full_name': participant_data.get('full_name', 'N/A'),
                                'enrollment_no': participant_enrollment,
                                'department': participant_data.get('department', 'N/A')
                            })
                    
                    team_info = {
                        "team_name": team_reg_data.get('team_name'),
                        "participant_count": len(team_participants) + 1,  # +1 for leader
                        "leader_name": student_data.get('full_name'),
                        "leader_enrollment": enrollment_no,
                        "participants": participants                    }
        
        # Redirect to success page with payment completion message
            return templates.TemplateResponse("client/registration_success.html", {
            "request": request,
            "registrar_id": registration_id,
            "event_name": event.get("event_name", event_id),
            "is_team_registration": is_team_registration,
            "team_info": team_info,
            "payment_completed": True,
            "is_student_logged_in": True,
            "student_data": student_data
        })
        
        # Send payment confirmation email
        try:
            student_email = student_data.get('email')
            if student_email:
                await email_service.send_payment_confirmation(
                    student_email=student_email,
                    student_name=student_data.get('full_name', ''),
                    event_title=event.get("event_name", event_id),
                    event_date=event.get("start_datetime"),
                    event_time=event.get("start_datetime").strftime("%H:%M"),
                    event_location=event.get("venue"),
                    registration_id=registration_id,
                    amount_paid=event.get('registration_fee', 0),
                    payment_method="Online Payment",
                    is_team_registration=is_team_registration,
                    team_name=team_info.get('team_name') if team_info else None
                )
        except Exception as e:
            print(f"Failed to send payment confirmation email: {str(e)}")
            # Continue even if email fails
        
        return templates.TemplateResponse("client/registration_success.html", {
            "request": request,
            "registrar_id": registration_id,
            "event_name": event.get("event_name", event_id),
            "is_team_registration": is_team_registration,
            "team_info": team_info,
            "payment_completed": True,
            "is_student_logged_in": True,
            "student_data": student_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in confirm_payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment confirmation failed")

@router.post("/events/{event_id}/cancel-registration")
async def cancel_registration(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Cancel registration for an event using the new relational mapping approach"""
    try:
        # Get student data
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
        if not student_data:
            raise HTTPException(status_code=404, detail="Student not found")
        
        event_participations = student_data.get('event_participations', {})
        
        # Check if student is registered for this event
        if event_id not in event_participations:
            raise HTTPException(status_code=404, detail="Registration not found for this event")
        
        participation = event_participations[event_id]
        registration_type = participation.get('registration_type')
        
        if registration_type == 'individual':
            # Cancel individual registration
            await cancel_individual_registration(student.enrollment_no, event_id, participation)
            
        elif registration_type == 'team_leader':
            # Only team leaders can cancel team registration
            await cancel_team_registration(student.enrollment_no, event_id, participation)
            
        elif registration_type == 'team_participant':
            # Team participants cannot cancel - only team leader can cancel the entire team
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            event_name = event.get('event_name', 'Event') if event else 'Event'
            return RedirectResponse(
                url=f"/client/dashboard?error=participant_cannot_cancel&event_name={event_name}", 
                status_code=302
            )
        
        # Get event details for response
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        event_name = event.get('event_name', 'Event') if event else 'Event'
        
        # Redirect to dashboard with success message
        return RedirectResponse(
            url=f"/client/dashboard?success=registration_cancelled&event_name={event_name}", 
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in cancel_registration: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration cancellation failed")


async def cancel_individual_registration(enrollment_no: str, event_id: str, participation: dict):
    """Cancel individual registration"""
    registration_id = participation.get('registration_id')
    
    # Remove from student data
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": enrollment_no},
        {"$unset": {f"event_participations.{event_id}": ""}}
    )
    
    # Remove from event registrations mapping
    if registration_id:
        await DatabaseOperations.update_one(
            "events",
            {"event_id": event_id},
            {"$unset": {f"registrations.{registration_id}": ""}}
        )


async def cancel_team_participant(enrollment_no: str, event_id: str, registration_id: str, team_registration_id: str):
    """Cancel individual team participant registration"""
    # Remove participant from student data
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": enrollment_no},
        {"$unset": {f"event_participations.{event_id}": ""}}
    )
    
    # Remove from event registrations mapping
    if registration_id:
        await DatabaseOperations.update_one(
            "events",
            {"event_id": event_id},
            {"$unset": {f"registrations.{registration_id}": ""}}
        )
    
    # Update team registration to remove this participant
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$pull": {f"team_registrations.{team_registration_id}.team_participants": enrollment_no}}
    )
    
    # Update team size
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$inc": {f"team_registrations.{team_registration_id}.total_team_size": -1}}
    )


async def cancel_team_registration(enrollment_no: str, event_id: str, participation: dict):
    """Cancel team registration (handles both team leader and participant)"""
    registration_id = participation.get('registration_id')
    team_registration_id = participation.get('team_registration_id')
    registration_type = participation.get('registration_type')
    
    if registration_type == 'team_leader':
        # If team leader is cancelling, cancel entire team
        await cancel_entire_team(event_id, team_registration_id)
    else:
        # If participant is cancelling, remove just the participant
        await cancel_team_participant(enrollment_no, event_id, registration_id, team_registration_id)


async def cancel_entire_team(event_id: str, team_registration_id: str):
    """Cancel entire team registration"""
    # Get event data to find team details
    event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
    if not event_data:
        return
    
    team_registrations = event_data.get('team_registrations', {})
    if team_registration_id not in team_registrations:
        return
    
    team_reg = team_registrations[team_registration_id]
    team_leader = team_reg.get('team_leader_enrollment')  # Using correct field name
    team_participants = team_reg.get('participants', [])  # Using correct field name
    
    # Handle case where team_leader might be None
    if not team_leader:
        all_members = team_participants
    else:
        all_members = [team_leader] + team_participants
    
    # Remove all team members from student data
    for member_enrollment in all_members:
        if member_enrollment:  # Check if enrollment is not None
            await DatabaseOperations.update_one(
                "students",
                {"enrollment_no": member_enrollment},
                {"$unset": {f"event_participations.{event_id}": ""}}
            )
    
    # Remove individual registration mappings for all team members
    # We need to find and remove all registration IDs that map to team member enrollment numbers
    registrations = event_data.get('registrations', {})
    registration_ids_to_remove = []
    
    for reg_id, member_enrollment in registrations.items():
        if member_enrollment in all_members:
            registration_ids_to_remove.append(reg_id)
    
    # Remove all individual registration mappings for team members
    for reg_id in registration_ids_to_remove:
        await DatabaseOperations.update_one(
            "events",
            {"event_id": event_id},
            {"$unset": {f"registrations.{reg_id}": ""}}
        )
    
    # Remove team registration from event data (do this last)
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$unset": {f"team_registrations.{team_registration_id}": ""}}
    )

@router.get("/events/{event_id}/manage-team")
async def manage_team_get(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Display team management interface for team leaders during registration phase"""
    try:
        from bson import ObjectId, json_util
        import json
        
        # Get student data
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
        if not student_data:
            raise HTTPException(status_code=404, detail="Student not found")
        
        event_participations = student_data.get('event_participations', {})
        
        # Check if student is registered for this event
        if event_id not in event_participations:
            raise HTTPException(status_code=404, detail="Registration not found for this event")
        
        participation = event_participations[event_id]
        registration_type = participation.get('registration_type')
        
        # Only team leaders can manage teams
        if registration_type != 'team_leader':
            raise HTTPException(status_code=403, detail="Only team leaders can manage teams")
        
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
          # Check if event is in registration phase (upcoming with registration_open sub_status)
        if event.get('status') != 'upcoming' or event.get('sub_status') != 'registration_open':
            return templates.TemplateResponse("client/team_management.html", {
                "request": request,
                "event": event,
                "student": student,
                "error": "Team management is only available during the registration phase"
            })
          # Get current team details
        team_registration_id = participation.get('team_registration_id')
        team_details = None
        team_participants = []
        
        if team_registration_id:
            team_registrations = event.get('team_registrations', {})
            team_details = team_registrations.get(team_registration_id, {})
            
            # Get detailed participant information
            if team_details:
                participant_enrollments = team_details.get('participants', [])
                for enrollment in participant_enrollments:
                    participant_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment})
                    if participant_data:                        team_participants.append({
                            "enrollment_no": enrollment,
                            "full_name": participant_data.get('full_name', ''),
                            "email": participant_data.get('email', ''),
                            "mobile_no": participant_data.get('mobile_no', ''),
                            "department": participant_data.get('department', ''),
                            "semester": participant_data.get('semester', '')
                        })
        
        # Create team_info structure that matches template expectations
        team_info = None
        if team_details:
            # Get leader data
            leader_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
            participant_count = len(team_participants) + 1  # +1 for leader
            
            # Calculate departments count
            departments = set()
            if leader_data and leader_data.get('department'):
                departments.add(leader_data.get('department'))
            for participant in team_participants:
                if participant.get('department'):
                    departments.add(participant.get('department'))
            departments_count = len(departments) if departments else 1
              # Format registration date
            registration_date = team_details.get('registration_date')
            if registration_date:
                if isinstance(registration_date, str):
                    formatted_date = registration_date[:10]  # Just the date part
                elif hasattr(registration_date, 'strftime'):  # datetime object
                    formatted_date = registration_date.strftime('%Y-%m-%d')
                else:
                    formatted_date = str(registration_date)  # Convert anything else to string
            else:
                formatted_date = 'N/A'
            
            team_info = {
                "team_name": team_details.get('team_name', 'Unknown Team'),
                "leader_name": leader_data.get('full_name', student.full_name) if leader_data else student.full_name,
                "leader_enrollment": student.enrollment_no,
                "leader_department": leader_data.get('department', 'N/A') if leader_data else 'N/A',
                "leader_email": leader_data.get('email', student.email) if leader_data else student.email,
                "leader_mobile": leader_data.get('mobile_no', 'N/A') if leader_data else 'N/A',
                "participant_count": participant_count,
                "departments_count": departments_count,
                "registration_date": formatted_date,
                "participants": team_participants
            }        # Serialize ObjectIDs in event data to avoid JSON serialization issues
        serialized_event = {}
        for key, value in event.items():
            if isinstance(value, ObjectId):
                serialized_event[key] = str(value)
            else:
                serialized_event[key] = value
        
        return templates.TemplateResponse("client/team_management.html", {
            "request": request,
            "event": serialized_event,
            "student": student,
            "team_details": team_details,
            "team_participants": team_participants,
            "team_info": team_info,
            "team_registration_id": team_registration_id,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
            "is_student_logged_in": True,
            "student_data": student.model_dump()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in manage_team_get: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading team management")

@router.post("/events/{event_id}/manage-team")
async def manage_team_post(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Handle team management actions (add/remove/update participants)"""
    try:
        from bson import ObjectId, json_util
        import json
        
        form_data = await request.form()
        action = form_data.get("action")
        
        # Get student data
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
        if not student_data:
            raise HTTPException(status_code=404, detail="Student not found")
        
        event_participations = student_data.get('event_participations', {})
        
        # Check if student is team leader for this event
        if event_id not in event_participations:
            raise HTTPException(status_code=404, detail="Registration not found for this event")
        
        participation = event_participations[event_id]
        if participation.get('registration_type') != 'team_leader':
            raise HTTPException(status_code=403, detail="Only team leaders can manage teams")
          # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event or event.get('status') != 'upcoming' or event.get('sub_status') != 'registration_open':
            raise HTTPException(status_code=400, detail="Team management is only available during registration phase")
        
        team_registration_id = participation.get('team_registration_id')
        
        if action == "add_participant":
            await add_team_participant(event_id, team_registration_id, form_data)
        elif action == "remove_participant":
            await remove_team_participant(event_id, team_registration_id, form_data)
        elif action == "update_participant":
            await update_team_participant(event_id, team_registration_id, form_data)
        
        # Redirect back to team management page with success message
        return RedirectResponse(
            url=f"/client/events/{event_id}/manage-team?success=team_updated", 
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in manage_team_post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating team")

async def add_team_participant(event_id: str, team_registration_id: str, form_data: dict):
    """Add a participant to the team registration after validation and confirmation"""
    from bson import ObjectId, json_util
    import json
    
    enrollment_no = form_data.get("participant_enrollment").strip()
    
    # Validate enrollment number
    if not enrollment_no:
        raise HTTPException(status_code=400, detail="Enrollment number is required")
    
    # Check if the participant exists in students database
    existing_participant = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    if not existing_participant:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    # Get event details to check team size limits
    event = await DatabaseOperations.find_one("events", {"event_id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Get current team details
    team_details = event.get('team_registrations', {}).get(team_registration_id, {})
    current_team_size = len(team_details.get('participants', [])) + 1  # +1 for team leader
    max_team_size = event.get('team_size_max', 5)
    
    # Check team size limit
    if current_team_size >= max_team_size:
        raise HTTPException(status_code=400, detail=f"Team size cannot exceed the maximum limit of {max_team_size} participants")
    
    # Check if student is already part of this team
    if enrollment_no in team_details.get('participants', []) or enrollment_no == team_details.get('team_leader_enrollment'):
        raise HTTPException(status_code=400, detail="This student is already part of the team")
                
        # Check if already registered for this event
    event_participations = existing_participant.get('event_participations', {})
    if event_id in event_participations:
        raise HTTPException(status_code=400, detail="Participant is already registered for this event")
      # Generate only registration ID for the new participant - other IDs will be generated when needed
    participant_registration_id = generate_registration_id(enrollment_no, event_id, existing_participant.get('full_name', ''))
    
    # Create event participation record for new participant with only registration_id
    participant_participation = EventParticipation(
        registration_id=participant_registration_id,
        attendance_id=None,  # Generated when attendance is marked
        feedback_id=None,    # Generated when feedback is submitted
        certificate_id=None, # Generated when certificate is collected
        registration_type="team_participant",
        team_registration_id=team_registration_id,
        registration_datetime=datetime.now(),
        student_data={
            "full_name": existing_participant.get('full_name', ''),
            "email": existing_participant.get('email', ''),
            "mobile_no": existing_participant.get('mobile_no', ''),
            "department": existing_participant.get('department', ''),
            "semester": existing_participant.get('semester', ''),
            "gender": existing_participant.get('gender', ''),
            "date_of_birth": existing_participant.get('date_of_birth', None)
        }
    )
    
    # Add to student's event participations
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": enrollment_no},
        {"$set": {f"event_participations.{event_id}": participant_participation.model_dump()}}
    )
    
    # Add participant to event registrations mapping
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$set": {f"registrations.{participant_registration_id}": enrollment_no}}
    )
    
    # Add participant to team registration in event data
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$addToSet": {f"team_registrations.{team_registration_id}.participants": enrollment_no}}
    )

async def remove_team_participant(event_id: str, team_registration_id: str, form_data: dict):
    """Remove a participant from the team registration"""
    from bson import ObjectId, json_util
    import json
    
    enrollment_no = form_data.get("participant_enrollment").strip()
    
    # Validate enrollment number
    if not enrollment_no:
        raise HTTPException(status_code=400, detail="Enrollment number is required")
        
    # Get event details to check team size limits
    event = await DatabaseOperations.find_one("events", {"event_id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Get current team details
    team_details = event.get('team_registrations', {}).get(team_registration_id, {})
    current_team_size = len(team_details.get('participants', [])) + 1  # +1 for team leader
    min_team_size = event.get('team_size_min', 2)
    
    # Check minimum team size
    if current_team_size <= min_team_size:
        raise HTTPException(status_code=400, detail=f"Team size cannot be less than the minimum of {min_team_size} participants")
    
    # Get the participant's registration ID BEFORE removing event participation
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    registration_id = None
    if student_data:
        event_participations = student_data.get('event_participations', {})
        if event_id in event_participations:
            registration_id = event_participations[event_id].get('registration_id')
    
    # Remove from student's event participations
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": enrollment_no},
        {"$unset": {f"event_participations.{event_id}": ""}}
    )
    
    # Remove from event registrations mapping if registration ID was found
    if registration_id:
        await DatabaseOperations.update_one(
            "events",
            {"event_id": event_id},
            {"$unset": {f"registrations.{registration_id}": ""}}
        )
    
    # Remove participant from team registration in event data
    await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$pull": {f"team_registrations.{team_registration_id}.participants": enrollment_no}}
    )

async def update_team_participant(event_id: str, team_registration_id: str, form_data: dict):
    """Update details of a team participant"""
    enrollment_no = form_data.get("participant_enrollment").strip()
    full_name = form_data.get("participant_name").strip()
    email = form_data.get("participant_email").strip()
    mobile_no = form_data.get("participant_mobile").strip()
    
    # Validate enrollment number
    if not enrollment_no:
        raise HTTPException(status_code=400, detail="Enrollment number is required")
    
    # Update participant details in student data
    update_fields = {}
    if full_name:
        update_fields["full_name"] = full_name
    if email:
        update_fields["email"] = email
    if mobile_no:
        update_fields["mobile_no"] = mobile_no
    
    if update_fields:
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": enrollment_no},
            {"$set": update_fields}
        )
        
        # Update the student_data in the event participation as well
        student_data_updates = {}
        for field, value in update_fields.items():
            student_data_updates[f"event_participations.{event_id}.student_data.{field}"] = value
        
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": enrollment_no},            {"$set": student_data_updates}
        )


@router.get("/events/{event_id}/mark-attendance")
async def show_attendance_form(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Display the attendance marking form for an event - requires student login"""
    try:
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if the event is active/happening now
        current_datetime = datetime.now()
        event_start = None
        event_end = None
        
        # Parse event start and end dates (handling both legacy and new formats)
        if "start_datetime" in event:
            try:
                if isinstance(event["start_datetime"], str):
                    event_start = datetime.fromisoformat(event["start_datetime"].replace('Z', '+00:00') if 'Z' in event["start_datetime"] else event["start_datetime"])
                elif isinstance(event["start_datetime"], datetime):
                    event_start = event["start_datetime"]
            except (ValueError, TypeError):
                event_start = None
        elif "start_date" in event and "start_time" in event:
            try:
                event_start = datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                event_start = None
                
        if "end_datetime" in event:
            try:
                if isinstance(event["end_datetime"], str):
                    event_end = datetime.fromisoformat(event["end_datetime"].replace('Z', '+00:00') if 'Z' in event["end_datetime"] else event["end_datetime"])
                elif isinstance(event["end_datetime"], datetime):
                    event_end = event["end_datetime"]
            except (ValueError, TypeError):
                event_end = None
        elif "end_date" in event and "end_time" in event:
            try:
                event_end = datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                event_end = None
        
        # Check if the event is in progress or within allowed window for attendance
        is_event_active = True  # Default to active for testing
        attendance_window = timedelta(hours=1)  # Allow marking attendance 1 hour before and after event
        
        if event_start and event_end:
            current_with_buffer = current_datetime - attendance_window
            event_end_with_buffer = event_end + attendance_window
            is_event_active = (current_with_buffer <= event_end) and (current_datetime <= event_end_with_buffer)
        
        # Check if the student is registered for this event
        student_id = student.enrollment_no
        is_registered = False
        registration_id = None
        
        # Check in the registrations data of the event
        registrations = event.get("registrations", {})
        if isinstance(registrations, dict):
            for reg_id, enrolled_id in registrations.items():
                if enrolled_id == student_id:
                    is_registered = True
                    registration_id = reg_id
                    break
        elif isinstance(registrations, list):
            for reg in registrations:
                if isinstance(reg, dict) and reg.get("enrollment_no") == student_id:
                    is_registered = True
                    registration_id = reg.get("registration_id")
                    break        # Check if attendance was already marked - method 1: check attendance collection
        attendance_records = await DatabaseOperations.find_many("attendance", {
            "event_id": event_id,
            "enrollment_no": student_id
        })
        
        # Convert the MongoDB cursor to a list of dictionaries
        attendance_records_list = []
        for record in attendance_records:
            # Convert any datetime objects to strings
            serialized_record = {}
            for key, value in record.items():
                if isinstance(value, datetime):
                    serialized_record[key] = value.isoformat()
                else:
                    serialized_record[key] = value
            attendance_records_list.append(serialized_record)
          # Method 2: Check if attendance is marked in the event document
        event_attendances = event.get("attendances", {})
        if not attendance_records_list and isinstance(event_attendances, dict):
            # Check if student's enrollment number exists in the attendance details
            for att_id, att_details in event_attendances.items():
                if isinstance(att_details, dict) and att_details.get("enrollment_no") == student_id:
                    # First try to find the full attendance record from the attendance collection
                    att_record = await DatabaseOperations.find_one("attendance", {"attendance_id": att_id})
                    if att_record:
                        # Convert datetime objects to strings
                        serialized_record = {}
                        for key, value in att_record.items():
                            if isinstance(value, datetime):
                                serialized_record[key] = value.isoformat()
                            else:
                                serialized_record[key] = value
                        attendance_records_list.append(serialized_record)
                    else:
                        # If record not in attendance collection, use data from event document
                        attendance_records_list.append({
                            "attendance_id": att_id,
                            "enrollment_no": att_details.get("enrollment_no"),
                            "full_name": att_details.get("full_name"),
                            "event_id": event_id,
                            "attendance_marked_at": att_details.get("marked_at"),
                            "attendance_status": att_details.get("status", "present")
                        })
        
        attendance_already_marked = len(attendance_records_list) > 0
          # Create a new dictionary with serialized values to prevent datetime serialization issues
        serialized_event = {}
        for key, value in event.items():
            if isinstance(value, datetime):
                serialized_event[key] = value.isoformat()
            else:
                serialized_event[key] = value
                
        # Add attendances field if it doesn't exist (for backward compatibility)
        if "attendances" not in serialized_event:
            serialized_event["attendances"] = {}
        
        # Add formatted datetime strings
        if event_start:
            serialized_event["formatted_start"] = event_start.strftime("%Y-%m-%d %H:%M")
        if event_end:
            serialized_event["formatted_end"] = event_end.strftime("%Y-%m-%d %H:%M")
        
        current_time_formatted = current_datetime.strftime("%Y-%m-%d %H:%M")
        
        # Serialize student data
        serialized_student = student.model_dump()
          # Check if attendance was already marked and redirect to success page if it was
        if attendance_already_marked and len(attendance_records_list) > 0:
            # Use the first attendance record
            existing_attendance = attendance_records_list[0]
            
            # Return the attendance success template directly
            return templates.TemplateResponse("client/attendance_success.html", {
                "request": request,
                "event": serialized_event,
                "student": serialized_student,
                "already_marked": True,
                "attendance": existing_attendance,
                "registration": {
                    "registrar_id": registration_id,
                    "full_name": student.full_name
                },
                "is_student_logged_in": True,
                "student_data": serialized_student
            })
              # If student is not registered, redirect to not_registered page
        if not is_registered:
            return templates.TemplateResponse("client/not_registered.html", {
                "request": request,
                "event": serialized_event,
                "student": serialized_student,
                "is_student_logged_in": True,
                "student_data": serialized_student
            })
        
        # Prepare registration data if student is registered
        registration_data = None
        auto_filled = False
        if is_registered:
            # Get student's participation data for this event
            student_doc = await DatabaseOperations.find_one("students", {"enrollment_no": student_id})
            if student_doc and "event_participations" in student_doc and event_id in student_doc["event_participations"]:
                participation = student_doc["event_participations"][event_id]
                
                # Create registration data object for template
                registration_data = {
                    "registrar_id": registration_id,
                    "enrollment_no": student_id,
                    "full_name": student.full_name,
                    "email": student.email,
                    "mobile_no": student.mobile_no,
                    "department": student.department,
                    "registration_type": participation.get("registration_type", "individual")
                }
                auto_filled = True
        
        return templates.TemplateResponse("client/mark_attendance.html", {
            "request": request,
            "event": serialized_event,
            "student": serialized_student,
            "is_registered": is_registered,
            "registration_id": registration_id,
            "registration": registration_data,  # Add registration data for auto-filling
            "auto_filled": auto_filled,  # Flag to indicate auto-filled data
            "is_event_active": is_event_active,
            "attendance_already_marked": attendance_already_marked,
            "attendance_records": attendance_records_list,
            "current_time": current_time_formatted,
            "is_student_logged_in": True,
            "student_data": serialized_student
        })
        
    except Exception as e:
        print(f"Error in show_attendance_form: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/{event_id}/mark-attendance")
async def submit_attendance(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Handle attendance form submission"""
    try:
        # Get form data
        form_data = dict(await request.form())
        
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
          # Create a serialized version of the event
        serialized_event = {}
        for key, value in event.items():
            if isinstance(value, datetime):
                serialized_event[key] = value.isoformat()
            else:
                serialized_event[key] = value
                
        # Add attendances field if it doesn't exist (for backward compatibility)
        if "attendances" not in serialized_event:
            serialized_event["attendances"] = {}
        
        # Check if the student is registered for this event
        student_id = student.enrollment_no
        is_registered = False
        registration_id = form_data.get("registration_id")
        
        # If registration_id is provided in form, verify it exists for this event
        if registration_id:
            # Check in the registrations data of the event
            registrations = event.get("registrations", {})
            if isinstance(registrations, dict):
                for reg_id, enrolled_id in registrations.items():
                    if reg_id == registration_id:
                        is_registered = True
                        # Verify submitted enrollment matches the enrollment associated with this registration
                        if enrolled_id != student_id:
                            return templates.TemplateResponse("client/mark_attendance.html", {
                                "request": request,
                                "event": serialized_event,
                                "student": student.model_dump(),
                                "is_registered": False,
                                "error": "Registration ID does not match your student account",
                                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "is_student_logged_in": True,
                                "student_data": student.model_dump()
                            }, status_code=400)
                        break
            elif isinstance(registrations, list):
                for reg in registrations:
                    if isinstance(reg, dict) and reg.get("registration_id") == registration_id:
                        is_registered = True
                        break        # If no registration_id provided, check if student is registered by enrollment
        else:
            # Check in the registrations data of the event
            registrations = event.get("registrations", {})
            if isinstance(registrations, dict):
                for reg_id, enrolled_id in registrations.items():
                    if enrolled_id == student_id:
                        is_registered = True
                        registration_id = reg_id
                        break
            elif isinstance(registrations, list):
                for reg in registrations:
                    if isinstance(reg, dict) and reg.get("enrollment_no") == student_id:
                        is_registered = True
                        registration_id = reg.get("registration_id")
                        break
        
        # If student is not registered, redirect to not_registered page
        if not is_registered:
            return templates.TemplateResponse("client/not_registered.html", {
                "request": request,
                "event": serialized_event,
                "student": student.model_dump(),
                "is_student_logged_in": True,
                "student_data": student.model_dump()
            })
          # Check if attendance was already marked - method 1: check attendance collection
        existing_attendance = await DatabaseOperations.find_one("attendance", {
            "event_id": event_id,
            "enrollment_no": student_id
        })
          # Method 2: Check if attendance is marked in the event document
        if not existing_attendance:
            event_attendances = event.get("attendances", {})
            if isinstance(event_attendances, dict):
                # Check if student's enrollment number exists in the attendance details
                for att_id, att_details in event_attendances.items():
                    if isinstance(att_details, dict) and att_details.get("enrollment_no") == student_id:
                        # First try to find the full attendance record from attendance collection
                        att_record = await DatabaseOperations.find_one("attendance", {"attendance_id": att_id})
                        if att_record:
                            existing_attendance = att_record
                        else:
                            # If not found in attendance collection, create a record from event data
                            existing_attendance = {
                                "attendance_id": att_id,
                                "enrollment_no": att_details.get("enrollment_no"),
                                "full_name": att_details.get("full_name"),
                                "event_id": event_id,
                                "attendance_marked_at": att_details.get("marked_at"),
                                "attendance_status": att_details.get("status", "present")
                            }
                        break
        
        if existing_attendance:
            # Serialize the existing attendance record
            serialized_attendance = {}
            for key, value in existing_attendance.items():
                if isinstance(value, datetime):
                    serialized_attendance[key] = value.isoformat()
                else:
                    serialized_attendance[key] = value
            
            # Format attendance time if available
            attendance_time = existing_attendance.get("attendance_marked_at")
            if isinstance(attendance_time, datetime):
                attendance_time_formatted = attendance_time.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(attendance_time, str):
                try:
                    # Try to parse as datetime if it's a string
                    parsed_time = datetime.fromisoformat(attendance_time.replace('Z', '+00:00') if 'Z' in attendance_time else attendance_time)
                    attendance_time_formatted = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    attendance_time_formatted = attendance_time
            else:
                attendance_time_formatted = str(attendance_time) if attendance_time is not None else "Unknown"
                
            return templates.TemplateResponse("client/attendance_success.html", {
                "request": request,
                "event": serialized_event,
                "student": student.model_dump(),
                "already_marked": True,
                "attendance": serialized_attendance,
                "registration": {
                    "registrar_id": registration_id,
                    "full_name": student.full_name
                },
                "is_student_logged_in": True,
                "student_data": student.model_dump()
            })            
        # Generate a new attendance ID with the required parameters
        try:
            attendance_id = generate_attendance_id(enrollment_no=student.enrollment_no, event_id=event_id)
        except Exception as e:
            print(f"Error generating attendance ID: {str(e)}")
            # Fallback to a simple format if the ID generation fails
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            attendance_id = f"ATT{student.enrollment_no[:4]}{timestamp[-6:]}"
        
        # Create attendance record
        attendance_record = {
            "attendance_id": attendance_id,
            "registration_id": registration_id,
            "event_id": event_id,
            "enrollment_no": student.enrollment_no,
            "full_name": student.full_name,
            "email": student.email,
            "mobile_no": student.mobile_no,
            "department": student.department,
            "semester": student.semester,
            "event_name": event.get("event_name", ""),
            "attendance_marked_at": datetime.now().isoformat(),
            "marked_by": "Student Self-Service",
            "attendance_status": "present"
        }
        
        # Save attendance record to database
        db = await Database.get_database()
        result = await db["attendance"].insert_one(attendance_record)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to record attendance")
              # Update student's attendance record in their profile
        # Fetch the most recent student data to ensure we're working with current data
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student.enrollment_no})
        if not student_data:
            # If student data not found, use what we have in the model
            student_data = student.model_dump()
        
        # Ensure event_participations exists in the student data
        if "event_participations" not in student_data:
            student_data["event_participations"] = {}
        
        # Update or create the participation record for this event
        if event_id not in student_data["event_participations"]:
            # Create a new participation record if one doesn't exist
            student_data["event_participations"][event_id] = {
                "registration_id": registration_id,
                "registration_date": datetime.now().isoformat(),
                "registration_type": "individual",  # Default to individual
                "participation_status": "registered"
            }
        
        # Add attendance information to the participation record
        student_data["event_participations"][event_id]["attendance_id"] = attendance_id
        student_data["event_participations"][event_id]["attendance_marked_at"] = attendance_record["attendance_marked_at"]
        student_data["event_participations"][event_id]["attendance_status"] = "present"
                
        # Update the student record in the database
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": student.enrollment_no},
            {"$set": {"event_participations": student_data["event_participations"]}}
        )
          # Also store attendance record in event document for easier lookup
        # Create attendance details dictionary according to the model's expectation
        attendance_details = {
            "enrollment_no": student.enrollment_no,
            "full_name": student.full_name,
            "marked_at": attendance_record["attendance_marked_at"],
            "status": "present"
        }
        
        await DatabaseOperations.update_one(
            "events",
            {"event_id": event_id},
            {"$set": {f"attendances.{attendance_id}": attendance_details}}
        )
        
        # Update attendance count in event document
        await DatabaseOperations.update_one(
            "events",
            {"event_id": event_id},
            {"$inc": {"attendance_count": 1}}
        )
        
        # Send attendance confirmation email
        try:
            # Format attendance date string properly from the ISO string
            attendance_iso_date = attendance_record["attendance_marked_at"]
            formatted_date = attendance_iso_date.split('T')[0] if 'T' in attendance_iso_date else attendance_iso_date[:10]
            
            await email_service.send_attendance_confirmation(
                student_email=student.email,
                student_name=student.full_name,
                event_title=event.get("event_name", "Unknown Event"),
                attendance_date=formatted_date,
                event_venue=event.get("venue", "Not specified"),
                attendance_id=attendance_id,
                attendance_time=attendance_record["attendance_marked_at"]
            )
        except Exception as e:
            print(f"Failed to send attendance confirmation email: {str(e)}")
       # Return success response
        return templates.TemplateResponse("client/attendance_success.html", {
            "request": request,
            "event": serialized_event,
            "student": student.model_dump(),
            "already_marked": False,
            "attendance": attendance_record,
            "registration": {
                "registrar_id": registration_id,
                "full_name": student.full_name
            },
            "is_student_logged_in": True,
            "student_data": student.model_dump()
        })
        
    except Exception as e:
        print(f"Error in submit_attendance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/{event_id}/attendance-stats")
async def get_attendance_stats(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Get attendance statistics for an event"""
    try:
        # Only allow super admin and admin users to access this route
        # Check if user is a super admin or has admin role
        if student.role not in ["super_admin", "admin", "organizer"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")
            
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
              # Get attendances from event document
        attendances = event.get("attendances", {})
        attendance_count = len(attendances) if attendances else 0
        
        # If there are attendances in the event document, add them to the attendance list
        if attendances and isinstance(attendances, dict):
            for att_id, att_details in attendances.items():
                if isinstance(att_details, dict):
                    # Add department to stats if not already there
                    department = att_details.get("department", "Unknown")
                    if department not in departments_stats:
                        departments_stats[department] = 0
                    departments_stats[department] += 1
        
        # Get total registrations count
        registrations = event.get("registrations", {})
        registration_count = len(registrations) if isinstance(registrations, dict) else 0
        
        # Calculate attendance percentage
        attendance_percentage = 0
        if registration_count > 0:
            attendance_percentage = (attendance_count / registration_count) * 100
            
        # Get attendance records from attendance collection for more details
        attendance_records = await DatabaseOperations.find_many("attendance", {"event_id": event_id})
        attendance_list = []
        departments_stats = {}
        
        # Process attendance records
        async for record in attendance_records:
            # Add to attendance list
            attendance_list.append({
                "attendance_id": record.get("attendance_id"),
                "enrollment_no": record.get("enrollment_no"),
                "full_name": record.get("full_name"),
                "department": record.get("department"),
                "marked_at": record.get("attendance_marked_at")
            })
            
            # Update department statistics
            department = record.get("department", "Unknown")
            if department not in departments_stats:
                departments_stats[department] = 0
            departments_stats[department] += 1
            
        # Create stats response
        stats = {
            "event_id": event_id,
            "event_name": event.get("event_name", ""),
            "total_registrations": registration_count,
            "total_attendance": attendance_count,
            "attendance_percentage": round(attendance_percentage, 2),
            "departments": departments_stats,
            "attendance_list": attendance_list
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_attendance_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/{event_id}/fix-attendances")
async def fix_attendances(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Fix attendance records that might be in the old format"""
    try:
        # Check admin permissions
        if student.role not in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")
            
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if attendances exist and need fixing
        attendances = event.get("attendances", {})
        fixed_count = 0
        
        if attendances:
            fixed_attendances = {}
            
            # Go through each attendance record
            for att_id, att_value in attendances.items():
                if isinstance(att_value, str):
                    # This is an old format record (attendance_id: enrollment_no)
                    enrollment_no = att_value
                    
                    # Find student details
                    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
                    
                    if student_data:
                        # Look for attendance record in the attendance collection
                        att_record = await DatabaseOperations.find_one("attendance", {"attendance_id": att_id})
                        
                        if att_record:
                            # Create attendance details from the record
                            fixed_attendances[att_id] = {
                                "enrollment_no": enrollment_no,
                                "full_name": att_record.get("full_name", student_data.get("full_name", "Unknown")),
                                "marked_at": att_record.get("attendance_marked_at", datetime.now().isoformat()),
                                "status": att_record.get("attendance_status", "present")
                            }
                        else:
                            # Create attendance details from student data
                            fixed_attendances[att_id] = {
                                "enrollment_no": enrollment_no,
                                "full_name": student_data.get("full_name", "Unknown"),
                                "marked_at": datetime.now().isoformat(),
                                "status": "present"
                            }
                        
                        fixed_count += 1
                elif isinstance(att_value, dict):
                    # This is already in the correct format
                    fixed_attendances[att_id] = att_value
            
            # Update the event document with fixed attendances
            if fixed_count > 0:
                await DatabaseOperations.update_one(
                    "events",
                    {"event_id": event_id},
                    {"$set": {"attendances": fixed_attendances}}
                )
        
        return {
            "success": True,
            "message": f"Fixed {fixed_count} attendance records",
            "event_id": event_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in fix_attendances: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/tools/fix-attendance-format/{event_id}")
async def fix_attendance_format(request: Request, event_id: str, student: Student = Depends(require_student_login)):
    """Utility function to fix attendance format for events with string values in attendances field"""
    try:
        # Check if user has admin privileges
        if student.role not in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")
            
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
            
        # Get attendances field
        attendances = event.get("attendances", {})
        if not attendances:
            return {"status": "success", "message": "No attendances found in event"}
            
        updates_made = 0
        
        # Check each attendance record
        for att_id, att_value in list(attendances.items()):  # Use list() to avoid dictionary size change during iteration
            if isinstance(att_value, str):
                # This is old format - convert to new format
                enrollment_no = att_value
                
                # Find student details
                student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
                
                if student_data:
                    full_name = student_data.get("full_name", "Unknown")
                else:
                    full_name = "Unknown"
                    
                # Try to find attendance record in attendance collection
                att_record = await DatabaseOperations.find_one("attendance", {"attendance_id": att_id})
                marked_at = None
                
                if att_record:
                    marked_at = att_record.get("attendance_marked_at")
                
                # If no marked_at found, use current time
                if not marked_at:
                    marked_at = datetime.now().isoformat()
                    
                # Create new attendance details dictionary
                new_att_details = {
                    "enrollment_no": enrollment_no,
                    "full_name": full_name,
                    "marked_at": marked_at,
                    "status": "present"
                }
                
                # Update in event document
                await DatabaseOperations.update_one(
                    "events",
                    {"event_id": event_id},
                    {"$set": {f"attendances.{att_id}": new_att_details}}
                )
                
                updates_made += 1
        
        return {
            "status": "success", 
            "message": f"Fixed {updates_made} attendance records", 
            "event_id": event_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in fix_attendance_format: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))