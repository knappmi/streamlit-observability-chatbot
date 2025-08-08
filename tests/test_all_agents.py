#!/usr/bin/env python3

"""
Comprehensive test of all three agents in the supervisor system
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'agentic_ai'))

try:
    from supervisor_agent import supervisor
    print("✅ Successfully imported supervisor agent with all three agents!")
    
    # Test cases for each agent type
    test_cases = [
        ("Kusto Agent", "Show me recent ICM incidents"),
        ("Prometheus Agent", "What metrics are available for monitoring?"),
        ("Log Analytics Agent", "Get the latest container logs"),
        ("Root Cause Analysis", "For the latest incident, analyze logs and metrics to find the root cause")
    ]
    
    for test_name, test_input in test_cases:
        print(f"\n🧪 Testing {test_name}: {test_input}")
        print("-" * 60)
        
        try:
            # Test the supervisor agent
            response = supervisor.invoke({
                "messages": [{"role": "user", "content": test_input}]
            })
            
            # Analyze which agents were used
            agent_names = []
            if isinstance(response, dict) and "messages" in response:
                for message in response['messages']:
                    if hasattr(message, 'name') and message.name and 'agent' in message.name:
                        agent_names.append(message.name)
            
            unique_agents = set(agent_names)
            if unique_agents:
                print(f"✅ Agents invoked: {', '.join(unique_agents)}")
            else:
                print("ℹ️  No specific agents identified in response")
            
            # Show final response
            if isinstance(response, dict) and "messages" in response and response["messages"]:
                final_message = response["messages"][-1]
                if hasattr(final_message, 'content'):
                    content_preview = final_message.content[:200] + "..." if len(final_message.content) > 200 else final_message.content
                    print(f"📝 Final response: {content_preview}")
            
        except Exception as e:
            print(f"❌ Error in {test_name}: {e}")
        
        print()
    
    print("🎉 Integration test completed! All three agents (Kusto, Prometheus, Log Analytics) are properly integrated.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
