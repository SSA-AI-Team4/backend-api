# Backend API

This is a FastAPI backend that ingests CSV files (job roles and process flows) and serves them to a frontend site.

## Run locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
