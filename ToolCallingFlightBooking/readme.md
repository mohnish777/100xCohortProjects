# ✈️ Flight Booking Agent

AI-powered flight booking agent using OpenAI's function calling and AviationStack API.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Activate virtual environment
source functionCallEnv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Update `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
AVIATIONSTACK_API_KEY=your_aviationstack_api_key_here
```

### 3. Run the App

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## 📁 Files

- `agent.py` - Core agent with function calling logic
- `app.py` - Streamlit web interface
- `.env` - API keys
- `requirements.txt` - Dependencies

## 🔧 How It Works

The agent uses OpenAI's function calling to:
1. Search flights via AviationStack API
2. Get user preferences (seat/meal)
3. Book flights

**conversation_log** shows all function calls and responses in the UI.

## ⚠️ Limitations

Free tier AviationStack API:
- Only current/today's flights
- No pricing info
- 1,000 requests/month

## 💡 Example Queries

- "Find flights from Tokyo to Osaka"
- "Search flights from HND to KIX"
- "What are my preferences?"
