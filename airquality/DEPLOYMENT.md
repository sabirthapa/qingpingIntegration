# Deployment Guide

Complete guide for deploying the Air Quality Automation Dashboard.

## 📋 Pre-Deployment Checklist

- [ ] Backend API is deployed and accessible
- [ ] All Lambda functions are working
- [ ] DynamoDB tables are created
- [ ] Qingping API credentials are configured
- [ ] Tuya API credentials are configured
- [ ] API Gateway CORS is configured

## 🔧 AWS API Gateway CORS Configuration

### Step 1: Enable CORS in API Gateway Console

1. **Open API Gateway Console**
   - Go to AWS Console → API Gateway
   - Select your HTTP API (e.g., "air-quality-api")

2. **Configure CORS**
   - Click "CORS" in the left sidebar
   - Click "Configure"

3. **Set CORS Rules**:

   **For Development:**
   ```
   Access-Control-Allow-Origin: *
   Access-Control-Allow-Methods: GET, POST, OPTIONS
   Access-Control-Allow-Headers: Content-Type, Authorization
   Access-Control-Max-Age: 3600
   ```

   **For Production:**
   ```
   Access-Control-Allow-Origin: https://your-domain.com
   Access-Control-Allow-Methods: GET, POST, OPTIONS
   Access-Control-Allow-Headers: Content-Type, Authorization
   Access-Control-Allow-Credentials: true
   Access-Control-Max-Age: 3600
   ```

4. **Save and Deploy**
   - Click "Save"
   - Deploy to your stage (e.g., "dev")

### Step 2: Verify CORS Configuration

Test with curl:

```bash
curl -X OPTIONS https://your-api-id.execute-api.region.amazonaws.com/dev/qingping/devices \
  -H "Origin: http://localhost:8000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

Expected headers in response:
```
< Access-Control-Allow-Origin: *
< Access-Control-Allow-Methods: GET, POST, OPTIONS
< Access-Control-Allow-Headers: Content-Type, Authorization
```

### Step 3: Configure Lambda Response Headers (Optional)

If CORS still doesn't work, add headers in Lambda responses:

```python
def lambda_handler(event, context):
    # ... your logic ...
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(response_data)
    }
```

## 🚀 Frontend Deployment Options

### Option 1: AWS S3 + CloudFront (Recommended for Production)

#### Step 1: Create S3 Bucket
```bash
aws s3 mb s3://air-quality-dashboard
```

#### Step 2: Enable Static Website Hosting
```bash
aws s3 website s3://air-quality-dashboard \
  --index-document air-quality-dashboard.html \
  --error-document air-quality-dashboard.html
```

#### Step 3: Upload Files
```bash
aws s3 cp air-quality-dashboard.html s3://air-quality-dashboard/ \
  --content-type "text/html" \
  --cache-control "max-age=3600"
```

#### Step 4: Set Bucket Policy (Public Read)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::air-quality-dashboard/*"
    }
  ]
}
```

Apply policy:
```bash
aws s3api put-bucket-policy \
  --bucket air-quality-dashboard \
  --policy file://bucket-policy.json
```

#### Step 5: Create CloudFront Distribution

**Via Console:**
1. Go to CloudFront → Create Distribution
2. **Origin Settings**:
   - Origin Domain: `air-quality-dashboard.s3-website-region.amazonaws.com`
   - Origin Protocol: HTTP only
3. **Default Cache Behavior**:
   - Viewer Protocol: Redirect HTTP to HTTPS
   - Allowed Methods: GET, HEAD, OPTIONS
   - Cache Policy: Managed-CachingOptimized
4. **Settings**:
   - Price Class: Use only North America and Europe (or All)
   - Alternate Domain Names: `dashboard.yourdomain.com` (optional)
   - SSL Certificate: Default or custom ACM certificate

**Via CLI:**
```bash
aws cloudfront create-distribution \
  --origin-domain-name air-quality-dashboard.s3-website-us-west-1.amazonaws.com \
  --default-root-object air-quality-dashboard.html
```

#### Step 6: Update DNS (Optional)
If using custom domain:
```
dashboard.yourdomain.com  CNAME  d1234abcd.cloudfront.net
```

### Option 2: Netlify (Fastest for Small Projects)

#### Via Web UI:
1. Go to [netlify.com](https://netlify.com)
2. Sign up / log in
3. Drag and drop `air-quality-dashboard.html`
4. Get instant URL: `https://random-name-123.netlify.app`

#### Via CLI:
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --dir=. --prod
```

#### Custom Domain:
1. Netlify Dashboard → Domain Settings
2. Add custom domain
3. Update DNS records as instructed

### Option 3: Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### Option 4: GitHub Pages

#### Step 1: Create GitHub Repository
```bash
git init
git add air-quality-dashboard.html README.md
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/air-quality-dashboard.git
git push -u origin main
```

#### Step 2: Enable GitHub Pages
1. Go to repository Settings → Pages
2. Source: Deploy from branch `main`
3. Folder: `/ (root)`
4. Save

#### Step 3: Access
URL: `https://yourusername.github.io/air-quality-dashboard/air-quality-dashboard.html`

To use root path, rename file to `index.html`:
```bash
mv air-quality-dashboard.html index.html
git add index.html
git commit -m "Rename to index.html"
git push
```

URL becomes: `https://yourusername.github.io/air-quality-dashboard/`

### Option 5: Firebase Hosting

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize
firebase init hosting

# Select:
# - What do you want to use as your public directory? → .
# - Configure as single-page app? → Yes
# - Set up automatic builds? → No
# - File exists, overwrite? → No

# Deploy
firebase deploy --only hosting
```

## 🔒 Production Security Hardening

### 1. Update API CORS
Change from `*` to your specific domain:
```json
{
  "AllowOrigins": ["https://dashboard.yourdomain.com"]
}
```

### 2. Add API Key (Optional)
Protect your API Gateway with API keys:

```bash
# Create API key
aws apigateway create-api-key \
  --name "dashboard-key" \
  --enabled

# Create usage plan
aws apigateway create-usage-plan \
  --name "dashboard-plan" \
  --throttle burstLimit=100,rateLimit=50 \
  --quota limit=10000,period=DAY

# Associate key with plan
aws apigateway create-usage-plan-key \
  --usage-plan-id <plan-id> \
  --key-id <key-id> \
  --key-type API_KEY
```

Update frontend to include API key:
```javascript
const response = await fetch(`${API_BASE_URL}/endpoint`, {
  method: 'POST',
  headers: { 
    'Content-Type': 'application/json',
    'x-api-key': 'your-api-key-here'
  },
  body: JSON.stringify(data)
});
```

### 3. Enable HTTPS
- Always use HTTPS in production
- CloudFront, Netlify, Vercel provide free SSL
- For S3 website hosting, use CloudFront

### 4. Content Security Policy
Add CSP headers to protect against XSS:

**For CloudFront:**
1. Create Lambda@Edge function
2. Add CSP header:
```javascript
exports.handler = (event, context, callback) => {
    const response = event.Records[0].cf.response;
    const headers = response.headers;
    
    headers['content-security-policy'] = [{
        key: 'Content-Security-Policy',
        value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' unpkg.com cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' fonts.googleapis.com cdn.tailwindcss.com; font-src fonts.gstatic.com; connect-src 'self' *.execute-api.*.amazonaws.com;"
    }];
    
    callback(null, response);
};
```

### 5. Rate Limiting
In API Gateway:
- Enable throttling
- Set burst: 100 requests
- Set rate: 50 requests/second

## 📊 Monitoring & Analytics

### CloudWatch Metrics
Monitor API Gateway metrics:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=air-quality-api \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Lambda Logs
View Lambda logs:
```bash
aws logs tail /aws/lambda/qingping_bind_device --follow
```

### CloudFront Logs (Optional)
Enable CloudFront access logs:
1. CloudFront → Distribution → General
2. Standard Logging: On
3. S3 Bucket: cloudfront-logs-bucket
4. Log Prefix: air-quality-dashboard/

## 🧪 Testing Deployment

### Health Check Script
```bash
#!/bin/bash

API_BASE="https://your-api-id.execute-api.region.amazonaws.com/dev"

# Test CORS
echo "Testing CORS..."
curl -X OPTIONS "${API_BASE}/qingping/devices" \
  -H "Origin: https://your-domain.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Test List Devices
echo -e "\n\nTesting List Devices..."
curl "${API_BASE}/qingping/devices?user_id=dev"

# Test Bind Device (with fake data)
echo -e "\n\nTesting Bind Device..."
curl -X POST "${API_BASE}/qingping/bind-device" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","device_token":"000000","product_id":1203}'
```

### Frontend Test Checklist
- [ ] Page loads without errors
- [ ] All tabs are clickable
- [ ] Can navigate between views
- [ ] Forms accept input
- [ ] API calls succeed (check Network tab)
- [ ] Success/error messages display
- [ ] Responsive on mobile
- [ ] Icons render correctly

## 🔄 Continuous Deployment

### GitHub Actions (Example)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to S3

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-1
    
    - name: Deploy to S3
      run: |
        aws s3 cp air-quality-dashboard.html s3://air-quality-dashboard/ \
          --content-type "text/html" \
          --cache-control "max-age=300"
    
    - name: Invalidate CloudFront
      run: |
        aws cloudfront create-invalidation \
          --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
          --paths "/*"
```

### Netlify Auto-Deploy
Just push to GitHub - Netlify auto-deploys from connected repository.

## 🐛 Troubleshooting Deployment

### Issue: CORS Still Not Working
**Solution:**
1. Check API Gateway CORS settings
2. Clear browser cache (hard refresh: Ctrl+Shift+R)
3. Check Lambda response headers
4. Verify OPTIONS method is allowed
5. Check CloudWatch logs for Lambda errors

### Issue: 403 Forbidden from S3
**Solution:**
1. Verify bucket policy allows public read
2. Check bucket CORS configuration
3. Ensure files are uploaded with correct permissions

### Issue: CloudFront Shows Old Version
**Solution:**
Create invalidation:
```bash
aws cloudfront create-invalidation \
  --distribution-id E1234ABCD5678 \
  --paths "/*"
```

### Issue: API Gateway 502 Bad Gateway
**Solution:**
1. Check Lambda function logs
2. Verify Lambda timeout (increase if needed)
3. Check IAM permissions for Lambda execution role

## 📱 Mobile Considerations

### Progressive Web App (Optional)
Add `manifest.json`:
```json
{
  "name": "Air Quality Dashboard",
  "short_name": "AQ Dashboard",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#3b82f6",
  "icons": [
    {
      "src": "icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}
```

Add to HTML head:
```html
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#3b82f6">
```

## 📈 Performance Optimization

### 1. Enable Compression
CloudFront automatically compresses responses.

For S3 website hosting, pre-compress:
```bash
gzip -9 -c air-quality-dashboard.html > air-quality-dashboard.html.gz
aws s3 cp air-quality-dashboard.html.gz s3://bucket/ \
  --content-encoding gzip \
  --content-type "text/html"
```

### 2. CDN for Dependencies
Already using CDN for:
- React (unpkg.com)
- Tailwind CSS (cdn.tailwindcss.com)
- Lucide Icons (unpkg.com)

### 3. Cache Strategy
CloudFront cache behavior:
- HTML: max-age=300 (5 minutes)
- API responses: no-cache
- Static assets: max-age=31536000 (1 year)

## ✅ Post-Deployment Checklist

- [ ] Dashboard accessible via URL
- [ ] All API endpoints working
- [ ] CORS configured correctly
- [ ] SSL certificate active (HTTPS)
- [ ] Mobile responsive
- [ ] Error messages displaying properly
- [ ] Loading states working
- [ ] Navigation functional
- [ ] Forms submitting successfully
- [ ] Data persisting to DynamoDB

## 🎉 You're Deployed!

Your Air Quality Automation Dashboard is now live and ready to use.

**Next Steps:**
1. Share URL with users
2. Monitor CloudWatch metrics
3. Collect user feedback
4. Plan future enhancements

For issues, check:
- Browser console for frontend errors
- CloudWatch logs for backend errors
- API Gateway access logs
- CloudFront logs (if enabled)

---

**Happy Deploying! 🚀**
