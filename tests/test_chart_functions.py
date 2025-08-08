#!/usr/bin/env python3
"""
Direct test of updated line graph chart functions
"""

import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Utility function for JSON serialization
def convert_numpy_to_list(obj):
    """Convert numpy arrays to lists for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_numpy_to_list(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_list(item) for item in obj]
    elif hasattr(obj, 'tolist'):  # numpy array
        return obj.tolist()
    else:
        return obj

def create_timeseries_line_chart(
    data: str,
    x_column: str = "timestamp",
    y_column: str = "value", 
    title: str = "Time Series Data",
    x_label: str = "Time",
    y_label: str = "Value"
):
    """
    Create an interactive line chart from time series data.
    
    Args:
        data: JSON string containing the time series data
        x_column: Name of the column containing time/date values
        y_column: Name of the column containing numeric values
        title: Chart title
        x_label: Label for x-axis
        y_label: Label for y-axis
    
    Returns:
        JSON string containing the chart data for Streamlit rendering
    """
    try:
        # Parse the data
        if isinstance(data, str):
            data_list = json.loads(data)
        else:
            data_list = data
        
        # Convert to DataFrame
        df = pd.DataFrame(data_list)
        
        if df.empty:
            return json.dumps({"error": "No data provided"})
        
        # Ensure we have the required columns
        if x_column not in df.columns or y_column not in df.columns:
            return json.dumps({"error": f"Required columns {x_column} and {y_column} not found in data"})
        
        # Convert timestamp column to datetime if it's not already
        if df[x_column].dtype == 'object':
            df[x_column] = pd.to_datetime(df[x_column])
        
        # Sort by time
        df = df.sort_values(x_column)
        
        # Create the line chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df[x_column],
            y=df[y_column],
            mode='lines+markers',
            name=y_label,
            line=dict(width=2),
            marker=dict(size=4)
        ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            hovermode='x unified',
            template='plotly_white'
        )
        
        # Return the chart data as JSON string that can be parsed by Streamlit
        chart_response = {
            "type": "plotly_figure", 
            "figure_data": fig.to_dict(), 
            "description": f"Created time series chart: {title}"
        }
        chart_response = convert_numpy_to_list(chart_response)
        return json.dumps(chart_response)
        
    except Exception as e:
        return json.dumps({"error": f"Error creating chart: {str(e)}"})

def test_chart_functions():
    """Test the updated chart functions."""
    
    print("🧪 Testing updated chart function...")
    
    # Generate sample time series data
    timestamps = []
    values = []
    base_time = datetime.now() - timedelta(hours=1)
    
    for i in range(60):
        timestamp = base_time + timedelta(minutes=i)
        value = 50 + 20 * np.sin(i/10) + np.random.normal(0, 5)
        timestamps.append(timestamp.isoformat())
        values.append(value)
    
    sample_data = [{"timestamp": t, "value": v} for t, v in zip(timestamps, values)]
    sample_data_json = json.dumps(sample_data)
    
    try:
        result = create_timeseries_line_chart(
            data=sample_data_json,
            title="Test CPU Usage",
            y_label="CPU %"
        )
        
        print(f"🔍 Function result type: {type(result)}")
        
        # Parse result to check if it's valid JSON
        result_data = json.loads(result)
        if "error" in result_data:
            print(f"❌ Chart creation failed: {result_data['error']}")
            return False
        else:
            print("✅ Chart function updated successfully - returns JSON string")
            print(f"📊 Description: {result_data.get('description', 'No description')}")
            
            # Test that we can create a figure from the data
            figure_data = result_data.get('figure_data')
            if figure_data:
                # This simulates what Streamlit will do
                from plotly.graph_objects import Figure
                fig = Figure(figure_data)
                print(f"✅ Successfully created Plotly figure from returned data")
                print(f"📈 Figure has {len(fig.data)} traces")
                return True
            else:
                print("❌ No figure_data in response")
                return False
    except Exception as e:
        print(f"❌ Chart test failed: {e}")
        return False

def test_streamlit_parsing_simulation():
    """Simulate how Streamlit will parse the agent response."""
    
    print("\n🧪 Testing Streamlit parsing simulation...")
    
    # Simulate what the agent response would look like
    mock_agent_response = '''
    I'll create a line graph for your CPU usage data.

    {"type": "plotly_figure", "figure_data": {"data": [{"x": ["2024-01-01T10:00:00", "2024-01-01T10:05:00", "2024-01-01T10:10:00"], "y": [45.2, 52.1, 48.7], "mode": "lines+markers", "name": "CPU %", "type": "scatter"}], "layout": {"title": "CPU Usage Over Time", "xaxis": {"title": "Time"}, "yaxis": {"title": "CPU %"}, "template": "plotly_white"}}, "description": "Created time series chart: CPU Usage Over Time"}

    The chart shows your CPU usage fluctuating over the selected time period.
    '''
    
    try:
        # Look for chart objects in the response (this simulates extract_and_render_plotly_charts)
        i = 0
        charts_found = 0
        while i < len(mock_agent_response):
            if '"type": "plotly_figure"' in mock_agent_response[i:]:
                start_idx = mock_agent_response.find('{"type": "plotly_figure"', i)
                if start_idx != -1:
                    # Find the end of the JSON object
                    brace_count = 0
                    j = start_idx
                    while j < len(mock_agent_response):
                        if mock_agent_response[j] == '{':
                            brace_count += 1
                        elif mock_agent_response[j] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = mock_agent_response[start_idx:j+1]
                                try:
                                    parsed = json.loads(json_str)
                                    if parsed.get('type') == 'plotly_figure':
                                        charts_found += 1
                                        print(f"✅ Found chart object: {parsed.get('description', 'No description')}")
                                        
                                        # Test that we can create a figure from the data
                                        figure_data = parsed.get('figure_data')
                                        if figure_data:
                                            from plotly.graph_objects import Figure
                                            fig = Figure(figure_data)
                                            print(f"✅ Successfully created Plotly figure from agent response")
                                            print(f"📈 Figure has {len(fig.data)} traces")
                                except json.JSONDecodeError as e:
                                    print(f"❌ JSON parsing error: {e}")
                                break
                        j += 1
                    i = j + 1
                else:
                    break
            else:
                break
        
        if charts_found > 0:
            print(f"✅ Successfully found and parsed {charts_found} chart objects from agent response")
            return True
        else:
            print("❌ No chart objects found in mock agent response")
            return False
            
    except Exception as e:
        print(f"❌ Streamlit parsing simulation failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Updated Chart Function Implementation")
    print("=" * 60)
    
    # Test the updated chart function
    function_success = test_chart_functions()
    
    # Test Streamlit parsing simulation
    parsing_success = test_streamlit_parsing_simulation()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results:")
    print(f"   Chart Function Update: {'✅ PASS' if function_success else '❌ FAIL'}")
    print(f"   Streamlit Parsing: {'✅ PASS' if parsing_success else '❌ FAIL'}")
    
    if function_success and parsing_success:
        print("\n🎉 All tests passed! Charts will now render in Streamlit.")
        print("📈 The agent will return JSON strings that Streamlit can parse and display!")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
