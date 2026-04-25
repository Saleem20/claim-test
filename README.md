# 🧪 Bulk Claim Tester — Synthetic Persona Lab

Test up to **15 marketing claims** simultaneously against **6 synthetic consumer personas** powered by Claude AI — before anything goes to a vendor or research agency.

Built with Python · Streamlit · Anthropic Claude API

---

## What It Does

- Enter a category, product name and up to 15 claims
- Select which personas to test against
- Run all tests in one click
- Get scored, verdicted results ranked by performance
- Export to CSV for briefing documents

### Personas included
| Persona | Age |
|---|---|
| 🏙️ Young Urban Professional | 25–34 |
| 🏡 Suburban Family | 35–49 |
| 🌿 Empty Nester | 50–64 |
| 🧾 Budget-Conscious Shopper | All ages |
| 🧘 Health & Wellness Seeker | 28–45 |
| ☕ Senior Traditional | 65+ |

### Each result includes
- First gut reaction
- Name score (1–5) + Claim score (1–5)
- Written claim feedback
- What resonates / Concerns
- **Pass / Revise / Reject** verdict with reason

---

## Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/bulk-claim-tester.git
cd bulk-claim-tester
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your API key
Create `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```
Get your key at [console.anthropic.com](https://console.anthropic.com)

### 4. Run
```bash
streamlit run app.py
```
Opens at `http://localhost:8501`

---

## Deploy to Streamlit Cloud (Free)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/bulk-claim-tester.git
git push -u origin main
```

### Step 2 — Connect to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → branch: `main` → main file: `app.py`
5. Click **Advanced settings** → **Secrets**
6. Paste:
   ```
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
7. Click **Deploy**

Your app will be live at `https://YOUR_USERNAME-bulk-claim-tester-app-XXXXX.streamlit.app`

---

## Project Structure

```
bulk-claim-tester/
├── app.py              ← Main Streamlit application
├── personas.py         ← Persona definitions
├── claude_api.py       ← Claude API interface
├── requirements.txt    ← Python dependencies
├── .gitignore
├── .streamlit/
│   ├── config.toml     ← Dark theme config
│   └── secrets.toml    ← API key (local only, gitignored)
└── README.md
```

---

## Disclaimer

Synthetic persona outputs are hypothesis-generation tools for initial claim screening. They are not a substitute for primary consumer research. Validate all findings before presenting to vendors or stakeholders.

---

*Built on the principles outlined in "Synthetic Personas: How AI is Realising the Full Potential of Consumer Segmentation" — RDA Research, 2026.*
