# development.py
import os
import re
import json
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema import BaseMessage, HumanMessage, AIMessage

from utils.vector_store import VectorStore

class RestaurantSearchTool:
    def __init__(self, json_path='meguro_shops.json', language: str = "ja"):
        # ベクトルストアの初期化
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
        self.description = "Search for restaurants in Tokyo with context-aware search"
        
        # LLMの初期化
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # エリアキャッシュの初期化
        self.area_cache = {}
        self._build_area_index()
    
    def _build_area_index(self):
        """エリアインデックスを構築して高速検索を可能に"""
        for restaurant in self.restaurants_data:
            # 複数のエリア関連フィールドからインデックスを作成
            areas = []
            
            # small_area（例：目黒）
            if 'small_area' in restaurant and 'name' in restaurant['small_area']:
                areas.append(restaurant['small_area']['name'])
            
            # middle_area（例：品川･目黒･田町･浜松町･五反田）
            if 'middle_area' in restaurant and 'name' in restaurant['middle_area']:
                areas.append(restaurant['middle_area']['name'])
            
            # station_name（例：目黒）
            if 'station_name' in restaurant:
                areas.append(restaurant['station_name'])
            
            # addressから抽出（例：東京都目黒区...）
            if 'address' in restaurant:
                # 例：「東京都目黒区」から「目黒」を抽出
                address_match = re.search(r'(新宿|渋谷|池袋|銀座|上野|秋葉原|新橋|浅草|品川|六本木|目黒)', restaurant['address'])
                if address_match:
                    areas.append(address_match.group(1))
            
            # 各エリアでインデックスを作成
            for area in areas:
                if area:
                    if area not in self.area_cache:
                        self.area_cache[area] = []
                    self.area_cache[area].append(restaurant)
    
    def validate_query(self, query: str) -> bool:
        """エリアの検証を含む高度なクエリバリデーション"""
        # 東京の主要エリアが含まれているかチェック
        return bool(re.search(r'東京|新宿|渋谷|池袋|銀座|上野|秋葉原|新橋|浅草|品川|六本木|目黒', query))
    
    async def _rephrase_query_with_history(self, query: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        """チャット履歴を考慮してクエリを再構築"""
        if not chat_history:
            return query
        
        rephrase_prompt = ChatPromptTemplate.from_messages([
            ("system", """チャット履歴と最新のユーザー質問を使用して、レストラン検索に適した独立した質問に言い換えてください。
            チャット履歴の文脈を考慮して、より具体的で検索しやすい形に変換してください。
            同じ言語で返答してください。"""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}")
        ])
        
        chain = rephrase_prompt | self.llm | StrOutputParser()
        
        # チャット履歴をフォーマット
        formatted_history = []
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                formatted_history.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                formatted_history.append(("assistant", msg.content))
        
        rephrased = await chain.ainvoke({
            "input": query,
            "chat_history": formatted_history
        })
        
        return rephrased.strip()
    
    def _extract_restaurant_info(self, restaurant_data: Dict[str, Any]) -> Dict[str, Any]:
        """レストランの全情報を構造化して抽出"""
        # 必要な情報を安全に取得
        def safe_get(data, *keys):
            for key in keys:
                if isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    return ""
            return data or ""
        
        # 完全な情報を含むディクショナリを作成
        return {
            # 基本情報
            "id": restaurant_data.get("id", ""),
            "name": restaurant_data.get("name", ""),
            "name_kana": restaurant_data.get("name_kana", ""),
            "logo_image": restaurant_data.get("logo_image", ""),
            
            # 位置情報
            "address": restaurant_data.get("address", ""),
            "station_name": restaurant_data.get("station_name", ""),
            "lat": restaurant_data.get("lat", ""),
            "lng": restaurant_data.get("lng", ""),
            
            # エリア情報
            "small_area": safe_get(restaurant_data, "small_area", "name"),
            "middle_area": safe_get(restaurant_data, "middle_area", "name"),
            "large_area": safe_get(restaurant_data, "large_area", "name"),
            
            # ジャンル情報
            "genre": safe_get(restaurant_data, "genre", "name"),
            "genre_catch": safe_get(restaurant_data, "genre", "catch"),
            "sub_genre": safe_get(restaurant_data, "sub_genre", "name"),
            
            # 予算情報
            "budget": safe_get(restaurant_data, "budget", "name"),
            "budget_average": safe_get(restaurant_data, "budget", "average"),
            "budget_code": safe_get(restaurant_data, "budget", "code"),
            
            # 営業時間
            "open": restaurant_data.get("open", ""),
            "close": restaurant_data.get("close", ""),
            
            # 施設・サービス
            "capacity": restaurant_data.get("capacity", ""),
            "party_capacity": restaurant_data.get("party_capacity", ""),
            "access": restaurant_data.get("access", ""),
            "mobile_access": restaurant_data.get("mobile_access", ""),
            
            # URL・予約情報
            "urls_pc": safe_get(restaurant_data, "urls", "pc"),
            "coupon_urls_pc": safe_get(restaurant_data, "coupon_urls", "pc"),
            "coupon_urls_sp": safe_get(restaurant_data, "coupon_urls", "sp"),
            
            # 画像
            "photo_l": safe_get(restaurant_data, "photo", "pc", "l"),
            "photo_m": safe_get(restaurant_data, "photo", "pc", "m"),
            "photo_s": safe_get(restaurant_data, "photo", "pc", "s"),
            
            # キャッチコピー・説明
            "catch": restaurant_data.get("catch", ""),
            "other_memo": restaurant_data.get("other_memo", ""),
            "shop_detail_memo": restaurant_data.get("shop_detail_memo", ""),
            
            # 設備・サービス詳細
            "private_room": restaurant_data.get("private_room", ""),
            "horigotatsu": restaurant_data.get("horigotatsu", ""),
            "tatami": restaurant_data.get("tatami", ""),
            "card": restaurant_data.get("card", ""),
            "non_smoking": restaurant_data.get("non_smoking", ""),
            "charter": restaurant_data.get("charter", ""),
            "parking": restaurant_data.get("parking", ""),
            "barrier_free": restaurant_data.get("barrier_free", ""),
            "show": restaurant_data.get("show", ""),
            "karaoke": restaurant_data.get("karaoke", ""),
            "band": restaurant_data.get("band", ""),
            "tv": restaurant_data.get("tv", ""),
            "lunch": restaurant_data.get("lunch", ""),
            "midnight": restaurant_data.get("midnight", ""),
            "english": restaurant_data.get("english", ""),
            "pet": restaurant_data.get("pet", ""),
            "child": restaurant_data.get("child", ""),
            "wifi": restaurant_data.get("wifi", ""),
            "course": restaurant_data.get("course", ""),
            "free_drink": restaurant_data.get("free_drink", ""),
            "free_food": restaurant_data.get("free_food", ""),
            "wedding": restaurant_data.get("wedding", ""),
        }
    
    def search_restaurants(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """拡張されたレストラン検索：完全な情報を含む結果を返す"""
        # ベクトル検索で候補レストランを取得
        search_results = self.vector_store.search_restaurants(query, max_results)
        
        # 結果を整形
        restaurants = []
        for match in search_results:
            restaurant_id = match['id']
            
            # JSONデータから完全な情報を取得
            restaurant_data = self.restaurants_by_id.get(restaurant_id, {})
            
            if restaurant_data:
                # 完全なレストラン情報を抽出
                restaurant_info = self._extract_restaurant_info(restaurant_data)
                
                # ベクトル検索のスコアを追加
                restaurant_info["score"] = match['score']
                
                restaurants.append(restaurant_info)
        
        return restaurants
    
    async def _rank_restaurants(self, query: str, restaurants: List[Dict[str, Any]], top_k: int = 5) -> str:
        """LLMを使用してレストランをランク付けして表示（全情報を考慮）"""
        # より詳細なレストラン情報を作成
        restaurants_list = "\n\n".join([
            f"{i+1}. {r['name']}\n"
            f"   エリア: {r['small_area']} ({r['station_name']}駅)\n"
            f"   ジャンル: {r['genre']}\n"
            f"   予算: {r['budget']} ({r['budget_average']})\n"
            f"   特徴: {r['catch']}\n"
            f"   営業時間: {r['open']}\n"
            f"   施設: 個室: {r['private_room']}, 禁煙: {r['non_smoking']}, カード: {r['card']}\n"
            f"   その他: 英語: {r['english']}, 子供連れ: {r['child']}, Wi-Fi: {r['wifi']}\n"
            f"   アクセス: {r['access']}"
            for i, r in enumerate(restaurants[:20])
        ])
        
        rank_prompt = ChatPromptTemplate.from_template(
            """あなたは親切なレストランコンシェルジュです。以下のレストランリストからユーザーの質問に最も適したものを選んでください。

ユーザーの質問: "{query}"

レストランリスト:
{restaurants}

トップ3を選んで、以下の形式で表示してください：
- 店名、エリア、ジャンル、予算
- おすすめの理由（1文）
- 特筆すべき設備やサービス（あれば）
- アクセス方法"""
        )
        
        chain = rank_prompt | self.llm | StrOutputParser()
        
        ranked_response = await chain.ainvoke({
            "query": query,
            "restaurants": restaurants_list
        })
        
        return ranked_response
    
    def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """特定のレストランの詳細情報を取得"""
        restaurant_data = self.restaurants_by_id.get(restaurant_id)
        if restaurant_data:
            return self._extract_restaurant_info(restaurant_data)
        return None
    
    async def invoke(self, query: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        try:
            # 1. チャット履歴を考慮してクエリを再構築
            rephrased_query = await self._rephrase_query_with_history(query, chat_history)
            
            # 2. クエリのバリデーション（エリア特定）
            if not self.validate_query(rephrased_query):
                return "どのエリアのレストランを探していますか？東京の主要エリア（新宿、渋谷、銀座など）を指定してください。"
            
            # 3. レストラン検索（10件まで取得）
            restaurants = self.search_restaurants(rephrased_query, max_results=10)
            
            # 4. 結果が見つからない場合
            if not restaurants:
                return "申し訳ありません。条件に合うレストランが見つかりませんでした。\n" \
                       "エリアや料理ジャンルを変えて再検索してみてください。"
            
            # 5. LLMを使用してレストランをランク付けして返す
            ranked_response = await self._rank_restaurants(rephrased_query, restaurants)
            
            return ranked_response
            
        except Exception as e:
            print(f"Error in restaurant search: {e}")
            return "検索中にエラーが発生しました。もう一度お試しください。"

# FAQツールとGreetingToolは以前と同じ実装を維持