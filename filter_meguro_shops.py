import json

# Input and output file paths
input_file = '/Users/mbp231/Desktop/Ninja/hotpepper_data/shops/large_area_Z011_shops.json'
output_file = '/Users/mbp231/Desktop/Ninja/meguro_shops.json'

# Read the input JSON file
with open(input_file, 'r', encoding='utf-8') as f:
    shops = json.load(f)

# Filter shops with small_area name as "目黒"
meguro_shops = [
    shop for shop in shops 
    if shop.get('small_area', {}).get('name') == '目黒'
]

# Write filtered shops to a new JSON file
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(meguro_shops, f, ensure_ascii=False, indent=2)

print(f"Total shops in original file: {len(shops)}")
print(f"Shops in 目黒: {len(meguro_shops)}")
