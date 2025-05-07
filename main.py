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

@app.get("/api/options")
def get_options(request: Request, db: Session = Depends(get_db)):
    login_required(request)

    companies = db.query(models.Company).all()
    surveyors = db.query(models.Surveyor).all()
    computers = db.query(models.Computer).all()

    return JSONResponse({
        "companies": [
            {"id": c.id, "name": c.company_name, "company_id": c.company_id}
            for c in companies
        ],
        "surveyors": [
            {"id": s.id, "name": s.name}
            for s in surveyors
        ],
        "computers": [
            {"id": comp.id, "serial_number": comp.serial_number}
            for comp in computers
        ]
    })

@app.post("/api/create/company")
def create_company(
    request: Request,
    company_name: str = Form(...),
    company_id: str = Form(...),
    email: str = Form(...),
    mobile_number: str = Form(...),
    director: str = Form(...),
    db: Session = Depends(get_db)
):
    login_required(request)

    existing = db.query(models.Company).filter_by(company_id=company_id).first()
    if not existing:
        db.add(models.Company(
            company_name=company_name,
            company_id=company_id,
            email=email,
            mobile_number=mobile_number,
            director=director
        ))
        db.commit()
        return JSONResponse({"message": "Company created"})
    return JSONResponse({"message": "Company already exists"})

@app.post("/api/create/surveyor")
def create_surveyor(
    request: Request,
    name: str = Form(...),
    company_id: int = Form(...),
    db: Session = Depends(get_db)
):
    login_required(request)

    company = db.query(models.Company).filter_by(id=company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    surveyor = db.query(models.Surveyor).filter_by(name=name).first()
    if not surveyor:
        surveyor = models.Surveyor(name=name)
        db.add(surveyor)
        db.commit()
        db.refresh(surveyor)

    if company not in surveyor.companies:
        surveyor.companies.append(company)
        db.commit()

    return JSONResponse({"message": "Surveyor created or linked"})

@app.post("/api/create/computer")
def create_computer(
    request: Request,
    serial_number: str = Form(...),
    surveyor_id: int = Form(...),
    db: Session = Depends(get_db)
):
    login_required(request)
    existing = db.query(models.Computer).filter_by(serial_number=serial_number).first()
    if not existing:
        db.add(models.Computer(serial_number=serial_number, surveyor_id=surveyor_id))
        db.commit()
        return JSONResponse({"message": "Computer created"})
    return JSONResponse({"message": "Computer already exists"})

@app.post("/api/create/license")
def create_license(
    request: Request,
    computer_id: int = Form(...),
    paid: bool = Form(...),
    expire_date: str = Form(...),
    db: Session = Depends(get_db)
):
    login_required(request)
    db.add(models.License(computer_id=computer_id, paid=paid, expire_date=expire_date))
    db.commit()
    return JSONResponse({"message": "License created"})

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
                        "email": company.email,
                        "surveyor_name": surveyor.name,
                        "computer_serial_number": computer.serial_number,
                        "paid": license.paid,
                        "expire_date": license.expire_date.isoformat(),
                        "status": license.paid and license.expire_date > date.today(),
                        "license_id": license.id
                    })
    return JSONResponse(data)

@app.post("/api/delete/{license_id}")
def delete_entry(license_id: int, request: Request, db: Session = Depends(get_db)):
    login_required(request)
    license = db.query(models.License).filter_by(id=license_id).first()
    if license:
        db.delete(license)
        db.commit()
        return JSONResponse({"message": "Deleted license"})
    raise HTTPException(status_code=404, detail="License not found")