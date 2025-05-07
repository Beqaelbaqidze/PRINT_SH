from fastapi import FastAPI, Request, Form, Depends, HTTPException, Path
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from datetime import date
import models
from database import SessionLocal, engine

# DB setup
models.Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your_super_secret_key")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Login Required Decorator
def login_required(request: Request):
    if not request.session.get("logged_in"):
        raise HTTPException(status_code=401, detail="Not authenticated")

# Login routes
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        request.session["logged_in"] = True
        return RedirectResponse("/dashboard", status_code=302)
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Unified Flat API Endpoint with Real Values
@app.get("/api/all")
def api_all(request: Request, db: Session = Depends(get_db)):
    login_required(request)
    companies = db.query(models.Company).all()
    data = []

    for company in companies:
        for surveyor in company.surveyors:
            for computer in surveyor.computers:
                for license in computer.licenses:
                    data.append({
                        "company_name": company.company_name,
                        "company_id": company.company_id,
                        "email": company.email,
                        "mobile_number": company.mobile_number,
                        "director": company.director,
                        "surveyor_name": surveyor.name,
                        "computer_serial_number": computer.serial_number,
                        "paid": license.paid,
                        "expire_date": license.expire_date,
                        "status": license.paid and license.expire_date > date.today()
                    })

    return JSONResponse(data)