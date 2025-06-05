"""
ID Generation utilities for events, registrations, attendance, feedback, and certificates
"""
import hashlib
from datetime import datetime
from typing import Dict, Any

def generate_registration_id(enrollment_no: str, event_id: str, full_name: str) -> str:
    """
    Generate a memorable registration ID using event and student information
    Format: REG_[EVENT_PREFIX]_[ENROLLMENT_SUFFIX]_[HASH_SUFFIX]
    Example: REG_BLOCK2025_30043_A7B2
    """
    # Extract meaningful parts
    event_prefix = event_id[:8].upper()  # First 8 chars of event ID
    enrollment_suffix = enrollment_no[-5:]  # Last 5 chars of enrollment
    
    # Create a short hash for uniqueness
    hash_input = f"{enrollment_no}_{event_id}_{full_name}_{datetime.now().isoformat()}"
    hash_object = hashlib.md5(hash_input.encode())
    hash_suffix = hash_object.hexdigest()[:4].upper()
    
    return f"REG_{event_prefix}_{enrollment_suffix}_{hash_suffix}"

def generate_attendance_id(enrollment_no: str, event_id: str, session_info: str = "") -> str:
    """
    Generate attendance ID for event sessions
    Format: ATT_[EVENT_PREFIX]_[ENROLLMENT_SUFFIX]_[HASH_SUFFIX]
    Example: ATT_BLOCK2025_30043_B8C3
    """
    event_prefix = event_id[:8].upper()
    enrollment_suffix = enrollment_no[-5:]
    
    hash_input = f"{enrollment_no}_{event_id}_attendance_{session_info}_{datetime.now().isoformat()}"
    hash_object = hashlib.md5(hash_input.encode())
    hash_suffix = hash_object.hexdigest()[:4].upper()
    
    return f"ATT_{event_prefix}_{enrollment_suffix}_{hash_suffix}"

def generate_feedback_id(enrollment_no: str, event_id: str) -> str:
    """
    Generate feedback ID
    Format: FBK_[EVENT_PREFIX]_[ENROLLMENT_SUFFIX]_[HASH_SUFFIX]
    Example: FBK_BLOCK2025_30043_C9D4
    """
    event_prefix = event_id[:8].upper()
    enrollment_suffix = enrollment_no[-5:]
    
    hash_input = f"{enrollment_no}_{event_id}_feedback_{datetime.now().isoformat()}"
    hash_object = hashlib.md5(hash_input.encode())
    hash_suffix = hash_object.hexdigest()[:4].upper()
    
    return f"FBK_{event_prefix}_{enrollment_suffix}_{hash_suffix}"

def generate_certificate_id(enrollment_no: str, event_id: str, full_name: str) -> str:
    """
    Generate certificate ID
    Format: CERT_[EVENT_PREFIX]_[ENROLLMENT_SUFFIX]_[HASH_SUFFIX]
    Example: CERT_BLOCK2025_30043_D1E5
    """
    event_prefix = event_id[:8].upper()
    enrollment_suffix = enrollment_no[-5:]
    
    hash_input = f"{enrollment_no}_{event_id}_certificate_{full_name}_{datetime.now().isoformat()}"
    hash_object = hashlib.md5(hash_input.encode())
    hash_suffix = hash_object.hexdigest()[:4].upper()
    
    return f"CERT_{event_prefix}_{enrollment_suffix}_{hash_suffix}"

def generate_team_registration_id(leader_enrollment: str, event_id: str, team_name: str) -> str:
    """
    Generate team registration ID
    Format: TEAM_[EVENT_PREFIX]_[LEADER_SUFFIX]_[HASH_SUFFIX]
    Example: TEAM_BLOCK2025_30043_F2G6
    """
    event_prefix = event_id[:8].upper()
    leader_suffix = leader_enrollment[-5:]
    
    hash_input = f"{leader_enrollment}_{event_id}_team_{team_name}_{datetime.now().isoformat()}"
    hash_object = hashlib.md5(hash_input.encode())
    hash_suffix = hash_object.hexdigest()[:4].upper()
    
    return f"TEAM_{event_prefix}_{leader_suffix}_{hash_suffix}"
