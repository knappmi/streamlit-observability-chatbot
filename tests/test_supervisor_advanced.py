#!/usr/bin/env python3

"""
Advanced test script for the supervisor agent
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'agentic_ai'))

try:
    from supervisor_agent import supervisor
    print("✅ Successfully imported supervisor agent!")
    
    # Test cases
    test_cases = [
        "Hello, can you help me?",
        "What can you do for me?",
        "Help me with incident analysis",
        "Show me some Kusto data"
    ]
    
    for i, test_input in enumerate(test_cases):
        print(f"\n🧪 Test {i+1}: {test_input}")
        
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
                    
        except Exception as e:
            print(f"❌ Error in test {i+1}: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
