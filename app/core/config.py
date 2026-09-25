from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./job_agent.db"
    auto_submit: bool = False
    min_fit_score: float = 0.72
    poll_seconds: int = 60
    greenhouse_boards_json: str = "{}"
    lever_sites_json: str = "{}"
    java_resume_path: str = "resumes/java_resume.docx"
    ai_resume_path: str = "resumes/ai_resume.docx"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
