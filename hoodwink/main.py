import os
from fastapi import FastAPI
from fastapi import HTTPException
import uvicorn
from hoodwink.processor import fetch_text, extract_ingredients
from pydantic import BaseModel

app = FastAPI()


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
