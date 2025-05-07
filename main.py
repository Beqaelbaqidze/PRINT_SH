from fastapi import FastAPI, Request, Form, Depends, HTTPException, Path
from fastapi.responses import RedirectResponse, HTMLResponse
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

# Auth Middleware
def login_required(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)

# Login / Logout
@app.get("/", response_class=HTMLResponse)
def login_form(request: Request):
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

# Dashboard: Relational Join View
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)

    companies = db.query(models.Company).all()
    surveyors = db.query(models.Surveyor).all()
    computers = db.query(models.Computer).all()
    licenses = db.query(models.License).all()

    # Join real values for display
    licenses_with_info = []
    for lic in licenses:
        comp = lic.computer
        surveyor = comp.surveyor
        licenses_with_info.append({
            "license_id": lic.id,
            "computer_serial": comp.serial_number,
            "surveyor_name": surveyor.name,
            "paid": lic.paid,
            "expire_date": lic.expire_date,
            "status": lic.paid and lic.expire_date > date.today()
        })

    computers_with_info = []
    for comp in computers:
        computers_with_info.append({
            "computer_id": comp.id,
            "serial_number": comp.serial_number,
            "surveyor_name": comp.surveyor.name
        })

    surveyors_with_info = []
    for s in surveyors:
        surveyors_with_info.append({
            "surveyor_id": s.id,
            "name": s.name,
            "companies": [c.company_name for c in s.companies]
        })

    companies_info = [{
        "id": c.id,
        "company_name": c.company_name,
        "company_id": c.company_id,
        "email": c.email,
        "mobile": c.mobile_number,
        "director": c.director
    } for c in companies]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "companies": companies_info,
        "surveyors": surveyors_with_info,
        "computers": computers_with_info,
        "licenses": licenses_with_info
    })

# The rest of the CRUD for Companies, Surveyors, Computers, Licenses remains unchanged (already provided).