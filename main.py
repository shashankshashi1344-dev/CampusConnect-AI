import os
import logging

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("campusconnect")

app = FastAPI(title="CampusConnect AI")
app.mount("/static", StaticFiles(directory="static"), name="static")

KNOWLEDGE = """
Presidency University sample competition information (TECHNOPIA 2.0; not official regulations):
Academics: Students may contact their faculty advisor for academic-related assistance.
Attendance: Students should follow the minimum attendance requirement prescribed by university regulations.
Examinations: Examination timetables and notifications are published through official university channels.
Placements: Students may contact the Placement Department for training and placement-related information.
Library: Students may access library resources according to the library's timings and regulations.
Hostel: Hostel-related complaints should be submitted to the Hostel Administration.
Administration: Students may contact the respective administrative office for certificates and student records.
Events: University event announcements are shared through official communication channels.
Unknown facts must not be invented. If the answer is not supported by this information, say it is unavailable.
"""


class Question(BaseModel):
    question: str


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/api/ask")
async def ask(data: Question):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is missing from the service environment")
        return {"answer": "AI backend is not configured yet. Add GEMINI_API_KEY as a server environment variable to enable AI responses."}

    prompt = f"""You are CampusConnect AI, a university helpdesk assistant.
Answer using ONLY the supplied knowledge. Do not invent facts, dates, percentages, contacts, office hours or policies.
If the information is not present, clearly say it is unavailable in the supplied information and direct the student to official university channels or the relevant office.
Be concise, friendly and helpful. Understand paraphrased questions and follow-up wording.
KNOWLEDGE:
{KNOWLEDGE}
STUDENT QUESTION: {data.question}
Answer:"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                params={"key": api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
    except httpx.RequestError as exc:
        logger.exception("Could not connect to Gemini API: %s", type(exc).__name__)
        return {"answer": "CampusConnect AI cannot reach the AI service right now. Please try again shortly."}

    if response.status_code != 200:
        # Log the provider's diagnostic response, but never log the API key.
        logger.error(
            "Gemini API returned HTTP %s: %s",
            response.status_code,
            response.text[:1500],
        )
        return {
            "answer": f"The AI provider returned an error (HTTP {response.status_code}). Please try again later."
        }

    try:
        result = response.json()
        answer = result["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError):
        logger.error("Gemini API response did not contain a usable answer: %s", response.text[:1000])
        answer = "I couldn't generate a response right now. Please try again."

    return {"answer": answer}
