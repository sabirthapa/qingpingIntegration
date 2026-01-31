# Backend Improvements Guide

This document outlines the backend enhancements needed to fully support the frontend dashboard.

## 🎯 Priority Improvements

### 1. List Mappings Endpoint (HIGH PRIORITY)

**Why:** The Mappings tab currently can't display user mappings.

**Endpoint:** `GET /mapping/sensor-plug?user_id={user_id}`

**DynamoDB Changes Required:**
```python
# Add GSI to SensorPlugMapping table
{
    'TableName': 'SensorPlugMapping',
    'GlobalSecondaryIndexes': [
        {
            'IndexName': 'gsi_user_id',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        }
    ]
}
```

**Lambda Implementation:**
```python
import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_SENSOR_PLUG_MAPPING', 'SensorPlugMapping'))

class DecimalEncoder(json.JSONEncoder):
    """Convert Decimal to int/float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """List all sensor-plug mappings for a user"""
    
    # Get user_id from query parameters
    user_id = event.get('queryStringParameters', {}).get('user_id', 'dev')
    
    try:
        # Query using GSI
        response = table.query(
            IndexName='gsi_user_id',
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={
                ':uid': user_id
            }
        )
        
        mappings = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'status': 'ok',
                'user_id': user_id,
                'count': len(mappings),
                'mappings': mappings
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error listing mappings: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'message': f'Failed to list mappings: {str(e)}'
            })
        }
```

**API Gateway Configuration:**
```bash
# Create route
aws apigatewayv2 create-route \
  --api-id <your-api-id> \
  --route-key "GET /mapping/sensor-plug" \
  --target "integrations/<integration-id>"
```

**Testing:**
```bash
curl "https://your-api.execute-api.region.amazonaws.com/dev/mapping/sensor-plug?user_id=dev"
```

---

### 2. Add user_id to Mapping Table (HIGH PRIORITY)

**Why:** Current mapping table doesn't track which user owns each mapping.

**Current Schema:**
```python
{
    'sensor_mac': 'CCB5D131C3D0',  # PK
    'enabled': True,
    'tuya_device_id': 'eb0c85955233eb117aygws'
}
```

**Updated Schema:**
```python
{
    'sensor_mac': 'CCB5D131C3D0',  # PK
    'user_id': 'dev',              # NEW - for multi-user support
    'enabled': True,
    'tuya_device_id': 'eb0c85955233eb117aygws',
    'created_at': 1673500000,      # NEW - timestamp
    'updated_at': 1673500000       # NEW - timestamp
}
```

**Update Mapping Creation Lambda:**
```python
import time

def lambda_handler(event, context):
    # ... existing code ...
    
    # When creating/updating mapping
    item = {
        'sensor_mac': sensor_mac,
        'user_id': user_id,  # Add this
        'tuya_device_id': tuya_device_id,
        'enabled': enabled,
        'updated_at': int(time.time())
    }
    
    # On creation only
    if creating_new:
        item['created_at'] = int(time.time())
    
    table.put_item(Item=item)
```

---

### 3. Latest Sensor Readings Endpoint (MEDIUM PRIORITY)

**Why:** Dashboard should display current air quality metrics.

**Endpoint:** `GET /readings/latest?user_id={user_id}`

**Lambda Implementation:**
```python
import json
import boto3
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
readings_table = dynamodb.Table(os.environ.get('TABLE_SENSOR_READINGS', 'SensorReadings'))
devices_table = dynamodb.Table(os.environ.get('TABLE_QINGPING_DEVICES', 'QingpingDevices'))

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """Get latest readings for all user's sensors"""
    
    user_id = event.get('queryStringParameters', {}).get('user_id', 'dev')
    
    try:
        # Get user's devices
        devices_response = devices_table.query(
            IndexName='gsi_user_id',
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        
        devices = devices_response.get('Items', [])
        latest_readings = []
        
        # For each device, get latest reading
        for device in devices:
            sensor_mac = device['sensor_mac']
            
            # Query readings table for this sensor (descending order)
            readings_response = readings_table.query(
                KeyConditionExpression=Key('sensor_mac').eq(sensor_mac),
                ScanIndexForward=False,  # Descending order
                Limit=1
            )
            
            readings = readings_response.get('Items', [])
            
            if readings:
                latest_reading = readings[0]
                latest_reading['device_name'] = device.get('device_name', '')
                latest_readings.append(latest_reading)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'status': 'ok',
                'user_id': user_id,
                'count': len(latest_readings),
                'readings': latest_readings
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error getting latest readings: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'message': str(e)
            })
        }
```

**Frontend Integration:**
```javascript
// Add to api service
async getLatestReadings(userId) {
  const response = await fetch(`${API_BASE_URL}/readings/latest?user_id=${userId}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return response.json();
}

// In component
const [latestReadings, setLatestReadings] = useState({});

useEffect(() => {
  const loadLatestReadings = async () => {
    try {
      const data = await api.getLatestReadings(userId);
      const readingsMap = {};
      data.readings.forEach(r => {
        readingsMap[r.sensor_mac] = r;
      });
      setLatestReadings(readingsMap);
    } catch (err) {
      console.error('Failed to load readings:', err);
    }
  };
  
  loadLatestReadings();
  // Refresh every 30 seconds
  const interval = setInterval(loadLatestReadings, 30000);
  return () => clearInterval(interval);
}, [userId]);
```

---

### 4. Historical Readings Endpoint (LOW PRIORITY)

**Endpoint:** `GET /readings/history?sensor_mac={mac}&limit={n}&from={timestamp}`

**Lambda Implementation:**
```python
def lambda_handler(event, context):
    """Get historical readings for a sensor"""
    
    params = event.get('queryStringParameters', {})
    sensor_mac = params.get('sensor_mac')
    limit = int(params.get('limit', 100))
    from_timestamp = params.get('from', None)
    
    if not sensor_mac:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'sensor_mac required'})
        }
    
    try:
        query_params = {
            'KeyConditionExpression': Key('sensor_mac').eq(sensor_mac),
            'ScanIndexForward': False,
            'Limit': limit
        }
        
        if from_timestamp:
            query_params['KeyConditionExpression'] &= Key('ts').lte(int(from_timestamp))
        
        response = readings_table.query(**query_params)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'ok',
                'sensor_mac': sensor_mac,
                'count': len(response['Items']),
                'readings': response['Items']
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

---

### 5. Sensor Statistics Endpoint (LOW PRIORITY)

**Endpoint:** `GET /readings/stats?sensor_mac={mac}&period={hours}`

Calculate aggregates: min, max, avg for PM2.5, CO2, etc.

**Lambda Implementation:**
```python
from statistics import mean, median

def lambda_handler(event, context):
    params = event.get('queryStringParameters', {})
    sensor_mac = params.get('sensor_mac')
    period_hours = int(params.get('period', 24))
    
    # Calculate cutoff timestamp
    cutoff = int(time.time()) - (period_hours * 3600)
    
    try:
        response = readings_table.query(
            KeyConditionExpression=Key('sensor_mac').eq(sensor_mac) & Key('ts').gte(cutoff)
        )
        
        readings = response['Items']
        
        if not readings:
            return {'statusCode': 404, 'body': json.dumps({'error': 'No data'})}
        
        # Calculate statistics
        pm25_values = [r['pm25'] for r in readings if 'pm25' in r]
        co2_values = [r['co2'] for r in readings if 'co2' in r]
        
        stats = {
            'sensor_mac': sensor_mac,
            'period_hours': period_hours,
            'sample_count': len(readings),
            'pm25': {
                'min': min(pm25_values) if pm25_values else None,
                'max': max(pm25_values) if pm25_values else None,
                'avg': mean(pm25_values) if pm25_values else None,
                'median': median(pm25_values) if pm25_values else None
            },
            'co2': {
                'min': min(co2_values) if co2_values else None,
                'max': max(co2_values) if co2_values else None,
                'avg': mean(co2_values) if co2_values else None,
                'median': median(co2_values) if co2_values else None
            }
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(stats, cls=DecimalEncoder)
        }
    
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
```

---

## 🔐 Authentication (FUTURE)

### AWS Cognito Integration

**Step 1: Create User Pool**
```bash
aws cognito-idp create-user-pool \
  --pool-name air-quality-users \
  --policies PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true} \
  --auto-verified-attributes email
```

**Step 2: Create User Pool Client**
```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id <pool-id> \
  --client-name air-quality-dashboard \
  --generate-secret false
```

**Step 3: API Gateway Authorizer**
```bash
aws apigatewayv2 create-authorizer \
  --api-id <api-id> \
  --authorizer-type JWT \
  --identity-source '$request.header.Authorization' \
  --jwt-configuration Audience=<client-id>,Issuer=https://cognito-idp.<region>.amazonaws.com/<pool-id> \
  --name cognito-authorizer
```

**Step 4: Update Lambda to Extract User**
```python
def lambda_handler(event, context):
    # Extract user from Cognito JWT
    claims = event['requestContext']['authorizer']['jwt']['claims']
    user_id = claims['sub']  # Cognito user ID
    email = claims['email']
    
    # Use user_id in queries
    # ...
```

---

## 📊 Monitoring Improvements

### CloudWatch Custom Metrics

**Track API Usage:**
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def log_metric(metric_name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='AirQualityDashboard',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit
            }
        ]
    )

# In Lambda
log_metric('DevicesBound', 1)
log_metric('MappingsCreated', 1)
```

**Create Alarms:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name high-error-rate \
  --alarm-description "Alert on high API error rate" \
  --metric-name Errors \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## 🧪 Testing Improvements

### Integration Tests

```python
import pytest
import boto3
import requests

API_BASE = "https://your-api.execute-api.region.amazonaws.com/dev"

def test_bind_device():
    response = requests.post(
        f"{API_BASE}/qingping/bind-device",
        json={
            "user_id": "test-user",
            "device_token": "000000",
            "product_id": 1203
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'

def test_list_devices():
    response = requests.get(f"{API_BASE}/qingping/devices?user_id=test-user")
    assert response.status_code == 200
    data = response.json()
    assert 'devices' in data

def test_create_mapping():
    response = requests.post(
        f"{API_BASE}/mapping/sensor-plug",
        json={
            "user_id": "test-user",
            "sensor_mac": "TEST1234",
            "tuya_device_id": "test-device",
            "enabled": True
        }
    )
    assert response.status_code == 200
```

---

## 🚀 Quick Implementation Priority

1. **Week 1: List Mappings**
   - [ ] Add GSI to SensorPlugMapping table
   - [ ] Create Lambda for GET /mapping/sensor-plug
   - [ ] Add API Gateway route
   - [ ] Test with frontend

2. **Week 2: User ID in Mappings**
   - [ ] Update mapping creation Lambda
   - [ ] Migrate existing mappings (add user_id)
   - [ ] Test multi-user isolation

3. **Week 3: Latest Readings**
   - [ ] Create Lambda for GET /readings/latest
   - [ ] Add API Gateway route
   - [ ] Update frontend to display readings
   - [ ] Add auto-refresh

4. **Future: Authentication**
   - [ ] Set up Cognito User Pool
   - [ ] Add authorizer to API Gateway
   - [ ] Update Lambdas to extract user from JWT
   - [ ] Add login/logout to frontend

---

## 📝 Notes

- All new Lambdas should include CORS headers
- Use Decimal encoder for DynamoDB responses
- Add comprehensive error handling
- Log to CloudWatch for debugging
- Consider rate limiting for production

---

**For Questions:** Check CloudWatch logs and API Gateway execution logs for detailed error information.
