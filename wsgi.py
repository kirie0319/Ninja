# wsgi.py
import json
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
from openai import AsyncOpenAI
import sys
import os
import uvicorn
import traceback
from typing import Optional, Dict, Any, Union
from dotenv import load_dotenv

load_dotenv()

from utils.file_operations import load_json, save_json, to_pretty_json, get_last_conversation, clear_chat_data
from utils.ai_services import AIService
from utils.vector_store import VectorStore

vector_store = VectorStore()

ai_service = AIService()


import re
from development import RestaurantSearchTool
from langchain.schema import HumanMessage, AIMessage
# from test_restaurant_search import run_ai_generated_tests, generate_test_queries_with_ai
        
restaurant_search_tool = RestaurantSearchTool()

async def predict_missing_preferences(user_message: str, existing_preferences: dict) -> dict:
    """Use OpenAI to predict missing restaurant search preferences"""
    print("🔍 Starting preference prediction process...")
    
    # Comprehensive debug logging setup
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'input_message': user_message,
        'existing_preferences': existing_preferences,
        'prediction_attempt': 'started',
        'error': None,
        'environment': {
            'openai_key_exists': bool(os.getenv("OPENAI_API_KEY")),
            'python_version': sys.version,
            'async_openai_version': getattr(AsyncOpenAI, '__version__', 'unknown')
        }
    }
    
    try:
        # Validate input
        print("✅ Validating input preferences...")
        if not isinstance(existing_preferences, dict):
            print(f"❌ Invalid preferences type: {type(existing_preferences)}")
            raise ValueError(f"Invalid preferences type: {type(existing_preferences)}")
        
        # Check OpenAI API key
        print("🔑 Checking OpenAI API key...")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OpenAI API key is not set!")
            raise ValueError("OPENAI_API_KEY is not set in environment variables")
        print("✅ API key verified successfully")
        
        # Prepare the prompt for prediction
        print("📝 Preparing prediction prompt...")
        prompt = f"""TASK: Predict restaurant search preferences for Tokyo dining as a JSON object.

CONTEXT:
- Current cuisine preference: {existing_preferences.get('cuisine_type', 'Not specified')}
- Current location preference: {existing_preferences.get('location', 'Not specified')}

USER MESSAGE: '{user_message}'

PREDICTION GUIDELINES:
1. If user message is vague or empty, use context and defaults
2. Extract specific preferences from the message
3. Prioritize existing preferences
4. Use Meguro as default location for Tokyo dining
5. Suggest authentic Japanese dining experiences

REQUIRED JSON RESPONSE FORMAT:
{{
    "location": "Specific Tokyo area (default: Meguro)",
    "cuisine_type": "Specific Japanese cuisine style",
    "budget_level": "Low/Medium/High",
    "party_size": "Number of people",
    "english_menu_needed": "Yes/No"
}}

IMPORTANT RULES:
- Respond ONLY with a valid JSON object
- If unsure, use sensible defaults
- Focus on creating a helpful restaurant recommendation"""
        
        # Debug: Log prompt details
        debug_info['prompt'] = prompt
        
        # Use OpenAI to generate predictions
        print("🤖 Calling OpenAI API for predictions...")
        client = AsyncOpenAI(api_key=api_key)
        
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert restaurant preference predictor for Tokyo dining. Respond with a JSON object containing restaurant preferences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Add some creativity to predictions
                max_tokens=300  # Limit response length
            )
        except Exception as api_err:
            print(f"❌ OpenAI API call failed: {api_err}")
            debug_info['api_error'] = str(api_err)
            raise ValueError(f"OpenAI API call failed: {api_err}")
        
        # Parse the response
        print("📊 Parsing API response...")
        if not response.choices:
            print("❌ No response choices from OpenAI")
            raise ValueError("No response choices from OpenAI")
        
        prediction_str = response.choices[0].message.content
        debug_info['raw_prediction'] = prediction_str
        
        try:
            prediction = json.loads(prediction_str)
            print("✅ Successfully parsed prediction JSON")
            debug_info['parsed_prediction'] = prediction
        except json.JSONDecodeError as json_err:
            print(f"❌ Failed to parse JSON: {json_err}")
            debug_info['json_parse_error'] = str(json_err)
            raise ValueError(f"Failed to parse JSON: {json_err}. Raw content: {prediction_str}")
        
        # Merge predictions with existing preferences, prioritizing existing data
        print("🔄 Merging predictions with existing preferences...")
        for key, value in prediction.items():
            if not existing_preferences.get(key) and value:
                existing_preferences[key] = value
                print(f"  ➕ Added {key}: {value}")
        
        # Ensure some defaults if still missing
        print("🏁 Applying default preferences...")
        defaults = {
            'location': 'Meguro',
            'cuisine_type': 'Japanese',
            'budget_level': 'Medium',
            'party_size': '2',
            'english_menu_needed': 'Yes'
        }
        
        for key, default_value in defaults.items():
            if not existing_preferences.get(key):
                existing_preferences[key] = default_value
                print(f"  ➕ Default {key}: {default_value}")
        
        debug_info['final_preferences'] = existing_preferences
        debug_info['prediction_attempt'] = 'success'
        
        # Optional: Log debug info to a file
        try:
            with open('preference_prediction_debug.log', 'a') as debug_file:
                debug_file.write(json.dumps(debug_info, indent=2) + '\n')
            print("💾 Debug info logged successfully")
        except Exception as log_err:
            print(f"❌ Error logging debug info: {log_err}")
        
        print("🎉 Preference prediction completed successfully!")
        return existing_preferences
    
    except Exception as e:
        # Comprehensive error handling
        print(f"❌ Prediction process failed: {e}")
        debug_info['error'] = {
            'type': type(e).__name__,
            'message': str(e),
            'traceback': traceback.format_exc()
        }
        debug_info['prediction_attempt'] = 'failed'
        
        # Log error details
        try:
            with open('preference_prediction_debug.log', 'a') as debug_file:
                debug_file.write(json.dumps(debug_info, indent=2) + '\n')
            print("💾 Error details logged")
        except Exception as log_err:
            print(f"❌ Error logging debug info: {log_err}")
        
        # Print detailed error for immediate visibility
        print(f"Error predicting preferences: {e}")
        print(f"Debug Info: {json.dumps(debug_info, indent=2)}")
        
        # Fallback to hardcoded defaults
        print("🔄 Returning default preferences")
        return {
            'location': 'Meguro',
            'cuisine_type': 'Japanese',
            'budget_level': 'Medium',
            'party_size': '2',
            'english_menu_needed': 'Yes'
        }

def construct_search_query(user_message: str, user_preferences: dict) -> str:
    # Extract location from user preferences or default to Tokyo
    location = user_preferences.get("location", "Tokyo")
    
    # If location is still empty or too generic, try to extract from the summary
    if not location or location.lower() in ["tokyo", "japan"]:
        # Look for specific areas in the user message
        areas = ["Shinjuku", "Shibuya", "Ginza", "Ikebukuro", "Meguro", "Roppongi", "Harajuku"]
        for area in areas:
            if area.lower() in user_message.lower():
                location = area
                break
    
    cuisine_type = user_preferences.get("cuisine_type", "")
    budget_level = user_preferences.get("budget_level", "")
    party_size = user_preferences.get("party_size", "")
    english_menu_needed = user_preferences.get("english_menu_needed", "")

    query_parts = []

    if location:
        query_parts.append(f"Location: {location}")
    if cuisine_type:
        query_parts.append(f"Cuisine Type: {cuisine_type}")
    if budget_level:
        query_parts.append(f"Budget Level: {budget_level}")
    if party_size:
        query_parts.append(f"Party Size: {party_size}")
    if english_menu_needed:
        query_parts.append(f"English Menu Needed: {english_menu_needed}")

    search_query = " ".join(query_parts)
    return search_query

def format_search_results(search_results: str = None) -> str:
    if not search_results:
        search_results = "申し訳ありません。現在、レストランの検索結果が見つかりませんでした。"
    
    formatted = "\n## 🍽️ レストランのご提案 / Restaurant Recommendations\n\n"
    formatted += search_results
    formatted += "\n\n---\n*ご予約は直接レストランにお問い合わせいただくか、お手伝いが必要な場合はお知らせください。*"
    formatted += "\n*Please contact the restaurants directly for reservations, or let me know if you need assistance.*"
    
    return formatted

async def execute_restaurant_search(summary: str, user_preferences: Union[str, dict], user_history_json: str, session_id: str) -> str:
    """RestaurantSearchToolを使用してレストランを検索"""
    try:
        # user_preferencesがJSON文字列の場合、辞書に変換
        if isinstance(user_preferences, str):
            try:
                user_preferences = json.loads(user_preferences)
            except json.JSONDecodeError:
                user_preferences = {}
        
        # 不足する情報を予測
        user_preferences = await predict_missing_preferences(summary, user_preferences)
        
        # チャット履歴を構築
        chat_history = []
        if user_history_json:
            try:
                history_data = json.loads(user_history_json)
                if isinstance(history_data, dict):
                    for user_id, user_data in history_data.items():
                        if 'messages' in user_data:
                            for msg_pair in user_data['messages']:
                                if 'user' in msg_pair:
                                    chat_history.append(HumanMessage(content=msg_pair['user']['content']))
                                if 'assistant' in msg_pair:
                                    chat_history.append(AIMessage(content=msg_pair['assistant']['content']))
            except Exception as history_error:
                print(f"Error parsing history: {history_error}")
                chat_history = []
        
        # 検索クエリを構築
        search_query = construct_search_query(summary, user_preferences)
        
        # RestaurantSearchToolを実行
        try:
            search_result = await restaurant_search_tool.invoke(search_query, chat_history)
        except Exception as search_error:
            print(f"Search tool invocation error: {search_error}")
            search_result = None
        
        # 検索結果をフォーマット
        formatted_result = format_search_results(search_result)
        
        return formatted_result
        
    except Exception as e:
        print(f"Restaurant search error: {e}")
        return "申し訳ありません。レストラン検索中にエラーが発生しました。"

# about adding the json format
class AsyncRestaurantInfoExtractor:
    def __init__(self, api_key: str, json_file_path: str = "user_preferences.json"):
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.json_file_path = json_file_path
        
        self.REQUIRED_INFO = {
            "cuisine_type": None,
            "budget_level": None,
            "location": None,
            "travel_time": None,
            "party_size": None,
            "seating_preference": None,
            "dietary_restrictions": [],
            "occasion": None,
            "english_menu_needed": None,
            "last_updated": None
        }

        self._initialize_json_file()

    async def _load_from_json(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return self.REQUIRED_INFO.copy()

    async def _save_to_json(self, data: Dict[str, Any]):
        data['last_updated'] = datetime.now().isoformat()
        with open(self.json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _initialize_json_file(self):
        try: 
            if not os.path.exists(self.json_file_path):
                with open(self.json_file_path, 'w') as f:
                    json.dump(self.REQUIRED_INFO, f, indent=4)
            else:
                with open(self.json_file_path, 'r') as f:
                    existing_data = json.load(f)
                
                updated_data = {**self.REQUIRED_INFO, **existing_data}
                
                with open(self.json_file_path, 'w') as f:
                    json.dump(updated_data, f, indent=4)
        except json.JSONDecodeError as e:
            print(f"JSON読み込みエラー: {e}")
            with open(self.json_file_path, 'w') as f:
                json.dump(self.REQUIRED_INFO, f, indent=4)
        except IOError as e:
            print(f"ファイル操作エラー: {e}")

    async def extract_restaurant_info(self, user_message: str) -> Dict[str, Any]:
        current_info = await self._load_from_json()
        prompt = f"""あなたはレストラン予約アシスタントです。ユーザーの発言から以下の情報を抽出してください。
        
            ユーザーの発言："{user_message}"

            以下の項目に該当する情報があれば抽出してください：
            1. cuisine_type (料理の種類：例 和食、イタリアン、フレンチなど)
            2. budget_level (予算：例 低、中、高)
            3. location (場所：例 東京、新宿、渋谷など)
            4. travel_time (移動時間：例 30分以内、1時間以内など)
            5. party_size (人数：例 2人、4人など)
            6. seating_preference (席の希望：例 個室、カウンター、テラスなど)
            7. dietary_restrictions (食事制限：例 ベジタリアン、アレルギーなど)
            8. occasion (目的：例 デート、ビジネス、誕生日など)
            9. english_menu_needed (英語メニューの必要性：例 はい、いいえ)

            該当する情報がない場合は、その項目はNoneまたは空のリストにしてください。
            JSONフォーマットで回答してください。
            """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            extracted_info = json.loads(response.choices[0].message.content)
            
            for key, value in extracted_info.items():
                if key in current_info and value is not None:
                    if key == "dietary_restrictions" and isinstance(value, list):
                        current_info[key] = list(set(current_info[key] + value))
                    else:
                        current_info[key] = value
            
            await self._save_to_json(current_info)
            
            return current_info
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            raise HTTPException(status_code=500, detail=f"OpenAI APIエラー: {str(e)}")
    
    async def get_null_fields(self):
        current_info = await self._load_from_json()
        null_fields = []
        
        for key, value in current_info.items():
            if key == "last_updated":
                continue
                
            if value is None or (isinstance(value, list) and len(value) == 0):
                null_fields.append(key)
        
        return null_fields
    
    async def extract_and_format_user_requirements(self) -> str:
        summary = await self.get_missing_info_summary()
        
        output = []
        output.append("=== レストラン検索要件 ===\n")

        if summary["filled_fields"]:   
            output.append("【入力済み情報】")
            field_names = {
                "cuisine_type": "料理ジャンル",
                "budget_level": "予算レベル",
                "location": "エリア",
                "travel_time": "移動時間",
                "party_size": "人数",
                "seating_preference": "席の希望",
                "dietary_restrictions": "食事制限",
                "occasion": "利用目的",
                "english_menu_needed": "英語メニュー",
            }
            
            for key, value in summary["filled_fields"].items():
                display_name = field_names.get(key, key)
                output.append(f"  ✓ {display_name}: {value}")
            output.append("")

        if summary["missing_fields"]:
            output.append("【不足情報】")
            for field in summary["missing_fields"]:
                display_name = field_names.get(field, field)
                output.append(f"  ✗ {display_name}: 未入力")
            output.append("")

        output.append(f"【入力完了率】: {summary['completion_rate']}")

        return "\n".join(output)
    
    async def reset_info(self):
        await self._save_to_json(self.REQUIRED_INFO.copy())



extractor = AsyncRestaurantInfoExtractor(os.getenv("OPENAI_API_KEY"))
user_preferences_file = "user_preferences.json"
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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.post("/api/chat")
async def process_message(message_request: MessageRequest, session_id: Optional[str] = Cookie(None)):
    body = message_request.message

    #extract info and update json
    extraction_info = await extractor.extract_restaurant_info(body)
    await extractor._save_to_json(extraction_info)
    
    user_id = str(uuid.uuid4())
    
    history = await load_json(chat_log_file, [])
    summary = await load_json(summary_file, [])
    user_history_for_json = await load_json(user_history_file, {})
    user_preferences = await load_json(user_preferences_file, {})

    last_pair = await get_last_conversation(history)

    if last_pair:
        last_two_json = await to_pretty_json(last_pair)
    else:
        last_two_json = ""
    
    user_history_json = await to_pretty_json(user_history_for_json)
    summary_json = await to_pretty_json(summary)
    user_preferences_json = await to_pretty_json(user_preferences)
    
    user_message = {
        "role": "user", 
        "content": body, 
        "user_id": user_id, 
        "timestamp": datetime.now().isoformat()
    }
    
    history.append(user_message)
    
    text_response = await ai_service.openrouter_generate_response(body, summary_json, user_history_json, last_two_json, user_preferences_json)

    intent = await ai_service.openrouter_classify_intent(text_response)
    print(intent)
    if intent == "ready":
        with open("meguro_shops.json", "r", encoding="utf-8") as f:
            meguro_shops = json.load(f)
        restaurant_results = vector_store.search_restaurants(summary[0]["content"], top_k=5)
        ids = [item["id"] for item in restaurant_results]
        id_set = set(ids)
        matched_shops = [shop for shop in meguro_shops if shop["id"] in id_set]
        conversation_summary = summary[0]["content"]

        photo_urls  = []   # 写真 URL 一覧
        detail_urls = []

        for shop in matched_shops:
            pc_photo = shop.get("photo", {}).get("pc", {})
            photo_url = (
                pc_photo.get("m") or
                pc_photo.get("l") or
                pc_photo.get("s") or ""
            )
            detail_url = shop.get("urls", {}).get("pc", "")
            photo_urls.append(photo_url)
            detail_urls.append(detail_url)
        print(photo_urls)

        search_prompt = f"""
        あなたは目黒のレストラン案内AIアシスタントです。以下の情報を基に、ユーザーに合わせたパーソナライズされたレストラン提案をしてください。

        【ユーザーの好みやコンテキスト】
        {conversation_summary}
        
        【ユーザーの設定情報】
        {user_preferences_json}
        
        【検索結果のレストラン情報】
        {matched_shops}
        
        以下の点に注意して、ユーザーに適したレストランを紹介する文章を作成してください：
        
        1. ユーザーの好みや状況に合わせた提案をしてください
        2. 丁寧でフレンドリーな口調で、会話形式で紹介してください
        3. 特におすすめのレストランがあれば、その理由も含めて説明してください
        4. 各レストランの特徴や雰囲気についても触れてください
        5. 予約のアドバイスや訪問時のヒントも可能であれば含めてください
        6. チャットUIで表示されることを考慮して、適切な長さと読みやすさを心がけてください
        7. Please answer in English
        8. Add the detail_url from {detail_urls} to each restaurant introduction. Do not use Markdown syntax for images - just provide the URLs in your text.

        """

        try:
            openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            search_response = await openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": search_prompt}
                ]
            )
            assistant_content = search_response.choices[0].message.content
        except Exception as e:
            print(f"Error generating response: {e}")
            assistant_content = ""
        response = JSONResponse(
            content={
                "response": assistant_content, 
                "image_urls": photo_urls,
                }
        )
        response.set_cookie(key="session_id", value=session_id)
        return response
            
        


    response_text = text_response
    assistant_response = {
        "id": text_response.id if hasattr(text_response, 'id') else str(uuid.uuid4()),
        "role": "assistant",
        "content": response_text,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }

    result = {
        "response": response_text
    }

    quick_response = await ai_service.openrouter_generate_quick_summarize_response(body)

    quick_assistant_response = {
        "role": "assistant",
        "id": str(uuid.uuid4()),
        "content": quick_response,
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
    await extractor.reset_info()
    return JSONResponse(content={"status": "success", "message": "Clear chat history and reset info"})

if __name__ == "__main__":
    # Ensure index.html is in templates directory
    if not os.path.exists('templates/index.html'):
        print("Error: index.html not found in templates directory")
        print("Current directory:", os.getcwd())
        print("Files in current directory:", os.listdir())
        sys.exit(1)
        
    # Run the FastAPI application with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)