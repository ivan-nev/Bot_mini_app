from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory='Server/templates')

# app.mount("Server/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("triangl_calc.html", {"request": request})

@app.get("/stubacme-calc")
async def stub_acme_calc(request:Request):
    return templates.TemplateResponse("stubacme-calc.html", {"request": request})

@app.get("/metric-calc")
async def metric_calc(request:Request):
    return templates.TemplateResponse("metric-calc.html", {"request": request})

@app.get("/test")
async def metric_calc(request:Request):
    return templates.TemplateResponse("test.html", {"request": request})

@app.get("/test2")
async def metric_calc(request:Request):
    return templates.TemplateResponse("test2.html", {"request": request})



@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
