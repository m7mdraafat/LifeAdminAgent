# 🏠 Life Admin Assistant

An AI-powered personal assistant that helps you manage life's administrative tasks — documents, subscriptions, and major life events with smart checklists.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

### 📄 Document Tracking
- Track important documents with expiry dates (passport, license, insurance, etc.)
- Automatic reminders at 90, 30, and 7 days before expiry
- Organize by category and family member
- Visual urgency indicators (🔴 urgent, 🟠 warning, 🟡 upcoming)

### 💳 Subscription Management
- Track all your recurring subscriptions
- Monitor free trials to avoid surprise charges
- Calculate monthly and yearly spending summaries
- Spending breakdown by category

### 📋 Life Event Checklists
Pre-built checklists for major life events:
- 🏠 **Moving** - 16 tasks from notice to settling in
- 💼 **New Job** - Onboarding and first month tasks
- 🚗 **Buying a Car** - Research to registration
- 🏡 **Buying a Home** - Pre-approval to closing
- 💒 **Getting Married** - Planning to post-wedding tasks
- ✈️ **Travel** - Planning to departure checklist
- 🎯 **Custom** - Create your own checklists

### 🔔 Notifications
- Email reminders for expiring documents
- Free trial ending alerts
- Daily digest summaries

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- [GitHub Token](https://github.com/settings/tokens) for GitHub Models API

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/life-admin-assistant.git
   cd life-admin-assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file in the project root:
   ```env
   GITHUB_TOKEN=your_github_token_here
   MODEL_NAME=openai/gpt-4.1-mini
   DATABASE_PATH=data/life_admin.db
   
   # Optional: Email notifications
   SENDER_EMAIL=your_email@gmail.com
   SENDER_PASSWORD=your_app_password
   NOTIFICATION_EMAIL=recipient@example.com
   
   # Optional: Tracing
   TRACING_ENABLED=true
   OTLP_ENDPOINT=http://localhost:4317
   ```

### Running the App

**Web UI (Streamlit)**
```bash
python run_web.py
```
Opens at http://localhost:8501

**Command Line**
```bash
python main.py
```

## 📁 Project Structure

```
life-admin-assistant/
├── main.py                 # CLI entry point
├── run_web.py              # Streamlit launcher
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── data/                   # SQLite database storage
├── evaluation/             # Evaluation framework
│   ├── evaluate_agent.py   # Evaluation runner
│   └── test_dataset.json   # Test cases
├── knowledge/              # Knowledge base files
└── src/
    ├── agent.py            # Main AI agent configuration
    ├── config.py           # Configuration management
    ├── cli.py              # Command-line interface
    ├── webapp.py           # Streamlit web UI
    ├── database/
    │   ├── models/         # Data models
    │   └── repository/     # Database operations
    ├── prompts/
    │   └── system_prompt.txt
    └── tools/              # Agent tools
        ├── documents.py    # Document tracking
        ├── subscriptions.py# Subscription management
        ├── checklists.py   # Life event checklists
        └── notifications.py# Email notifications
```

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `add_document` | Track a new document with expiry date |
| `list_documents` | List all tracked documents |
| `get_expiring_documents` | Show documents expiring soon |
| `add_subscription` | Track a new subscription |
| `get_spending_summary` | Calculate subscription spending |
| `get_trial_alerts` | Check for ending free trials |
| `start_life_event` | Begin tracking a life event |
| `get_checklist` | View life event checklist |
| `mark_task_complete` | Mark a checklist task done |
| `send_expiry_reminder` | Send email notification |
| `get_daily_digest` | Get summary of items needing attention |

## 🔍 Observability

The agent includes OpenTelemetry tracing for debugging:

1. **Enable tracing** in your `.env`:
   ```env
   TRACING_ENABLED=true
   ```

2. **View traces** in VS Code:
   - Open Command Palette (`Ctrl+Shift+P`)
   - Run "AI Toolkit: Open Trace Viewer"

## 📊 Evaluation

Run evaluation to test agent quality:

```bash
python evaluation/evaluate_agent.py
```

This will:
1. Run test queries against the agent
2. Evaluate response quality and tool usage
3. Generate results in `evaluation/results.json`

## ☁️ Deployment (Streamlit Cloud)

1. Push code to GitHub
2. Connect repo to [Streamlit Cloud](https://streamlit.io/cloud)
3. Add secrets in Streamlit dashboard:
   ```toml
   GITHUB_TOKEN = "your_token"
   MODEL_NAME = "openai/gpt-4.1-mini"
   DATABASE_PATH = "data/life_admin.db"
   ```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- Powered by [GitHub Models](https://github.com/marketplace/models)
- UI built with [Streamlit](https://streamlit.io/)