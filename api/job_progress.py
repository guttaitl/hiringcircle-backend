from fastapi import WebSocket

connections = {}

async def connect(job_id: str, websocket: WebSocket):
    await websocket.accept()
    connections[job_id] = websocket

def disconnect(job_id: str):
    connections.pop(job_id, None)

async def send(job_id: str, message: str):
    ws = connections.get(str(job_id))
    if ws:
        await ws.send_text(message)