from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import requests
from pydantic import BaseModel
import httpx
from google import genai

load_dotenv()
print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))

app = FastAPI()

#  CORS設定（Vue.jsからのリクエスト）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://meshi-ai-app.web.app"
    ],
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

# Google Places APIのみを使用する
# レスポンス改善のため
@app.get("/search")
async def search_restaurants(query: str, location: str, count: int = 5):
    # Google Places APIを使用してレストランを検索
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.primaryTypeDisplayName"
    }
    # 緯度経度の場所は、locationBias を使う
    body = {
        "textQuery": query,
        "languageCode": "ja",
        "maxResultCount": count,
    }

    # 緯度経度かどうか判定
    if ',' in location and any(c.isdigit() for c in location):
        try:
            lat, lng = location.split(',')
            body["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": float(lat),
                        "longitude": float(lng)
                    },
                    "radius": 1000.0
                }
            }
        except:
            body["textQuery"] = f"{query} {location}"
    else:
        body["textQuery"] = f"{query} {location}"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
    data = response.json()
    print(data)

    results = []
    for place in data.get("places", []):
        results.append({
            "name": place.get("displayName", {}).get("text"),
            "address": place.get("formattedAddress"),
            "category": place.get("primaryTypeDisplayName", {}).get("text"),
            "rating": place.get("rating")
        })

    return {
        "restaurants": results
    }

# Gemini APIのみを使用する
# レスポンス改善のため
class AICommentRequest(BaseModel):
    query: str
    restaurants: list

@app.post("/ai-comment")
def create_ai_comment(req: AICommentRequest):

    shop_list = "\n".join([
        f"{i+1}. {r['name']} 評価{r['rating']}"
        for i, r in enumerate(req.restaurants)
    ])

    prompt = f"""
            あなたはグルメライターです。

            以下のレストランの中から、「{req.query}」を探しているユーザーがいます。
            その人に最もおすすめなお店を紹介してください。

            条件
            ・100文字以内
            ・絵文字を1個まで
            ・自然な日本語
            ・店名を2〜3店舗入れる
            ・ランキング形式にしない
            
            店舗一覧
            {shop_list}
            """
    response =  client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt
    )
    return {
        "ai_comment": response.text
    }