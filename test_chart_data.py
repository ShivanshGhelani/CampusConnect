#!/usr/bin/env python3
"""
Quick test script to create sample event data for the pie chart testing
"""

import json
import os

def create_sample_event_data():
    """Create sample event data to test the pie chart"""
    
    sample_events = [
        {
            "id": "event_001",
            "title": "Tech Innovation Summit 2025",
            "status": "active",
            "sub_status": "registration_open",
            "type": "hackathon"
        },
        {
            "id": "event_002", 
            "title": "AI Workshop Series",
            "status": "active",
            "sub_status": "live",
            "type": "workshop"
        },
        {
            "id": "event_003",
            "title": "Campus Career Fair",
            "status": "active",
            "sub_status": "registration_not_started",
            "type": "career_fair"
        },
        {
            "id": "event_004",
            "title": "Spring Coding Contest",
            "status": "completed",
            "sub_status": "completed",
            "type": "competition"
        },
        {
            "id": "event_005",
            "title": "Data Science Bootcamp",
            "status": "active",
            "sub_status": "registration_open",
            "type": "workshop"
        },
        {
            "id": "event_006",
            "title": "Cybersecurity Seminar",
            "status": "completed",
            "sub_status": "completed",
            "type": "seminar"
        }
    ]
    
    detailed_status_counts = {
        "registration_open": 0,
        "live": 0,
        "registration_not_started": 0,
        "completed": 0
    }
    
    print("Sample Event Data for Pie Chart Testing")
    print("=" * 50)
    print(f"Total Events: {len(sample_events)}")
    print("\nEvent Breakdown:")
    print("-" * 30)
    
    for event in sample_events:
        status = event.get('status', 'unknown')
        sub_status = event.get('sub_status', '')
        
        print(f"• {event['title']} ({event['id']})")
        print(f"  Status: {status}, Sub-status: {sub_status}")
        
        if status == 'active' and sub_status == 'registration_open':
            detailed_status_counts["registration_open"] += 1
            print(f"  → Chart Category: Registration Open")
        elif status == 'active' and sub_status == 'live':
            detailed_status_counts["live"] += 1
            print(f"  → Chart Category: Live Event")
        elif status == 'active' and sub_status == 'registration_not_started':
            detailed_status_counts["registration_not_started"] += 1
            print(f"  → Chart Category: Registration Not Started")
        elif status == 'completed':
            detailed_status_counts["completed"] += 1
            print(f"  → Chart Category: Completed")
        print()
    
    print("Chart Data Summary:")
    print("-" * 30)
    for key, value in detailed_status_counts.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    total = sum(detailed_status_counts.values())
    print(f"\nTotal for Chart: {total}")
    
    # Calculate percentages
    print("\nChart Percentages:")
    print("-" * 20)
    for key, value in detailed_status_counts.items():
        percentage = (value / total * 100) if total > 0 else 0
        print(f"{key.replace('_', ' ').title()}: {percentage:.1f}%")
    
    return detailed_status_counts

def generate_chart_test_data():
    """Generate the exact data structure that the dashboard expects"""
    
    data = create_sample_event_data()
    
    print("\n" + "=" * 50)
    print("CHART.JS DATA STRUCTURE")
    print("=" * 50)
    
    chart_config = {
        "labels": ["Registration Open", "Live Events", "Not Started", "Completed"],
        "data": [
            data["registration_open"],
            data["live"], 
            data["registration_not_started"],
            data["completed"]
        ],
        "backgroundColor": [
            "#3B82F6",  # Blue for registration open
            "#10B981",  # Green for live events  
            "#F59E0B",  # Yellow for not started
            "#6B7280"   # Gray for completed
        ]
    }
    
    print("Chart Configuration:")
    print(json.dumps(chart_config, indent=2))
    
    return chart_config

if __name__ == "__main__":
    sample_data = generate_chart_test_data()
    
    print("\n" + "=" * 50)
    print("TESTING RECOMMENDATION")
    print("=" * 50)
    print("✅ The pie chart should display with 4 segments:")
    print(f"   • Blue segment: {sample_data['data'][0]} events (Registration Open)")
    print(f"   • Green segment: {sample_data['data'][1]} events (Live Events)")  
    print(f"   • Yellow segment: {sample_data['data'][2]} events (Not Started)")
    print(f"   • Gray segment: {sample_data['data'][3]} events (Completed)")
    print("\n✅ If Chart.js loads successfully, you should see:")
    print("   • A doughnut chart with colored segments")
    print("   • Hover tooltips showing percentages")
    print("   • Custom legend below the chart")
    print("\n❌ If Chart.js fails to load, you should see:")
    print("   • A fallback message with retry button")
    print("   • No chart canvas, but dashboard still functional")
