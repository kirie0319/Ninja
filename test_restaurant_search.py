import asyncio
import pytest
import os
import json
import uuid
from development import RestaurantSearchTool
from wsgi import execute_restaurant_search
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

async def generate_test_queries_with_ai():
    """生成AIにテストクエリを考えさせる"""
    
    llm = ChatOpenAI(
        model_name="gpt-4.1",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    query_generation_prompt = ChatPromptTemplate.from_template(
        """あなたは外国人旅行者向けのレストラン検索システムのテストを設計しています。
        
        シナリオ：
        - 英語が主言語の外国人旅行者
        - 目黒エリアで寿司を食べたい
        - 予算は50000円
        - 英語メニューや英語対応スタッフを希望
        - カウンター席で板前の技を見たい
        - 伝統的または現代的な日本の雰囲気を楽しみたい
        - ソロまたは2〜4人の小グループ
        
        以下の形式で8個のテストクエリを生成してください：
        - 日本語と英語両方でユニークなクエリを作成
        - 実際の外国人旅行者が使いそうな自然な表現
        - 様々な検索パターンをカバー（予算、ジャンル、言語対応、雰囲気など）
        
        JSONフォーマットで出力してください：
        {{
            "test_queries": [
                {{
                    "query": "クエリテキスト",
                    "language": "ja" または "en",
                    "expected_focus": "期待される検索結果の焦点",
                    "difficulty": "easy", "medium", または "hard"
                }},
                ...
            ]
        }}"""
    )
    
    chain = query_generation_prompt | llm | StrOutputParser()
    response = await chain.ainvoke({})
    
    try:
        # JSONを解析して構造化データを返す
        parsed_response = json.loads(response)
        return parsed_response.get("test_queries", [])
    except json.JSONDecodeError:
        # JSONパースに失敗した場合は、デフォルトのテストクエリを返す
        print("Warning: AI response could not be parsed. Using fallback queries.")
        return [
            {
                "query": "目黒 寿司 英語メニュー",
                "language": "ja",
                "expected_focus": "英語対応可能な寿司店",
                "difficulty": "easy"
            },
            {
                "query": "Meguro sushi restaurant English menu",
                "language": "en",
                "expected_focus": "English-friendly sushi restaurants",
                "difficulty": "easy"
            },
            {
                "query": "目黒の5000円から10000円の寿司レストラン",
                "language": "ja",
                "expected_focus": "特定の予算範囲の寿司店",
                "difficulty": "medium"
            },
            {
                "query": "Traditional sushi experience counter seating Meguro",
                "language": "en",
                "expected_focus": "伝統的なカウンター席の寿司体験",
                "difficulty": "hard"
            }
        ]

@pytest.mark.asyncio
async def test_restaurant_search_tool():
    # Initialize the tool
    tool = RestaurantSearchTool()
    
    # AIを使って動的にテストクエリを生成
    test_query_data = await generate_test_queries_with_ai()
    test_queries = [q["query"] for q in test_query_data]
    
    if "--json" in pytest.config.args:
        print("\n" + "="*50)
        print("AI-Generated Restaurant Search Test Results (JSON Format)")
        print("="*50)
        
        # AIが生成したテストクエリの情報を表示
        print("\n🤖 AI Generated Test Queries:")
        print(json.dumps(test_query_data, ensure_ascii=False, indent=2))
        
        test_results = []
        
        for idx, query_obj in enumerate(test_query_data):
            query = query_obj["query"]
            try:
                result = await tool.invoke(query)
                test_results.append({
                    "query": query,
                    "query_metadata": query_obj,
                    "result": result,
                    "status": "success"
                })
                
                print(f"\n📍 Query #{idx+1}: '{query}'")
                print(f"Language: {query_obj['language']}")
                print(f"Expected Focus: {query_obj['expected_focus']}")
                print(f"Difficulty: {query_obj['difficulty']}")
                print(f"Result (JSON):")
                print(json.dumps({"query": query, "result": result}, ensure_ascii=False, indent=2))
                
            except Exception as e:
                test_results.append({
                    "query": query,
                    "query_metadata": query_obj,
                    "error": str(e),
                    "status": "error"
                })
                print(f"\n❌ Error for query '{query}': {str(e)}")
        
        # Save full results to file
        with open('ai_generated_test_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                "generated_queries": test_query_data,
                "test_results": test_results
            }, f, ensure_ascii=False, indent=2)
        
        print("\n✅ Full test results saved to 'ai_generated_test_results.json'")
    
    # Normal pytest assertions
    for query in test_queries:
        try:
            result = await tool.invoke(query)
            assert isinstance(result, str), f"Result for '{query}' should be a string"
            assert len(result) > 0, f"Result for '{query}' should not be empty"
            assert any(keyword in result for keyword in ['おすすめ', 'レストラン', 'English', '英語', '外国', '寿司']), \
                   f"Result for '{query}' should contain relevant restaurant information"
        except Exception as e:
            pytest.fail(f"Query '{query}' failed: {str(e)}")
    
    # Test invalid query
    invalid_query_result = await tool.invoke("北海道のレストラン")
    assert isinstance(invalid_query_result, str), "Invalid query should return a string message"
    assert "どのエリアのレストラン" in invalid_query_result, "Invalid query message should suggest specifying an area"

@pytest.mark.asyncio
async def test_search_restaurants():
    tool = RestaurantSearchTool()
    
    # AIを使って検索テストクエリを生成
    ai_search_queries = await generate_test_queries_with_ai()
    
    for query_obj in ai_search_queries[:3]:  # 最初の3つのクエリでテスト
        search_query = query_obj["query"]
        search_results = tool.search_restaurants(search_query)
        
        if "--json" in pytest.config.args:
            print("\n" + "="*50)
            print(f"Direct Search Results Test (JSON Format) - {search_query}")
            print("="*50)
            
            print(f"\n📍 Query: '{search_query}'")
            print(f"Generated by AI - Language: {query_obj['language']}")
            print(f"Expected Focus: {query_obj['expected_focus']}")
            print(f"Raw search results ({len(search_results)} results):")
            print(json.dumps(search_results[:2], ensure_ascii=False, indent=2))  # 最初の2つの結果のみ表示
            
            # 外国人観光客向けの分析を実施
            analysis = {
                "total_results": len(search_results),
                "english_supported": len([r for r in search_results if r.get('english') == 'あり']),
                "budget_range": {},
                "wifi_available": len([r for r in search_results if r.get('wifi') == 'あり']),
                "credit_card_accepted": len([r for r in search_results if r.get('card') == '利用可']),
            }
            
            # 予算分布の分析
            for result in search_results:
                budget = result.get('budget', 'Unknown')
                analysis["budget_range"][budget] = analysis["budget_range"].get(budget, 0) + 1
            
            print("\nSearch Results Analysis:")
            print(json.dumps(analysis, ensure_ascii=False, indent=2))
        
        assert isinstance(search_results, list), "Search results should be a list"
        
        # Check individual restaurant details with focus on foreign tourist needs
        for restaurant in search_results:
            assert 'name' in restaurant
            assert 'genre' in restaurant
            assert 'score' in restaurant
            
            # 外国人旅行者に重要な機能をチェック
            if restaurant.get('english') == 'あり':
                if "--json" in pytest.config.args:
                    print(f"✓ {restaurant['name']} has English support")

# Standalone AI-driven test function
async def run_ai_generated_tests():
    """AIが生成したクエリを使用してテストを実行"""
    
    print("\n" + "="*60)
    print("AI-Generated Foreign Tourist Restaurant Search Tests")
    print("="*60)
    
    # 外国人観光客シナリオの詳細定義
    tourist_scenario = {
        "profile": "Foreign Tourist in Meguro",
        "preferences": {
            "budget": "¥5,0000-10,0000",
            "language": "English support required",
            "cuisine": "Sushi (primary) + Japanese options",
            "atmosphere": "Traditional or modern Japanese",
            "group_size": "1-4 people",
            "special_preferences": [
                "Counter seating to watch chef",
                "Authentic experience",
                "Photography-friendly"
            ]
        },
        "constraints": [
            "Language barrier",
            "Unfamiliar with Japanese customs",
            "Limited time in Tokyo"
        ]
    }
    
    print("\n👤 Tourist Scenario:")
    print(json.dumps(tourist_scenario, ensure_ascii=False, indent=2))
    
    # AIにこのシナリオに基づいてクエリを生成させる
    test_queries = await generate_test_queries_with_ai()
    
    print("\n🤖 AI-Generated Test Queries:")
    print(json.dumps(test_queries, ensure_ascii=False, indent=2))
    
    tool = RestaurantSearchTool()
    all_results = []
    
    for idx, query_obj in enumerate(test_queries):
        print(f"\n" + "="*40)
        print(f"Test #{idx+1}: {query_obj['query']}")
        print(f"Language: {query_obj['language']}")
        print(f"Expected Focus: {query_obj['expected_focus']}")
        print(f"Difficulty: {query_obj['difficulty']}")
        print("="*40)
        
        try:
            # Raw search resultsの取得と分析
            raw_results = tool.search_restaurants(query_obj['query'])
            
            # 外国人観光客向けの特別な分析
            tourist_friendly_analysis = {
                "english_support_count": 0,
                "proper_budget_match": 0,
                "tourist_friendly_features": {}
            }
            
            for result in raw_results:
                # 英語サポートの確認
                if result.get('english') == 'あり':
                    tourist_friendly_analysis["english_support_count"] += 1
                
                # 予算マッチの確認（5000-10000円範囲）
                if "budget" in result:
                    if "5000" in result["budget"] or "6000" in result["budget"] or "8000" in result["budget"]:
                        tourist_friendly_analysis["proper_budget_match"] += 1
                
                # その他の外国人向け機能
                features = []
                if result.get('wifi') == 'あり':
                    features.append('Wi-Fi')
                if result.get('card') == '利用可':
                    features.append('Credit Card')
                if result.get('non_smoking') == '全面禁煙':
                    features.append('Non-Smoking')
                
                if features:
                    tourist_friendly_analysis["tourist_friendly_features"][result['name']] = features
            
            # LLMからの最終レスポンス取得
            final_response = await tool.invoke(query_obj['query'])
            
            test_result = {
                "query": query_obj['query'],
                "query_metadata": query_obj,
                "raw_results_count": len(raw_results),
                "tourist_analysis": tourist_friendly_analysis,
                "final_response": final_response,
                "status": "success"
            }
            
            print("\n📊 Tourist-Friendly Analysis:")
            print(json.dumps(tourist_friendly_analysis, ensure_ascii=False, indent=2))
            
            print("\n💬 Final AI Response:")
            print(final_response)
            
        except Exception as e:
            test_result = {
                "query": query_obj['query'],
                "query_metadata": query_obj,
                "error": str(e),
                "status": "error"
            }
            print(f"\n❌ Error: {str(e)}")
        
        all_results.append(test_result)
    
    # Save comprehensive results
    output_file = 'ai_generated_tourist_search_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "scenario": tourist_scenario,
            "generated_queries": test_queries,
            "test_results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ All test results saved to '{output_file}'")
    
    # Print executive summary
    success_count = sum(1 for r in all_results if r['status'] == 'success')
    print(f"\n📈 Executive Summary:")
    print(f"- Total tests: {len(all_results)}")
    print(f"- Successful: {success_count}")
    print(f"- AI query generation quality: {'Good' if success_count > len(all_results) * 0.8 else 'Needs improvement'}")

# Main execution
if __name__ == "__main__":
    import sys
    
    if "--json" in sys.argv:
        # Run AI-driven tests
        asyncio.run(run_ai_generated_tests())
    else:
        # Run with pytest
        sys.argv.append("--json")
        pytest.main(sys.argv)