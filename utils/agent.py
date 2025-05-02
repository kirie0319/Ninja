# utils/agent.py
from openai import AsyncOpenAI
import os, re, json 
from dotenv import load_dotenv

load_dotenv()

class NinjaAgent:
    def __init__(self, restaurant_search_tool, greet_tool, faq_tool):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tools = [restaurant_search_tool, greet_tool, faq_tool]

        # Update tools_definition to be more dynamic
        self.tools_definition = []
        if restaurant_search_tool:
            self.tools_definition.append({
                "type": "function",
                "name": "restaurant_search",
                "function": {
                    "name": "restaurant_search",
                    "description": "Search for restaurants and rate them",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
        
        if greet_tool:
            self.tools_definition.append({
                "type": "function",
                "name": "greet_user",
                "function": {
                    "name": "greet_user",
                    "description": "Greet the user",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            })
        
        if faq_tool:
            self.tools_definition.append({
                "type": "function",
                "name": "faq_lookup",
                "function": {
                    "name": "faq_lookup",
                    "description": "Let's answer your question",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The question to look up"
                            }
                        },
                        "required": ["query"]
                    }
                }
            })

        self.system_prompt = """
        あなたはレストラン推薦AIアシスタントです。ユーザーの要望に応じて最適なレストランを提案します。
        
        基本ルール:
        - 明るく親切な口調で回答してください
        - レストランの特徴や魅力を簡潔に説明してください
        - 提供されたツールを使って質問に答えてください
        - 挨拶にはgreet_userツールを使用してください
        - レストラン検索にはrestaurant_searchツールを使用してください
        - よくある質問にはfaq_lookupツールを使用してください
        
        応答形式:
        - レストラン情報は簡潔にまとめてください
        - 店名、ジャンル、特徴、予算の情報を含めてください
        - ユーザーが選びやすいよう比較情報を提供してください
        """

    async def get_tool_by_name(self, name):
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    async def sanitize_output(self, text):
        return re.sub(r'〔(?:\d+|tool_\d+)〕', '', text).strip()

    async def chat(self, message, history, session_id="anon"):
        if re.match(r"^(hi|hello|hey|yo|こんにちは)\s*[!!]?$", message.lower()):
            greet_tool = await self.get_tool_by_name("greet_user")
            return await greet_tool.invoke()
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in history:
            if msg["role"] in ["user",  "assistant"]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": message})

        try: 
            response = await self.openai_client.responses.create(
                model="gpt-4o",
                input=messages,
                tools=self.tools_definition,
                tool_choice="auto"
            )
            response_message = response.output_text 

            # Check if response has tool_calls
            if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    tool = await self.get_tool_by_name(function_name)
                    if tool:
                        if function_name == "restaurant_search":
                            tool_result = await tool.invoke(function_args.get("query", ""), history)
                        elif function_name == "greet_user":
                            tool_result = await tool.invoke()
                        elif function_name == "faq_lookup":
                            tool_result = await tool.invoke(function_args.get("query", ""))
                        else:
                            tool_result = "Unknown tool"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })
                second_response = await self.openai_client.responses.create(
                    model="gpt-4o",
                    input=messages
                )
                final_response = second_response.output_text
                return await self.sanitize_output(final_response)
            else:
                # If no tool calls, return the original response content
                # Ensure we're returning a string
                return await self.sanitize_output(
                    response_message.content if hasattr(response_message, 'content') 
                    else str(response_message)
                )

        except Exception as e:
            print(f"Error in chat: {e}")
            return "Sorry, I couldn't process your request. Please try again."
