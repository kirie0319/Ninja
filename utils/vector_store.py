# utils/vector_store.py
from operator import index
import os
from pydoc import text
from unittest import result
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class VectorStore:
    def __init__(self):
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        index_name = os.getenv("PINECONE_INDEX")
        index_name_list = [idx["name"] for idx in pc.list_indexes()]
        

        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

        if index_name not in index_name_list:
            print("Index not found, creating...")
            pc.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        else: 
            print("Index already exists")
        
        self.index = pc.Index(index_name)
    
    def get_embedding(self, text):
        response = self.openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )

        return response.data[0].embedding

    def store_restaurant(self, restaurant_id, restaurant_data, text_to_embed):
        restaurant_id = restaurant_data.get("id", "unknown_id")

        genre = restaurant_data.get("genre", {}) or {}
        sub_genre = restaurant_data.get("sub_genre", {}) or {}
        budget = restaurant_data.get("budget", {}) or {}
        area_data = {
            "large_area": restaurant_data.get("large_area", {}) or {},
            "middle_area": restaurant_data.get("middle_area", {}) or {},
            "small_area": restaurant_data.get("small_area", {}) or {},
        }
        text_to_embed = f"""
        名前: {restaurant_data.get("name", "")}
        ジャンル: {genre.get('name', '')} {genre.get('catch', '')}
        サブジャンル: {sub_genre.get('name', '')}
        エリア: {area_data['large_area'].get('name', '')} {area_data['middle_area'].get('name', '')} {area_data['small_area'].get('name', '')}
        アクセス: {restaurant_data.get("access", "")}
        予算: {budget.get('name', '')} {budget.get('average', '')}
        営業時間: {restaurant_data.get('open', '')}
        定休日: {restaurant_data.get('close', '')}
        その他: {restaurant_data.get('other_name', '')} {restaurant_data.get('shop_detail_memo', '')}
        """
        vector = self.get_embedding(text_to_embed)
        photo = restaurant_data.get("photo", {}) or {}
        usls = restaurant_data.get("urls", {}) or {}
        metadata = {
            "id": restaurant_id,
            "name": restaurant_data.get("name", ""),
            "name_kana": restaurant_data.get("name_kana", ""),
            "genre": restaurant_data.get("genre", {}).get("name", ""),
            "sub_genre": restaurant_data.get("sub_genre", {}).get("name", ""),
            "catch": restaurant_data.get("catch", ""),
            "photo_url": photo.get("pc", {}).get("m", ""),
            "logo_url": restaurant_data.get("logo_image", ""),
            "area": restaurant_data.get("middle_area", {}).get("name", ""),
            "address": restaurant_data.get("address", ""),
            "access": restaurant_data.get("access", ""),
            "station": restaurant_data.get("station_name", ""),
            "budget": restaurant_data.get("budget", {}).get("average", ""),
            "open": restaurant_data.get("open", ""),
            "close": restaurant_data.get("close", ""),
            "urls_pc": restaurant_data.get("urls", {}).get("pc", ""),
            "lunch": restaurant_data.get("lunch", ""),
            "wifi": restaurant_data.get("wifi", ""),
            "child": restaurant_data.get("child", ""),
            "card": restaurant_data.get("card", ""),
            "non_smoking": restaurant_data.get("non_smoking", ""),
            "capacity": str(restaurant_data.get("capacity", "")),
        }

        self.index.upsert(
            vectors=[(restaurant_id, vector, metadata)]
        )
        return {"id": restaurant_id, "status": "stored", "name": metadata["name"]}
    
    def search_restaurants(self, query, top_k=5):
        query_vector = self.get_embedding(query)
        
        result = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )
        return result.matches
