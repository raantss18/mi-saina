from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import scheduler

router = APIRouter()


class JobBody(BaseModel):
    name: str
    prompt: str
    schedule: str   # "every:N" | "daily:HH:MM" | "weekly:DOW:HH:MM"


@router.get("")
def list_jobs():
    return scheduler.load_jobs()


@router.post("")
def create_job(body: JobBody):
    return scheduler.add_job(body.name.strip(), body.prompt.strip(), body.schedule.strip())


@router.delete("/{job_id}")
def remove_job(job_id: str):
    scheduler.delete_job(job_id)
    return {"status": "deleted"}


@router.post("/{job_id}/toggle")
def toggle(job_id: str):
    scheduler.toggle_job(job_id)
    return {"status": "ok"}


@router.post("/{job_id}/run")
async def run_now(job_id: str):
    job = next((j for j in scheduler.load_jobs() if j["id"] == job_id), None)
    if not job:
        raise HTTPException(404, "Tâche introuvable")
    await scheduler._execute_job(job)
    return {"status": "ok"}
