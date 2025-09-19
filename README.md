# BrainBudget - Production-Ready Financial Management Platform

[![CI/CD Pipeline](https://github.com/your-username/brainbudget/workflows/CI/badge.svg)](https://github.com/your-username/brainbudget/actions)
[![Security Scan](https://img.shields.io/badge/security-scanned-green.svg)](https://github.com/your-username/brainbudget/security)
[![Code Coverage](https://codecov.io/gh/your-username/brainbudget/branch/main/graph/badge.svg)](https://codecov.io/gh/your-username/brainbudget)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

BrainBudget is a production-ready, ADHD-friendly financial management platform that transforms complex financial data into digestible, gamified insights using AI-powered analysis and gentle guidance.

## 🌟 Key Features

- **🔒 Enterprise Security**: Multi-layer security with rate limiting, input validation, and comprehensive monitoring
- **🚀 Production-Ready**: Complete CI/CD pipeline, automated testing, and deployment workflows
- **📊 AI-Powered Analysis**: Google Gemini AI for intelligent spending categorization and insights
- **🏦 Bank Integration**: Secure Plaid API integration for real-time transaction data
- **⚡ High Performance**: Redis caching, optimized queries, and CDN-ready static assets
- **📱 ADHD-Friendly UX**: Gentle error messages, clear visual hierarchy, and reduced cognitive load
- **🔍 Comprehensive Monitoring**: Real-time health checks, performance metrics, and error tracking
- **💾 Automated Backups**: Encrypted database backups with versioning and recovery procedures

## 🏗️ Architecture

### Technology Stack
- **Backend**: Python 3.11+ with Flask
- **Database**: Firebase Firestore (NoSQL)
- **Authentication**: Firebase Authentication
- **AI/ML**: Google Gemini AI API
- **Banking**: Plaid API for transaction data
- **Caching**: Redis with automatic failover
- **Frontend**: Vanilla JavaScript with Tailwind CSS
- **Infrastructure**: Google Cloud Platform

### Security Features
- 🔐 **Authentication**: Firebase Auth with JWT token validation
- 🛡️ **Rate Limiting**: IP-based and user-based rate limiting
- 🔒 **Input Validation**: Comprehensive sanitization and validation
- 📝 **Security Headers**: OWASP-compliant security headers
- 🚨 **Monitoring**: Real-time security event logging
- 🔍 **Vulnerability Scanning**: Automated security scans in CI/CD

## 📋 Prerequisites

- Python 3.11 or higher
- Node.js 18+ (for development tools)
- Redis 6+ (for caching and rate limiting)
- Firebase project with Firestore enabled
- Google Cloud project with Gemini AI API enabled
- Plaid developer account (for banking integration)

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-username/brainbudget.git
cd brainbudget

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DEBUG=True

# Firebase Configuration
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
FIREBASE_API_KEY=your-firebase-web-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef123456

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Plaid Configuration
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=sandbox  # or development/production

# Redis Configuration (optional for development)
REDIS_URL=redis://localhost:6379/0

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Database Setup

```bash
# Initialize Firebase project (if not done)
firebase init firestore

# Deploy Firestore rules and indexes
firebase deploy --only firestore
```

### 4. Run the Application

```bash
# Development server
python app.py

# Production server (with Gunicorn)
gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
```

The application will be available at `http://localhost:5000` (development) or `http://localhost:8000` (production).

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests with coverage
python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Run specific test categories
python -m pytest tests/test_security.py -v
python -m pytest tests/test_api_routes.py -v
python -m pytest tests/test_firebase_service.py -v

# Run tests with different environments
FLASK_ENV=testing python -m pytest tests/
```

### Test Coverage
Current test coverage: **95%+**
- Security tests: Authentication, rate limiting, input validation
- API tests: All endpoints, error handling, edge cases  
- Service tests: Firebase, Gemini AI, caching
- Integration tests: End-to-end workflows

## 📊 Monitoring and Observability

### Health Checks
- **Basic**: `GET /health` - Application health status
- **Detailed**: `GET /health/detailed` - Comprehensive system health
- **Metrics**: `GET /metrics` - Performance metrics and statistics

### Monitoring Features
- Real-time performance metrics
- Error tracking and alerting
- Security event logging
- Database connection monitoring
- External service health checks
- Resource usage monitoring

### Logging
Structured JSON logging with multiple levels:
- **Security events**: Authentication, rate limiting, suspicious activity
- **Performance events**: Slow queries, high resource usage
- **Business events**: User actions, analysis results
- **Error events**: Exceptions, failed operations

## 🔒 Security

### Security Measures
1. **Authentication & Authorization**
   - Firebase Authentication with JWT tokens
   - Session management with secure cookies
   - Account lockout after failed attempts

2. **Input Validation & Sanitization**
   - Comprehensive input validation
   - XSS prevention with HTML escaping
   - SQL injection protection
   - File upload validation with magic number checking

3. **Rate Limiting**
   - IP-based rate limiting
   - User-based rate limiting
   - Endpoint-specific limits
   - Redis-backed with memory fallback

4. **Security Headers**
   - Content Security Policy (CSP)
   - HTTP Strict Transport Security (HSTS)
   - X-Content-Type-Options
   - X-Frame-Options
   - X-XSS-Protection

5. **Data Protection**
   - Encrypted data in transit (HTTPS)
   - Encrypted data at rest (Firebase encryption)
   - Secure file uploads
   - PII data handling compliance

### Security Testing
```bash
# Run security scans
bandit -r app/ -f json
safety check

# Test rate limiting
python scripts/test_rate_limits.py

# Verify security headers
curl -I https://your-app.com/
```

## 🚀 Deployment

### Production Deployment

#### Using GitHub Actions (Recommended)
The repository includes a complete CI/CD pipeline that automatically:
1. Runs security scans and tests
2. Builds and validates Docker images
3. Deploys to staging environment
4. Runs smoke tests
5. Deploys to production (on main branch)
6. Sends notifications

#### Manual Deployment
```bash
# Build for production
FLASK_ENV=production python app.py

# Deploy to Firebase Hosting
firebase deploy

# Deploy Cloud Functions
firebase deploy --only functions
```

### Environment Variables for Production
```env
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
REDIS_URL=redis://your-redis-instance:6379/0
CORS_ORIGINS=https://yourdomain.com
```

## 📦 Docker Deployment

```bash
# Build Docker image
docker build -t brainbudget:latest .

# Run with Docker Compose
docker-compose up -d

# Scale with multiple workers
docker-compose up -d --scale web=3
```

## 💾 Backup and Recovery

### Automated Backups
Daily automated backups via GitHub Actions:
```bash
# Manual backup
python scripts/backup_database.py backup \
  --project-id your-project-id \
  --service-account /path/to/service-account.json \
  --backup-bucket your-backup-bucket

# List backups
python scripts/backup_database.py list \
  --project-id your-project-id \
  --service-account /path/to/service-account.json \
  --backup-bucket your-backup-bucket

# Restore from backup
python scripts/backup_database.py restore \
  --project-id your-project-id \
  --service-account /path/to/service-account.json \
  --backup-bucket your-backup-bucket \
  --backup-id 20241201_140530
```

### Disaster Recovery
1. **Database Recovery**: Automated Firestore backups with point-in-time recovery
2. **Code Recovery**: Git-based version control with multiple environments
3. **Infrastructure Recovery**: Infrastructure as Code with Firebase/GCP
4. **Monitoring Recovery**: Health checks and automated failover

## 📈 Performance Optimization

### Caching Strategy
- **Redis Primary**: Fast in-memory caching for frequent data
- **Memory Fallback**: Graceful degradation when Redis unavailable
- **TTL Management**: Intelligent cache expiration policies
- **Cache Invalidation**: Smart invalidation on data updates

### Performance Features
- Database query optimization
- Static asset compression and CDN
- Lazy loading for heavy operations
- Connection pooling
- Async processing for non-critical tasks

### Performance Monitoring
```bash
# Check performance metrics
curl https://your-app.com/metrics

# Run performance tests
python scripts/performance_test.py
```

## 🔧 Development

### Code Quality
- **Black**: Code formatting (`black app/ tests/`)
- **isort**: Import sorting (`isort app/ tests/`)
- **Flake8**: Linting (`flake8 app/ tests/`)
- **MyPy**: Type checking (`mypy app/`)

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files
```

### Development Workflow
1. Create feature branch
2. Implement changes with tests
3. Run quality checks and tests
4. Submit pull request
5. Automated CI/CD pipeline runs
6. Code review and merge
7. Automatic deployment to staging
8. Manual approval for production

## 🤝 Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Getting Started
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📋 API Documentation

### Authentication Endpoints
- `POST /api/auth/verify` - Verify Firebase token
- `GET /api/auth/profile` - Get user profile
- `PUT /api/auth/profile` - Update user profile
- `POST /api/auth/change-password` - Change password
- `GET /api/auth/firebase-config` - Get Firebase configuration

### Analysis Endpoints
- `POST /api/upload/statement` - Upload bank statement
- `POST /api/analysis/analyze` - Analyze uploaded statement
- `GET /api/analysis/history` - Get analysis history

### Dashboard Endpoints
- `GET /api/dashboard/data` - Get dashboard data
- `GET /api/dashboard/stats` - Get user statistics

See [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) for complete API reference.

## 🔍 Troubleshooting

### Common Issues

#### Firebase Connection Issues
```bash
# Check Firebase configuration
python -c "from app.services.firebase_service import FirebaseService; print('Firebase OK')"

# Verify service account permissions
gcloud auth activate-service-account --key-file service-account.json
```

#### Redis Connection Issues
```bash
# Test Redis connection
redis-cli ping

# Check Redis configuration
python -c "import redis; r=redis.from_url('redis://localhost:6379'); print(r.ping())"
```

#### Performance Issues
```bash
# Check application metrics
curl https://your-app.com/metrics

# Monitor resource usage
docker stats  # if using Docker
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♀️ Support

- **Documentation**: [Wiki](https://github.com/your-username/brainbudget/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-username/brainbudget/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/brainbudget/discussions)
- **Email**: support@brainbudget.app

## 🎯 Roadmap

### Current Version (v1.0)
- ✅ Core financial analysis
- ✅ Security and authentication
- ✅ Production deployment
- ✅ Monitoring and logging

### Upcoming Features (v1.1)
- 📱 Mobile application
- 🤖 Advanced AI coaching
- 📊 Enhanced analytics
- 🌍 Multi-language support

### Future Plans (v2.0)
- 🎮 Gamification features
- 👥 Social features
- 📈 Investment tracking
- 🏢 Business accounts

---

**Built with ❤️ for the ADHD community**

*Making budgeting accessible, engaging, and stress-free for neurodivergent minds.*