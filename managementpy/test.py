from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import json
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)


# client = Client(account_sid, auth_token)
client = OpenAI()
log_file = "chat_log.json"
summary_dir = 'user_summries'

os.makedirs(summary_dir, exist_ok=True)

def load_history():
  try:
    with open(log_file, "r") as f:
      return json.load(f)
  except FileNotFoundError:
    return []

def save_history(history):
  with open(log_file, "w") as f:
    json.dump(history, f, indent=2, ensure_ascii=False)

def get_user_summary(user_id):
  """ユーザーのサマリーを取得"""
  summary_file = f"{summary_dir}/user_summary_{user_id.replace(':', '_').replace('+', '')}.json"
  try:
    with open(summary_file, "r") as f:
      return json.load(f)
  except FileNotFoundError:
    return None

def summarize_conversation(history, user_summary_):
  """会話履歴をようやくしてJSONに保存する機能"""
  summary_file = f"{summary_dir}/user_summary_{user_id.replace(':', '_')}.json"
  try:
    with open(summary_file, "f") as f:
      user_summary = json.load(f)
  except FileNotFoundError:
    user_summary = {
      "user_id": user_id,
      "preferences": {},
      "last_conversation_date": None,
      "conversation_count": 0
    }
  summarize_prompt = [
        {"role": "system", "content": """
        You are an assistant to extract important information from the chat histroy with user
        以下の会話履歴から、日本食レストランに関する次の情報を抽出してJSONフォーマットで返してください：
        1. cuisine_preferences: ユーザーの好きな料理タイプのリスト
        2. budget_range: 予算の範囲（数値の最小と最大）
        3. location_preferences: 好みの場所や地域のリスト
        4. dietary_restrictions: 食事制限やアレルギーのリスト
        5. mentioned_restaurants: 言及されたレストラン名のリスト
        6. atmosphere_preferences: 好みの雰囲気（例：カジュアル、フォーマル）
        7. important_notes: その他の重要な注意点
        
        JSONフォーマットのみを返してください。わからない情報は空のリストか null にしてください。
        """},
        {"role": "user", "content": f"以下の会話履歴を分析してください: {json.dumps(history[-10:], ensure_ascii=False)}"}
    ]

  try:
    summary_response = client.responses.create(
      model="gpt-4o",
      messages=summarize_prompt,
      response_format={"type": "json_object"},
    )

    extracted_info = json.loads(summary_response.choices[0].message.content)

    for category, values in extracted_info.items():
      if values:
        if category in user_summary["preferences"]:
          if isinstance(values, list) and isinstance(user_summary["preferences"][category], list):
            for item in values:
              if item not in user_summary["preferences"][category]:
                user_summary["preferences"][categroy].append(item)
          else:
            user_summary["preferences"][category] = values
    user_summary["conversation_count"] += 1
    user_summary["last_conversation_date"] = datetime.now().isoformat()

    with open(summary_file, "w") as f:
      json.dump(user_summary, f, indent=2, ensure_ascii=False)

    return user_summary
  except Exception as e:
    print(f"サマリー作成エラー: {e}")
    return None


@app.route("/webhook", methods=["GET","POST"])
def whatsapp_bot():
  print(dir(datetime.now()))
  user_id = request.values.get('From', '') # get the user phone number
  body = request.values.get('Body', None)
  resp = MessagingResponse()
  history = load_history()
  user_history = [msg for msg in history if msg.get("user_id", "") == user_id]

  user_message = {"role": "user", "content": body, "user_id": user_id, "timestamp": datetime.now().isoformat()}
  history.append(user_message)
  user_history.append(user_message)

  user_summary = get_user_summary(user_id)
  
  system_instruction = """# Ninja.AI Restaurant Recommendation System

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

Remember that your primary goal is to connect users with authentic Japanese dining experiences that they'll genuinely enjoy, while providing the detailed information and warm hospitality that would make their visit memorable."""

  if user_summary:
    system_instruction += "\n\n## ユーザー情報サマリー\n以下はこのユーザーとの過去の会話から抽出した情報です：\n"
    system_instruction += json.dumps(user_summary["preferences"], indent=2, ensure_ascii=False)
    
    recent_messages = []
    for msg in user_history[-6:]:
      if "user_id" in msg:
        recent_messages.append({"role": msg["role"], "content": msg["content"]})
      else:
        recent_messages.append(msg)
  else:
    recent_messages = [{"role": "user", "content": body}]

  test = client.responses.create(
    model="gpt-4o",
    instructions=system_instruction,
    input=recent_messages,
    # input=body,
    store=False
  )

  assistant_message = {"role": "assistant", "content": test.output_text, "user_id": user_id, "timestamp": datetime.now().isoformat()}
  history.append(assistant_message)

  save_history(history)
  print(test.output)
  print(user_id)
  resp.message(test.output_text)


  # msg = resp.message("Thank you for contacting us via WhatsApp!")
  # msg.media("https://images.pexels.com/photos/67468/pexels-photo-67468.jpeg?cs=srgb&dl=pexels-life-of-pix-67468.jpg&fm=jpg")
  print(dir(test.output))

  return str(resp)
if __name__ == "__main__":
    app.run(debug=True)