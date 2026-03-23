from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI()

@app.websocket("/ws/job")
async def job_ws(websocket: WebSocket):
    await websocket.accept()

    # simulate job steps
    steps = [
        "Initializing...",
        "Validating data...",
        "Uploading files...",
        "Saving to database...",
        "Finalizing..."
    ]

    for step in steps:
        await websocket.send_text(step)
        await asyncio.sleep(2)

    await websocket.send_text("SUCCESS")