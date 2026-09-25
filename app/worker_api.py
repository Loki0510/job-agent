import asyncio
import html
import os
import pathlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from app.worker import main as worker_main
from app.worker_state import categorized, read_history, baseline_ids

RESUME_DIR=pathlib.Path(os.getenv("RESUME_DIR","/data/resumes"))
SETUP_TOKEN=os.getenv("SETUP_TOKEN","")

def _check(token):
    if not SETUP_TOKEN or token!=SETUP_TOKEN:
        raise HTTPException(status_code=401,detail="invalid setup token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    RESUME_DIR.mkdir(parents=True,exist_ok=True)
    task=asyncio.create_task(worker_main())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app=FastAPI(title="Job Agent Worker",version="0.5",lifespan=lifespan)

@app.get("/health")
async def health():
    return {
        "status":"ok",
        "java_resume":(RESUME_DIR/"resume_java.docx").exists(),
        "ai_resume":(RESUME_DIR/"resume_ai.docx").exists(),
        "auto_submit":os.getenv("AUTO_SUBMIT","false").lower()=="true",
        "baseline_jobs":len(baseline_ids()),
    }

@app.get("/applications")
async def applications(token: str):
    _check(token)
    groups=categorized()
    return {"counts":{key:len(value) for key,value in groups.items()},**groups}

@app.get("/history")
async def history(token: str, limit: int=250):
    _check(token)
    limit=max(1,min(limit,1000))
    rows=read_history(limit)
    return {"count":len(rows),"history":rows}

@app.get("/setup",response_class=HTMLResponse)
async def setup(token: str):
    _check(token)
    safe=html.escape(token,quote=True)
    return f"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Agent Resume Setup</title>
<style>body{{font-family:system-ui;max-width:720px;margin:40px auto;padding:0 18px}}label{{display:block;margin:20px 0 6px}}button{{margin-top:24px;padding:10px 18px}}</style>
</head><body>
<h1>Private résumé setup</h1>
<p>Upload the Java/full-stack résumé and the AI/GenAI résumé. They are stored on the private Railway volume, not in GitHub.</p>
<form action="/setup/resumes?token={safe}" method="post" enctype="multipart/form-data">
<label>Java / Full Stack résumé (.docx)</label>
<input name="java_resume" type="file" accept=".docx" required>
<label>AI / GenAI résumé (.docx)</label>
<input name="ai_resume" type="file" accept=".docx" required>
<br><button type="submit">Save résumés</button>
</form></body></html>"""

@app.post("/setup/resumes",response_class=HTMLResponse)
async def upload_resumes(token: str, java_resume: UploadFile=File(...), ai_resume: UploadFile=File(...)):
    _check(token)
    RESUME_DIR.mkdir(parents=True,exist_ok=True)
    if not (java_resume.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400,detail="Java resume must be .docx")
    if not (ai_resume.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400,detail="AI resume must be .docx")
    java_bytes=await java_resume.read()
    ai_bytes=await ai_resume.read()
    if not java_bytes or not ai_bytes or len(java_bytes)>5_000_000 or len(ai_bytes)>5_000_000:
        raise HTTPException(status_code=400,detail="invalid resume file size")
    (RESUME_DIR/"resume_java.docx").write_bytes(java_bytes)
    (RESUME_DIR/"resume_ai.docx").write_bytes(ai_bytes)
    return "<h2>Saved.</h2><p>Both résumés are now stored privately and persistently. You can close this page.</p>"
