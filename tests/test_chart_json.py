"""
Test script to verify chart JSON format and parsing
"""
import json
import plotly.graph_objects as go
import pandas as pd
import numpy as np

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

def test_chart_creation():
    """Test creating a chart and JSON serialization"""
    
    # Create sample data
    sample_data = [
        {"timestamp": "2024-01-01T00:00:00", "value": 10},
        {"timestamp": "2024-01-01T01:00:00", "value": 15},
        {"timestamp": "2024-01-01T02:00:00", "value": 12},
        {"timestamp": "2024-01-01T03:00:00", "value": 18}
    ]
    
    df = pd.DataFrame(sample_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Create the line chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['value'],
        mode='lines+markers',
        name='Test Metric',
        line=dict(width=2),
        marker=dict(size=4)
    ))
    
    fig.update_layout(
        title="Test Time Series Chart",
        xaxis_title="Time",
        yaxis_title="Value",
        hovermode='x unified',
        template='plotly_white'
    )
    
    # Create chart response
    chart_response = {
        "type": "plotly_figure", 
        "figure_data": fig.to_dict(), 
        "description": "Created test time series chart"
    }
    
    # Apply numpy conversion
    chart_response = convert_numpy_to_list(chart_response)
    
    # Convert to JSON string
    json_str = json.dumps(chart_response)
    
    print("JSON String Length:", len(json_str))
    print("JSON String Preview (first 200 chars):", json_str[:200])
    
    # Test parsing back
    try:
        parsed_back = json.loads(json_str)
        print("✅ JSON parsing successful")
        print("Chart type:", parsed_back.get('type'))
        print("Has figure_data:", 'figure_data' in parsed_back)
        print("Description:", parsed_back.get('description'))
        
        # Test creating figure from parsed data
        try:
            test_fig = go.Figure(parsed_back['figure_data'])
            print("✅ Plotly figure recreation successful")
        except Exception as e:
            print("❌ Plotly figure recreation failed:", str(e))
            
    except Exception as e:
        print("❌ JSON parsing failed:", str(e))
    
    return json_str

if __name__ == "__main__":
    test_json = test_chart_creation()
    
    # Save to file for inspection
    with open("test_chart_output.json", "w") as f:
        f.write(test_json)
    print("Test output saved to test_chart_output.json")
