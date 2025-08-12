# 🗳️ Pollarize - Advanced Polling API

A comprehensive Django REST API for creating, managing, and analyzing polls with integrated payment processing, analytics, and compliance features.

[![Django](https://img.shields.io/badge/Django-5.0.7-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org/)
[![REST Framework](https://img.shields.io/badge/DRF-3.15.2-red.svg)](https://django-rest-framework.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Features

### 🔐 **Authentication & User Management**
- JWT-based authentication with refresh tokens
- User registration and profile management
- Secure logout with token blacklisting
- Role-based permissions

### 📊 **Advanced Polling System**
- Create polls with multiple choice options
- Real-time voting with IP tracking
- Poll categories and bookmarking
- Share polls with referral tracking
- Poll analytics and insights

### 💳 **Payment Integration**
- Paystack payment gateway integration
- Secure payment processing for premium features
- Refund management system
- Referral rewards and commission tracking
- Webhook handling for payment verification

### 📈 **Analytics & Insights**
- Comprehensive poll analytics
- User engagement tracking
- Real-time dashboard with metrics
- Data export capabilities (Excel/CSV)
- Historical trend analysis

### 🛡️ **Compliance & Security**
- Geolocation-based restrictions
- Comprehensive audit logging
- IP address tracking and validation
- Security middleware integration
- GDPR-compliant data handling

## 🏗️ Architecture

```
pollarize/
├── apps/
│   ├── core/           # Authentication, users, base models
│   ├── polls/          # Polling system, voting, bookmarks
│   ├── payments/       # Payment processing, refunds, rewards
│   ├── analytics/      # Data analytics, reporting, exports
│   └── compliance/     # Security, logging, geolocation
├── config/             # Django settings, URL routing
├── docs/               # Documentation and roadmaps
└── tests/              # Comprehensive test suite
```

## 🔧 Technology Stack

- **Backend**: Django 5.0.7 + Django REST Framework
- **Database**: SQLite (development) / MySQL (production)
- **Authentication**: JWT with SimpleJWT
- **Payments**: Paystack API integration
- **Documentation**: drf-yasg (Swagger/OpenAPI)
- **Caching**: Redis (optional)
- **Background Tasks**: Celery (optional)
- **Static Files**: WhiteNoise

## 🚦 Quick Start

### Prerequisites
- Python 3.10+
- Git
- Virtual environment tool (venv/virtualenv)

### 1. Clone the Repository
```bash
git clone https://github.com/DaviesBrown/pollarize.git
cd pollarize
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
DJANGO_SECRET_KEY=your-super-secret-key-here
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Paystack API Keys (get from https://paystack.com/)
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key
PAYSTACK_SECRET_KEY=sk_test_your_secret_key
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Collect Static Files
```bash
python manage.py collectstatic
```

### 7. Run Development Server
```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the API!

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/swagger/`
- **ReDoc**: `http://localhost:8000/redoc/`

### API Endpoints

#### 🔐 Authentication
```
POST   /api/v1/auth/register/       # User registration
POST   /api/v1/auth/token/          # Login (get tokens)
POST   /api/v1/auth/token/refresh/  # Refresh access token
POST   /api/v1/auth/token/verify/   # Verify token
POST   /api/v1/auth/logout/         # Logout
GET    /api/v1/users/me/            # Current user profile
```

#### 📊 Polls
```
GET    /api/v1/polls/               # List polls
POST   /api/v1/polls/               # Create poll
GET    /api/v1/polls/{id}/          # Poll details
PUT    /api/v1/polls/{id}/          # Update poll
DELETE /api/v1/polls/{id}/          # Delete poll
POST   /api/v1/votes/               # Cast vote
GET    /api/v1/bookmarks/           # User bookmarks
POST   /api/v1/shares/              # Share poll
```

#### 💳 Payments
```
GET    /api/v1/payments/            # Payment history
POST   /api/v1/payments/            # Initialize payment
GET    /api/v1/refunds/             # Refund requests
POST   /api/v1/refunds/             # Request refund
GET    /api/v1/rewards/             # Referral rewards
```

#### 📈 Analytics
```
GET    /api/v1/analytics/polls/     # Poll analytics
GET    /api/v1/analytics/users/     # User analytics
GET    /api/v1/analytics/dashboard/ # Analytics dashboard
GET    /api/v1/analytics/export/    # Export data
```

#### 🛡️ Compliance
```
GET    /api/v1/compliance/logs/     # Audit logs
GET    /api/v1/compliance/rules/    # Compliance rules
POST   /api/v1/compliance/check/    # Compliance check
```

## 🎯 Deployment

### PythonAnywhere (Recommended for beginners)

Perfect for testing and small-scale deployment:

```bash
# Use the optimized requirements file
pip install -r requirements-pythonanywhere.txt

# Verify deployment readiness
python manage.py verify_deployment
```

📖 **Full deployment guide**: See `PYTHONANYWHERE_DEPLOYMENT.md`

### Production Deployment

For production environments:

```bash
# Set production environment variables
export DJANGO_DEBUG=0
export DJANGO_ALLOWED_HOSTS=yourdomain.com
export CELERY_ALWAYS_EAGER=0  # Enable background tasks

# Use production requirements
pip install -r requirements.txt

# Set up database (MySQL/PostgreSQL)
python manage.py migrate
python manage.py collectstatic --noinput
```

## 🧪 Testing

### Run Test Suite
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.polls
python manage.py test apps.payments

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Integration Tests
```bash
# Test payment integration
python test_payment_integration.py

# Test Phase 4 features
python test_phase4.py
```

## 🔧 Development Tools

### Management Commands
```bash
# Verify deployment configuration
python manage.py verify_deployment

# Create sample data
python manage.py loaddata fixtures/sample_data.json

# Generate API documentation
python manage.py generate_swagger
```

### Development Server
```bash
# Run with auto-reload
python manage.py runserver

# Run on specific port
python manage.py runserver 0.0.0.0:8080
```

## 📊 Monitoring & Analytics

### Built-in Analytics
- Real-time poll performance metrics
- User engagement tracking
- Payment transaction analytics
- Geographic voting patterns

### Health Checks
```bash
# System health check
python manage.py check --deploy

# Database connectivity
python manage.py dbshell

# Cache status (if Redis enabled)
python manage.py shell -c "from django.core.cache import cache; print(cache.get('test'))"
```

## 🔒 Security Features

- **CSRF Protection**: Enabled by default
- **JWT Security**: Secure token handling with blacklisting
- **Rate Limiting**: API throttling for abuse prevention
- **Input Validation**: Comprehensive data validation
- **Audit Logging**: Complete action audit trail
- **Geolocation Filtering**: Geographic access control

## 🌍 Internationalization

The API is designed with i18n support:
- UTF-8 encoding for all text fields
- Timezone-aware datetime handling
- Multi-language error messages
- Geographic compliance features

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run the test suite**: `python manage.py test`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation for API changes
- Use meaningful commit messages

## 📁 Project Structure

```
pollarize/
├── 📱 apps/
│   ├── 🔐 core/           # User management, authentication
│   ├── 📊 polls/          # Polling system core
│   ├── 💳 payments/       # Payment processing
│   ├── 📈 analytics/      # Data analytics
│   └── 🛡️ compliance/     # Security & compliance
├── ⚙️ config/             # Django configuration
├── 📚 docs/               # Documentation
├── 🧪 tests/              # Test suite
├── 📊 static/             # Static files
├── 🗃️ db.sqlite3          # Development database
├── 📋 requirements.txt    # Python dependencies
├── 🐍 manage.py           # Django management
└── 🌍 .env                # Environment variables
```

## 🆘 Troubleshooting

### Common Issues

1. **Migration Errors**
   ```bash
   python manage.py makemigrations
   python manage.py migrate --fake-initial
   ```

2. **Static Files Not Loading**
   ```bash
   python manage.py collectstatic --clear
   ```

3. **Payment Webhook Issues**
   - Verify Paystack webhook URL configuration
   - Check webhook signature validation
   - Review payment logs in admin

4. **Database Connection Issues**
   - Check database credentials in `.env`
   - Verify database server is running
   - Test connection with `python manage.py dbshell`

### Getting Help

- 📖 Check the documentation in `docs/`
- 🐛 Create an issue on GitHub
- 💬 Review existing issues and discussions
- 📧 Contact the development team

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Django REST Framework** - For the excellent API framework
- **Paystack** - For payment processing capabilities
- **The Django Community** - For continuous inspiration and support

## 📞 Support

- **Documentation**: Check the `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/DaviesBrown/pollarize/issues)
- **Discussions**: [GitHub Discussions](https://github.com/DaviesBrown/pollarize/discussions)

---

## 🚀 What's Next?

- 📱 Mobile app development
- 🔔 Real-time notifications
- 🌐 Multi-language support
- 📊 Advanced analytics dashboard
- 🤖 AI-powered poll insights

**Ready to build amazing polling experiences?** Get started now! 🎯

---

*Made with ❤️ by the Pollarize team*
