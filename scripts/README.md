# Scripts Directory

This directory contains various utility scripts organized by purpose:

## Debug Scripts (`debug/`)
Scripts for debugging and checking system state:
- `check_data_state.py` - Check current data state in database
- `check_events.py` - Verify event data integrity 
- `check_student_teams.py` - Check student team relationships
- `debug_event_detail.py` - Debug specific event details
- `debug_team_data.py` - Debug team registration data
- `temp_check.py` - Temporary debugging script
- `verify_team_fix.py` - Verify team data fixes

## Data Migration Scripts (`data_migration/`)
Scripts for data cleanup and migration:
- `cleanup_registrations.py` - Clean up registration data to follow proper event lifecycle
- `fix_team_data.py` - Fix team registration data issues
- `fix_team_data_v2.py` - Updated team data fix script
- `recreate_team_data.py` - Recreate team registration data

## Testing Scripts (`testing/`)
Scripts for testing various system functionalities:
- `test_cancel_debug.py` - Test cancellation debugging
- `test_complete_cancel.py` - Test complete cancellation flow
- `test_complete_cancellation.py` - Test comprehensive cancellation
- `test_final_cancel.py` - Final cancellation testing
- `test_registration_flow.py` - Test event registration flow
- `test_team_cancel.py` - Test team cancellation
- `test_team_cancellation.py` - Test team cancellation logic
- `test_team_cancel_final.py` - Final team cancellation tests
- `test_validation_flow.py` - Test event lifecycle validation

## Administrative Scripts (root level)
Core administrative scripts:
- `create_admin.py` - Create admin users
- `delete_events.py` - Delete events from system
- `manage_admins.py` - Manage admin user accounts
- `migrate_admin_roles.py` - Migrate admin role structure
- `migrate_event_data_structure.py` - Migrate event data structure
- `upgrade_to_super_admin.py` - Upgrade admin to super admin

## Usage
All scripts should be run from the main project directory:
```bash
cd s:\Projects\UCG_v2\Admin
python scripts/debug/check_data_state.py
python scripts/data_migration/cleanup_registrations.py
python scripts/testing/test_validation_flow.py
```
