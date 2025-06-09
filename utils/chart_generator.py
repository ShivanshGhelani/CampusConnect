"""
Chart Generator Module for Server-Side Chart Generation
Uses Plotly to generate static HTML charts that can be embedded in templates
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any


def generate_event_status_pie_chart(detailed_status_counts: Dict[str, int]) -> str:
    """
    Generates a pie chart for event status distribution using Plotly
    
    Args:
        detailed_status_counts: Dictionary containing event counts by status
        
    Returns:
        HTML string of the plotly chart that can be embedded in the template
    """
    # Filter out completed events - only show 3 categories
    active_status_counts = {
        k: v for k, v in detailed_status_counts.items() 
        if k != 'completed'
    }
    
    # Prepare data for the chart
    labels = {
        'registration_open': 'Registration Open',
        'live': 'Live Events',
        'registration_not_started': 'Not Started'
    }
    
    colors = {
        'registration_open': '#3B82F6',  # Blue
        'live': '#10B981',  # Green
        'registration_not_started': '#F59E0B'  # Yellow
    }
    
    # Create labels and values lists
    chart_labels = [labels.get(status, status.replace('_', ' ').title()) for status in active_status_counts.keys()]
    values = list(active_status_counts.values())
    color_values = [colors.get(status, '#6B7280') for status in active_status_counts.keys()]
    
    # Calculate total for percentage display
    total = sum(values)
    
    # If no data, return placeholder message
    if total == 0:
        return '<div class="flex items-center justify-center h-80 text-gray-500">' + \
               '<div class="text-center">' + \
               '<i class="fas fa-chart-pie text-4xl mb-4"></i>' + \
               '<p class="text-lg font-medium">No event data available</p>' + \
               '<p class="text-sm">Chart will appear when events are created</p>' + \
               '</div></div>'
    
    # Create the pie chart with Plotly
    fig = go.Figure(data=[go.Pie(
        labels=chart_labels,
        values=values,
        hole=.6,  # Make it a donut chart
        marker=dict(colors=color_values),
        textinfo='percent',
        hoverinfo='label+value+percent',
        textfont_size=14,
    )])
    
    # Configure layout
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        height=400,
        width=500,
        font=dict(
            family="Arial, sans-serif",
            size=12,
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title={
            'text': f"Event Status Distribution ({total} total)",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    # Generate HTML
    return fig.to_html(include_plotlyjs='cdn', full_html=False)


def generate_activity_timeline_chart(activity_data: List[Dict[str, Any]]) -> str:
    """
    Generates a timeline chart for event activities
    
    Args:
        activity_data: List of activity logs 
        
    Returns:
        HTML string of the plotly chart that can be embedded in the template
    """
    # If no data, return placeholder message
    if not activity_data:
        return '<div class="flex items-center justify-center h-80 text-gray-500">' + \
               '<div class="text-center">' + \
               '<i class="fas fa-chart-line text-4xl mb-4"></i>' + \
               '<p class="text-lg font-medium">No activity data available</p>' + \
               '<p class="text-sm">Timeline will appear when activity is logged</p>' + \
               '</div></div>'
    
    # Convert activity data to DataFrame for easier processing
    df = pd.DataFrame(activity_data)
    
    # Create the timeline chart
    fig = px.line(df, x='timestamp', y='count', color='trigger_type', 
                 labels={'count': 'Number of Events', 'timestamp': 'Date', 'trigger_type': 'Trigger Type'})
    
    # Configure layout
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        height=400,
        width=500,
        font=dict(
            family="Arial, sans-serif",
            size=12,
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title={
            'text': "Event Activity Timeline",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    # Generate HTML
    return fig.to_html(include_plotlyjs='cdn', full_html=False)
