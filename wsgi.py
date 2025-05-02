# wsgi.py
from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import uuid
from datetime import datetime
from openai import OpenAI
import sys
import uvicorn
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from utils.file_operations import load_json, save_json, to_pretty_json, get_last_conversation, clear_chat_data
from utils.ai_services import AIService

ai_service = AIService()

chat_log_file = "chat_log.json"
summary_file = "chatsummary.json"
user_history_file = "user_history.json"
max_rallies = 7
image_options = "https://images.pexels.com/photos/67468/pexels-photo-67468.jpeg?cs=srgb&dl=pexels-life-of-pix-67468.jpg&fm=jpg"

async def update_user_messages(phone_number, message_pair):
  user_history = await load_json(user_history_file, {})

  if user_history is None or isinstance(user_history, list):
    user_history = {}

  if phone_number not in user_history:
    user_history[phone_number] = {
    "user_id": str(uuid.uuid4()),
    "created_at": datetime.now().isoformat(),
    "messages": []
    }

  if phone_number in user_history and "messages" not in user_history[phone_number]:
    user_history[phone_number]["messages"] =[]

  user_history[phone_number]["messages"].append(message_pair)

  if len(user_history[phone_number]["messages"]) > max_rallies:
    user_history[phone_number]["messages"] = user_history[phone_number]["messages"][-max_rallies:]
  await save_json(user_history_file, user_history)

# Create a FastAPI app
app = FastAPI(title="Ninja.AI Restaurant Recommendation System")

# Create a directory for templates if it doesn't exist
os.makedirs('templates', exist_ok=True)

# Save index.html to templates directory
if not os.path.exists('templates/index.html'):
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(open('index.html', 'r', encoding='utf-8').read())

# Setup templates
templates = Jinja2Templates(directory="templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request model
class MessageRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def process_message(message_request: MessageRequest, session_id: Optional[str] = Cookie(None)):
    body = message_request.message
    
    user_id = str(uuid.uuid4())
    
    history = await load_json(chat_log_file, [])
    summary = await load_json(summary_file, [])
    user_history_for_json = await load_json(user_history_file, {})

    last_pair = await get_last_conversation(history)

    if last_pair:
        last_two_json = await to_pretty_json(last_pair)
    else:
        last_two_json = ""
    
    user_history_json = await to_pretty_json(user_history_for_json)
    summary_json = await to_pretty_json(summary)
    
    user_message = {
        "role": "user", 
        "content": body, 
        "user_id": user_id, 
        "timestamp": datetime.now().isoformat()
    }
    
    history.append(user_message)

    intent = await ai_service.openrouter_classify_intent(body)
    
    # Process the response based on intent
    if intent == "image_request":
        
        text_response = await ai_service.openrouter_generate_response(body, summary_json, user_history_json, last_two_json)
        
        response_text = text_response
        
        assistant_response = {
            "role": "assistant",
            "id": str(uuid.uuid4()),
            "content": response_text,
            "image_url": image_options,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

        quick_response = await ai_service.openrouter_generate_quick_summarize_response(body)

        quick_assistant_response = {
            "role": "assistant",
            "id": str(uuid.uuid4()),
            "content": response_text,
            "image_url": image_options,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        
        result = {
            "response": response_text,
            "image_url": image_options
        }
    
    else:  # text_response
        text_response = await ai_service.openrouter_generate_response(body, summary_json, user_history_json, last_two_json)
        
        response_text = text_response
        
        assistant_response = {
            "id": text_response.id if hasattr(text_response, 'id') else str(uuid.uuid4()),
            "role": "assistant",
            "content": response_text,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

        quick_response = await ai_service.openrouter_generate_quick_summarize_response(body)

        quick_assistant_response = {
            "role": "assistant",
            "id": str(uuid.uuid4()),
            "content": response_text,
            "image_url": image_options,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        
        result = {
            "response": response_text
        }
    
    # Update history and user messages
    history.append(assistant_response)
    await save_json(chat_log_file, history)

    quick_reply_response = await ai_service.openrouter_generate_quick_reply(body, response_text, summary_json)

    result["quickReplies"] = quick_reply_response



    
    
    message_pair = {
        "user": user_message,
        "assistant": quick_assistant_response,
        "timestamp": datetime.now().isoformat()
    }
    
    await update_user_messages(user_id, message_pair)
    
    summarize_response = await ai_service.openrouter_summarize_conversation(summary_json, user_history_json, last_two_json)
    
    summary = [{"role": "developer", "content": summarize_response}]
    await save_json(summary_file, summary)
    
    # Create a response with a cookie to track the session
    response = JSONResponse(content=result)
    response.set_cookie(key="session_id", value=session_id)
    
    return response

@app.post("/clear")
async def Clear():
    await clear_chat_data()
    return JSONResponse(content={"status": "success", "message": "Clear chat history"})

if __name__ == "__main__":
    # Ensure index.html is in templates directory
    if not os.path.exists('templates/index.html'):
        print("Error: index.html not found in templates directory")
        print("Current directory:", os.getcwd())
        print("Files in current directory:", os.listdir())
        sys.exit(1)
        
    # Run the FastAPI application with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)