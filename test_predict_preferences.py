import asyncio
import json
import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Ninja.wsgi import predict_missing_preferences

async def test_predict_missing_preferences():
    print("\n🌟 Comprehensive Preference Prediction Test 🌟")
    
    # Test cases with different scenarios
    test_cases = [
        {
            "name": "Empty Preferences",
            "message": "東京で美味しい日本食を食べたい",
            "preferences": {}
        },
        {
            "name": "Partial Preferences",
            "message": "新宿で2人でディナー",
            "preferences": {"location": "Shinjuku"}
        },
        {
            "name": "Specific Preferences",
            "message": "渋谷で高級な和食を探しています",
            "preferences": {"location": "Shibuya", "budget_level": "High"}
        }
    ]
    
    # Run tests
    for case in test_cases:
        print(f"\n📋 Test Case: {case['name']}")
        print(f"User Message: {case['message']}")
        print(f"Initial Preferences: {json.dumps(case['preferences'], indent=2, ensure_ascii=False)}")
        
        try:
            result = await predict_missing_preferences(case['message'], case['preferences'])
            print("\n🏆 Final Preferences:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"❌ Test failed: {e}")

if __name__ == '__main__':
    asyncio.run(test_predict_missing_preferences())
