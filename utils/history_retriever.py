# utils/history_retriever.py
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class HistoryRetriever:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def rephrase_query(self, query, chat_history):
        if not chat_history:
            return query

        formatted_history = ""
        for msg in chat_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                formatted_history += f"{role.upper()}: {content}\n"
        prompt = [
            {"role": "system", "content": "Based on the conversation history and the most recent user question, generate an independent question for restaurant search. If the latest question is a greeting or small talk, simply return the original question as-is"},
            {"role": "user", "content": f"conversation history:\n{formatted_history}\n\nlatest question:\n{query}\n\nGenerate an independent question for restaurant search."}
        ]

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                temperature=0.2,
                max_tokens=150
            )
            rephrased_query = response.choices[0].message.content.strip()
            return rephrased_query
        except Exception as e:
            print(f"Error rephrasing query: {e}")
            return query

    async def search(self, query, chat_history=None, top_k=5):
        try:
            if chat_history:
                rephrased_query = await self.rephrase_query(query, chat_history)
                print(f"original query: '{query}'")
                print(f"rephrased query: '{rephrased_query}'")
            else:
                rephrased_query = query
            results = self.vector_store.search_restaurants(rephrased_query, top_k)
            return results
        except Exception as e:
            print(f"Error rephrasing query: {e}")
            return self.vector_store.search_restaurants(query, top_k)
        