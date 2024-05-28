import os
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from hoodwink.processor import fetch_text, extract_ingredients
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Request

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_bearer_token(request: Request, call_next):
    if request.method == "OPTIONS":
        # Allow CORS preflight requests to pass through
        response = await call_next(request)
        return response

    auth_header = request.headers.get("Authorization")
    expected_token = os.getenv("SIMPLE_AUTH_TOKEN")
    if auth_header != f"Bearer {expected_token}":
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    response = await call_next(request)
    return response


class UrlModel(BaseModel):
    url: str


@app.post("/extract-ingredients/")
async def extract_ingredients_from_url(url: UrlModel):
    try:
        text = fetch_text(url.url)
        ingredients = extract_ingredients(text)
        return ingredients
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"Hello": "World"}


def main():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
