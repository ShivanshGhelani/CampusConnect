# Event Data Structure Documentation

This document explains the new event data structure implementation that supports both individual and team-based events, with proper payment tracking and separation of concerns.

## Overview

The new data structure supports four types of events:
1. **Individual Free Events**
2. **Individual Paid Events**
3. **Team-based Free Events**
4. **Team-based Paid Events**

## Data Storage Strategy

### In Student Data (`students` collection)

Each student stores their event participations in the `event_participations` field:

```json
{
  "enrollment_no": "22BEIT30043",
  "event_participations": {
    "EVENT_ID": {
      "registration_id": "value",
      "attendance_id": "value",
      "feedback_id": "value", 
      "certificate_id": "value",
      "payment_id": "value",          // For paid events only
      "payment_status": "complete/pending", // For paid events only
      "registration_type": "individual/team_member",
      "team_name": "TeamName"         // For team events only
    }
  }
}
```

### In Event Data (`events` collection)

Events store aggregated data in different arrays based on event type:

#### Individual Events
```json
{
  "event_id": "WORKSHOP_2025",
  "is_paid": false,
  "is_team_based": false,
  "registration_fee": null,
  
  "registrations": {
    "registrar_id": "enrollment_no"
  },
  "attendances": {
    "attendance_id": "enrollment_no"
  },
  "feedbacks": {
    "feedback_id": "enrollment_no"
  },
  "certificates": {
    "certificate_id": "enrollment_no"
  }
}
```

#### Team Events
```json
{
  "event_id": "HACKATHON_2025", 
  "is_paid": true,
  "is_team_based": true,
  "registration_fee": 500.0,
  
  "team_registrations": {
    "TeamName": {
      "member1_enrollment": "registrar_id",
      "member2_enrollment": "registrar_id",
      "payment_id": "value",           // For paid events
      "payment_status": "complete/pending"  // For paid events
    }
  },
  "team_attendances": {
    "TeamName": {
      "member1_enrollment": "attendance_id",
      "member2_enrollment": "attendance_id"
    }
  },
  "team_feedbacks": {
    "TeamName": {
      "member1_enrollment": "feedback_id",
      "member2_enrollment": "feedback_id"
    }
  },
  "team_certificates": {
    "TeamName": {
      "member1_enrollment": "certificate_id",
      "member2_enrollment": "certificate_id"
    }
  }
}
```

## Implementation Details

### 1. Individual Free Events

**Student Data:**
```json
"EVENT_ID": {
  "registration_id": "value",
  "attendance_id": "value", 
  "feedback_id": "value",
  "certificate_id": "value",
  "registration_type": "individual"
}
```

**Event Data:**
```json
"registrations": {
  "registrar_id": "enrollment_no"
},
"attendances": {
  "attendance_id": "enrollment_no"
},
"feedbacks": {
  "feedback_id": "enrollment_no"
},
"certificates": {
  "certificate_id": "enrollment_no"
}
```

### 2. Individual Paid Events

**Student Data:**
```json
"EVENT_ID": {
  "registration_id": "value",
  "attendance_id": "value",
  "feedback_id": "value", 
  "certificate_id": "value",
  "payment_id": "value",
  "payment_status": "complete/pending",
  "registration_type": "individual"
}
```

**Event Data:** Same as individual free events (payment tracking in student data)

### 3. Team-based Free Events

**Student Data:**
```json
"EVENT_ID": {
  "registration_id": "value",
  "attendance_id": "value",
  "feedback_id": "value",
  "certificate_id": "value", 
  "registration_type": "team_member",
  "team_name": "TeamName"
}
```

**Event Data:**
```json
"team_registrations": {
  "TeamName": {
    "member1_enrollment": "registrar_id",
    "member2_enrollment": "registrar_id"
  }
},
"team_attendances": {
  "TeamName": {
    "member1_enrollment": "attendance_id",
    "member2_enrollment": "attendance_id"
  }
},
"team_feedbacks": {
  "TeamName": {
    "member1_enrollment": "feedback_id", 
    "member2_enrollment": "feedback_id"
  }
},
"team_certificates": {
  "TeamName": {
    "member1_enrollment": "certificate_id",
    "member2_enrollment": "certificate_id"
  }
}
```

### 4. Team-based Paid Events

**Student Data:**
```json
"EVENT_ID": {
  "registration_id": "value",
  "attendance_id": "value",
  "feedback_id": "value",
  "certificate_id": "value",
  "payment_id": "value",
  "payment_status": "complete/pending", 
  "registration_type": "team_member",
  "team_name": "TeamName"
}
```

**Event Data:**
```json
"team_registrations": {
  "TeamName": {
    "member1_enrollment": "registrar_id",
    "member2_enrollment": "registrar_id",
    "payment_id": "value",
    "payment_status": "complete/pending"
  }
}
// + same structure for attendances, feedbacks, certificates
```

## API Usage

### Using EventDataManager

```python
from utils.event_data_manager import EventDataManager

# Individual registration
await EventDataManager.add_individual_registration(
    event_id="WORKSHOP_2025",
    enrollment_no="22BEIT30043", 
    registrar_id="REG123",
    is_paid=False
)

# Team registration
await EventDataManager.add_team_registration(
    event_id="HACKATHON_2025",
    team_name="CodeNinjas",
    members=[
        {"enrollment_no": "22BEIT30001", "registrar_id": "REG001"},
        {"enrollment_no": "22BEIT30002", "registrar_id": "REG002"}
    ],
    is_paid=True,
    payment_id="PAY123"
)

# Update payment status
await EventDataManager.update_payment_status(
    event_id="HACKATHON_2025",
    enrollment_no="22BEIT30001", 
    payment_status="complete",
    team_name="CodeNinjas"
)

# Get event statistics
stats = await EventDataManager.get_event_statistics("HACKATHON_2025")
print(f"Total participants: {stats['total_participants']}")
```

## Migration

To migrate existing events to the new structure:

```bash
python scripts/migrate_event_data_structure.py
```

This will:
1. Add new required fields to existing events
2. Migrate old registration data to new format
3. Create sample event configurations
4. Update student participation records

## Benefits

1. **Separation of Concerns**: Registration, attendance, feedback, and certificates are tracked separately
2. **Payment Tracking**: Proper support for paid events with payment status
3. **Team Support**: Native support for team-based events
4. **Scalability**: Easy to query and generate statistics
5. **Consistency**: Same structure for both individual and team events
6. **Backward Compatibility**: Migration script preserves existing data

## Testing

Run the demo script to see the new structure in action:

```bash
python scripts/demo_event_data_structures.py
```

This will demonstrate:
- Individual free event flow
- Individual paid event flow
- Team free event flow
- Team paid event flow
- Event statistics generation
