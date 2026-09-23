from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging
from typing import List, Dict
from datetime import datetime, timezone
from app.services.llm_service import llm_service

logger = logging.getLogger("voxvision.websocket")

router = APIRouter(tags=["WebSocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining active: {len(self.active_connections)}")

    async def send_json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)

manager = ConnectionManager()

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for VoxVision AI chat communication.
    Receives user messages, queries modular LLM service, and returns AI responses.
    """
    await manager.connect(websocket)
    conversation_history: List[Dict[str, str]] = []

    # Send initial connection acknowledgment payload
    await manager.send_json({
        "type": "connection_ack",
        "message": "Connected to VoxVision AI WebSocket Server",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                await manager.send_json({
                    "type": "error",
                    "message": "Invalid JSON format payload received.",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, websocket)
                continue

            msg_type = payload.get("type", "chat_message")

            # Handle Heartbeat Ping
            if msg_type == "ping":
                await manager.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, websocket)
                continue

            # Handle Chat Message
            if msg_type == "chat_message":
                user_message = payload.get("message", "").strip()
                session_id = payload.get("session_id", "default")

                if not user_message:
                    await manager.send_json({
                        "type": "error",
                        "message": "Empty message string provided.",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }, websocket)
                    continue

                # Query LLM service (Gemini, OpenAI, or Mock)
                llm_result = await llm_service.generate(user_message, conversation_history)
                reply_text = llm_result.get("reply", "No response generated.")
                status = llm_result.get("status", "success")

                # Update conversation history if successful
                if status == "success":
                    conversation_history.append({"role": "user", "content": user_message})
                    conversation_history.append({"role": "assistant", "content": reply_text})
                    # Keep history manageable (last 10 turns)
                    if len(conversation_history) > 20:
                        conversation_history = conversation_history[-20:]

                # Return payload over WebSocket
                response_payload = {
                    "type": "chat_response",
                    "reply": reply_text,
                    "status": status,
                    "provider": llm_result.get("provider", "voxvision"),
                    "model": llm_result.get("model", ""),
                    "error_code": llm_result.get("error_code"),
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await manager.send_json(response_payload, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket unexpected error: {e}")
        manager.disconnect(websocket)

