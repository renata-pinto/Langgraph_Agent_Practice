from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agent import run_agent_task # Import your celery task
from celery.result import AsyncResult

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace "*" with your React URL
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/ask")
async def ask_cardia(request: ChatRequest):
    # 1. Hand the question to the worker
    task = run_agent_task.delay(request.message)
    # 2. Return the task_id immediately so the app doesn't hang
    return {"task_id": task.id}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    task_result = AsyncResult(task_id)
    if task_result.ready():
        result_data = task_result.result # This is now our dict from Step 2
        return {
            "status": "SUCCESS", 
            "response": result_data["answer"], # The clean message for the user
            "internal_sources": result_data["sources"] # Hidden proof for you!
        }
    return {"status": "PROCESSING"}