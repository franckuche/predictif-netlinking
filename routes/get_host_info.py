# routes/get_host_info.py
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import httpx
import os

# Création d'une instance de APIRouter
router = APIRouter()

# Charge les variables d'environnement à partir du fichier .env
load_dotenv()

templates = Jinja2Templates(directory="templates")
API_KEY = os.getenv("BABBAR_API_KEY")

@router.post("/get-host-info/", response_class=HTMLResponse)
async def get_host_info(request: Request, host: str = Form(...)):
    url = "https://www.babbar.tech/api/host/overview/main"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {"host": host}

    with httpx.Client() as client:
        api_response = client.post(url, json=data, headers=headers)

    if api_response.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")
    elif api_response.status_code == 429:
        raise HTTPException(status_code=429, detail="Too Many Requests")
    elif api_response.status_code != 200:
        raise HTTPException(status_code=api_response.status_code, detail="API request failed")

    response_data = api_response.json()
    if not isinstance(response_data, dict):
        raise HTTPException(status_code=500, detail="Invalid JSON response")

    return templates.TemplateResponse("get-host-info.html", {"request": request, "response_data": response_data})
