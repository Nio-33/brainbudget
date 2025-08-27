# 🧠💰 BrainBudget Deployment Guide

## 🚀 Quick Start Options

### Option 1: Smart Deployment Script (Recommended)
```bash
python deploy.py
```
This script automatically:
- Tests network connectivity
- Finds available ports
- Tries multiple host configurations
- Creates fallback options
- Provides troubleshooting guidance

### Option 2: Production WSGI Server
```bash
python run_production.py
```
Uses Gunicorn for better performance and reliability.

### Option 3: Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t brainbudget .
docker run -p 8080:8080 --env-file .env brainbudget
```

### Option 4: Standard Flask Development
```bash
python app.py
```

## 🔧 Network Troubleshooting

If you're experiencing "connection refused" errors, try these solutions:

### 1. Check Firewall Settings
**macOS:**
- System Preferences → Security & Privacy → Firewall
- Turn off firewall temporarily or add Python to allowed apps

**Windows:**
- Windows Defender Firewall → Allow an app through firewall
- Add Python.exe to exceptions

### 2. Try Different URLs
The app runs on multiple addresses:
- `http://127.0.0.1:5000`
- `http://localhost:5000`
- `http://[your-local-ip]:5000`

### 3. Browser Solutions
- Try different browsers (Chrome, Safari, Firefox, Edge)
- Use incognito/private mode
- Clear browser cache
- Disable browser extensions temporarily

### 4. Port Conflicts
If port 5000 is busy:
```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process (replace PID)
kill -9 <PID>
```

### 5. Network Configuration
```bash
# Test localhost connectivity
ping localhost
ping 127.0.0.1

# Check hosts file
cat /etc/hosts
# Should contain: 127.0.0.1 localhost
```

## 🌐 Production Deployment

### Environment Variables
Ensure your `.env` file contains:
```
SECRET_KEY=your-secure-secret-key
FIREBASE_PROJECT_ID=brainbudget-63ce4
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-fbsvc@brainbudget-63ce4.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n[your-key]\n-----END PRIVATE KEY-----"
GEMINI_API_KEY=AIzaSyBb6ja0zxf7FpZYSx1TP1xvEFshFj6mI60
PLAID_CLIENT_ID=671c7e2ff3a5d20013b56be4
PLAID_SECRET=8a4c1d7ab9e0a4c0a2c5fdb81c5e7f5e
```

### Production Checklist
- [ ] Set `FLASK_ENV=production` in `.env`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper CORS origins
- [ ] Set up HTTPS (recommended)
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Regular backups

## 📱 Accessing the Application

Once running, you can access:
- **Homepage**: `/` - Beautiful landing page with upload interface
- **Dashboard**: `/dashboard` - Financial insights and charts
- **Upload**: `/upload` - File upload interface
- **AI Coach**: `/coach` - AI-powered financial guidance
- **Settings**: `/settings` - User preferences
- **API Health**: `/health` - Server health check

## 🐳 Docker Deployment Details

### Build and Run
```bash
# Build the image
docker build -t brainbudget .

# Run with environment file
docker run -p 8080:8080 --env-file .env brainbudget

# Run with Docker Compose (recommended)
docker-compose up --build
```

### Docker URLs
- `http://localhost:8080`
- `http://127.0.0.1:8080`

## ⚡ Performance Tips

1. **Use Production Server**: Gunicorn instead of Flask dev server
2. **Enable Caching**: Browser and static file caching
3. **Optimize Images**: Compress PWA icons and assets
4. **Database Optimization**: Firestore indexes and queries
5. **CDN**: Use CDN for static assets in production

## 🔍 Debugging

### Check Application Logs
```bash
# View logs
tail -f logs/brainbudget.log

# Docker logs
docker-compose logs -f brainbudget
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8080/health

# Test authentication
curl -X POST http://localhost:8080/api/auth/verify
```

### Common Issues

**Issue**: "Module not found"
**Solution**: Install requirements
```bash
pip install -r requirements.txt
```

**Issue**: "Firebase not configured"
**Solution**: Check `.env` file has valid Firebase credentials

**Issue**: "Connection refused"
**Solution**: Try deployment script or Docker option

## 📞 Support

If you continue experiencing issues:
1. Run the diagnostic script: `python deploy.py`
2. Try Docker deployment: `docker-compose up --build`
3. Check the fallback HTML file created by deployment script
4. Verify all environment variables are correctly set

The application is fully functional and deployment-ready! 🎉