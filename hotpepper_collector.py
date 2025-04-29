import requests
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from tqdm import tqdm
import logging

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hotpepper_data_collection.log'),
        logging.StreamHandler()
    ]
)

class HotpepperDataCollector:
    """ホットペッパーAPIを使用してデータを収集・保存するクラス"""
    
    def __init__(self, api_key, output_dir='hotpepper_data'):
        """
        初期化
        
        Args:
            api_key (str): ホットペッパーAPIのAPIキー
            output_dir (str): データを保存するディレクトリ
        """
        self.api_key = api_key
        self.base_url = "http://webservice.recruit.co.jp/hotpepper"
        self.output_dir = output_dir
        
        # 出力ディレクトリの作成
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'shops'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'areas'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'genres'), exist_ok=True)
        
        # APIリクエストの間隔 (秒)
        self.request_interval = 1
        
        logging.info(f"ホットペッパーデータコレクター初期化: 出力先 {output_dir}")
    
    def _make_request(self, endpoint, params=None):
        """
        APIリクエストを実行
        
        Args:
            endpoint (str): APIエンドポイント
            params (dict): リクエストパラメータ
            
        Returns:
            dict: APIレスポンスのJSONデータ
        """
        if params is None:
            params = {}
        
        # 共通パラメータ
        params.update({
            'key': self.api_key,
            'format': 'json',
        })
        
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"APIリクエストエラー: {endpoint} - {e}")
            return None
    
    def get_large_areas(self):
        """大エリア情報を取得"""
        logging.info("大エリア情報の取得開始")
        data = self._make_request('large_area/v1/')
        
        if data and 'results' in data:
            file_path = os.path.join(self.output_dir, 'areas', 'large_areas.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"大エリア情報を保存: {file_path}")
            return data['results']['large_area']
        else:
            logging.error("大エリア情報の取得に失敗")
            return []
    
    def get_middle_areas(self, large_area=None):
        """中エリア情報を取得"""
        logging.info("中エリア情報の取得開始")
        params = {}
        if large_area:
            params['large_area'] = large_area
        
        data = self._make_request('middle_area/v1/', params)
        
        if data and 'results' in data:
            file_path = os.path.join(self.output_dir, 'areas', 'middle_areas.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"中エリア情報を保存: {file_path}")
            return data['results']['middle_area']
        else:
            logging.error("中エリア情報の取得に失敗")
            return []
    
    def get_small_areas(self, middle_area=None):
        """小エリア情報を取得"""
        logging.info("小エリア情報の取得開始")
        params = {}
        if middle_area:
            params['middle_area'] = middle_area
        
        data = self._make_request('small_area/v1/', params)
        
        if data and 'results' in data:
            file_path = os.path.join(self.output_dir, 'areas', 'small_areas.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"小エリア情報を保存: {file_path}")
            return data['results']['small_area']
        else:
            logging.error("小エリア情報の取得に失敗")
            return []
    
    def get_genres(self):
        """ジャンル情報を取得"""
        logging.info("ジャンル情報の取得開始")
        data = self._make_request('genre/v1/')
        
        if data and 'results' in data:
            file_path = os.path.join(self.output_dir, 'genres', 'genres.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"ジャンル情報を保存: {file_path}")
            return data['results']['genre']
        else:
            logging.error("ジャンル情報の取得に失敗")
            return []
    
    def get_shops_by_area(self, area_code, area_type='large_area', start=1, count=100):
        """
        エリアコードを指定して店舗情報を取得
        
        Args:
            area_code (str): エリアコード
            area_type (str): エリアタイプ (large_area, middle_area, small_area)
            start (int): 取得開始位置
            count (int): 1回のリクエストでの取得件数
            
        Returns:
            list: 店舗情報のリスト
        """
        params = {
            area_type: area_code,
            'start': start,
            'count': count,
        }
        
        data = self._make_request('gourmet/v1/', params)
        
        if data and 'results' in data:
            return {
                'shops': data['results']['shop'],
                'results_available': data['results']['results_available'],
                'results_returned': data['results']['results_returned'],
                'results_start': data['results']['results_start']
            }
        else:
            logging.error(f"店舗情報の取得に失敗: {area_type}={area_code}")
            return {'shops': [], 'results_available': 0, 'results_returned': 0, 'results_start': 0}
    
    def get_all_shops_by_area(self, area_code, area_type='large_area'):
        """
        エリアコードを指定して全店舗情報を取得
        
        Args:
            area_code (str): エリアコード
            area_type (str): エリアタイプ (large_area, middle_area, small_area)
            
        Returns:
            list: 全店舗情報のリスト
        """
        logging.info(f"エリア {area_code} の全店舗情報取得開始")
        
        all_shops = []
        start = 1
        count = 100  # APIの制限に合わせる
        
        # 最初のリクエスト
        result = self.get_shops_by_area(area_code, area_type, start, count)
        all_shops.extend(result['shops'])
        
        # 総店舗数
        total_available = result['results_available']
        logging.info(f"エリア {area_code} の総店舗数: {total_available}")
        
        # 残りの店舗を取得
        with tqdm(total=total_available, initial=len(all_shops)) as pbar:
            while len(all_shops) < total_available:
                start += count
                time.sleep(self.request_interval)  # API制限を考慮
                
                result = self.get_shops_by_area(area_code, area_type, start, count)
                new_shops = result['shops']
                all_shops.extend(new_shops)
                
                pbar.update(len(new_shops))
                
                if not new_shops:
                    break
        
        # 保存
        file_name = f"{area_type}_{area_code}_shops.json"
        file_path = os.path.join(self.output_dir, 'shops', file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_shops, f, ensure_ascii=False, indent=2)
        
        logging.info(f"エリア {area_code} の全店舗情報を保存: {file_path}")
        return all_shops
    
    def get_shop_detail(self, shop_id):
        """
        店舗IDを指定して詳細情報を取得
        
        Args:
            shop_id (str): 店舗ID
            
        Returns:
            dict: 店舗詳細情報
        """
        params = {'id': shop_id}
        data = self._make_request('gourmet/v1/', params)
        
        if data and 'results' in data and 'shop' in data['results'] and len(data['results']['shop']) > 0:
            shop_detail = data['results']['shop'][0]
            
            # 保存
            file_path = os.path.join(self.output_dir, 'shops', f"shop_{shop_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(shop_detail, f, ensure_ascii=False, indent=2)
            
            return shop_detail
        else:
            logging.error(f"店舗詳細の取得に失敗: shop_id={shop_id}")
            return None
    
    def collect_all_data(self):
        """全データの収集を実行"""
        logging.info("全データ収集プロセス開始")
        
        # エリア情報の取得
        large_areas = self.get_large_areas()
        middle_areas = self.get_middle_areas()
        small_areas = self.get_small_areas()
        
        # ジャンル情報の取得
        genres = self.get_genres()
        
        # エリアごとの店舗情報を取得
        all_shops = []
        
        # 大エリアごとに店舗を取得
        for area in large_areas:
            area_code = area['code']
            shops = self.get_all_shops_by_area(area_code, 'large_area')
            all_shops.extend(shops)
            time.sleep(self.request_interval)
        
        # 全店舗の詳細情報を取得（オプション）
        # 注: 多数の店舗がある場合は時間がかかります
        unique_shop_ids = set(shop['id'] for shop in all_shops)
        logging.info(f"ユニーク店舗数: {len(unique_shop_ids)}")
        
        # DataFrameに変換して保存
        df_shops = pd.DataFrame(all_shops)
        df_shops.to_csv(os.path.join(self.output_dir, 'all_shops.csv'), index=False)
        
        logging.info("全データ収集完了")
        return {
            'large_areas': large_areas,
            'middle_areas': middle_areas,
            'small_areas': small_areas,
            'genres': genres,
            'shops': all_shops
        }


# 使用例
if __name__ == "__main__":
    # APIキーを設定
    API_KEY = "cee74691e08d6d18"
    
    # データコレクターの初期化
    collector = HotpepperDataCollector(API_KEY)
    
    # オプション1: 全データを収集
    collector.collect_all_data()
    
    # オプション2: 特定のエリアのみ収集
    # 東京エリア (Z011) の店舗を取得
    # shops = collector.get_all_shops_by_area('Z011', 'large_area')
    
    print(f"取得した店舗数: {len(shops)}")