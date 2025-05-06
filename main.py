from urllib import request
from fastapi import FastAPI, HTTPException, Form, Request, Body
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
import psycopg2
import psycopg2.extras
from starlette.middleware.sessions import SessionMiddleware


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your_super_secret_key")



# Static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS for frontend JS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL connection
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        user="beqa",
        password="1524Elbaqa",
        database="licenses"
    )

# === Routes ===

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if not request.session.get("logged_in"):  # If the user is not logged in, redirect to the login page
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request})  # Show the dashboard if logged in




@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Hardcoded credentials for example; you should use a database or hashed passwords for production
    if username == "admin" and password == "admin1234":
        request.session["logged_in"] = True  # Store the login status in the session
        return RedirectResponse("/dashboard", status_code=302)  # Redirect to dashboard after successful login
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()  # Clear the session (i.e., log the user out)
    return RedirectResponse("/login", status_code=302)  # Redirect to login page after logout



# === Models ===

class AllTablesCreate(BaseModel):
    company_name: str
    company_id_number: str
    mobile_number: str
    email: str
    director: str
    measurer_company: str
    machine_serial_number: str
    measurer_computer: str
    price: float
    paid: bool
    expire_date: str

class AllTablesUpdate(BaseModel):
    company_id: int
    company_name: str
    mobile_number: str
    email: str
    director: str
    measurer_company: str
    computer_id: int
    machine_serial_number: str
    measurer_computer: str
    license_id: int
    price: float
    paid: bool
    expire_date: str

# === CRUD ===

@app.post("/all/create")
def all_create(data: AllTablesCreate):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check existing
        cursor.execute("SELECT id FROM companies WHERE company_id_number = %s", (data.company_id_number,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Company ID already exists.")
        cursor.execute("SELECT id FROM computers WHERE machine_serial_number = %s", (data.machine_serial_number,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Machine serial already exists.")

        # Insert company
        cursor.execute("""
            INSERT INTO companies (company_name, company_id_number, mobile_number, email, director, measurer)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (data.company_name, data.company_id_number, data.mobile_number, data.email, data.director, data.measurer_company))
        company_id = cursor.fetchone()['id']

        # Insert computer
        cursor.execute("""
            INSERT INTO computers (machine_serial_number, measurer, company_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (data.machine_serial_number, data.measurer_computer, company_id))
        computer_id = cursor.fetchone()['id']

        # Insert license
        cursor.execute("""
            INSERT INTO licenses (computer_id, price, paid, expire_date)
            VALUES (%s, %s, %s, %s)
        """, (computer_id, data.price, data.paid, data.expire_date))

        conn.commit()
        return {"message": "Inserted successfully."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.post("/all/update")
def all_update(data: AllTablesUpdate):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            UPDATE companies SET company_name=%s, mobile_number=%s, email=%s, director=%s, measurer=%s
            WHERE id=%s
        """, (data.company_name, data.mobile_number, data.email, data.director, data.measurer_company, data.company_id))

        cursor.execute("""
            UPDATE computers SET machine_serial_number=%s, measurer=%s
            WHERE id=%s
        """, (data.machine_serial_number, data.measurer_computer, data.computer_id))

        cursor.execute("""
            UPDATE licenses SET price=%s, paid=%s, expire_date=%s
            WHERE id=%s
        """, (data.price, data.paid, data.expire_date, data.license_id))

        conn.commit()
        return {"message": "Updated successfully."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.delete("/all/delete/{company_id}")
def all_delete(company_id: int):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("DELETE FROM companies WHERE id = %s", (company_id,))
        conn.commit()
        return {"message": "Deleted successfully."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.get("/all/list")
def get_all_data():
    if not request.session.get("logged_in"):  # Check if the user is logged in
        return RedirectResponse("/login", status_code=302)  # Redirect if not logged in
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT
                c.id AS company_id,
                c.company_name,
                c.company_id_number,
                c.mobile_number,
                c.email,
                c.director,
                c.measurer AS measurer_company,
                cp.id AS computer_id,
                cp.machine_serial_number,
                cp.measurer AS measurer_computer,
                l.id AS license_id,
                l.price,
                l.paid,
                l.expire_date
            FROM companies c
            JOIN computers cp ON cp.company_id = c.id
            JOIN licenses l ON l.computer_id = cp.id
        """)
        results = cursor.fetchall()
        for row in results:
            for key, value in row.items():
                if isinstance(value, Decimal):
                    row[key] = float(value)
                elif isinstance(value, date):
                    row[key] = value.isoformat()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.post("/all/filter")
def filter_data(filter: dict = Body(...)):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT
                c.id AS company_id,
                c.company_name,
                c.company_id_number,
                c.mobile_number,
                c.email,
                c.director,
                c.measurer AS measurer_company,
                cp.id AS computer_id,
                cp.machine_serial_number,
                cp.measurer AS measurer_computer,
                l.id AS license_id,
                l.price,
                l.paid,
                l.expire_date
            FROM companies c
            JOIN computers cp ON cp.company_id = c.id
            JOIN licenses l ON l.computer_id = cp.id
            WHERE 1=1
        """
        params = []
        field_mapping = {
            "company_name": "c.company_name",
            "company_id_number": "c.company_id_number",
            "mobile_number": "c.mobile_number",
            "email": "c.email",
            "director": "c.director",
            "measurer_company": "c.measurer",
            "machine_serial_number": "cp.machine_serial_number",
            "measurer_computer": "cp.measurer",
            "price": "l.price",
            "paid": "l.paid",
            "expire_date": "l.expire_date"
        }

        for key, db_field in field_mapping.items():
            if key in filter and filter[key] not in [None, ""]:
                if key in ["price", "paid"]:
                    query += f" AND {db_field} = %s"
                    params.append(filter[key])
                elif key == "expire_date":
                    query += f" AND DATE({db_field}) = %s"
                    params.append(filter[key])
                else:
                    query += f" AND {db_field} ILIKE %s"
                    params.append(f"%{filter[key]}%")

        cursor.execute(query, params)
        results = cursor.fetchall()
        for row in results:
            for key, value in row.items():
                if isinstance(value, Decimal):
                    row[key] = float(value)
                elif isinstance(value, date):
                    row[key] = value.isoformat()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.post("/api/verify_license")
def verify_license(
    company_name: str = Form(...),
    measurer: str = Form(...),
    machine_name: str = Form(...),
    company_id: str = Form(...)
):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT 
                c.id AS company_id,
                c.company_name,
                c.measurer,
                l.paid,
                l.expire_date
            FROM companies c
            JOIN computers cp ON cp.company_id = c.id
            JOIN licenses l ON l.computer_id = cp.id
            WHERE c.company_name = %s
              AND cp.measurer = %s
              AND cp.machine_serial_number = %s
              AND c.company_id_number = %s
        """, (company_name, measurer, machine_name, company_id))

        row = cursor.fetchone()
        if row:
            today = date.today()
            is_paid = row["paid"] == 1
            not_expired = row["expire_date"] >= today
            return {
                "valid": is_paid and not_expired,
                "company_name": row["company_name"],
                "company_id": row["company_id"],
                "measurer": row["measurer"],
                "paid": bool(row["paid"]),
                "expire_date": str(row["expire_date"])
            }
        return {"valid": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
