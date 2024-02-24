from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from routes.check_keywords import router as check_keywords_router
from routes.get_host_info import router as get_host_info_router

# Charger les variables d'environnement
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inclure les routers
app.include_router(get_host_info_router)
app.include_router(check_keywords_router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})