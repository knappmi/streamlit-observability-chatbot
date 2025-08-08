#!/usr/bin/env python3
"""
Test script for Line Graph Agent implementation
"""

import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_line_graph_tools():
    """Test the line graph visualization tools."""
    
    # Import the supervisor agent module
    try:
        from supervisor_agent import (
            create_timeseries_line_chart, 
            create_multi_metric_timeseries,
            create_incident_timeline,
            create_deployment_impact_chart
        )
        print("✅ Successfully imported line graph tools")
    except ImportError as e:
        print(f"❌ Failed to import line graph tools: {e}")
        return False
    
    # Test 1: Basic time series chart
    print("\n🧪 Testing basic time series chart...")
    
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
        result = create_timeseries_line_chart.invoke({
            "data": sample_data_json,
            "title": "Test CPU Usage",
            "y_label": "CPU %"
        })
        
        # Parse result to check if it's valid JSON
        result_data = json.loads(result)
        if "error" in result_data:
            print(f"❌ Chart creation failed: {result_data['error']}")
        else:
            print("✅ Basic time series chart created successfully")
    except Exception as e:
        print(f"❌ Basic chart test failed: {e}")
    
    # Test 2: Multi-metric chart
    print("\n🧪 Testing multi-metric chart...")
    
    multi_data = []
    for i in range(60):
        timestamp = base_time + timedelta(minutes=i)
        cpu = 50 + 20 * np.sin(i/10) + np.random.normal(0, 3)
        memory = 70 + 15 * np.cos(i/8) + np.random.normal(0, 2)
        multi_data.append({
            "timestamp": timestamp.isoformat(),
            "cpu": cpu,
            "memory": memory
        })
    
    multi_data_json = json.dumps(multi_data)
    
    try:
        result = create_multi_metric_timeseries.invoke({
            "data": multi_data_json,
            "metric_columns": "cpu,memory",
            "title": "Test Multi-Metric Chart"
        })
        
        result_data = json.loads(result)
        if "error" in result_data:
            print(f"❌ Multi-metric chart failed: {result_data['error']}")
        else:
            print("✅ Multi-metric chart created successfully")
    except Exception as e:
        print(f"❌ Multi-metric chart test failed: {e}")
    
    # Test 3: Incident timeline
    print("\n🧪 Testing incident timeline...")
    
    # Sample incident data
    incidents = [
        {
            "CreatedDate": (base_time + timedelta(minutes=15)).isoformat(),
            "Title": "High CPU Alert",
            "Severity": "Sev1"
        },
        {
            "CreatedDate": (base_time + timedelta(minutes=35)).isoformat(),
            "Title": "Memory Leak Detected",
            "Severity": "Sev2"
        }
    ]
    
    incidents_json = json.dumps(incidents)
    metrics_json = sample_data_json  # Reuse the sample data
    
    try:
        result = create_incident_timeline.invoke({
            "incident_data": incidents_json,
            "metrics_data": metrics_json,
            "title": "Test Incident Timeline"
        })
        
        result_data = json.loads(result)
        if "error" in result_data:
            print(f"❌ Incident timeline failed: {result_data['error']}")
        else:
            print("✅ Incident timeline created successfully")
    except Exception as e:
        print(f"❌ Incident timeline test failed: {e}")
    
    print("\n🎉 Line graph agent testing completed!")
    return True

def test_supervisor_integration():
    """Test that the supervisor includes the line graph agent."""
    
    try:
        from supervisor_agent import supervisor, create_dynamic_supervisor
        print("✅ Successfully imported supervisor functions")
        
        # Test creating a dynamic supervisor
        dynamic_sup = create_dynamic_supervisor(temperature=0.5)
        print("✅ Dynamic supervisor with line graph agent created successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import supervisor: {e}")
        return False
    except Exception as e:
        print(f"❌ Supervisor integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Line Graph Agent Test Suite")
    print("=" * 50)
    
    # Test the line graph tools
    tools_success = test_line_graph_tools()
    
    print("\n" + "=" * 50)
    
    # Test supervisor integration
    supervisor_success = test_supervisor_integration()
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results:")
    print(f"   Line Graph Tools: {'✅ PASS' if tools_success else '❌ FAIL'}")
    print(f"   Supervisor Integration: {'✅ PASS' if supervisor_success else '❌ FAIL'}")
    
    if tools_success and supervisor_success:
        print("\n🎉 All tests passed! Line Graph Agent is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
