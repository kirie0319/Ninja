# utils/tools.py
import re 

class RestaurantSearchTool:
    def __init__(self, history_retriever):
        self.history_retriever = history_retriever
        self.name = "restaurant_search"
        self.description = "Search for restaurants and rate them"

    async def invoke(self, query, chat_history=None):
        if not re.search(r'東京|新宿|渋谷|池袋|銀座|上野|秋葉原|新橋|浅草|品川|六本木|目黒)', query):
            return "Where are you looking for restaurants? ex: 目黒のレストランを検索する"
        
        results = await self.history_retriever.search(query, chat_history)

        if not results:
            return "Sorry, I couldn't find any restaurants matching your query. Please try again."

        restaurants_list = []
        for i, match in enumerate(results):
            if i >= 3:
                break

            metadata = match.metadata
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
                "score": match.score
            }
            restaurants_list.append(restaurant)
        return restaurants_list

class GreetTool:
    def __init__(self):
        self.name = "greet_user"
        self.description = "Greet the user"
    
    async def invoke(self):
        return "Hello! What kind of restaurant are you looking for? Let's find it!"

class FAQTool:
    def __init__(self):
        self.name = "faq_lookup"
        self.description = "Let's answer your question"

        self.faqs = {
            "Business Hours": "Restaurant business hours vary by location. Please check the information displayed in the search results.",
            "Reservation": "Reservations can be made through Hot Pepper Gourmet or the official website of each restaurant.",
            "Coupons": "Many restaurants offer great deals through coupons on Hot Pepper Gourmet.",
            "Child-Friendly": "To find restaurants that welcome children, use the search filter for 'Child-Friendly'.",
            "COVID Measures": "Please refer to each restaurant's detail page to check their COVID-19 precautions."
        }
    
    async def invoke(self, query):
        lower_query = query.lower()
        for key, value in self.faqs.items():
            if key in lower_query:
                return value
            
        return "I'm sorry, I couldn't find an answer to your question. Please try again."
