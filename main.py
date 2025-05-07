from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, String, Boolean, Date, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date

# Database setup
DATABASE_URL = "postgresql://beqa:1524Elbaqa@localhost:5432/licenses"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Table model
class LicenseRegistry(Base):
    __tablename__ = "license_registry"
    company_name = Column(String, primary_key=True)
    company_code = Column(String)
    email = Column(String)
    mobile_number = Column(String)
    director = Column(String)
    surveyor_name = Column(String, primary_key=True)
    computer_serial = Column(String, primary_key=True)
    paid = Column(Boolean, default=False)
    expire_date = Column(Date)

Base.metadata.create_all(bind=engine)

# App setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/all")
def get_all():
    db = SessionLocal()
    rows = db.query(LicenseRegistry).all()
    result = []
    for row in rows:
        result.append({
            "company_name": row.company_name,
            "company_code": row.company_code,
            "email": row.email,
            "mobile_number": row.mobile_number,
            "director": row.director,
            "surveyor_name": row.surveyor_name,
            "computer_serial_number": row.computer_serial,
            "paid": row.paid,
            "expire_date": row.expire_date.isoformat(),
            "status": row.paid and row.expire_date > date.today()
        })
    return JSONResponse(result)

@app.get("/api/options")
def get_options():
    db = SessionLocal()
    companies = db.query(LicenseRegistry.company_name).distinct().all()
    surveyors = db.query(LicenseRegistry.surveyor_name).distinct().all()
    computers = db.query(LicenseRegistry.computer_serial).distinct().all()
    return JSONResponse({
        "companies": [{"id": c.company_name, "name": c.company_name} for c in companies],
        "surveyors": [{"id": s.surveyor_name, "name": s.surveyor_name} for s in surveyors],
        "computers": [{"id": c.computer_serial, "serial_number": c.computer_serial} for c in computers]
    })

@app.post("/api/create/full")
def create_full(
    new_company_name: str = Form(...),
    new_company_code: str = Form(...),
    new_company_email: str = Form(...),
    new_company_mobile: str = Form(...),
    new_company_director: str = Form(...),
    new_surveyor_name: str = Form(...),
    new_computer_serial: str = Form(...),
    paid: bool = Form(...),
    expire_date: str = Form(...)
):
    db = SessionLocal()
    expire = date.fromisoformat(expire_date)
    entry = LicenseRegistry(
        company_name=new_company_name,
        company_code=new_company_code,
        email=new_company_email,
        mobile_number=new_company_mobile,
        director=new_company_director,
        surveyor_name=new_surveyor_name,
        computer_serial=new_computer_serial,
        paid=paid,
        expire_date=expire
    )
    db.merge(entry)
    db.commit()
    return JSONResponse({"message": "License created"})

