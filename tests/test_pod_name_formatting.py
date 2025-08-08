#!/usr/bin/env python3
"""
Test the Prometheus data formatting with problematic pod names like "ama-metrics-787d9cbd86-4wfw7".
"""

import json
from datetime import datetime

def format_prometheus_range_data_for_charts(prometheus_response):
    """Test version of the formatting function with the fixes."""
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
                    # Clean label values - remove special characters that might cause issues
                    clean_value = str(value).replace('-', '_').replace('.', '_').replace('/', '_')
                    label_parts.append(f"{key}_{clean_value}")
            
            if label_parts:
                metric_name = f"{metric_name}_{'_'.join(label_parts)}"
            
            # Process each timestamp/value pair
            for timestamp, value in result.get('values', []):
                try:
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
                except (ValueError, TypeError) as e:
                    print(f"Error processing timestamp/value pair: {timestamp}, {value} - {e}")
                    continue
        
        # Sort by timestamp
        formatted_data.sort(key=lambda x: x['timestamp'])
        return formatted_data
        
    except Exception as e:
        print(f"Error formatting Prometheus data: {e}")
        return []

def test_problematic_pod_name():
    """Test formatting with the problematic pod name from the error."""
    
    print("🧪 Testing Prometheus data formatting with problematic pod name...")
    
    # Mock response with the problematic pod name
    mock_prometheus_response = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "__name__": "container_memory_rss",
                        "pod": "ama-metrics-787d9cbd86-4wfw7",
                        "container": "ama-metrics",
                        "namespace": "kube-system"
                    },
                    "values": [
                        [1723104000, "104857600"],  # 100MB
                        [1723104300, "109051904"],  # 104MB
                        [1723104600, "113246208"]   # 108MB
                    ]
                },
                {
                    "metric": {
                        "__name__": "container_memory_rss",
                        "pod": "normal-pod-name", 
                        "container": "app",
                        "namespace": "default"
                    },
                    "values": [
                        [1723104000, "125829120"],  # 120MB
                        [1723104300, "120586240"],  # 115MB
                        [1723104600, "130023424"]   # 124MB
                    ]
                }
            ]
        }
    }
    
    print("📊 Input data:")
    print(f"   Pod 1: ama-metrics-787d9cbd86-4wfw7 (problematic name)")
    print(f"   Pod 2: normal-pod-name (normal name)")
    
    # Format the data
    try:
        formatted_data = format_prometheus_range_data_for_charts(mock_prometheus_response)
        
        if not formatted_data:
            print("❌ FAILURE: No formatted data returned")
            return False
        
        print(f"✅ SUCCESS: Formatted {len(formatted_data)} data rows")
        
        # Check the first row
        first_row = formatted_data[0]
        print("📋 Sample formatted row:")
        print(f"   Timestamp: {first_row.get('timestamp', 'missing')}")
        
        # Check metric names
        metric_columns = [col for col in first_row.keys() if col != 'timestamp']
        print("📈 Generated metric column names:")
        for col in metric_columns:
            print(f"   - {col}")
        
        # Verify special characters were handled
        has_problematic_chars = any('-' in col or '.' in col for col in metric_columns)
        if has_problematic_chars:
            print("⚠️  WARNING: Some metric names still contain problematic characters")
            return False
        else:
            print("✅ SUCCESS: All special characters were cleaned from metric names")
        
        # Test JSON serialization
        json_result = json.dumps(formatted_data)
        print(f"✅ JSON serialization successful: {len(json_result)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILURE: Exception during formatting: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_problematic_pod_name()
    
    if success:
        print(f"\n🎉 CONCLUSION: Fixed problematic pod name handling!")
        print("   ➡️ Special characters in pod names are now cleaned")
        print("   ➡️ Error handling improved with better diagnostics")  
        print("   ➡️ Chart creation should now work with complex pod names")
    else:
        print(f"\n💥 CONCLUSION: Still have issues with pod name formatting")
