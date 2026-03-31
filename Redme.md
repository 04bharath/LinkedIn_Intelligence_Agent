# 💼 LinkedIn Intelligence & Job Scraper

A production-grade Streamlit dashboard that scrapes LinkedIn job postings via RapidAPI, extracts structured data using AI, deduplicates with vector search, and saves everything to Google Sheets — all in one pipeline.

---

## ✨ Features

- **Multi-endpoint scraping** — Tries 3 RapidAPI LinkedIn endpoints in order; falls back to rich mock data so the demo always works
- **AI-powered extraction** — Uses Lyzr AI to parse 18 structured fields from raw job posts; smart regex fallback if API is unavailable
- **Vector deduplication** — Qdrant vector database stores job embeddings; duplicates are detected before saving
- **Semantic skill matching** — Enter your skills and get ranked job matches using `sentence-transformers` cosine similarity
- **Google Sheets export** — Auto-saves every new job to a linked spreadsheet with 20 columns
- **Premium dark UI** — Deep navy theme, animated pipeline, stat cards, activity log

---

## 🗂️ Project Structure

```
├── app.py            # Streamlit UI (all pages & layout)
├── fetch.py          # LinkedIn job fetching via RapidAPI
├── lyzr.py           # AI extraction layer (Lyzr AI + regex fallback)
├── qdrant_db.py      # Vector DB — store, search, deduplicate
├── sheets.py         # Google Sheets output layer
├── config.py         # API keys & configuration
├── creds.json        # Google service account credentials
└── requirements.txt  # Python dependencies
```

---

## ⚙️ Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/your-username/linkedin-intelligence.git
cd linkedin-intelligence
pip install -r requirements.txt
```

### 2. Configure API keys

Edit `config.py`:

```python
RAPIDAPI_KEY      = "your_rapidapi_key"
Lyzr_API_KEY      = "your_lyzr_api_key"
QDRANT_URL        = "https://your-cluster.qdrant.io"   # or leave blank for in-memory
QDRANT_API_KEY    = "your_qdrant_api_key"
GOOGLE_CREDS_FILE = "creds.json"
GOOGLE_SHEET_NAME = "LinkedIn"
```

### 3. Set up Google Sheets (optional)

1. Create a [Google Cloud service account](https://console.cloud.google.com/)
2. Enable the **Google Sheets API** and **Google Drive API**
3. Download the JSON key and save it as `creds.json` in the project root
4. Share your target Google Sheet with the service account email

### 4. Run the app

```bash
streamlit run app.py
```

---

## 🔑 API Keys Required

| Service | Purpose | Get it at |
|---|---|---|
| RapidAPI | Scrape LinkedIn job posts | [rapidapi.com](https://rapidapi.com) |
| Lyzr AI | Extract 18 fields from job posts | [lyzr.ai](https://www.lyzr.ai) |
| Qdrant Cloud | Persistent vector storage | [cloud.qdrant.io](https://cloud.qdrant.io) |
| Google Sheets | Export job data | [console.cloud.google.com](https://console.cloud.google.com) |

> **Note:** All services have free tiers. The app runs fully offline (with mock data + in-memory Qdrant) if no keys are configured.

---

## 🖥️ Pages

### 📊 Dashboard
Overview of pipeline stats — jobs fetched, saved, duplicates skipped, and total in database. Run a fetch directly from here.

### 🔍 Fetch Jobs
Enter a keyword (e.g. `Data Scientist`, `ML Engineer`) and trigger the full pipeline:

```
Fetch → AI Extract → Deduplicate → Store → Save to Sheets
```

### 🧠 Skill Matching
Enter your skills (comma-separated) and get semantically ranked job matches from the database using vector cosine similarity.

### 📋 Stored Jobs
Browse all jobs in the Qdrant database in a sortable table. Download as CSV.

### ⚙️ Settings
View API configuration, check integration status, and reset the database.

---

## 🧠 Extracted Fields (18)

Each job post is parsed into the following structured fields:

| Field | Description |
|---|---|
| `post_id` | Unique identifier |
| `role` | Job title |
| `company_name` | Hiring company |
| `location` | City / region |
| `primary_skills` | Top technical skills required |
| `secondary_skills` | Nice-to-have skills |
| `must_to_have` | Absolute requirements |
| `years_of_experience` | Experience range |
| `looking_for_college_students` | Yes / No |
| `intern` | Yes / No |
| `salary_package` | Compensation if mentioned |
| `email` | Contact email |
| `phone` | Contact phone |
| `hiring_intent` | Active / Passive / Unknown |
| `author_name` | Post author |
| `author_linkedin_url` | Author's LinkedIn profile |
| `post_url` | Direct link to the post |
| `date_posted` | Publication date |

---

## 🏗️ Tech Stack

- **[Streamlit](https://streamlit.io)** — UI framework
- **[RapidAPI](https://rapidapi.com)** — LinkedIn job data source
- **[Lyzr AI](https://www.lyzr.ai)** — AI field extraction
- **[Qdrant](https://qdrant.tech)** — Vector database for storage & search
- **[sentence-transformers](https://sbert.net)** — `all-MiniLM-L6-v2` for skill embeddings
- **[gspread](https://docs.gspread.org)** — Google Sheets integration

---

## 📦 Requirements

```
streamlit>=1.35
requests>=2.31
lyzr
qdrant-client>=1.9
sentence-transformers>=2.7
gspread>=6.1
oauth2client>=4.1.3
```

---

## 📄 License

MIT License — free to use, modify, and distribute.