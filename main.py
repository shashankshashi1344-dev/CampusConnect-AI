import logging
import os
import re

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("campusconnect")

app = FastAPI(title="CampusConnect AI", version="1.0.0")
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

FAQS = [
    (("academic", "academics", "faculty", "advisor", "subject", "course", "study", "class"),
     "For academic-related assistance, students may contact their faculty advisor."),
    (("attendance", "absent", "minimum attendance", "attendance percentage"),
     "Students should follow the minimum attendance requirement prescribed by university regulations. The exact percentage is not provided in the supplied information, so please check the official university regulations."),
    (("exam", "examination", "timetable", "time table", "schedule", "exam date", "notification"),
     "Examination timetables and notifications are published through official university channels. The exact date of your next examination is not available in the supplied information."),
    (("placement", "job", "career", "training", "internship", "recruit"),
     "For training and placement-related information, students may contact the Placement Department."),
    (("hostel", "room", "accommodation", "warden"),
     "Hostel-related complaints should be submitted to the Hostel Administration."),
    (("library", "book", "journal", "resource", "reading"),
     "Students may access library resources according to the library's timings and regulations. Specific timings are not provided in the supplied information."),
    (("certificate", "administration", "admin", "student record", "records", "transcript", "document"),
     "For certificates and student records, students may contact the respective administrative office."),
    (("event", "events", "fest", "function", "announcement"),
     "University event announcements are shared through official communication channels."),
]


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


def local_answer(question: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]", " ", question.lower())
    normalized = " ".join(normalized.split())
    best_answer = None
    best_score = 0
    for keywords, answer in FAQS:
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_score = score
            best_answer = answer
    if best_answer:
        return best_answer
    return (
        "This information is not available in the supplied university knowledge source. "
        "Please contact the relevant university department or check official university "
        "communication channels. I don't want to guess and give you incorrect information."
    )


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "CampusConnect AI",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    }


@app.post("/api/ask")
async def ask(data: Question):
    question = data.question.strip()
    if not question:
        return {"answer": "Please enter a question.", "mode": "local"}

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    # Always keep the helpdesk useful even when the external AI provider is unavailable.
    fallback = local_answer(question)
    if not api_key:
        return {
            "answer": fallback,
            "mode": "local",
            "notice": "Using the campus knowledge base because Gemini is not configured.",
        }

    prompt = f"""You are CampusConnect AI, a university helpdesk assistant.
Answer using ONLY the supplied knowledge. Do not invent facts, dates, percentages, contacts, office hours or policies.
If the information is not present, clearly say it is unavailable in the supplied information and direct the student to official university channels or the relevant office.
Be concise, friendly and helpful. Understand paraphrased questions.
KNOWLEDGE:
{KNOWLEDGE}
STUDENT QUESTION: {question}
Answer:"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
        if response.status_code != 200:
            # Do not log or return credentials. Keep the helpdesk usable during provider errors.
            logger.error("Gemini API returned HTTP %s", response.status_code)
            return {
                "answer": fallback,
                "mode": "local",
                "notice": f"Gemini is temporarily unavailable (HTTP {response.status_code}); using the campus knowledge base.",
            }

        result = response.json()
        answer = result["candidates"][0]["content"]["parts"][0]["text"]
        return {"answer": answer, "mode": "gemini"}
    except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Gemini request/response failed: %s", type(exc).__name__)
        return {
            "answer": fallback,
            "mode": "local",
            "notice": "Gemini is temporarily unavailable; using the campus knowledge base.",
        }
