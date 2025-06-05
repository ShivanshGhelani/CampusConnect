#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_operations import DatabaseOperations

async def test_team_cancellation_complete():
    """Test complete team cancellation data cleanup"""
    
    print("=== Testing Team Cancellation Data Cleanup ===\n")
    
    # Test data
    event_id = "AI_ML_BO_30043"
    team_registration_id = "TEAM_AI_ML_BO_30043_B953"
    team_leader = "KU2023CSE2054"
    team_participants = ["KU2023CSE2053", "KU2023CSE2055"]
    all_members = [team_leader] + team_participants
    
    print(f"Event ID: {event_id}")
    print(f"Team Registration ID: {team_registration_id}")
    print(f"Team Leader: {team_leader}")
    print(f"Team Participants: {team_participants}")
    print(f"All Members: {all_members}\n")
    
    # 1. Check current data state
    print("1. Current Data State:")
    print("-" * 40)
    
    # Check event data
    event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
    if event_data:
        team_registrations = event_data.get('team_registrations', {})
        registrations = event_data.get('registrations', {})
        
        print(f"Team registrations in event: {list(team_registrations.keys())}")
        print(f"Individual registrations in event: {len(registrations)} total")
        
        # Count registrations for team members
        team_member_regs = {reg_id: enrollment for reg_id, enrollment in registrations.items() 
                           if enrollment in all_members}
        print(f"Team member registrations: {len(team_member_regs)}")
        for reg_id, enrollment in team_member_regs.items():
            print(f"  {reg_id}: {enrollment}")
    
    # Check student data
    print("\nStudent Event Participations:")
    for enrollment in all_members:
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment})
        if student_data:
            event_participations = student_data.get('event_participations', {})
            if event_id in event_participations:
                participation = event_participations[event_id]
                print(f"  {enrollment}: {participation.get('registration_type', 'unknown')} - Team ID: {participation.get('team_registration_id', 'None')}")
            else:
                print(f"  {enrollment}: No participation found")
        else:
            print(f"  {enrollment}: Student not found")
    
    print("\n" + "="*60)
    
    # 2. Simulate the cancel_entire_team function
    print("\n2. Simulating Team Cancellation:")
    print("-" * 40)
    
    if not event_data:
        print("ERROR: Event not found!")
        return
    
    team_registrations = event_data.get('team_registrations', {})
    if team_registration_id not in team_registrations:
        print("ERROR: Team registration not found!")
        return
    
    team_reg = team_registrations[team_registration_id]
    found_leader = team_reg.get('team_leader')
    found_participants = team_reg.get('team_participants', [])
    found_members = [found_leader] + found_participants
    
    print(f"Found team leader: {found_leader}")
    print(f"Found team participants: {found_participants}")
    print(f"Found all members: {found_members}")
    
    # Step 1: Remove event participations from student records
    print("\nRemoving event participations from student records...")
    for member_enrollment in found_members:
        if member_enrollment:  # Check for None values
            result = await DatabaseOperations.update_one(
                "students",
                {"enrollment_no": member_enrollment},
                {"$unset": {f"event_participations.{event_id}": ""}}
            )
            print(f"  Updated {member_enrollment}: {result.modified_count} records modified")
    
    # Step 2: Remove team registration from event data
    print("\nRemoving team registration from event data...")
    result = await DatabaseOperations.update_one(
        "events",
        {"event_id": event_id},
        {"$unset": {f"team_registrations.{team_registration_id}": ""}}
    )
    print(f"  Removed team registration: {result.modified_count} records modified")
    
    # Step 3: Remove individual registration mappings
    print("\nRemoving individual registration mappings...")
    registrations = event_data.get('registrations', {})
    removed_count = 0
    for reg_id, member_enrollment in registrations.items():
        if member_enrollment in found_members:
            result = await DatabaseOperations.update_one(
                "events",
                {"event_id": event_id},
                {"$unset": {f"registrations.{reg_id}": ""}}
            )
            print(f"  Removed registration {reg_id} ({member_enrollment}): {result.modified_count} records modified")
            removed_count += 1
    
    print(f"\nTotal individual registrations removed: {removed_count}")
    
    print("\n" + "="*60)
    
    # 3. Verify cleanup
    print("\n3. Verification After Cleanup:")
    print("-" * 40)
    
    # Check event data after cleanup
    event_data_after = await DatabaseOperations.find_one("events", {"event_id": event_id})
    if event_data_after:
        team_registrations_after = event_data_after.get('team_registrations', {})
        registrations_after = event_data_after.get('registrations', {})
        
        print(f"Team registrations remaining: {list(team_registrations_after.keys())}")
        print(f"Individual registrations remaining: {len(registrations_after)} total")
        
        # Check if any team member registrations remain
        remaining_team_regs = {reg_id: enrollment for reg_id, enrollment in registrations_after.items() 
                              if enrollment in found_members}
        print(f"Team member registrations remaining: {len(remaining_team_regs)}")
        if remaining_team_regs:
            for reg_id, enrollment in remaining_team_regs.items():
                print(f"  STILL EXISTS: {reg_id}: {enrollment}")
    
    # Check student data after cleanup
    print("\nStudent Event Participations After Cleanup:")
    for enrollment in found_members:
        if enrollment:  # Check for None values
            student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment})
            if student_data:
                event_participations = student_data.get('event_participations', {})
                if event_id in event_participations:
                    participation = event_participations[event_id]
                    print(f"  STILL EXISTS: {enrollment}: {participation.get('registration_type', 'unknown')}")
                else:
                    print(f"  CLEANED: {enrollment}: No participation found")
            else:
                print(f"  ERROR: {enrollment}: Student not found")
    
    print("\n" + "="*60)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_team_cancellation_complete())
