# CampusConnect AI — TECHNOPIA 2.0

A responsive university campus helpdesk prototype based on the supplied competition problem statement.

## Features
- Mobile-friendly chat interface and service categories
- Grounded answers for academics, attendance, examinations, placements, library, hostel, administration and events
- Unknown-information handling
- FastAPI backend with Gemini API integration
- API key read only from server environment variable

## Run locally
1. Install Python 3.10+.
2. In this folder run: `pip install -r requirements.txt`
3. Set `GEMINI_API_KEY` as an environment variable on the server (do not put it in frontend files).
4. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Open `http://localhost:8000`.

If no API key/backend is configured, the frontend falls back to a clearly labelled local demo response matcher. That fallback is for UI demonstration only and is not a substitute for the required AI integration.

## Deployment
Deploy this folder to a Python host that supports FastAPI. Set `GEMINI_API_KEY` in the host's secret/environment-variable settings. Do not commit `.env` or API keys to GitHub.

## Knowledge-source limitation
The supplied competition document contains sample information, not official university regulations. This prototype does not invent exact attendance percentages, exam dates, library hours, phone numbers or other missing details.
