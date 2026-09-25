import base64, os, pathlib, tempfile

PERSISTENT_DIR=pathlib.Path(os.getenv("RESUME_DIR","/data/resumes"))

def _secret(name):
    direct=os.getenv(name,"").strip()
    if direct:
        return direct
    parts=[]
    for i in range(1,20):
        value=os.getenv(f"{name}_{i:02d}","").strip()
        if not value:
            break
        parts.append(value)
    return "".join(parts)

def _persistent(profile_name):
    filename="resume_ai.docx" if profile_name=="ai" else "resume_java.docx"
    path=PERSISTENT_DIR/filename
    return str(path) if path.exists() and path.stat().st_size>0 else None

def _decode_var(name, filename):
    raw=_secret(name)
    if not raw:
        return None
    root=pathlib.Path(tempfile.gettempdir())/"job-agent-resumes"
    root.mkdir(parents=True,exist_ok=True)
    path=root/filename
    if not path.exists():
        path.write_bytes(base64.b64decode(raw))
    return str(path)

def resume_for(profile_name):
    stored=_persistent(profile_name)
    if stored:
        return stored
    if profile_name=="ai":
        return _decode_var("RESUME_AI_B64","resume_ai.docx")
    return _decode_var("RESUME_JAVA_B64","resume_java.docx")
