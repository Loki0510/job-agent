import base64, os, pathlib, tempfile

def _decode_var(name, filename):
    raw=os.getenv(name,"").strip()
    if not raw:
        return None
    root=pathlib.Path(tempfile.gettempdir())/"job-agent-resumes"
    root.mkdir(parents=True,exist_ok=True)
    path=root/filename
    if not path.exists():
        path.write_bytes(base64.b64decode(raw))
    return str(path)

def resume_for(profile_name):
    if profile_name=="ai":
        return _decode_var("RESUME_AI_B64","resume_ai.docx")
    return _decode_var("RESUME_JAVA_B64","resume_java.docx")
