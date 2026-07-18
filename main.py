from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import requests
from google import genai

load_dotenv()
print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))

app = FastAPI()

#  CORS設定（Vue.jsからのリクエスト）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(
            api_key=GEMINI_API_KEY
        )

@app.get("/")
def read_root():
    return {"message": "MeshiAI API is running!"}

@app.get("/search")
def search_restaurants(query: str, location: str):
    # Google Places APIを使用してレストランを検索
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.primaryTypeDisplayName"
    }
    body = {
        "textQuery": f"{query} {location}",
        "languageCode": "ja",
        "maxResultCount": 5,
    }
    response = requests.post(url, headers=headers, json=body)
    data = response.json()

    results = []
    for place in data.get("places", []):
        results.append({
            "name": place.get("displayName", {}).get("text"),
            "address": place.get("formattedAddress"),
            "category": place.get("primaryTypeDisplayName", {}).get("text"),
            "rating": place.get("rating")
        })

    shop_list = "\n".join([
        f"{i+1}. {r['name']} ({r['category']}) 評価{r['rating']}"
        for i, r in enumerate(results)
    ])
    prompt = f"""
            あなたはグルメライターです。

            以下のレストランの中から、「{query}」を探しているユーザーへの
            おすすめコメントを100文字以内で日本語で生成してください。

            条件
            ・100文字以内
            ・絵文字を1個まで
            ・自然な日本語
            ・店名を2〜3店舗入れる
            ・ランキング形式にしない
            
            店舗一覧
            {shop_list}
            """
    ai_response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt
    )
    ai_comment = ai_response.text

    return {
        "ai_comment": ai_comment,
        "restaurants": results
    }