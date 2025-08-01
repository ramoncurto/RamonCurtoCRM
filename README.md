﻿# Ramon CRM - Complete Customer Relationship Management System

A comprehensive CRM system that combines Telegram bot functionality, web dashboard, audio processing, and customer management capabilities. This is a full-featured business solution for managing customer interactions, leads, and communications.

## 🚀 Features

### Core CRM Functionality
- **Customer Management**: Store and manage customer information, interactions, and history
- **Lead Tracking**: Track potential customers through the sales pipeline
- **Communication Hub**: Centralized communication management across multiple channels
- **Data Analytics**: Dashboard with customer insights and business metrics

### Telegram Bot Integration
- **Audio Processing**: Transcribe voice messages and audio files using OpenAI Whisper
- **Multi-language Support**: Handle audio in multiple languages with automatic transcription
- **Interactive Commands**: Bot commands for quick customer lookups and updates
- **Real-time Notifications**: Instant alerts for new customer interactions

### Web Dashboard
- **Modern UI**: Clean, responsive web interface for desktop and mobile
- **Customer Database**: View and manage all customer records
- **Interaction History**: Complete audit trail of customer communications
- **Analytics Dashboard**: Business metrics and performance insights
- **Export Capabilities**: Generate reports and export customer data

### Audio Processing
- **Voice-to-Text**: Convert audio messages to searchable text
- **File Management**: Organize and store audio files with metadata
- **Quality Control**: Audio validation and processing error handling
- **Multi-format Support**: Handle various audio formats (MP3, WAV, OGG)

### Database Management
- **SQLite Database**: Lightweight, reliable data storage
- **Data Integrity**: Proper indexing and relationship management
- **Backup System**: Automated data backup and recovery
- **Migration Support**: Database schema versioning and updates

## 🛠️ Technology Stack

- **Backend**: Python 3.10+
- **Web Framework**: Flask
- **Database**: SQLite
- **AI/ML**: OpenAI API (Whisper for transcription)
- **Telegram API**: python-telegram-bot
- **Audio Processing**: pydub, speech_recognition
- **Frontend**: HTML5, CSS3, JavaScript
- **Testing**: pytest, unittest

## 📋 Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key
- Twilio Account (for SMS functionality)
- Git

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ramoncurto/RamonCurtoCRM.git
   cd RamonCurtoCRM
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Twilio Configuration (optional)
   TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
   TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
   TWILIO_PHONE_NUMBER=your_twilio_phone_number_here
   
   # Database Configuration
   DATABASE_URL=sqlite:///database.db
   
   # Server Configuration
   HOST=0.0.0.0
   PORT=5000
   DEBUG=True
   ```

4. **Initialize the database**
   ```bash
   python main.py
   ```

5. **Start the web server**
   ```bash
   python start_server.py
   ```

## 🎯 Usage

### Starting the CRM System

1. **Launch the main application**
   ```bash
   python main.py
   ```
   This starts the Telegram bot and initializes the database.

2. **Access the web dashboard**
   Open your browser and navigate to `http://localhost:5000`

3. **Telegram Bot Commands**
   - `/start` - Initialize the bot
   - `/help` - Show available commands
   - `/customer <name>` - Search for customer information
   - `/add <name> <phone>` - Add new customer
   - `/update <name> <field> <value>` - Update customer information

### Web Dashboard Features

- **Dashboard**: Overview of key metrics and recent activities
- **Customers**: Manage customer database with search and filter
- **History**: View complete interaction history
- **Analytics**: Business insights and performance reports

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest

# Run specific test modules
python test_audio_workflow.py
python test_db.py
python test_endpoints.py
python test_error_handling.py
python test_webhook_integration.py
```

## 📊 Project Structure

```
ramon_bot_v2/
├── main.py                 # Main application entry point
├── bot.py                  # Telegram bot implementation
├── start_server.py         # Web server launcher
├── requirements.txt        # Python dependencies
├── database.db            # SQLite database
├── templates/             # Web dashboard templates
│   ├── dashboard.html
│   ├── history.html
│   └── athletes.html
├── uploads/              # Audio file storage
├── temp_audio_files/     # Temporary audio processing
├── media/               # Static assets
├── tests/               # Test files
│   ├── test_audio_workflow.py
│   ├── test_db.py
│   ├── test_endpoints.py
│   └── test_error_handling.py
└── WORKFLOW_TEST_REPORT.md  # Test documentation
```

## 🔧 Configuration

### Audio Processing Settings
- **Max Duration**: 300 seconds per audio file
- **Supported Formats**: MP3, WAV, OGG, M4A
- **Language Detection**: Automatic with OpenAI Whisper
- **Quality Settings**: Configurable in `main.py`

### Database Configuration
- **Type**: SQLite (file-based)
- **Location**: `database.db` in project root
- **Backup**: Automatic backup system
- **Migrations**: Schema versioning support

## 📈 Performance

- **Audio Processing**: ~30 seconds per minute of audio
- **Database Queries**: <100ms for standard operations
- **Web Response**: <200ms for dashboard pages
- **Concurrent Users**: Supports multiple simultaneous users

## 🔒 Security

- **API Key Protection**: Environment variables for sensitive data
- **Input Validation**: All user inputs are sanitized
- **File Upload Security**: Audio file validation and scanning
- **Database Security**: SQL injection prevention
- **HTTPS Support**: Ready for production SSL deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `WORKFLOW_TEST_REPORT.md` for detailed usage
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and ideas

## 💰 Cost Considerations

- **OpenAI API**: ~$0.006 per minute of audio transcription
- **Telegram Bot**: Free (with rate limits)
- **Twilio SMS**: Pay-per-use pricing
- **Hosting**: Minimal server requirements

## 🚀 Deployment

### Local Development
```bash
python main.py
```

### Production Deployment
1. Set up a production server (Ubuntu recommended)
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables
4. Use a process manager (systemd, supervisor)
5. Set up reverse proxy (nginx) for web dashboard
6. Configure SSL certificates

### Docker Deployment (Coming Soon)
```bash
docker build -t ramon-crm .
docker run -p 5000:5000 ramon-crm
```

---

**Ramon CRM** - Transforming customer relationships through intelligent automation and comprehensive management tools.
