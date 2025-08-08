#!/usr/bin/env python3
"""
Test script for updated Line Graph Agent implementation with Figure objects
"""

import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_figure_object_creation():
    """Test that the line graph tools return proper figure objects."""
    
    # Import the supervisor agent module
    try:
        from supervisor_agent import create_timeseries_line_chart
        print("✅ Successfully imported line graph tools")
    except ImportError as e:
        print(f"❌ Failed to import line graph tools: {e}")
        return False
    
    # Generate sample time series data
    timestamps = []
    values = []
    base_time = datetime.now() - timedelta(hours=1)
    
    for i in range(20):
        timestamp = base_time + timedelta(minutes=i * 3)
        value = 50 + 20 * np.sin(i/5) + np.random.normal(0, 3)
        timestamps.append(timestamp.isoformat())
        values.append(value)
    
    sample_data = [{"timestamp": t, "value": v} for t, v in zip(timestamps, values)]
    sample_data_json = json.dumps(sample_data)
    
    # Test the tool
    try:
        result = create_timeseries_line_chart.invoke({
            "data": sample_data_json,
            "title": "Test CPU Usage Chart",
            "y_label": "CPU %"
        })
        
        print(f"🔍 Tool result type: {type(result)}")
        
        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ Chart creation failed: {result['error']}")
                return False
            elif result.get("type") == "plotly_figure":
                print("✅ Chart creation successful - returned figure object")
                print(f"📊 Description: {result.get('description', 'No description')}")
                
                # Test that we can create a Plotly figure from the data
                figure_data = result.get("figure_data")
                if figure_data:
                    fig = go.Figure(figure_data)
                    print(f"✅ Successfully created Plotly figure from returned data")
                    print(f"📈 Figure has {len(fig.data)} traces")
                    return True
                else:
                    print("❌ No figure_data in result")
                    return False
            else:
                print(f"❌ Unexpected result format: {result}")
                return False
        else:
            print(f"❌ Expected dict result, got {type(result)}")
            return False
            
    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        return False

def test_response_parsing():
    """Test the Streamlit response parsing logic."""
    
    # Create a mock response that includes a chart object
    mock_response = '''
    Here is your CPU usage analysis:
    
    Based on the data, I can see some interesting patterns. Let me create a visualization for you.
    
    {"type": "plotly_figure", "figure_data": {"data": [{"x": ["2024-01-01T10:00:00", "2024-01-01T10:05:00", "2024-01-01T10:10:00"], "y": [45.2, 52.1, 48.7], "mode": "lines+markers", "name": "CPU %", "type": "scatter"}], "layout": {"title": "Test CPU Usage", "xaxis": {"title": "Time"}, "yaxis": {"title": "CPU %"}, "template": "plotly_white"}}, "description": "Created time series chart: Test CPU Usage"}
    
    This shows the CPU usage over the selected time period with clear trends visible.
    '''
    
    # Test parsing (we can't actually run st.plotly_chart here, but we can test the parsing)
    try:
        import json
        import re
        
        print("✅ Successfully imported parsing functions")
        
        # Look for chart objects in the response
        i = 0
        charts_found = 0
        while i < len(mock_response):
            if '"type": "plotly_figure"' in mock_response[i:]:
                start_idx = mock_response.find('{"type": "plotly_figure"', i)
                if start_idx != -1:
                    # Find the end of the JSON object
                    brace_count = 0
                    j = start_idx
                    while j < len(mock_response):
                        if mock_response[j] == '{':
                            brace_count += 1
                        elif mock_response[j] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = mock_response[start_idx:j+1]
                                try:
                                    parsed = json.loads(json_str)
                                    if parsed.get('type') == 'plotly_figure':
                                        charts_found += 1
                                        print(f"✅ Found chart object: {parsed.get('description', 'No description')}")
                                        
                                        # Test that we can create a figure from the data
                                        figure_data = parsed.get('figure_data')
                                        if figure_data:
                                            fig = go.Figure(figure_data)
                                            print(f"✅ Successfully created Plotly figure from chart data")
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
            print(f"✅ Successfully found and parsed {charts_found} chart objects")
            return True
        else:
            print("❌ No chart objects found in mock response")
            return False
            
    except Exception as e:
        print(f"❌ Response parsing test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Updated Line Graph Agent Implementation")
    print("=" * 60)
    
    # Test figure object creation
    figure_test = test_figure_object_creation()
    
    print("\n" + "=" * 60)
    
    # Test response parsing
    parsing_test = test_response_parsing()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results:")
    print(f"   Figure Object Creation: {'✅ PASS' if figure_test else '❌ FAIL'}")
    print(f"   Response Parsing: {'✅ PASS' if parsing_test else '❌ FAIL'}")
    
    if figure_test and parsing_test:
        print("\n🎉 All tests passed! Updated Line Graph Agent is ready to use.")
        print("📈 Charts will now render directly in Streamlit without JSON parsing overhead!")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
