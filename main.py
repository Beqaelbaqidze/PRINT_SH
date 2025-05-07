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
                        "company_id": company.id,
                        "company_name": company.company_name,
                        "company_code": company.company_id,
                        "email": company.email,
                        "mobile_number": company.mobile_number,
                        "director": company.director,
                        "surveyor_id": surveyor.id,
                        "surveyor_name": surveyor.name,
                        "computer_id": computer.id,
                        "computer_serial_number": computer.serial_number,
                        "license_id": license.id,
                        "paid": license.paid,
                        "expire_date": license.expire_date,
                        "status": license.paid and license.expire_date > date.today()
                    })

    return JSONResponse(data)

# Create, Update, Delete Endpoints
@app.post("/api/create")
def create_entry(
    request: Request,
    company_name: str = Form(...),
    company_id: str = Form(...),
    email: str = Form(...),
    mobile_number: str = Form(...),
    director: str = Form(...),
    surveyor_name: str = Form(...),
    computer_serial: str = Form(...),
    paid: bool = Form(...),
    expire_date: str = Form(...),
    db: Session = Depends(get_db)
):
    login_required(request)

    company = db.query(models.Company).filter_by(company_id=company_id).first()
    if not company:
        company = models.Company(
            company_name=company_name,
            company_id=company_id,
            email=email,
            mobile_number=mobile_number,
            director=director
        )
        db.add(company)
        db.commit()
        db.refresh(company)

    surveyor = db.query(models.Surveyor).filter_by(name=surveyor_name).first()
    if not surveyor:
        surveyor = models.Surveyor(name=surveyor_name)
        db.add(surveyor)
        db.commit()
        db.refresh(surveyor)

    if company not in surveyor.companies:
        surveyor.companies.append(company)
        db.commit()

    computer = db.query(models.Computer).filter_by(serial_number=computer_serial).first()
    if not computer:
        computer = models.Computer(serial_number=computer_serial, surveyor_id=surveyor.id)
        db.add(computer)
        db.commit()
        db.refresh(computer)

    license = models.License(computer_id=computer.id, paid=paid, expire_date=expire_date)
    db.add(license)
    db.commit()

    return JSONResponse({"message": "Created successfully"})

@app.post("/api/delete/{license_id}")
def delete_entry(license_id: int, request: Request, db: Session = Depends(get_db)):
    login_required(request)
    license = db.query(models.License).filter_by(id=license_id).first()
    if license:
        db.delete(license)
        db.commit()
        return JSONResponse({"message": "Deleted license"})
    raise HTTPException(status_code=404, detail="License not found")

@app.post("/api/update/{license_id}")
def update_entry(
    license_id: int,
    request: Request,
    paid: bool = Form(...),
    expire_date: str = Form(...),
    db: Session = Depends(get_db)
):
    login_required(request)
    license = db.query(models.License).filter_by(id=license_id).first()
    if license:
        license.paid = paid
        license.expire_date = expire_date
        db.commit()
        return JSONResponse({"message": "Updated license"})
    raise HTTPException(status_code=404, detail="License not found")

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
