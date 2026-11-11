import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx

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
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(url, params={"key": api_key},
            json={"contents":[{"parts":[{"text":prompt}]}]})
    if response.status_code != 200:
        return {"answer":"The AI service is temporarily unavailable. Please try again or contact the relevant university office."}
    result = response.json()
    try:
        answer = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        answer = "I couldn't generate a response right now. Please try again."
    return {"answer": answer}
