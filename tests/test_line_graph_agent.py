#!/usr/bin/env python3
"""
Test script to verify the line graph agent calls tools instead of just describing charts.
"""

import sys
import os
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from agentic_ai.supervisor_agent import line_graph_agent

def test_line_graph_agent():
    """Test that the line graph agent actually calls chart creation tools."""
    
    print("🧪 Testing line graph agent behavior...")
    
    # Test data - simulating memory usage for multiple pods
    test_data = [
        {"timestamp": "2025-01-01T10:00:00Z", "podA_memory": 100, "podB_memory": 120, "podC_memory": 90},
        {"timestamp": "2025-01-01T10:05:00Z", "podA_memory": 105, "podB_memory": 115, "podC_memory": 95},
        {"timestamp": "2025-01-01T10:10:00Z", "podA_memory": 110, "podB_memory": 125, "podC_memory": 88},
        {"timestamp": "2025-01-01T10:15:00Z", "podA_memory": 95, "podB_memory": 130, "podC_memory": 92},
        {"timestamp": "2025-01-01T10:20:00Z", "podA_memory": 102, "podB_memory": 118, "podC_memory": 85}
    ]
    
    # Convert test data to JSON string
    test_data_json = json.dumps(test_data)
    
    # Create a request for multi-metric chart (like the failing case)
    request_message = {
        "messages": [
            {
                "role": "user", 
                "content": f"Create a multi-metric line chart showing RSS memory usage for all pods (podA, podB, podC) over time. Here's the data: {test_data_json}"
            }
        ]
    }
    
    print("📝 Sending request to line graph agent...")
    print(f"Request: Create multi-metric chart for pod memory usage")
    
    try:
        # Invoke the agent
        response = line_graph_agent.invoke(request_message)
        
        print(f"\n📤 Agent Response Type: {type(response)}")
        
        # Extract the final message content
        if isinstance(response, dict) and 'messages' in response:
            final_message = response['messages'][-1]['content']
        else:
            final_message = str(response)
        
        print(f"📄 Final Message Length: {len(final_message)} characters")
        print(f"🔍 First 200 chars: {final_message[:200]}")
        
        # Check if the response contains JSON (indicating tool was called)
        has_json = '"type": "plotly_figure"' in final_message or '"figure_data"' in final_message
        has_tool_call = 'create_' in final_message and ('timeseries' in final_message or 'multi_metric' in final_message)
        
        print(f"\n📊 Analysis:")
        print(f"  ✅ Contains JSON: {has_json}")
        print(f"  ✅ Contains tool call evidence: {has_tool_call}")
        
        if has_json:
            print("  🎯 SUCCESS: Agent called chart creation tool and returned JSON!")
        else:
            print("  ❌ FAILURE: Agent did not call chart creation tool")
            print(f"  📜 Full response: {final_message}")
        
        return has_json
        
    except Exception as e:
        print(f"❌ Error testing line graph agent: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_line_graph_agent()
    if success:
        print("\n🎉 Test PASSED: Line graph agent is calling tools correctly!")
    else:
        print("\n💥 Test FAILED: Line graph agent is not calling tools!")
    
    sys.exit(0 if success else 1)
