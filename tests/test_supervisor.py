#!/usr/bin/env python3

"""
Test script for the supervisor agent
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'agentic_ai'))

try:
    from supervisor_agent import supervisor
    print("✅ Successfully imported supervisor agent!")
    
    # Test basic functionality
    print("🧪 Testing supervisor agent...")
    
    # Simple test query
    test_input = {
        "messages": [
            {"role": "user", "content": "Hello, can you help me test the system?"}
        ]
    }
    
    print("📤 Sending test message to supervisor...")
    response = supervisor.invoke(test_input)
    
    print("✅ Supervisor agent responded successfully!")
    print(f"📋 Response: {response}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error testing supervisor: {e}")
    import traceback
    traceback.print_exc()
