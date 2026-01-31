# Air Quality Automation Dashboard

A modern, responsive web application for managing Qingping Air Monitor sensors and Tuya smart plug automation.

## 🎯 Features

### ✅ Implemented
- **Device Management**
  - Bind Qingping Air Monitor Lite sensors to your account
  - View all bound devices with status indicators
  - Display device information (MAC address, product code, binding timestamp)
  
- **Sensor-to-Plug Mapping**
  - Create mappings between sensors and Tuya smart plugs
  - Enable/disable automation per mapping
  - Delete mappings when no longer needed
  
- **Modern UI**
  - Clean, scientific monitoring aesthetic
  - Responsive design (mobile, tablet, desktop)
  - Real-time status indicators
  - Smooth animations and transitions
  - Error handling with user-friendly messages

### 🔜 Coming Soon
- List all mappings for a user (pending backend GET endpoint)
- Live sensor readings dashboard (PM2.5, CO2, temperature, humidity)
- Historical data visualization
- User authentication

## 🚀 Quick Start

### Option 1: Direct Browser Usage
1. Download `air-quality-dashboard.html`
2. Open it in any modern web browser
3. Start binding devices and creating mappings!

### Option 2: Local Development Server
```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx http-server

# Then open http://localhost:8000/air-quality-dashboard.html
```

### Option 3: Deploy to Static Hosting
Deploy the HTML file to any static hosting service:
- **AWS S3 + CloudFront**
- **Netlify** (drag and drop)
- **Vercel**
- **GitHub Pages**

## 📋 Prerequisites

### Backend Requirements
Your AWS backend must have:
1. **API Gateway HTTP API** with CORS enabled
2. **Lambda Functions**:
   - `qingping_bind_device` - Bind new sensors
   - `qingping_list_devices` - List user's sensors
   - `sensor_plug_mapping` - Create/update/delete mappings
3. **DynamoDB Tables**:
   - `QingpingDevices` - Sensor information
   - `SensorPlugMapping` - Sensor-to-plug mappings
   - `SensorReadings` - Time-series sensor data

### CORS Configuration
**CRITICAL**: Configure CORS in your API Gateway:

```json
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["GET", "POST", "OPTIONS"],
  "AllowHeaders": ["Content-Type", "Authorization"],
  "MaxAge": 3600
}
```

For production, replace `"*"` with your specific domain.

## 🔧 Configuration

### API Base URL
Update the API endpoint in the HTML file (line ~95):

```javascript
const API_BASE_URL = 'https://your-api-id.execute-api.your-region.amazonaws.com/dev';
```

Current default:
```javascript
const API_BASE_URL = 'https://ou1jc1tszb.execute-api.us-west-1.amazonaws.com/dev';
```

### User ID
Currently hardcoded to `'dev'` (line ~369):
```javascript
const [userId] = useState('dev'); // TODO: Replace with actual auth
```

## 📖 Usage Guide

### 1. Bind a New Device

1. Click the **"Bind Device"** tab
2. Enter your **device token** (6-digit pairing code from the sensor)
3. Verify **Product ID** is 1203 (default for Air Monitor Lite)
4. Click **"Bind Device"**
5. On success, you'll be redirected to the Devices page

**API Call:**
```http
POST /qingping/bind-device
Content-Type: application/json

{
  "user_id": "dev",
  "device_token": "123456",
  "product_id": 1203
}
```

### 2. View Your Devices

1. Click the **"Devices"** tab
2. View all your bound sensors
3. Each card shows:
   - Device name and MAC address
   - Product code
   - Binding timestamp
   - Active/Inactive status
   - Air quality status (if available)

**API Call:**
```http
GET /qingping/devices?user_id=dev
```

### 3. Map Sensor to Plug

1. From the Devices page, click **"Map to Plug"** on any sensor
2. Enter your **Tuya Device ID** (from Tuya IoT Platform)
3. Choose whether to enable automation immediately
4. Click **"Create Mapping"**

**API Call:**
```http
POST /mapping/sensor-plug
Content-Type: application/json

{
  "user_id": "dev",
  "sensor_mac": "CCB5D131C3D0",
  "tuya_device_id": "eb0c85955233eb117aygws",
  "enabled": true
}
```

### 4. Manage Mappings

1. Click the **"Mappings"** tab
2. View all sensor-to-plug mappings
3. **Toggle automation** using the power button
4. **Delete mapping** with the trash button

**Toggle API Call:**
```http
POST /mapping/sensor-plug
Content-Type: application/json

{
  "user_id": "dev",
  "sensor_mac": "CCB5D131C3D0",
  "tuya_device_id": "eb0c85955233eb117aygws",
  "enabled": false
}
```

**Delete API Call:**
```http
POST /mapping/sensor-plug
Content-Type: application/json

{
  "sensor_mac": "CCB5D131C3D0",
  "delete": true
}
```

## 🏗️ Architecture

### Frontend Stack
- **React 18** - UI framework
- **Tailwind CSS** - Styling
- **Lucide Icons** - Icon library
- **Babel Standalone** - JSX transformation (in-browser)

### Design System
- **Typography**: Plus Jakarta Sans (body), JetBrains Mono (code/data)
- **Color Palette**:
  - Primary: Blue-to-cyan gradients
  - Secondary: Purple-to-pink gradients
  - Status: Emerald (good), Yellow (moderate), Orange/Red (unhealthy)
- **Layout**: Responsive grid with card-based components
- **Animations**: Smooth transitions, hover effects, loading states

## 🔄 Automation Logic

When enabled, the system automatically controls your Tuya plug based on PM2.5 readings:

| PM2.5 Level | Air Quality | Plug Action |
|-------------|-------------|-------------|
| < 9 µg/m³   | Good        | OFF         |
| ≥ 9 µg/m³   | Moderate+   | ON          |

The backend webhook handler processes sensor readings and triggers Tuya control based on this threshold.

## 🐛 Troubleshooting

### CORS Errors
```
Access to fetch at 'https://...' from origin 'null' has been blocked by CORS policy
```

**Solution**: Enable CORS in API Gateway (see CORS Configuration section above)

### 404 Not Found
```
HTTP 404: endpoint not found
```

**Solutions**:
- Verify API Gateway stage is deployed
- Check route paths match exactly: `/qingping/bind-device`, `/qingping/devices`, `/mapping/sensor-plug`
- Ensure Lambda integrations are configured

### Device Binding Fails
```
Failed to bind device: HTTP 400
```

**Possible causes**:
- Invalid device token (6-digit pairing code)
- Device already bound to another account
- Qingping API credentials not configured in backend

**Check backend Lambda environment variables**:
- `QINGPING_APP_KEY`
- `QINGPING_APP_SECRET`

### Mapping List Empty
The Mappings page currently shows:
> "Mapping list endpoint not yet implemented in backend"

**Action Required**: Implement `GET /mapping/sensor-plug?user_id=dev` endpoint in backend

**Recommended Implementation**:
1. Add GSI on `user_id` to `SensorPlugMapping` table
2. Create Lambda to query mappings by user
3. Return array of mapping objects

## 📱 Browser Support

Tested and working on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## 🔐 Security Considerations

### Current State (Development)
- No authentication
- User ID hardcoded to "dev"
- API calls from any origin (CORS: `*`)

### Production Recommendations
1. **Add Authentication**
   - AWS Cognito integration
   - JWT token validation
   - Session management

2. **Restrict CORS**
   ```json
   {
     "AllowOrigins": ["https://your-domain.com"],
     "AllowCredentials": true
   }
   ```

3. **API Rate Limiting**
   - Implement in API Gateway
   - Prevent abuse

4. **Input Validation**
   - Sanitize all user inputs
   - Validate MAC addresses and device IDs

## 🚧 Known Limitations

1. **No Authentication** - Anyone can access with "dev" user ID
2. **No Real-time Updates** - Requires manual refresh to see changes
3. **Mapping List Not Implemented** - Backend endpoint needed
4. **No Historical Data** - Sensor readings not displayed yet
5. **Single User** - Multi-user support designed but not enforced

## 🛠️ Development Roadmap

### Phase 1: Core Functionality ✅
- [x] Device binding interface
- [x] Device listing
- [x] Mapping creation
- [x] Mapping management

### Phase 2: Backend Enhancements
- [ ] Implement GET /mapping/sensor-plug endpoint
- [ ] Add user_id to mapping table
- [ ] Create GSI on user_id
- [ ] Implement GET /readings/latest endpoint

### Phase 3: Authentication
- [ ] AWS Cognito integration
- [ ] Login/logout flows
- [ ] Protected routes
- [ ] User-specific data isolation

### Phase 4: Real-time Features
- [ ] WebSocket connection for live updates
- [ ] Real-time sensor readings display
- [ ] Push notifications for air quality alerts
- [ ] Historical data charts

### Phase 5: Advanced Features
- [ ] Multiple automation rules per sensor
- [ ] Custom PM2.5 thresholds
- [ ] Scheduling (turn off at night, etc.)
- [ ] Multi-plug control per sensor

## 📝 API Reference

### Bind Device
```http
POST /qingping/bind-device
Content-Type: application/json

Request:
{
  "user_id": "string",
  "device_token": "string",
  "product_id": number
}

Response:
{
  "status": "ok",
  "bound": {
    "user_id": "string",
    "mac": "string",
    "name": "string",
    "product": { ... }
  }
}
```

### List Devices
```http
GET /qingping/devices?user_id={user_id}

Response:
{
  "status": "ok",
  "user_id": "string",
  "count": number,
  "devices": [
    {
      "sensor_mac": "string",
      "device_name": "string",
      "product": { ... },
      "enabled": boolean,
      "bound_at": number
    }
  ]
}
```

### Create/Update Mapping
```http
POST /mapping/sensor-plug
Content-Type: application/json

Request:
{
  "user_id": "string",
  "sensor_mac": "string",
  "tuya_device_id": "string",
  "enabled": boolean
}

Response:
{
  "status": "ok",
  "mapping": { ... }
}
```

### Delete Mapping
```http
POST /mapping/sensor-plug
Content-Type: application/json

Request:
{
  "sensor_mac": "string",
  "delete": true
}

Response:
{
  "status": "ok"
}
```

## 💡 Tips

1. **Keep Device Tokens Secure** - Don't share your pairing codes
2. **Test with DRY_RUN** - Use backend's DRY_RUN mode before connecting real hardware
3. **Monitor Backend Logs** - Check CloudWatch for detailed error messages
4. **Use Browser DevTools** - Network tab shows all API calls for debugging

## 📄 License

This dashboard is part of your Air Quality Automation System project.

## 🤝 Support

For issues related to:
- **Frontend**: Check browser console for errors
- **Backend**: Review CloudWatch logs for Lambda functions
- **Qingping API**: Consult Qingping developer documentation
- **Tuya API**: Check Tuya IoT Platform console

## 📧 Contact

Dashboard created as part of the Air Quality Automation System.
Backend managed via AWS Lambda, API Gateway, and DynamoDB.

---

**Built with ❤️ for automated air quality control**
