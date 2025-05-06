import os
import math
import json
from typing import List, Dict, Any, Optional, Union

# サードパーティライブラリ
import pinecone
import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeStore

class CustomChatOpenAI(ChatOpenAI):
    """
    OpenRouterや特殊なモデル用のカスタムトークン推定器
    """
    def _estimate_tokens(self, text: str) -> int:
        """
        文字数に基づくシンプルなトークン推定
        """
        return math.ceil(len(text) / 4)

    def get_num_tokens(self, text: str) -> int:
        """
        テキストのトークン数を推定
        """
        return self._estimate_tokens(text)

    def get_num_tokens_from_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        メッセージからトークン数を推定
        """
        text = "\n".join([
            msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
            for msg in messages
        ])
        total_count = self._estimate_tokens(text)
        return {
            "total_count": total_count,
            "count_per_message": [0] * len(messages)
        }

class ZoeJobSearch:
    def __init__(self, language: str = "en"):
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
        
        # 言語設定
        self.language = language
        
    def search_jobs(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        求人検索を実行
        """
        # クエリの埋め込みを生成
        query_embedding = self.embeddings.embed_query(query)
        
        # Pineconeで類似性検索
        results = self.pinecone_index.query(
            vector=query_embedding,
            top_k=max_results,
            include_metadata=True
        )
        
        # 結果を整形
        jobs = [
            {
                "title": doc["metadata"]["title"],
                "location": doc["metadata"]["location"],
                "description": doc["pageContent"][:140] + "…"
            }
            for doc in results.get("matches", [])
        ]
        
        return jobs
    
    def rank_jobs(self, query: str, jobs: List[Dict[str, Any]]) -> str:
        """
        求人をランク付けし、レスポンスを生成
        """
        jobs_list = "\n\n".join([
            f"{i+1}. {job['title']} | {job['location']}\n{job['description']}"
            for i, job in enumerate(jobs)
        ])
        
        rank_prompt = ChatPromptTemplate.from_template(
            "求人をユーザーのクエリ: '{query}' に基づいてランク付けしてください。"
            "最大3つの求人について、それぞれ1文で理由を添えてください。\n\n"
            "求人リスト:\n{jobs}"
        )
        
        # プロンプトをフォーマット
        formatted_prompt = rank_prompt.format(query=query, jobs=jobs_list)
        
        # LLMで求人をランク付け
        ranked_response = self.llm.invoke(formatted_prompt)
        
        return ranked_response.content
    
    def process_job_search(self, query: str) -> str:
        """
        求人検索のメインプロセス
        """
        # 言語に応じた初期メッセージ
        if self.language.startswith("jp"):
            initial_message = "こんにちは！ 👋 どのようなお仕事をお探しですか？"
        else:
            initial_message = "Hello! 👋 How can I help you with your job search today?"
        
        # 求人検索
        jobs = self.search_jobs(query)
        
        if not jobs:
            return f"{initial_message}\n\n求人が見つかりませんでした。別のキーワードで検索してみてください。"
        
        # 求人のランク付け
        ranked_jobs = self.rank_jobs(query, jobs)
        
        return f"{initial_message}\n\n求人検索結果:\n{ranked_jobs}"

# 使用例
if __name__ == "__main__":
    job_search = ZoeJobSearch(language="ja")
    result = job_search.process_job_search("データサイエンティスト")
    print(result)
