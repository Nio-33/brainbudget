# BrainBudget 🧠💰

An AI-powered ADHD-friendly web app that makes budgeting fun by turning your bank statements and live spending data into cozy gamified insights and personalized financial advice.

## 🌟 Features

### Level 1 - Simple Statement Analyzer
- 📄 Upload bank/credit card statements (PDF/image)
- 🤖 AI-powered spending analysis and categorization using Google Gemini
- 💡 Personalized financial advice based on spending patterns
- 🤗 Clear, non-judgmental feedback and suggestions

### Level 2 - Real-time Tracker
- 🗄️ Historical financial records storage
- 🏦 Plaid API integration for live bank data
- 📊 Interactive spending visualizations and breakdowns
- 🔔 Push notifications for spending alerts
- 🎯 Gentle step-by-step onboarding process

### Level 3 (Future) - AI Finance Coach
- 📱 Daily spending summaries via WhatsApp
- 💬 Conversational AI for financial advice
- 🎯 Goal-setting and achievement tracking
- 🔮 Predictive spending insights
- 🎮 Gamification elements for budget adherence

## 🎯 Target Audience

- People with ADHD
- Individuals with poor impulse control
- Spreadsheet-averse users
- Anyone needing motivation and gentle financial guidance

## 🛠️ Tech Stack

### Backend
- **Python Flask** - Lightweight web framework
- **Firebase Firestore** - NoSQL database
- **Firebase Authentication** - User management
- **Firebase Cloud Storage** - File storage
- **Firebase Cloud Functions** - Serverless processing

### Frontend
- **HTML5 + Tailwind CSS** - Responsive design
- **Vanilla JavaScript** - Interactive functionality
- **Chart.js** - Data visualizations
- **Progressive Web App** features

### AI & Integrations
- **Google Gemini API** - Document analysis
- **Gemini Pro Vision** - OCR for statements
- **Plaid API** - Banking data integration
- **Firebase Cloud Messaging** - Push notifications

### Development Tools
- **Claude Code** - AI-assisted development
- **Firebase CLI** - Project management
- **Python virtual environments** - Dependency isolation

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- Firebase CLI
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/brainbudget.git
   cd brainbudget
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Firebase CLI**
   ```bash
   npm install -g firebase-tools
   firebase login
   ```

4. **Configure Firebase**
   ```bash
   firebase init
   # Select: Functions, Hosting, Firestore, Storage, Authentication
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

6. **Initialize Firebase Emulator**
   ```bash
   firebase emulators:start
   ```

7. **Run the development server**
   ```bash
   python app.py
   ```

### Environment Variables

Create a `.env` file with the following variables:

```env
# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY=your-private-key
FIREBASE_CLIENT_EMAIL=your-client-email

# Google Gemini API
GEMINI_API_KEY=your-gemini-api-key

# Plaid API (for Level 2)
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=sandbox

# Flask Configuration
SECRET_KEY=your-secret-key
DEBUG=True
```

## 📁 Project Structure

```
brainbudget/
├── app.py                  # Flask application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── README.md              # This file
├── firebase.json          # Firebase configuration
├── .firebaserc           # Firebase project settings
├── app/
│   ├── __init__.py       # Flask app factory
│   ├── routes/           # Flask routes
│   │   ├── __init__.py
│   │   ├── auth.py       # Authentication routes
│   │   ├── upload.py     # File upload handling
│   │   └── dashboard.py  # Dashboard routes
│   ├── services/         # Business logic
│   │   ├── __init__.py
│   │   ├── gemini_ai.py  # AI analysis service
│   │   ├── plaid_service.py # Banking integration
│   │   └── firebase_service.py # Firebase utilities
│   └── utils/            # Helper functions
│       ├── __init__.py
│       ├── pdf_parser.py # PDF processing
│       └── validators.py # Input validation
├── static/               # Static assets
│   ├── css/
│   │   └── style.css    # Custom styles
│   ├── js/
│   │   └── main.js      # Frontend JavaScript
│   └── images/          # App images
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── index.html       # Landing page
│   ├── upload.html      # Upload interface
│   └── dashboard.html   # Dashboard
├── functions/            # Firebase Cloud Functions
│   ├── main.py          # Cloud Functions entry point
│   └── requirements.txt # Cloud Functions dependencies
└── tests/                # Test files
    ├── __init__.py
    ├── test_app.py      # Application tests
    └── test_services.py # Service tests
```

## 🔧 Development Workflow

1. **Local Development**
   ```bash
   # Start Firebase emulators
   firebase emulators:start
   
   # Run Flask app
   python app.py
   ```

2. **Testing**
   ```bash
   # Run tests
   python -m pytest tests/
   
   # Run with coverage
   python -m pytest --cov=app tests/
   ```

3. **Deployment**
   ```bash
   # Deploy to Firebase
   firebase deploy
   ```

## 🎨 Design Principles

- **ADHD-Friendly**: Clear visual hierarchy, minimal cognitive load
- **Cozy Aesthetic**: Warm colors, friendly typography, approachable design
- **Non-Judgmental**: Positive reinforcement, supportive language
- **Gamified**: Progress tracking, achievement badges, gentle challenges
- **Step-by-Step**: Guided onboarding, progressive feature disclosure

## 🔒 Security & Privacy

- End-to-end encryption for sensitive financial data
- Firebase Security Rules for data access control
- GDPR compliant data handling
- Optional data deletion and export
- Secure API key management

## 🚗 Roadmap

### Phase 1 (Current)
- [x] Project setup and architecture
- [ ] Basic file upload functionality
- [ ] Gemini AI integration for statement analysis
- [ ] Spending categorization and visualization
- [ ] User authentication

### Phase 2
- [ ] Plaid API integration
- [ ] Real-time transaction tracking
- [ ] Push notifications
- [ ] Enhanced dashboard with trends

### Phase 3 (Future)
- [ ] Flutter mobile app
- [ ] WhatsApp integration
- [ ] Advanced AI coaching features
- [ ] Social accountability features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@brainbudget.app
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/brainbudget/issues)
- 📖 Documentation: [Wiki](https://github.com/yourusername/brainbudget/wiki)

## 🙏 Acknowledgments

- Built with ❤️ for the ADHD community
- Powered by Google Gemini AI
- Banking data via Plaid API
- Infrastructure by Firebase

---

**Made with 🧠 and ☕ for better financial wellness**