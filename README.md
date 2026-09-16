# BPUT Hackathon 2026 — Campus Operational Platform

A unified web platform replacing fragmented campus operations (attendance, complaints,
leave/gate-pass, notices, feedback, certificates) with a single dual-portal system.

## Tech Stack
- **Backend:** Django 5.0, PostgreSQL (prod) / SQLite (dev)
- **AI/LLM:** Local Ollama (Llama 3 / Qwen 2.5)
- **RAG:** FAISS + sentence-transformers
- **Frontend:** Django Templates + HTMX + PWA (offline-first)
- **i18n:** English, Hindi, Odia

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver