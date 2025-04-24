from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import json
import uuid
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)

account_sid = os.getenv("ACCOUNT_SID")
auth_token = os.getenv("AUTH_TOKEN")
# client = Client(account_sid, auth_token)
client = OpenAI()
chat_log_file = "chat_log.json"
summary_file = "chatsummary.json"
user_history_file = "user_history.json"
max_rallies = 7
image_options = "https://images.pexels.com/photos/67468/pexels-photo-67468.jpeg?cs=srgb&dl=pexels-life-of-pix-67468.jpg&fm=jpg"

def load_history():
  try:
    with open(chat_log_file, "r") as f:
      return json.load(f)
  except FileNotFoundError:
    return []
def load_summary():
  try:
    with open(summary_file, "r") as f:
      return json.load(f)
  except FileNotFoundError:
    return []
def load_user_history():
  try:
    with open(user_history_file, "r") as f:
      return json.load(f)
  except FileNotFoundError:
    return {}
def save_history(history):
  with open(chat_log_file, "w") as f:
    json.dump(history, f, indent=2, ensure_ascii=False)

def save_summary(summary):
  with open(summary_file, "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
def save_user_history(user_history):
  with open(user_history_file, "w") as f:
    json.dump(user_history, f, indent=2, ensure_ascii=False)

def get_user_id(phone_number):
  user_history = load_user_history()

  if phone_number is None or isinstance(user_history, list):
    user_history

  if phone_number not in user_history:
    user_history[phone_number] = {
      "user_id": str(uuid.uuid4()),
      "created_at": datetime.now().isoformat(),
      "message": []
    }
    save_user_history(user_history)
  return user_history[phone_number]["user_id"]

def update_user_messages(phone_number, message_pair):
  user_history = load_user_history()

  if user_history is None or isinstance(user_history, list):
    user_history = {}

  if phone_number not in user_history:
    get_user_id(phone_number)
    user_history = load_user_history()

    if user_history is None or isinstance(user_history, list):
      user_history = {}
      user_history[phone_number] = {
        "user_id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "message": []
      }

  if phone_number in user_history and "messages" not in user_history[phone_number]:
    user_history[phone_number]["messages"] =[]

  user_history[phone_number]["messages"].append(message_pair)

  if len(user_history[phone_number]["messages"]) > max_rallies:
    user_history[phone_number]["messages"] = user_history[phone_number]["messages"][-max_rallies:]
  save_user_history(user_history)

@app.route("/webhook", methods=["GET","POST"])
def whatsapp_bot():
  phone_number = request.values.get('From', '') # get the user phone number
  body = request.values.get('Body', None)
  resp = MessagingResponse()

  user_id = get_user_id(phone_number)

  history = load_history()
  history_json = json.dumps(history, ensure_ascii=False, indent=2)
  summary = load_summary()
  summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
  user_history_for_json = load_user_history()
  user_history_json = json.dumps(user_history_for_json, ensure_ascii=False, indent=2)

  user_message = {"role": "user", "content": body, "user_id": user_id, "timestamp": datetime.now().isoformat()}

  history.append(user_message)

  assistance_id = None
  if history:
    for msg in reversed(history):
      if msg.get("role") == "assistant":
        assistance_id = msg.get("id")
        break
  system_prompt = f"""# Ninja.AI Restaurant Recommendation System

## System Overview
You are Ninja.AI, an AI assistant specializing in Japanese restaurant recommendations. Your purpose is to help users find authentic, high-quality dining experiences in Japan, with a focus on Tokyo. You prioritize local favorites over tourist traps and aim to match users with restaurants that suit their specific preferences and budget.

## Core Values
- **Authentic Recommendations**: Prioritize local establishments with genuine quality over tourist-oriented places
- **Personalized Service**: Ask thoughtful follow-up questions to understand user preferences
- **Detailed Knowledge**: Provide specific, insider information about restaurants
- **Warm Hospitality (Omotenashi)**: Embody the Japanese spirit of hospitality with attentive, thoughtful service
- **Efficient Communication**: Balance thoroughness with concise responses

## Conversation Style
- **Tone**: Polite, warm, and knowledgeable but not overly formal
- **Structure**: Progressive narrowing of options based on user preferences
- **Questions**: Ask one clear follow-up question at a time to understand preferences better
- **Details**: Provide rich details about recommended restaurants (history, specialties, atmosphere)
- **Format**: Present information in organized, easy-to-scan formats with bullets and sections
- **Cultural Context**: Offer cultural insights when relevant

## Recommendation Process
1. **Initial Understanding**: Ask about cuisine preferences, location, and any specific requirements
2. **Progressive Refinement**: Narrow down options based on user responses
3. **Budget Confirmation**: Tactfully establish budget expectations 
4. **Final Recommendations**: Provide 1-3 detailed restaurant options with:
   - Restaurant name and location (including neighborhood character)
   - Specialty dishes and price points
   - Atmosphere and typical clientele
   - "Hidden value" aspects that make it special
5. **Practical Information**: Offer reservation assistance, directions, and dining tips
6. **Follow Through**: Ensure all user questions are addressed before concluding

## Restaurant Information to Include
- **Name & Location**: Full name with neighborhood context
- **Specialties**: Signature dishes with prices
- **Price Range**: Clear indication of typical per-person cost
- **Atmosphere**: Physical space and typical clientele
- **Local Reputation**: Why locals value this establishment
- **Availability**: Current reservation status if known
- **Access**: Clear directions from major landmarks
- **Insider Tips**: Recommendations for optimal experience

## Japanese Cultural Elements to Incorporate
- **Seasonal Awareness**: Mention seasonal specialties when appropriate
- **Dining Customs**: Subtly include relevant Japanese dining etiquette
- **Local Context**: Provide neighborhood character and history when relevant
- **Authenticity Markers**: Highlight elements that signal genuine quality to locals

## Response Structure
1. **Acknowledgment**: Confirm understanding of the user's preferences
2. **Options**: Present recommended restaurants in clear, structured format
3. **Details**: For each option, provide rich, specific details that demonstrate insider knowledge
4. **Next Steps**: Offer to make reservations or provide additional information
5. **Follow-up**: Ask if the recommendations meet their needs or if they'd like alternatives

## Example Interactions
When users provide vague requests like "recommend a good restaurant in Tokyo," respond with:
"Tokyo offers an incredible range of dining experiences. To help you find the perfect spot, could you share what type of cuisine you're interested in? Are you looking for traditional Japanese food, or perhaps something else?"

When users specify a cuisine type but little else, ask:
"[Cuisine type] is an excellent choice. Tokyo has many wonderful [cuisine] restaurants. Could you share what kind of atmosphere you're looking for? For example, are you interested in a high-end experience, a local favorite, or something more casual?"

For budget discussions, use indirect phrasing:
"To help find the perfect match, could you give me an idea of your budget expectations? Tokyo offers excellent [cuisine] options across many price points."

## Technical Requirements
- Ask only one question at a time to avoid overwhelming users
- Provide specific price ranges when discussing restaurant costs
- Include practical details like address and access information
- Balance detail with conciseness; prioritize quality information over quantity
- When making recommendations, present options in a clear, structured format

Remember that your primary goal is to connect users with authentic Japanese dining experiences that they'll genuinely enjoy, while providing the detailed information and warm hospitality that would make their visit memorable.

the below things are the summary of conversation and chat history with users so please continue the conversation naturally:

---
###Summary fo conversation
{summary_json}
###Recent conversation with users
{user_history_json}
"""
  summarizing_prompt = f"""You are an expert conversation summarizer.

Your task is to analyze and summarize a JSON-formatted chat history between a user and an AI assistant. The goal is to extract key details and provide a clear, structured summary of the conversation.

Use the following output format:

---

### Chat Summary

#### 1. **Overview**
Briefly describe the overall context of the conversation, the participants, and the tone.

#### 2. **Key Points**
List 5-7 bullet points that highlight the most important facts, insights, or decisions discussed during the conversation.

#### 3. **Topic Timeline** (optional)
If applicable, outline the main topics discussed in chronological order.

#### 4. **Follow-up Items**
List any remaining questions, action items, or topics that could be explored further.

#### 5. **Context Notes**
Mention any relevant background, such as the fictional setting, tone of the assistant, or relationship between participants.

---

Focus on clarity and usefulness. If the conversation is based on a fictional character (e.g., anime, games), preserve the tone and role-playing context in your summary.

Now, here is the chat history to summarize:
{history_json}
"""
  intent_prompt = f"""
You are an intent classifier. Classify the user's message into one of the following categories:

1. image_request → If the user is asking for a visual representation, image, or showing interest in something that would be better understood with a picture.
2. text_response → If the user wants to continue the conversation or is asking for a text-based answer.

Respond with only the category name: "image_request" or "text_response".

User message:
"{body}"
"""

  intent_res = client.responses.create(
    model="gpt-4o",
    input=[
        {"role": "system", "content": "You classify intent."},
        {"role": "user", "content": intent_prompt}
    ]
  )

  intent = intent_res.output_text

  assistant_response = {}

  if intent == "image_request":
      # GPTで画像選定 → Twilioに送信
      image_url = image_options
      if image_url:
          text_response = client.responses.create(
            model="gpt-4o",
            instructions=system_prompt,
            input=body,
            store=False
          )
          response_text = text_response.output_text        
          resp.message(response_text)
          msg = resp.message(response_text)
          msg.media("https://images.pexels.com/photos/67468/pexels-photo-67468.jpeg?cs=srgb&dl=pexels-life-of-pix-67468.jpg&fm=jpg")
          assistant_response = {
            "role": "assistant",
            "id": str(uuid.uuid4()),
            "content": response_text,
            "image_url": image_url,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
          }
      else:
          resp.message("ごめん、今はちょうどいい画像が見つからなかったんだ〜！")
          assistant_response = {
            "role": "assistant",
            "id": str(uuid.uuid4()),
            "content": response_text,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
          }
      # ここにhistoryの更新とsaveを追加
      history.append(assistant_response)
      save_history(history)

      message_pair = {
        "user": user_message,
        "assistant": assistant_response,
        "timestamp": datetime.now().isoformat()
      }
      update_user_messages(phone_number, message_pair)
      
      # returnステートメントを追加
      return str(resp)
  elif intent == "text_response":
      # 通常のルフィトーク生成
      if assistance_id:
        text_response = client.responses.create(
            model="gpt-4o",
            instructions=system_prompt,
            input=body,
            store=False
        )
      else:
        text_response = client.responses.create(
            model="gpt-4o",
            instructions=system_prompt,
            input=body,
            store=False
        )
      response_text = text_response.output_text        
      resp.message(response_text)

      assistant_response = {
        "id": text_response.id,
        "role": "assistant",
        "content": response_text,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
      }

      history.append(assistant_response)
      save_history(history)

      message_pair = {
        "user": user_message,
        "assistant": assistant_response,
        "timestamp": datetime.now().isoformat()
      }
      update_user_messages(phone_number, message_pair)


      summarize_bot = client.responses.create(
        model="gpt-4o",
        input=[{"role": "user", "content": summarizing_prompt}],
        store=False
      )

      summary = [{"role": "developer", "content": summarize_bot.output_text}]
      save_summary(summary)

      return str(resp)
if __name__ == "__main__":
    app.run(debug=True)