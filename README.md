# Ambiguity-Aware VQA for Accessibility

A web app that answers questions about **images** (and optionally short **videos**) with an explicit focus on **ambiguity-aware** and **accessibility-first** interaction. The UI supports screen readers, keyboard-only navigation, and optional voice input/output.

---

## What this project does

### Image VQA (required)
Upload an image and ask a question like:
- “What is on the table?”
- “Where is the keyboard?”
- “How many cups are there?”

The system returns an answer plus an ambiguity-aware description (objects, attributes, locations).

### Interaction modes
- **One-Pass**: A single comprehensive response that may describe multiple plausible interpretations.
- **Iterative**: A clarification flow designed for accessibility (e.g., refine intent for a focused answer).

### Video support
- **Video**: Samples frames across time and produces a timeline-style ambiguity-aware summary.

> Video features require **ffmpeg + ffprobe** installed on the backend machine.

---

## Tech stack

- **Frontend**: Next.js (React + TypeScript)
- **Backend**: FastAPI (Python)
- **Model**: OpenAI API (vision + text)
- **Accessibility**: ARIA live region, labeled inputs, keyboard-friendly controls, optional voice input/output

---
## Setup

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY
# for videos
sudo apt-get update
sudo apt-get install -y ffmpeg
uvicorn app.main:app --reload --port 8000
```
### Frontend
```bash
cd frontend
npm install
npm run dev
#the port 3000 is assumed, if port 3000 is occupied, you can switch to a new port, but make sure that you edit FRONTEND_ORIGIN in backend/.env to match the port.
```
### Use the app
Open the frontend in your browser:

http://localhost:3000
 (or other port if you changed it)

Upload an image (or video).

Type a question.

Choose a mode:

Respond in One Pass

Clarify Iteratively

Click Run.