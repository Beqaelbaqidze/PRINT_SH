from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from database import SessionLocal, engine
import models
import datetime
from fastapi import Path

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecret")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Login Required
def login_required(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)

# Routes
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

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)
    companies = db.query(models.Company).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "companies": companies})

# Example CRUD Route (Company list page)
@app.get("/companies", response_class=HTMLResponse)
def companies(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)
    companies = db.query(models.Company).all()
    return templates.TemplateResponse("companies.html", {"request": request, "companies": companies})

@app.get("/companies/add", response_class=HTMLResponse)
def add_company_form(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("company_form.html", {"request": request, "company": None})

@app.post("/companies/add")
def add_company(
    request: Request,
    company_name: str = Form(...),
    company_id: str = Form(...),
    email: str = Form(None),
    mobile_number: str = Form(None),
    director: str = Form(None),
    db: Session = Depends(get_db)
):
    new_company = models.Company(
        company_name=company_name,
        company_id=company_id,
        email=email,
        mobile_number=mobile_number,
        director=director
    )
    db.add(new_company)
    db.commit()
    return RedirectResponse("/companies", status_code=302)

@app.get("/companies/edit/{company_id}", response_class=HTMLResponse)
def edit_company_form(request: Request, company_id: int = Path(...), db: Session = Depends(get_db)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/", status_code=302)
    company = db.query(models.Company).filter_by(id=company_id).first()
    return templates.TemplateResponse("company_form.html", {"request": request, "company": company})

@app.post("/companies/edit/{company_id}")
def edit_company(
    request: Request,
    company_id: int = Path(...),
    company_name: str = Form(...),
    company_id_form: str = Form(...),
    email: str = Form(None),
    mobile_number: str = Form(None),
    director: str = Form(None),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter_by(id=company_id).first()
    company.company_name = company_name
    company.company_id = company_id_form
    company.email = email
    company.mobile_number = mobile_number
    company.director = director
    db.commit()
    return RedirectResponse("/companies", status_code=302)

@app.get("/companies/delete/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter_by(id=company_id).first()
    db.delete(company)
    db.commit()
    return RedirectResponse("/companies", status_code=302)