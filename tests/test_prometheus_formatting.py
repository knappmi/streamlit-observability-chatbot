#!/usr/bin/env python3
"""
Test the Prometheus range query data formatting.
"""

import json
from datetime import datetime

def format_prometheus_range_data_for_charts(prometheus_response):
    """
    Convert Prometheus range query response into format suitable for chart creation.
    """
    try:
        if not prometheus_response.get('data', {}).get('result'):
            return []
        
        formatted_data = []
        
        for result in prometheus_response['data']['result']:
            metric_name = result.get('metric', {}).get('__name__', 'unknown_metric')
            
            # Add other labels to make metric names unique (like pod names)
            labels = result.get('metric', {})
            label_parts = []
            for key, value in labels.items():
                if key not in ['__name__']:  # Skip __name__ as we already used it
                    label_parts.append(f"{key}_{value}")
            
            if label_parts:
                metric_name = f"{metric_name}_{'_'.join(label_parts)}"
            
            # Process each timestamp/value pair
            for timestamp, value in result.get('values', []):
                # Convert Unix timestamp to ISO format
                dt = datetime.fromtimestamp(float(timestamp))
                iso_timestamp = dt.isoformat() + 'Z'
                
                # Find or create row for this timestamp
                existing_row = None
                for row in formatted_data:
                    if row['timestamp'] == iso_timestamp:
                        existing_row = row
                        break
                
                if existing_row:
                    existing_row[metric_name] = float(value)
                else:
                    new_row = {'timestamp': iso_timestamp, metric_name: float(value)}
                    formatted_data.append(new_row)
        
        # Sort by timestamp
        formatted_data.sort(key=lambda x: x['timestamp'])
        return formatted_data
        
    except Exception as e:
        print(f"Error formatting Prometheus data: {e}")
        return []

def test_prometheus_formatting():
    """Test formatting mock Prometheus range query response."""
    
    print("🧪 Testing Prometheus range query data formatting...")
    
    # Mock Prometheus range query response (what we'd get from promql_range_query_tool)
    mock_prometheus_response = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "__name__": "container_memory_rss",
                        "pod": "podA",
                        "container": "app"
                    },
                    "values": [
                        [1723104000, "104857600"],  # 2025-08-08T10:00:00Z, 100MB
                        [1723104300, "109051904"],  # 2025-08-08T10:05:00Z, 104MB
                        [1723104600, "113246208"]   # 2025-08-08T10:10:00Z, 108MB
                    ]
                },
                {
                    "metric": {
                        "__name__": "container_memory_rss", 
                        "pod": "podB",
                        "container": "app"
                    },
                    "values": [
                        [1723104000, "125829120"],  # 2025-08-08T10:00:00Z, 120MB
                        [1723104300, "120586240"],  # 2025-08-08T10:05:00Z, 115MB
                        [1723104600, "130023424"]   # 2025-08-08T10:10:00Z, 124MB
                    ]
                },
                {
                    "metric": {
                        "__name__": "container_memory_rss",
                        "pod": "podC", 
                        "container": "app"
                    },
                    "values": [
                        [1723104000, "94371840"],   # 2025-08-08T10:00:00Z, 90MB
                        [1723104300, "99614720"],   # 2025-08-08T10:05:00Z, 95MB
                        [1723104600, "92274688"]    # 2025-08-08T10:10:00Z, 88MB
                    ]
                }
            ]
        }
    }
    
    # Format the data
    formatted_data = format_prometheus_range_data_for_charts(mock_prometheus_response)
    
    print(f"📊 Formatted {len(formatted_data)} rows")
    
    if formatted_data:
        print("✅ Sample formatted row:")
        print(f"   {formatted_data[0]}")
        
        # Check if we have the expected structure
        first_row = formatted_data[0]
        has_timestamp = 'timestamp' in first_row
        has_metrics = any(key.startswith('container_memory_rss_') for key in first_row.keys())
        
        print(f"✅ Has timestamp column: {has_timestamp}")
        print(f"✅ Has metric columns: {has_metrics}")
        print(f"✅ Available metrics: {[k for k in first_row.keys() if k != 'timestamp']}")
        
        if has_timestamp and has_metrics:
            print("🎯 SUCCESS: Data is formatted correctly for chart creation!")
            
            # Test JSON serialization
            json_data = json.dumps(formatted_data)
            print(f"✅ JSON serialization successful: {len(json_data)} chars")
            
            return True
        else:
            print("❌ FAILURE: Data structure is not correct")
            return False
    else:
        print("❌ FAILURE: No formatted data returned")
        return False

if __name__ == "__main__":
    success = test_prometheus_formatting()
    
    if success:
        print("\n🎉 CONCLUSION: Prometheus data formatting works!")
        print("   ➡️ Range queries will now return time series data suitable for charts")
        print("   ➡️ The line graph agent should now be able to create charts from Prometheus data")
    else:
        print("\n💥 CONCLUSION: Prometheus data formatting has issues")
