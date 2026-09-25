# Autonomous Job Agent

A continuously running job-discovery and matching service.

Current capabilities:
- Monitors configured Greenhouse and Lever job boards
- Deduplicates newly discovered postings in memory
- Scores jobs against a private deployment-time candidate profile
- Enforces minimum salary and fit rules
- Exposes health, profile, discovery, and job APIs
- Keeps personal data and resume files out of the public repository

## Run

Copy `.env.example` to `.env`, configure your private values, then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docker/Railway deployment is supported through the included Dockerfile.

## Safety and truthfulness

The agent is designed not to fabricate application answers. CAPTCHA, MFA, unsupported required questions, and other blocked flows should stop rather than be bypassed.

## Current limitation

This deployment stage performs continuous discovery, matching, and queue preparation. Fully automatic browser submission and persistent application tracking will be added after the deployed discovery service is verified.
