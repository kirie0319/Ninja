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
        self.openai_default_model = "gpt-4o"

        self.anthropic_client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.anthropic_default_model = "anthropic/claude-3.7-sonnet"

        self.summarize_prompt = None
        self.intent_prompt = None
        self.restaurant_prompt = None
        self.user_history_prompt = None
    
    async def initialize_prompt(self):
        self.summarize_prompt = await self.yaml_manager.load_prompt("prompts", "summarize")
        self.intent_prompt = await self.yaml_manager.load_prompt("prompts", "intent_classify")
        self.restaurant_prompt = await self.yaml_manager.load_prompt("prompts", "restaurant")
        self.user_history_prompt = await self.yaml_manager.load_prompt("prompts", "summarize_user_rep")
    
    async def openai_classify_intent(self, user_message: str) -> str:
        if not self.intent_prompt:
            await self.initialize_prompt()
        prompt_text = self.intent_prompt["prompt"].format(body=user_message)
        # print(prompt_text)
        try:
            response = await self.openai_client.responses.create(
                model=self.openai_default_model,
                input=[
                    {"role": "system", "content": "You classify intent."},
                    {"role": "user", "content": prompt_text}
                ]
            )
            return response.output_text
        except Exception as e:
            print(f"Error classifying intent: {e}")
            return "I'm sorry, I'm having troubule connecting to my services right now. Please try again later."
    
    async def openai_summarize_conversation(self, summary: list, user_history: list, last_two: list) -> str:
        if not self.summarize_prompt:
            await self.initialize_prompt()
        prompt_text = self.summarize_prompt["prompt"].format(
            summary_json=summary,
            user_history_json=user_history,
            last_two_json=last_two
        )
        # print(prompt_text)
        try:
            response = await self.openai_client.responses.create(
                model=self.openai_default_model,
                input=[
                    {"role": "user", "content": prompt_text}
                ],
                store=False
            )
            return response.output_text
        except Exception as e:
            print(f"Error summarizing conversation: {e}")
            return "Failed to summarize conversation."

    async def openai_generate_response(self, user_message: str, summary: list, user_history: list, last_two: list) -> str:
        if not self.restaurant_prompt:
            await self.initialize_prompt()
        prompt_text = self.restaurant_prompt["prompt"].format(
            summary_json=summary,
            user_history_json=user_history,
            last_two_json=last_two
        )
        print(prompt_text)
        try:
            response = await self.openai_client.responses.create(
                model=self.openai_default_model,
                instructions=prompt_text,
                input=user_message,
                store=False
            )
            return response.output_text
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm soory, I'm having trouble connecting to my services right now. Please try again later."

    async def openai_generate_quick_summarize_response(self, user_message: str) -> str:
        if not self.user_history_prompt:
            await self.initialize_prompt()
        prompt_text = self.user_history_prompt["prompt"]
        # print(prompt_text)
        try:
            response = await self.openai_client.responses.create(
               model=self.openai_default_model,
                instructions=prompt_text,
                input=user_message,
                store=False 
            )
            return response.output_text
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm soory, I'm having trouble connecting to my services right now. Please try again later."
