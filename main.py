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
    data = []

    for company in companies:
        for surveyor in company.surveyors:
            for computer in surveyor.computers:
                for lic in computer.licenses:
                    data.append({
                        "company_name": company.company_name,
                        "company_id": company.company_id,
                        "email": company.email,
                        "mobile": company.mobile_number,
                        "director": company.director,
                        "surveyor_name": surveyor.name,
                        "computer_serial": computer.serial_number,
                        "paid": lic.paid,
                        "expire_date": lic.expire_date,
                        "status": lic.paid and lic.expire_date > date.today()
                    })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "rows": data
    })


# The rest of the CRUD for Companies, Surveyors, Computers, Licenses remains unchanged (already provided).