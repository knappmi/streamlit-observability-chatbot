#!/usr/bin/env python3
"""
Demo script showing how to use the Line Graph Agent
"""

import sys
import os
import json
from datetime import datetime, timedelta
import numpy as np

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def demo_line_graph_usage():
    """Demonstrate how to use the line graph agent."""
    
    print("🎯 Line Graph Agent Demo")
    print("=" * 40)
    
    # Import the visualization tools
    from supervisor_agent import create_timeseries_line_chart, create_multi_metric_timeseries
    
    # Create sample metrics data
    print("\n📊 Creating sample time series data...")
    
    base_time = datetime.now() - timedelta(hours=1)
    sample_data = []
    
    for i in range(30):  # 30 data points over 1 hour
        timestamp = base_time + timedelta(minutes=2*i)  # Every 2 minutes
        cpu_usage = 40 + 30 * np.sin(i/5) + np.random.normal(0, 5)  # Simulated CPU
        memory_usage = 60 + 20 * np.cos(i/4) + np.random.normal(0, 3)  # Simulated Memory
        
        sample_data.append({
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "cpu": max(0, min(100, cpu_usage)),  # Clamp between 0-100
            "memory": max(0, min(100, memory_usage))  # Clamp between 0-100
        })
    
    print(f"✅ Generated {len(sample_data)} data points")
    
    # Demo 1: Single metric line chart
    print("\n🧪 Demo 1: Basic CPU usage line chart")
    
    # Extract CPU data for single metric chart
    cpu_data = [{"timestamp": d["timestamp"], "value": d["cpu"]} for d in sample_data]
    cpu_json = json.dumps(cpu_data)
    
    try:
        result = create_timeseries_line_chart.invoke({
            "data": cpu_json,
            "title": "CPU Usage Over Time",
            "y_label": "CPU Percentage (%)",
            "x_label": "Time"
        })
        
        # The result is a JSON string containing the Plotly figure
        print("✅ CPU usage chart created successfully")
        print(f"📏 Chart data size: {len(result)} characters")
        
    except Exception as e:
        print(f"❌ Failed to create CPU chart: {e}")
    
    # Demo 2: Multi-metric chart
    print("\n🧪 Demo 2: Multi-metric CPU and Memory chart")
    
    multi_json = json.dumps(sample_data)
    
    try:
        result = create_multi_metric_timeseries.invoke({
            "data": multi_json,
            "metric_columns": "cpu,memory",
            "title": "System Resource Usage",
            "x_label": "Time"
        })
        
        print("✅ Multi-metric chart created successfully")
        print(f"📏 Chart data size: {len(result)} characters")
        
    except Exception as e:
        print(f"❌ Failed to create multi-metric chart: {e}")
    
    print("\n🎉 Demo completed successfully!")
    print("\n💡 Usage Tips:")
    print("   - Use 'Create a line chart of CPU usage' in the chat")
    print("   - Ask for 'Multi-metric chart showing CPU and memory'")
    print("   - Request 'Incident timeline with system metrics'")
    print("   - Try 'Deployment impact chart for recent releases'")
    
    return True

if __name__ == "__main__":
    demo_line_graph_usage()
