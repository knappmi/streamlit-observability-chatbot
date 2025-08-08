"""
Test script to verify line graph agent tools are working
"""
import sys
import os

# Add current directory to path so we can import supervisor_agent
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'app', 'agentic_ai'))

try:
    from supervisor_agent import create_timeseries_line_chart, create_multi_metric_timeseries
    
    print("✅ Successfully imported chart tools")
    
    # Test creating a simple chart
    test_data = """[
        {"timestamp": "2024-01-01T00:00:00", "value": 10},
        {"timestamp": "2024-01-01T01:00:00", "value": 15},
        {"timestamp": "2024-01-01T02:00:00", "value": 12},
        {"timestamp": "2024-01-01T03:00:00", "value": 18}
    ]"""
    
    print("\n🧪 Testing create_timeseries_line_chart...")
    result = create_timeseries_line_chart(test_data, title="Test CPU Usage")
    
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result) if isinstance(result, str) else 'N/A'}")
    
    if isinstance(result, str):
        print(f"Is JSON string: {result.startswith('{')}")
        if '"type": "plotly_figure"' in result:
            print("✅ Contains plotly_figure type")
        else:
            print("❌ Missing plotly_figure type")
            
        # Preview first 200 chars
        print(f"Preview: {result[:200]}...")
    else:
        print(f"❌ Expected string, got: {type(result)}")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()
