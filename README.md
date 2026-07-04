# Security Monitoring Dashboard 🛡️

A web-based security monitoring dashboard to visualize and monitor system security logs and network traffic with automated alerts for suspicious activities.

## Features
- 🔐 Secure login with attempt tracking and lockout
- 📊 Real-time security logs visualization
- 🌐 Network traffic monitoring
- ⚠️ Automated alerts for suspicious activities
- 🔍 SOC (Security Operations Center) analyzer
- 📈 Comprehensive security overview
- ⛔ Brute force protection — locks after 3 failed attempts
- 🔒 HTTPS enabled with SSL certificates
- ☁️ Cloudflare tunnel support

## Tech Stack
- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **Security:** SSL/TLS, Cloudflare, Session Management
- **Analytics:** Security Analytics

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/raghupatil1007/security-monitoring-dashboard.git
cd security-monitoring-dashboard
```

### 2. Install dependencies
```bash
pip install flask
```

### 3. Run the application
```bash
python app.py
```

## Security Features
- Brute force protection with countdown timer
- Session-based authentication
- HTTPS support via SSL certificates
- Cloudflare tunnel for secure remote access
- Attempt tracking with visual indicators

## ⚠️ Important
- Never commit SSL certificates to GitHub
- Keep your credentials secure
- Use environment variables for sensitive data

---
Built by chetan borse 🚀