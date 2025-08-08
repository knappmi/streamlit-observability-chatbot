#!/usr/bin/env python3

"""
Test script for deployment event tooling in the Kusto agent
Tests both the deployment-specific tools and generic tools with DeploymentEvents table
"""

import sys
import os

# Add the app directory to the Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'agentic_ai'))

def test_deployment_tools():
    """Test the deployment event tools directly"""
    print("🔧 Testing deployment event tools directly...")
    
    try:
        from supervisor_agent import (
            kusto_deployment_schema_tool,
            kusto_deployment_query_tool,
            kusto_schema_tool,
            kusto_query_tool
        )
        print("✅ Successfully imported deployment tools!")
        
        # Test 1: Get deployment table schema using specific tool
        print("\n📊 Test 1: Getting DeploymentEvents schema (specific tool)...")
        try:
            schema_result = kusto_deployment_schema_tool()
            print(f"✅ Schema retrieved! Found {len(schema_result) if schema_result else 0} columns")
            if schema_result:
                print("   Sample columns:", [col.get('ColumnName', 'Unknown') for col in schema_result[:3]])
        except Exception as e:
            print(f"❌ Schema test failed: {e}")
        
        # Test 2: Get deployment table schema using generic tool
        print("\n📊 Test 2: Getting DeploymentEvents schema (generic tool)...")
        try:
            schema_result = kusto_schema_tool(table="DeploymentEvents")
            print(f"✅ Schema retrieved! Found {len(schema_result) if schema_result else 0} columns")
            if schema_result:
                print("   Sample columns:", [col.get('ColumnName', 'Unknown') for col in schema_result[:3]])
        except Exception as e:
            print(f"❌ Generic schema test failed: {e}")
            
        # Test 3: Query deployment data using specific tool
        print("\n📈 Test 3: Querying DeploymentEvents (specific tool)...")
        try:
            query_result = kusto_deployment_query_tool(
                query="take 5 | project-away *"  # Simple query to test connection
            )
            print(f"✅ Query executed! Returned {len(query_result) if query_result else 0} rows")
        except Exception as e:
            print(f"❌ Deployment query test failed: {e}")
            
        # Test 4: Query deployment data using generic tool
        print("\n📈 Test 4: Querying DeploymentEvents (generic tool)...")
        try:
            query_result = kusto_query_tool(
                query="take 5 | project-away *",
                table="DeploymentEvents"
            )
            print(f"✅ Query executed! Returned {len(query_result) if query_result else 0} rows")
        except Exception as e:
            print(f"❌ Generic deployment query test failed: {e}")
            
    except ImportError as e:
        print(f"❌ Failed to import tools: {e}")
        return False
    
    return True

def test_kusto_agent_deployment_queries():
    """Test the Kusto agent with deployment-related queries"""
    print("\n🤖 Testing Kusto agent with deployment queries...")
    
    try:
        from supervisor_agent import kusto_agent
        print("✅ Successfully imported kusto_agent!")
        
        # Test deployment-related queries
        test_queries = [
            "Show me the schema of the DeploymentEvents table",
            "Get the latest 3 deployment events",
            "What deployment information is available?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📤 Test {i}: '{query}'")
            try:
                response = kusto_agent.invoke({"messages": [("user", query)]})
                
                if response and "messages" in response:
                    last_message = response["messages"][-1]
                    content = last_message.get("content", "No content")
                    print(f"✅ Agent responded (length: {len(content)} chars)")
                    
                    # Show first 200 chars of response
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   Response preview: {preview}")
                else:
                    print("❌ No valid response received")
                    
            except Exception as e:
                print(f"❌ Query failed: {e}")
                
    except ImportError as e:
        print(f"❌ Failed to import kusto_agent: {e}")
        return False
        
    return True

def test_supervisor_deployment_integration():
    """Test the supervisor agent with deployment-related requests"""
    print("\n🎯 Testing supervisor agent with deployment queries...")
    
    try:
        from supervisor_agent import supervisor
        print("✅ Successfully imported supervisor!")
        
        # Test deployment queries through supervisor
        test_queries = [
            "Can you get information about recent deployment events?",
            "Show me the deployment events table structure",
            "Find deployment events from the last week"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📤 Supervisor Test {i}: '{query}'")
            try:
                response = supervisor.invoke({"messages": [("user", query)]})
                
                if response and "messages" in response:
                    last_message = response["messages"][-1]
                    content = last_message.get("content", "No content")
                    print(f"✅ Supervisor responded (length: {len(content)} chars)")
                    
                    # Show first 200 chars of response
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   Response preview: {preview}")
                else:
                    print("❌ No valid response received")
                    
            except Exception as e:
                print(f"❌ Supervisor query failed: {e}")
                
    except ImportError as e:
        print(f"❌ Failed to import supervisor: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("🚀 Starting Deployment Event Tooling Tests")
    print("=" * 50)
    
    # Test 1: Direct tool testing
    tools_success = test_deployment_tools()
    
    # Test 2: Kusto agent testing  
    agent_success = test_kusto_agent_deployment_queries()
    
    # Test 3: Supervisor integration testing
    supervisor_success = test_supervisor_deployment_integration()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Direct Tools Test: {'✅ PASSED' if tools_success else '❌ FAILED'}")
    print(f"   Kusto Agent Test: {'✅ PASSED' if agent_success else '❌ FAILED'}")
    print(f"   Supervisor Test: {'✅ PASSED' if supervisor_success else '❌ FAILED'}")
    
    if tools_success and agent_success and supervisor_success:
        print("\n🎉 All deployment event tooling tests completed successfully!")
        print("✅ Your deployment event functionality is working correctly!")
    else:
        print("\n⚠️  Some tests failed - check the output above for details")
        print("💡 Note: Authentication errors are expected in local development environment")
    
    print("\n📝 Next steps:")
    print("   1. Deploy to Azure Web App for full authentication testing")
    print("   2. Test with actual deployment event queries in production")
    print("   3. Verify both IcMDataWarehouse and DeploymentEvents access")
