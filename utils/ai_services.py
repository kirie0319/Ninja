# utils/ai_services.py
import os, yaml, json, asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic 
from typing import Dict, Any, Optional
from .yaml_manager import YAMLManager
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.yaml_manager = YAMLManager(".")
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.openai_default_model = "gpt-4.1"

        self.anthropic_client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.anthropic_default_model = "anthropic/claude-3.7-sonnet"
        self.openrouter_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.openrouter_default_model = "openai/gpt-4.1"

        self.summarize_prompt = None
        self.intent_prompt = None
        self.restaurant_prompt = None
        self.user_history_prompt = None
        self.quick_reply_prompt = None
    
    async def initialize_prompt(self):
        self.summarize_prompt = await self.yaml_manager.load_prompt("prompts", "summarize")
        self.intent_prompt = await self.yaml_manager.load_prompt("prompts", "intent_classify")
        self.restaurant_prompt = await self.yaml_manager.load_prompt("prompts", "restaurant")
        self.user_history_prompt = await self.yaml_manager.load_prompt("prompts", "summarize_user_rep")
        self.quick_reply_prompt = await self.yaml_manager.load_prompt("prompts", "quick_reply_prompt")
    
    async def openrouter_classify_intent(self, user_message: str) -> str:
        if not self.intent_prompt:
            await self.initialize_prompt()
        prompt_text = self.intent_prompt["prompt"].format(body=user_message)
        # print(prompt_text)
        try:
            response = await self.openrouter_client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You classify intent."
                    },
                    {
                        "role": "user",
                        "content": prompt_text
                    }
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error classifying intent: {e}")
            return "I'm sorry, I'm having troubule connecting to my services right now. Please try again later."
    
    async def openrouter_summarize_conversation(self, summary: list, user_history: list, last_two: list) -> str:
        if not self.summarize_prompt:
            await self.initialize_prompt()
        prompt_text = self.summarize_prompt["prompt"].format(
            summary_json=summary,
            user_history_json=user_history,
            last_two_json=last_two
        )
        # print(prompt_text)
        try:
            response = await self.openrouter_client.chat.completions.create(
                model=self.openrouter_default_model,
                messages=[
                    {
                        "role": "assistant",
                        "content": prompt_text
                    }
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error summarizing conversation: {e}")
            return "Failed to summarize conversation."

    async def openrouter_generate_response(self, user_message: str, summary: list, user_history: list, last_two: list, user_preferences: list) -> str:
        if not self.restaurant_prompt:
            await self.initialize_prompt()
        
        # Handle empty or None user_preferences
        if not user_preferences:
            user_preferences = '{}'  # Default to an empty JSON object
        
        prompt_text = self.restaurant_prompt['prompt'].format(
            summary_json=summary,
            user_history_json=user_history,
            last_two_json=last_two,
            user_preferences_json=user_preferences
        )
        print(prompt_text)
        try:
            response = await self.openrouter_client.chat.completions.create(
                model=self.openrouter_default_model,
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    },
                    {
                        "role": "assistant",
                        "content": prompt_text
                    }
                ]
            )
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm sorry, I'm having trouble connecting to my services right now. Please try again later."

    async def openrouter_generate_quick_summarize_response(self, user_message: str) -> str:
        if not self.user_history_prompt:
            await self.initialize_prompt()
        prompt_text = self.user_history_prompt["prompt"]
        # print(prompt_text)
        try:
            response = await self.openrouter_client.chat.completions.create(
                model=self.openrouter_default_model,
                messages=[
                    {
                        "role": "assistant",
                        "content": prompt_text
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm soory, I'm having trouble connecting to my services right now. Please try again later."

    async def openrouter_generate_quick_reply(self, user_message: str, assistant_message: str, summary: list) -> str:
        if not self.quick_reply_prompt:
            await self.initialize_prompt()
        prompt_text = self.quick_reply_prompt["prompt"].format(
            user_body=user_message,
            assistant_body=assistant_message,
            summary=summary
        )
        try:
            response = await self.openrouter_client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": prompt_text
                    }
                ]
            )
            content = response.choices[0].message.content.strip()
            quick_replies = [line for line in content.split('\n') if line.strip()]

            return quick_replies[:4]
        except Exception as e:
            print(f"Error generating quick replies: {e}")
            return [
                "Thanks for sharing",
                "Tell me more",
                "Interesting",
                "I see"
            ]

