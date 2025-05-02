# from random import sample
# from utils.vector_store import VectorStore
# import json

# def main():
    
#     vector_store = VectorStore()
    
#     sample_restaurant = {
#         "id": "J003917486",
#     "name": "プロント飯田橋店",
#     "logo_image": "https://imgfp.hotp.jp/IMGH/13/25/P040801325/P040801325_69.jpg",
#     "name_kana": "プロントイイダバシテン",
#     "address": "東京都新宿区揚場町１-１１ 飯田橋中央ビル Ｂ１Ｆ",
#     "station_name": "飯田橋",
#     "ktai_coupon": 0,
#     "large_service_area": {
#       "code": "SS10",
#       "name": "関東"
#     },
#     "service_area": {
#       "code": "SA11",
#       "name": "東京"
#     },
#     "large_area": {
#       "code": "Z011",
#       "name": "東京"
#     },
#     "middle_area": {
#       "code": "Y006",
#       "name": "水道橋・飯田橋・神楽坂"
#     },
#     "small_area": {
#       "code": "X069",
#       "name": "飯田橋"
#     },
#     "lat": 35.7024307662,
#     "lng": 139.7438133914,
#     "genre": {
#       "name": "居酒屋",
#       "catch": "「昼はカフェ、夜はサカバ。」",
#       "code": "G001"
#     },
#     "sub_genre": {
#       "name": "ダイニングバー・バル",
#       "code": "G002"
#     },
#     "budget": {
#       "code": "B001",
#       "name": "1501～2000円",
#       "average": "ランチ/カフェ：501～1000円、ディナー：1500～2000円"
#     },
#     "catch": "夜は酒場に♪貸切大歓迎！ キッサカバオリジナル！",
#     "capacity": 82,
#     "access": "東京メトロ飯田橋駅B1出口より直結。ＪＲ飯田橋駅より徒歩3分。朝とお昼はカフェ、夜はキッサカバに。",
#     "mobile_access": "東京ﾒﾄﾛ飯田橋駅B1出口より直結",
#     "urls": {
#       "pc": "https://www.hotpepper.jp/strJ003917486/?vos=nhppalsa000016"
#     },
#     "photo": {
#       "pc": {
#         "l": "https://imgfp.hotp.jp/IMGH/13/27/P040801327/P040801327_238.jpg",
#         "m": "https://imgfp.hotp.jp/IMGH/13/27/P040801327/P040801327_168.jpg",
#         "s": "https://imgfp.hotp.jp/IMGH/13/27/P040801327/P040801327_58_s.jpg"
#       },
#       "mobile": {
#         "l": "https://imgfp.hotp.jp/IMGH/13/27/P040801327/P040801327_168.jpg",
#         "s": "https://imgfp.hotp.jp/IMGH/13/27/P040801327/P040801327_100.jpg"
#       }
#     },
#     "open": "月～金: 06:30～23:00 （料理L.O. 22:30 ドリンクL.O. 22:30）土: 10:00～21:30 （料理L.O. 21:00 ドリンクL.O. 21:00）",
#     "close": "日、祝日",
#     "party_capacity": 100,
#     "other_memo": "貸切も大歓迎！3000円台の飲み放題付コースもご用意。お気軽にご相談ください。",
#     "shop_detail_memo": "地下鉄飯田橋駅B1出口直結、ＪＲ飯田橋駅徒歩3分。女子会、2次会、貸切等幅広いシーンでご利用頂けます。",
#     "budget_memo": "",
#     "wedding": "ご要望等ございましたら、まずはお気軽にお電話でお問い合わせください。",
#     "course": "あり",
#     "free_drink": "あり ：飲み放題付コースは3850円～",
#     "free_food": "なし ：食べ放題のご用意はございません。",
#     "private_room": "なし",
#     "horigotatsu": "なし",
#     "tatami": "なし",
#     "card": "利用可",
#     "non_smoking": "一部禁煙",
#     "charter": "貸切可",
#     "parking": "なし",
#     "barrier_free": "なし",
#     "show": "なし",
#     "karaoke": "なし",
#     "band": "不可",
#     "tv": "なし",
#     "lunch": "あり",
#     "midnight": "営業していない",
#     "english": "なし",
#     "pet": "不可",
#     "child": "お子様連れOK",
#     "wifi": "あり",
#     "coupon_urls": {
#       "pc": "https://www.hotpepper.jp/strJ003917486/map/?vos=nhppalsa000016",
#       "sp": "https://www.hotpepper.jp/strJ003917486/scoupon/?vos=nhppalsa000016"
#     }
#     }
#     result = vector_store.store_restaurant(
#         restaurant_id=sample_restaurant['id'], 
#         restaurant_data=sample_restaurant, 
#         text_to_embed=f"""
#         名前: {sample_restaurant.get("name", "")}
#         ジャンル: {sample_restaurant.get("genre", "").get('name', '')} {sample_restaurant.get('genre', '').get('catch', '')}
#         サブジャンル: {sample_restaurant.get("sub_genre", "").get('name', '')}
#         エリア: {sample_restaurant.get("large_area", "").get('name', '')} {sample_restaurant.get('middle_area', '').get('name', '')} {sample_restaurant.get('small_area', '').get('name', '')}
#         アクセス: {sample_restaurant.get("access", "")}
#         """
#     )
#     print(f"保存結果: {result}")
    
#     test_queries = [
#         "飯田橋で居酒屋を探しています",
#         "カフェで昼食が取れる場所",
#         "飲み放題があるお店",
#         "貸切ができるレストラン"
#     ]
#     for query in test_queries:
#         print(f"\n検索クエリ: '{query}'")
#         results = vector_store.search_restaurants(query)
        
#         print("検索結果:")
#         for i, match in enumerate(results):
#             print(f"{i+1}. {match.metadata['name']} (スコア: {match.score:.4f})")
#             print(f" ジャンル: {match.metadata['genre']}")
#             print(f" キャッチ: {match.metadata['catch']}")
#             print(f" エリア: {match.metadata['area']}")
#             print(f" 予算: {match.metadata['budget']}")
#             print(f" URL: {match.metadata['urls_pc']}")

# if __name__ == "__main__":
#     main()

import json, os
from utils.vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()

vector_store = VectorStore()

def import_restaurants_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    restaurants = data if isinstance(data, list) else [data]
    vector_store = VectorStore()

    print(f"合計 {len(restaurants)} 店舗をインポートしています...")
    for i, restaurant in enumerate(restaurants):
        # Generate text_to_embed
        text_to_embed = f"""
        名前: {restaurant.get("name", "")}
        ジャンル: {restaurant.get("genre", {}).get('name', '')} {restaurant.get("genre", {}).get('catch', '')}
        サブジャンル: {restaurant.get("sub_genre", {}).get('name', '')}
        エリア: {restaurant.get("large_area", {}).get('name', '')} {restaurant.get("middle_area", {}).get('name', '')} {restaurant.get("small_area", {}).get('name', '')}
        アクセス: {restaurant.get("access", "")}
        予算: {restaurant.get("budget", {}).get('name', '')} {restaurant.get("budget", {}).get('average', '')}
        """
        
        # Use restaurant ID or generate a unique identifier
        restaurant_id = restaurant.get('id', f'restaurant_{i+1}')
        
        result = vector_store.store_restaurant(
            restaurant_id=restaurant_id, 
            restaurant_data=restaurant, 
            text_to_embed=text_to_embed
        )
        print(f"[{i+1}/{len(restaurants)}] {result['name']} - {result['status']}")
    print("インポート完了")

if __name__ == "__main__":
    import_restaurants_from_file("meguro_shops.json")