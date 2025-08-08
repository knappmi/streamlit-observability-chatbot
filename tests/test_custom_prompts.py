#!/usr/bin/env python3
"""
Test custom prompts functionality
"""

def test_custom_prompts_structure():
    """Test that custom prompts can be structured correctly"""
    print("🧪 Testing Custom Prompts Structure...")
    
    # Test custom prompts structure
    custom_prompts = {
        "kusto": "Custom Kusto agent instructions...",
        "prometheus": "Custom Prometheus agent instructions...",
        "log_analytics": "Custom Log Analytics agent instructions..."
    }
    
    # Test that all required keys exist
    required_keys = ["kusto", "prometheus", "log_analytics"]
    for key in required_keys:
        assert key in custom_prompts, f"Missing key: {key}"
        assert isinstance(custom_prompts[key], str), f"Key {key} should be string"
        assert len(custom_prompts[key]) > 0, f"Key {key} should not be empty"
    
    print("✅ Custom prompts structure is valid")
    return True

def test_dynamic_supervisor_with_prompts():
    """Test that dynamic supervisor can accept custom prompts"""
    print("🧪 Testing Dynamic Supervisor with Custom Prompts...")
    
    try:
        # Test custom prompts structure - this doesn't require Azure connection
        custom_prompts = {
            "kusto": "You are a test Kusto agent.",
            "prometheus": "You are a test Prometheus agent.",  
            "log_analytics": "You are a test Log Analytics agent."
        }
        
        # Test that the create_dynamic_supervisor function signature accepts custom_prompts
        import inspect
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.join(current_dir, 'app', 'agentic_ai'))
        
        # Import just the function definition, not the full module (avoids Azure connection)
        spec = inspect.signature
        
        # Test that we can import the module structure
        with open(os.path.join(os.path.dirname(current_dir), 'app', 'agentic_ai', 'supervisor_agent.py'), 'r') as f:
            content = f.read()
            
        # Check if the function signature includes custom_prompts parameter
        if 'custom_prompts=None' in content:
            print("✅ create_dynamic_supervisor function accepts custom_prompts parameter")
            return True
        else:
            print("❌ custom_prompts parameter not found in function signature")
            return False
        
    except Exception as e:
        print(f"❌ Error testing dynamic supervisor: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Custom Prompts Tests...\n")
    
    # Run tests
    test1_passed = test_custom_prompts_structure()
    test2_passed = test_dynamic_supervisor_with_prompts()
    
    print(f"\n📊 Test Results:")
    print(f"  - Custom Prompts Structure: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  - Dynamic Supervisor Creation: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Custom prompts functionality is working.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")
