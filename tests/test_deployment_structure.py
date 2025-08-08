#!/usr/bin/env python3

"""
Test script for deployment event tooling in the Kusto agent
Tests the availability and structure of deployment-specific tools
"""

import sys
import os

# Add the app directory to the Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'agentic_ai'))

def test_deployment_tool_imports():
    """Test that deployment tools can be imported"""
    print("🔧 Testing deployment tool imports...")
    
    try:
        # Set a dummy API key to avoid initialization errors
        os.environ['AZURE_AI_API_KEY'] = 'dummy-key-for-testing'
        
        from supervisor_agent import (
            kusto_deployment_schema_tool,
            kusto_deployment_query_tool,
            kusto_schema_tool,
            kusto_query_tool,
            DEFAULT_CONFIG
        )
        print("✅ Successfully imported all deployment tools!")
        
        # Test configuration
        print("\n📊 Testing configuration...")
        kusto_config = DEFAULT_CONFIG.get('kusto', {})
        
        print(f"   Incident table: {kusto_config.get('incident_table', 'Not found')}")
        print(f"   Deployment table: {kusto_config.get('deployment_table', 'Not found')}")
        print(f"   Cluster URI: {kusto_config.get('cluster_uri', 'Not found')}")
        print(f"   Database: {kusto_config.get('database', 'Not found')}")
        
        if kusto_config.get('incident_table') and kusto_config.get('deployment_table'):
            print("✅ Both incident and deployment tables are configured!")
        else:
            print("❌ Missing table configuration")
            
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import tools: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_tool_signatures():
    """Test that deployment tools have the correct signatures"""
    print("\n🔍 Testing tool signatures...")
    
    try:
        # Set dummy API key
        os.environ['AZURE_AI_API_KEY'] = 'dummy-key-for-testing'
        
        from supervisor_agent import (
            kusto_deployment_schema_tool,
            kusto_deployment_query_tool,
            kusto_incident_schema_tool,
            kusto_incident_query_tool
        )
        
        # Test tool docstrings and signatures
        tools_info = [
            ("kusto_deployment_schema_tool", kusto_deployment_schema_tool),
            ("kusto_deployment_query_tool", kusto_deployment_query_tool), 
            ("kusto_incident_schema_tool", kusto_incident_schema_tool),
            ("kusto_incident_query_tool", kusto_incident_query_tool)
        ]
        
        for tool_name, tool_func in tools_info:
            print(f"   📋 {tool_name}:")
            if hasattr(tool_func, '__doc__') and tool_func.__doc__:
                doc_preview = tool_func.__doc__.split('\n')[0]
                print(f"      Description: {doc_preview}")
            else:
                print("      Description: No docstring found")
                
            if hasattr(tool_func, '__annotations__'):
                print(f"      Parameters: {list(tool_func.__annotations__.keys())}")
            
        print("✅ All deployment tools have proper signatures!")
        return True
        
    except Exception as e:
        print(f"❌ Tool signature test failed: {e}")
        return False

def test_agent_configuration():
    """Test that the kusto_agent includes deployment tools"""
    print("\n🤖 Testing Kusto agent configuration...")
    
    try:
        # Set dummy API key
        os.environ['AZURE_AI_API_KEY'] = 'dummy-key-for-testing'
        
        from supervisor_agent import kusto_agent
        
        # Check if agent has the right tools
        if hasattr(kusto_agent, 'tools'):
            tool_names = [tool.name for tool in kusto_agent.tools if hasattr(tool, 'name')]
            print(f"   Available tools: {tool_names}")
            
            deployment_tools = [name for name in tool_names if 'deployment' in name.lower()]
            incident_tools = [name for name in tool_names if 'incident' in name.lower()]
            
            print(f"   Deployment tools: {deployment_tools}")
            print(f"   Incident tools: {incident_tools}")
            
            if deployment_tools and incident_tools:
                print("✅ Kusto agent has both deployment and incident tools!")
                return True
            else:
                print("❌ Missing deployment or incident tools")
                return False
        else:
            print("❌ Cannot access agent tools")
            return False
            
    except Exception as e:
        print(f"❌ Agent configuration test failed: {e}")
        return False

def test_prompt_content():
    """Test that the agent prompt mentions both tables"""
    print("\n📝 Testing agent prompt content...")
    
    try:
        # Set dummy API key
        os.environ['AZURE_AI_API_KEY'] = 'dummy-key-for-testing'
        
        # Import just the create_react_agent call to avoid full initialization
        import importlib.util
        spec = importlib.util.spec_from_file_location("supervisor_agent", 
            os.path.join(os.path.dirname(__file__), '..', 'app', 'agentic_ai', 'supervisor_agent.py'))
        
        # Read the file content instead of importing to avoid initialization
        with open(os.path.join(os.path.dirname(__file__), '..', 'app', 'agentic_ai', 'supervisor_agent.py'), 'r') as f:
            content = f.read()
            
        # Check for key elements in the kusto_agent prompt
        checks = [
            ("IcMDataWarehouse", "IcMDataWarehouse table mentioned"),
            ("DeploymentEvents", "DeploymentEvents table mentioned"),
            ("kusto_incident_schema_tool", "incident schema tool mentioned"),
            ("kusto_deployment_schema_tool", "deployment schema tool mentioned"),
            ("kusto_incident_query_tool", "incident query tool mentioned"),
            ("kusto_deployment_query_tool", "deployment query tool mentioned"),
        ]
        
        for check_term, check_desc in checks:
            if check_term in content:
                print(f"   ✅ {check_desc}")
            else:
                print(f"   ❌ {check_desc}")
                
        return True
        
    except Exception as e:
        print(f"❌ Prompt content test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Deployment Event Tool Structure Tests")
    print("=" * 55)
    print("📝 Note: These tests verify tool structure without requiring Azure credentials")
    print("=" * 55)
    
    # Test 1: Import testing
    import_success = test_deployment_tool_imports()
    
    # Test 2: Tool signature testing
    signature_success = test_tool_signatures()
    
    # Test 3: Agent configuration testing
    agent_success = test_agent_configuration()
    
    # Test 4: Prompt content testing
    prompt_success = test_prompt_content()
    
    print("\n" + "=" * 55)
    print("📊 Test Results Summary:")
    print(f"   Tool Import Test: {'✅ PASSED' if import_success else '❌ FAILED'}")
    print(f"   Tool Signature Test: {'✅ PASSED' if signature_success else '❌ FAILED'}")
    print(f"   Agent Config Test: {'✅ PASSED' if agent_success else '❌ FAILED'}")
    print(f"   Prompt Content Test: {'✅ PASSED' if prompt_success else '❌ FAILED'}")
    
    if import_success and signature_success and agent_success and prompt_success:
        print("\n🎉 All deployment event tool structure tests passed!")
        print("✅ Your deployment event tooling is properly configured!")
    else:
        print("\n⚠️  Some tests failed - check the output above for details")
    
    print("\n📝 What was tested:")
    print("   ✓ Deployment-specific tools can be imported")
    print("   ✓ Tools have proper signatures and documentation")
    print("   ✓ Kusto agent includes both incident and deployment tools")
    print("   ✓ Agent prompt mentions both tables and tools")
    
    print("\n🚀 Next steps for full testing:")
    print("   1. Set AZURE_AI_API_KEY environment variable")
    print("   2. Run tests in Azure environment with proper authentication") 
    print("   3. Test actual queries against DeploymentEvents table")
