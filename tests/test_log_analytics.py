#!/usr/bin/env python3

"""
Test Log Analytics specific functionality
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'agentic_ai'))

try:
    from supervisor_agent import supervisor
    print("✅ Successfully imported supervisor agent!")
    
    # Test Log Analytics specific request
    test_input = "Show me the latest container logs from Log Analytics"
    
    print(f"\n🧪 Testing Log Analytics routing: {test_input}")
    
    try:
        # Test the supervisor agent
        response = supervisor.invoke({
            "messages": [{"role": "user", "content": test_input}]
        })
        
        print(f"✅ Response received: {type(response)}")
        
        # Check the structure of the response
        if isinstance(response, dict) and "messages" in response:
            print(f"📋 Number of messages: {len(response['messages'])}")
            
            for j, message in enumerate(response['messages']):
                print(f"   Message {j+1}: {type(message)}")
                if hasattr(message, 'content'):
                    content_preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
                    print(f"     Content preview: {content_preview}")
                if hasattr(message, 'name'):
                    print(f"     Name: {message.name}")
        
        # Check if log_analytics_agent was used
        agent_names = [msg.name for msg in response['messages'] if hasattr(msg, 'name')]
        if 'log_analytics_agent' in agent_names:
            print("✅ Log Analytics agent was successfully invoked!")
        else:
            print(f"ℹ️  Agents used: {set(agent_names)}")
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
