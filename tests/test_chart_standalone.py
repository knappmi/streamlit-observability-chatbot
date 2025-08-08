"""
Test script to verify chart creation functions directly
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

def create_timeseries_line_chart(
    data: str,
    x_column: str = "timestamp",
    y_column: str = "value", 
    title: str = "Time Series Data",
    x_label: str = "Time",
    y_label: str = "Value"
):
    """
    Create an interactive line chart from time series data - Test version.
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

if __name__ == "__main__":
    # Test creating a chart
    test_data = """[
        {"timestamp": "2024-01-01T00:00:00", "value": 10},
        {"timestamp": "2024-01-01T01:00:00", "value": 15},
        {"timestamp": "2024-01-01T02:00:00", "value": 12},
        {"timestamp": "2024-01-01T03:00:00", "value": 18}
    ]"""
    
    print("🧪 Testing create_timeseries_line_chart...")
    result = create_timeseries_line_chart(test_data, title="Test CPU Usage")
    
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result) if isinstance(result, str) else 'N/A'}")
    
    if isinstance(result, str):
        print(f"Is JSON string: {result.startswith('{')}")
        if '"type": "plotly_figure"' in result:
            print("✅ Contains plotly_figure type")
        else:
            print("❌ Missing plotly_figure type")
            
        # Try to parse it back
        try:
            parsed = json.loads(result)
            print("✅ JSON parsing successful")
            if 'figure_data' in parsed:
                print("✅ Contains figure_data")
                # Try to create the figure
                fig = go.Figure(parsed['figure_data'])
                print("✅ Plotly figure creation successful")
            else:
                print("❌ Missing figure_data")
        except Exception as e:
            print(f"❌ Error parsing/creating figure: {e}")
            
        # Preview first 200 chars
        print(f"Preview: {result[:200]}...")
    else:
        print(f"❌ Expected string, got: {type(result)}")
        
    print("\n✅ Chart function test completed!")
