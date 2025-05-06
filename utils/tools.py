import os
import math
import re
import json
from typing import List, Dict, Any, Optional, Union

import pinecone
import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from utils.vector_store import VectorStore

class CustomChatOpenAI(ChatOpenAI):
    def _estimate_tokens(self, text: str) -> int:
        return math.ceil(len(text) / 4)

    def get_num_tokens(self, text: str) -> int:
        return self._estimate_tokens(text)

    def get_num_tokens_from_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        text = "\n".join([
            msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
            for msg in messages
        ])
        total_count = self._estimate_tokens(text)
        return {
            "total_count": total_count,
            "count_per_message": [0] * len(messages)
        }

class RestaurantSearchTool:
    def __init__(self, json_path='meguro_shops.json', language: str = "ja"):
        # 環境変数からAPIキーを取得
        openai_key = os.getenv("OPENAI_API_KEY")
        pinecone_key = os.getenv("PINECONE_API_KEY")
        
        # Pineconeクライアントの初期化
        pinecone.init(api_key=pinecone_key)
        self.pinecone_index = pinecone.Index(os.getenv("PINECONE_INDEX_NAME"))
        
        # 埋め込みモデルの初期化
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=openai_key
        )
        
        # LLMの初期化
        self.llm = CustomChatOpenAI(
            model_name="google/gemini-2.5-flash-preview",
            api_key=openai_key
        )
        
        # ベクトルストア初期化
        self.vector_store = VectorStore()
        
        # JSONファイルを読み込む
        with open(json_path, 'r', encoding='utf-8') as f:
            self.restaurants_data = json.load(f)
        
        # IDでインデックスを作成して高速検索
        self.restaurants_by_id = {
            restaurant['id']: restaurant 
            for restaurant in self.restaurants_data
        }
        
        # 言語設定
        self.language = language
        
        self.name = "restaurant_search"
        self.description = "Search for restaurants in Tokyo"
    
    def validate_query(self, query):
        # 東京の主要エリアが含まれているかチェック
        return bool(re.search(r'東京|新宿|渋谷|池袋|銀座|上野|秋葉原|新橋|浅草|品川|六本木|目黒', query))
    
    def search_restaurants(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        # クエリの埋め込みを生成
        query_embedding = self.embeddings.embed_query(query)
        
        # Pineconeで類似性検索
        results = self.pinecone_index.query(
            vector=query_embedding,
            top_k=max_results,
            include_metadata=True
        )
        
        # 結果を整形
        restaurants = []
        for match in results.get("matches", []):
            restaurant_id = match['id']
            metadata = match['metadata']
            restaurant_data = self.restaurants_by_id.get(restaurant_id, {})
            
            restaurant = {
                "name": metadata.get("name", ""),
                "genre": metadata.get("genre", ""),
                "catch": metadata.get("catch", ""),
                "area": metadata.get("area", ""),
                "budget": metadata.get("budget", ""),
                "station": metadata.get("station", ""),
                "urls_pc": metadata.get("urls_pc", ""),
                "photo_url": metadata.get("photo_url", ""),
                "url": metadata.get("urls_pc", ""),
                "score": match['score']
            }
            restaurants.append(restaurant)
        
        return restaurants
    
    def rank_restaurants(self, query: str, restaurants: List[Dict[str, Any]]) -> str:
        """
        レストランをランク付けし、レスポンスを生成
        """
        restaurants_list = "\n\n".join([
            f"{i+1}. {rest['name']} | {rest['genre']} | {rest['budget']}\n{rest['catch']}"
            for i, rest in enumerate(restaurants)
        ])
        
        # プロンプトを作成
        messages = [
            SystemMessage(content="あなたは料理とレストランに精通した、親切で洗練されたアシスタントです。ユーザーの好みに合わせてレストランを分析し、最適な選択肢を提案してください。"),
            HumanMessage(content=f"以下のレストランから、私の好みに最も合うものを選んでください：\n\n{restaurants_list}\n\n私の要望は：{query}")
        ]
        
        # AIによる分析と推奨
        response = self.llm.invoke(messages)
        return response.content
    
    async def invoke(self, query, chat_history=None):
        # クエリのバリデーション
        if not self.validate_query(query):
            return "どのエリアのレストランを探していますか？例: 目黒のレストランを検索する"
        
        # レストラン検索
        restaurants = self.search_restaurants(query)
        
        if not restaurants:
            return "申し訳ありません。クエリに一致するレストランが見つかりませんでした。"
        
        # AIによるランク付けと推奨
        ai_recommendation = self.rank_restaurants(query, restaurants)
        
        return {
            "restaurants": restaurants,
            "ai_recommendation": ai_recommendation
        }
