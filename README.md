# 📬 AI Email Reading Agent

An intelligent email monitoring system that reads your inbox, classifies emails using AI (OpenAI GPT), and displays only the important ones on a live Streamlit dashboard.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                          │
│  ┌──────────────────┐    ┌──────────────────────────┐   │
│  │  email-agent     │    │  email-poller            │   │
│  │  (Dashboard)     │    │  (Background polling)    │   │
│  │                  │    │                          │   │
│  │  Streamlit UI    │    │  Runs every 2 minutes    │   │
│  │  Port 8501       │    │  Fetches + classifies    │   │
│  └────────┬─────────┘    └──────────┬───────────────┘   │
│           │                         │                    │
│           └──────────┬──────────────┘                   │
│                      ▼                                   │
│              ┌───────────────┐                          │
│              │  SQLite DB    │  (persistent volume)     │
│              │  email_agent  │                          │
│              └───────────────┘                          │
└─────────────────────────────────────────────────────────┘

Email Sources:
  Mock JSON  ──┐
  Gmail API  ──┤──► Email Reader ──► AI Classifier ──► DB ──► Dashboard
  IMAP       ──┘
```

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker & Docker Compose installed
- Git

### Step 1 — Clone & configure

```bash
git clone <your-repo-url>
cd ai-email-agent

# Copy the example env file
cp .env.example .env
```

### Step 2 — Edit `.env`

Open `.env` in any text editor and set your values:

```env
# Minimum required (mock mode, no real email needed):
EMAIL_SOURCE=mock
OPENAI_API_KEY=your-openai-api-key-here   # get from platform.openai.com
```

### Step 3 — Build & run

```bash
docker compose up --build
```

### Step 4 — Open dashboard

Visit **http://localhost:8501** in your browser.

Click **"🔄 Run Agent Now"** in the sidebar to process emails.

---

## ⚙️ Configuration Guide

### `.env` Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Optional* | — | Your OpenAI API key. Falls back to rule-based if not set. |
| `OPENAI_MODEL` | No | `gpt-3.5-turbo` | OpenAI model (`gpt-3.5-turbo`, `gpt-4o`, etc.) |
| `EMAIL_SOURCE` | No | `mock` | Email source: `mock`, `imap`, or `gmail` |
| `MOCK_EMAIL_PATH` | No | `/app/data/mock_emails.json` | Path to mock email JSON file |
| `IMAP_HOST` | If IMAP | `imap.gmail.com` | IMAP server hostname |
| `IMAP_PORT` | If IMAP | `993` | IMAP SSL port |
| `IMAP_USER` | If IMAP | — | Your email address |
| `IMAP_PASSWORD` | If IMAP | — | Your email app password |
| `GMAIL_CREDENTIALS_PATH` | If Gmail | `/app/credentials.json` | Path to Google OAuth credentials |
| `GMAIL_TOKEN_PATH` | If Gmail | `/app/token.json` | Path to stored OAuth token |
| `DATABASE_URL` | No | `sqlite:////app/db/email_agent.db` | Database connection string |
| `POLL_INTERVAL_SECONDS` | No | `120` | How often to check inbox (seconds) |

*Without `OPENAI_API_KEY`, the system uses a built-in rule-based classifier (still works, less accurate).

---

## 📧 Email Source Setup

### Option A — Mock Data (Default, No Credentials)

```env
EMAIL_SOURCE=mock
```

Uses `data/mock_emails.json`. Perfect for testing. Edit the file to add your own test emails.

---

### Option B — Gmail via IMAP

1. Enable 2-Factor Authentication on your Google Account
2. Go to **Google Account → Security → 2-Step Verification → App Passwords**
3. Create an app password for "Mail"
4. Set in `.env`:

```env
EMAIL_SOURCE=imap
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=yourname@gmail.com
IMAP_PASSWORD=xxxx-xxxx-xxxx-xxxx    # 16-char app password, no spaces
```

5. Enable IMAP in Gmail: **Gmail Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP**

---

### Option C — Gmail via API (OAuth2)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Gmail API**
3. Create **OAuth 2.0 Credentials** → Desktop App
4. Download `credentials.json` → place in project root
5. Run the auth flow once (outside Docker):

```bash
pip install google-auth-oauthlib google-api-python-client
python scripts/gmail_auth.py
```

This generates `token.json`. Then:

```env
EMAIL_SOURCE=gmail
```

Uncomment the volume mounts in `docker-compose.yml`:

```yaml
- ./credentials.json:/app/credentials.json:ro
- ./token.json:/app/token.json:ro
```

---

## 🤖 AI Classification Logic

### How It Works

Each email is passed to the classifier with: From, Subject, Body.

The AI returns a structured decision:

```json
{
  "important": true,
  "priority": "HIGH",
  "category": "SERVER_DOWN",
  "reason": "Client reports production outage causing immediate revenue loss."
}
```

### Priority Levels

| Priority | Description |
|---|---|
| **HIGH** | Requires immediate action (server down, payment failure, legal notice) |
| **MEDIUM** | Important but not emergency (client complaint, unusual billing) |
| **LOW** | Marginally important (routine business, shipping alerts) |

### Categories

| Category | Description |
|---|---|
| `PAYMENT_ISSUE` | Failed payments, billing problems, overdue invoices |
| `SERVER_DOWN` | Outages, production failures, infrastructure alerts |
| `CLIENT_COMPLAINT` | Angry customers, refund requests, negative feedback |
| `SECURITY_ALERT` | Unauthorized access, breach notifications |
| `LEGAL` | Legal notices, copyright claims, lawsuits |
| `BUSINESS_OPPORTUNITY` | Partnerships, contracts, large deals |
| `BILLING_ALERT` | Unusual cloud charges (AWS, GCP, etc.) |
| `SPAM` | Promotional, newsletter, automated emails |
| `GENERAL` | Everything else |

### AI vs Rule-Based Fallback

```
OPENAI_API_KEY set?
    ├── YES → OpenAI GPT classifies the email (accurate, context-aware)
    └── NO  → Rule-based keyword classifier (fast, offline, less accurate)
```

The rule-based classifier scans for ~25 important keywords vs ~15 spam keywords and determines category from keyword patterns.

---

## 🛡️ Duplicate Prevention

Every processed email ID is stored in SQLite. Before classifying, the agent checks:

```sql
SELECT * FROM processed_emails WHERE id = '<email_id>'
```

If found → skip. This ensures every email is processed **exactly once**, even across restarts.

---

## 📊 Dashboard Features

- **Stats bar** — Total scanned, important count, priority breakdown
- **Live notifications** — Each important email shown as a card with priority, category, reason
- **Priority filter** — Toggle HIGH/MEDIUM/LOW visibility in sidebar
- **Manual trigger** — "Run Agent Now" button to instantly scan inbox
- **Auto-refresh** — Toggle 30-second live mode
- **AI mode indicator** — Shows whether OpenAI or rule-based is active

---

## 🗂️ Project Structure

```
ai-email-agent/
├── Dockerfile
├── docker-compose.yml
├── .env.example               ← copy to .env
├── .gitignore
├── README.md
│
├── backend/
│   ├── requirements.txt
│   ├── database.py            ← SQLAlchemy models, DB init
│   ├── email_reader.py        ← Mock / IMAP / Gmail readers
│   ├── classifier.py          ← OpenAI + rule-based classifier
│   └── agent.py               ← Main processing loop, stats
│
├── frontend/
│   └── dashboard.py           ← Streamlit dashboard
│
└── data/
    └── mock_emails.json       ← 12 test emails (various categories)
```

---

## 🧪 Testing Without Docker

```bash
cd backend
pip install -r requirements.txt

# Set env vars
export EMAIL_SOURCE=mock
export OPENAI_API_KEY=your-key   # optional

# Run agent once
python -c "
from database import init_db
from agent import process_emails
init_db()
n = process_emails()
print(f'Processed {n} emails')
"

# Launch dashboard
cd ../frontend
streamlit run dashboard.py
```

---

## 🔧 Troubleshooting

| Issue | Fix |
|---|---|
| Dashboard blank / no emails | Click "Run Agent Now" in sidebar |
| IMAP login failed | Use App Password, not your Gmail password |
| OpenAI error | Check `OPENAI_API_KEY` in `.env`; system will fall back to rules |
| Gmail API error | Re-run `scripts/gmail_auth.py` to refresh `token.json` |
| Port 8501 in use | Change port in `docker-compose.yml` and `.env` |
| DB locked | Stop both containers, then `docker compose up` again |

---

## ⚠️ Limitations

1. **Gmail OAuth requires one-time browser auth** — run auth script before containerizing
2. **IMAP reads only UNSEEN emails** — already-read emails won't be fetched
3. **Mock mode resets on first run** — all 12 mock emails are processed once and remembered
4. **OpenAI costs money** — ~$0.001 per email with gpt-3.5-turbo; use mock mode for heavy testing
5. **No real-time push** — polling-based; new emails appear after the next poll cycle
6. **SQLite for single-node** — swap to PostgreSQL for multi-container production use

---

## 🔐 Security Notes

- Never commit `.env`, `credentials.json`, or `token.json` to git (covered by `.gitignore`)
- Use Gmail App Passwords, not your real password
- The `.env.example` file contains no real secrets — it's safe to commit

---

## 📄 License

MIT — free to use and modify.
