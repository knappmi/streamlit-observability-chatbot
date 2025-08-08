#!/usr/bin/env python3
"""
Standalone test to verify chart creation tools work properly.
"""

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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

def create_multi_metric_timeseries(
    data: str,
    x_column: str = "timestamp",
    metric_columns: str = "value1,value2", 
    title: str = "Multi-Metric Time Series",
    x_label: str = "Time"
):
    """Test version of the multi-metric chart function."""
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
        
        # Parse metric columns
        metrics = [col.strip() for col in metric_columns.split(',')]
        
        # Ensure we have the required columns
        missing_cols = [col for col in [x_column] + metrics if col not in df.columns]
        if missing_cols:
            return json.dumps({"error": f"Missing columns: {missing_cols}"})
        
        # Convert timestamp column to datetime if it's not already
        if df[x_column].dtype == 'object':
            df[x_column] = pd.to_datetime(df[x_column])
        
        # Sort by time
        df = df.sort_values(x_column)
        
        # Create the multi-line chart
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        for i, metric in enumerate(metrics):
            fig.add_trace(go.Scatter(
                x=df[x_column],
                y=df[metric],
                mode='lines+markers',
                name=metric,
                line=dict(width=2, color=colors[i % len(colors)]),
                marker=dict(size=4)
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title="Value",
            hovermode='x unified',
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Return the chart data as JSON string that can be parsed by Streamlit
        chart_response = {
            "type": "plotly_figure", 
            "figure_data": fig.to_dict(), 
            "description": f"Created multi-metric chart: {title} with metrics: {', '.join(metrics)}"
        }
        chart_response = convert_numpy_to_list(chart_response)
        return json.dumps(chart_response)
        
    except Exception as e:
        return json.dumps({"error": f"Error creating multi-metric chart: {str(e)}"})

def test_chart_creation_with_time_series():
    """Test creating a chart with proper time series data."""
    
    print("🧪 Testing multi-metric chart creation with TIME SERIES data...")
    
    # Create proper time series data with timestamps - this is what should work
    time_series_data = [
        {"timestamp": "2025-08-08T10:00:00Z", "podA_memory": 100, "podB_memory": 120, "podC_memory": 90},
        {"timestamp": "2025-08-08T10:05:00Z", "podA_memory": 105, "podB_memory": 115, "podC_memory": 95},
        {"timestamp": "2025-08-08T10:10:00Z", "podA_memory": 110, "podB_memory": 125, "podC_memory": 88},
        {"timestamp": "2025-08-08T10:15:00Z", "podA_memory": 95, "podB_memory": 130, "podC_memory": 92},
        {"timestamp": "2025-08-08T10:20:00Z", "podA_memory": 102, "podB_memory": 118, "podC_memory": 85}
    ]
    
    print("✅ Time series data has timestamps:", time_series_data[0].keys())
    
    result = create_multi_metric_timeseries(
        data=json.dumps(time_series_data),
        x_column="timestamp",
        metric_columns="podA_memory,podB_memory,podC_memory",
        title="RSS Memory Usage Over Time (All Pods)"
    )
    
    # Parse result to check if it contains chart data
    try:
        result_data = json.loads(result)
        if "figure_data" in result_data and "type" in result_data:
            print("🎯 SUCCESS: Chart creation with time series data works!")
            print(f"   Chart type: {result_data['type']}")
            print(f"   Description: {result_data.get('description', 'N/A')}")
            return True
        else:
            print("❌ FAILURE: Chart creation failed")
            print(f"   Result: {result}")
            return False
    except json.JSONDecodeError as e:
        print(f"❌ FAILURE: Could not parse result JSON: {e}")
        print(f"   Raw result: {result}")
        return False

def test_chart_creation_without_timestamps():
    """Test what happens when we try to create a chart without timestamps."""
    
    print("\n🧪 Testing multi-metric chart creation WITHOUT timestamps (like Prometheus snapshot)...")
    
    # Create data without timestamps - this is what Prometheus might return for instant query
    snapshot_data = [
        {"pod": "podA", "memory_value": 100},
        {"pod": "podB", "memory_value": 120},
        {"pod": "podC", "memory_value": 90}
    ]
    
    print("⚠️ Snapshot data lacks timestamps:", snapshot_data[0].keys())
    
    result = create_multi_metric_timeseries(
        data=json.dumps(snapshot_data),
        x_column="timestamp",  # This column doesn't exist!
        metric_columns="memory_value",
        title="RSS Memory Usage (Snapshot)"
    )
    
    # Parse result to check what happens
    try:
        result_data = json.loads(result)
        if "error" in result_data:
            print("✅ EXPECTED: Chart creation correctly failed due to missing timestamp column")
            print(f"   Error: {result_data['error']}")
            return True
        else:
            print("❌ UNEXPECTED: Chart creation succeeded despite missing timestamps")
            print(f"   Result: {result}")
            return False
    except json.JSONDecodeError as e:
        print(f"❌ FAILURE: Could not parse result JSON: {e}")
        print(f"   Raw result: {result}")
        return False

def main():
    print("🔬 Testing Chart Creation Functions\n")
    
    # Test 1: With proper time series data (should work)
    success1 = test_chart_creation_with_time_series()
    
    # Test 2: Without timestamps (should fail gracefully)  
    success2 = test_chart_creation_without_timestamps()
    
    print(f"\n📊 Test Results:")
    print(f"   Time series data: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Snapshot data: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 CONCLUSION: Chart functions work correctly!")
        print("   ➡️ The issue is that Prometheus is returning snapshot data instead of time series")
        print("   ➡️ Need to modify Prometheus queries to use range queries (query_range) not instant queries")
    else:
        print("\n💥 CONCLUSION: There are issues with the chart functions")

if __name__ == "__main__":
    main()
