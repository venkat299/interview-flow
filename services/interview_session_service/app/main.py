from fastapi import FastAPI
from api.v1.endpoints import interview_ws

app = FastAPI(title="Interview Session Service")
app.include_router(interview_ws.router, prefix="/api/v1")
