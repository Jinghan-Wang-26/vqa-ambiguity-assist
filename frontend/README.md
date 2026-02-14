# Ambiguity-Aware VQA for Accessibility (A+)

## Setup

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
