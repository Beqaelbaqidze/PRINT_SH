from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from pydantic import BaseModel
from datetime import date
from fastapi import Body
from starlette.middleware.sessions import SessionMiddleware
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super_secret_key_123")



# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jinja2 templates (optional, for HTML dashboard)
templates = Jinja2Templates(directory="templates")

# PostgreSQL Connection
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="licenses",
        user="beqa",
        password="1524Elbaqa",
        port=5432
    )

from fastapi.responses import RedirectResponse

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Simple hardcoded credentials
    if username == "admin" and password == "admin123":
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid credentials"
    })


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if request.session.get("user") != "admin":
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ---------- SELECT ALL ----------
@app.get("/api/companies")
def get_companies():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM companies ORDER BY id")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

@app.get("/api/operators")
def get_operators():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM operators ORDER BY id")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

@app.get("/api/computers")
def get_computers():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM computers ORDER BY id")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

@app.get("/api/licenses")
def get_licenses():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM licenses ORDER BY id")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

@app.get("/api/records")
def get_records():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT lr.id, c.name  AS company, o.name AS operator, cmp.serial_number, l.paid, l.expire_date, lr.license_status, lr.status
        FROM license_records lr
        LEFT JOIN companies c ON lr.company_fk = c.id
        LEFT JOIN operators o ON lr.operator_fk = o.id
        LEFT JOIN computers cmp ON lr.computer_fk = cmp.id
        LEFT JOIN licenses l ON lr.license_fk = l.id
        ORDER BY lr.id
    """)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


class LicenseRegistration(BaseModel):
    company_name: str
    company_code: str
    email: str
    mobile: str
    director: str
    operator_name: str
    serial_number: str
    paid: bool
    expire_date: date


# --- Registration Route ---
@app.post("/api/register")
def register_license(data: LicenseRegistration):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        conn.autocommit = False

        # --- Calculate status automatically ---
        today = date.today()
        license_status = "active" if data.paid and data.expire_date > today else "inactive"
        status = "enabled" if license_status == "active" else "disabled"

        # --- Check or Insert Company ---
        cursor.execute("SELECT id FROM companies WHERE name = %s OR code = %s", (data.company_name, data.company_code))
        result = cursor.fetchone()
        if result:
            company_id = result[0]
        else:
            cursor.execute("""
                INSERT INTO companies (name, code, email, mobile, director)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (data.company_name, data.company_code, data.email, data.mobile, data.director))
            company_id = cursor.fetchone()[0]

        # --- Check or Insert Operator ---
        cursor.execute("SELECT id FROM operators WHERE name = %s", (data.operator_name,))
        result = cursor.fetchone()
        if result:
            operator_id = result[0]
        else:
            cursor.execute("""
                INSERT INTO operators (name)
                VALUES (%s) RETURNING id
            """, (data.operator_name,))
            operator_id = cursor.fetchone()[0]

        # --- Check or Insert Computer ---
        cursor.execute("SELECT id FROM computers WHERE serial_number = %s", (data.serial_number,))
        result = cursor.fetchone()
        if result:
            computer_id = result[0]
        else:
            cursor.execute("""
                INSERT INTO computers (serial_number)
                VALUES (%s) RETURNING id
            """, (data.serial_number,))
            computer_id = cursor.fetchone()[0]

        # --- Always Insert License (since it's unique per record) ---
        cursor.execute("""
            INSERT INTO licenses (paid, expire_date)
            VALUES (%s, %s) RETURNING id
        """, (data.paid, data.expire_date))
        license_id = cursor.fetchone()[0]

        # --- Insert into license_records ---
        cursor.execute("""
            INSERT INTO license_records (company_fk, operator_fk, computer_fk, license_fk, license_status, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (company_id, operator_id, computer_id, license_id, license_status, status))

        conn.commit()
        return {"message": "Registration successful."}

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if conn:
            cursor.close()
            conn.close()


@app.post("/api/update-record")
def update_record(
    record_id: int = Body(...),
    paid: bool = Body(...),
    expire_date: date = Body(...),
    status: str = Body(...)
):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Auto-set paid = false if expired
        today = date.today()
        if expire_date < today:
            paid = False

        # Update license table
        cursor.execute("""
            UPDATE licenses
            SET paid = %s,
                expire_date = %s
            WHERE id = (
                SELECT license_fk FROM license_records WHERE id = %s
            )
        """, (paid, expire_date, record_id))

        # Update license_records status
        # Final license status logic
        if status == "disabled":
            license_status = "inactive"
        elif paid and expire_date >= today:
            license_status = "active"
        else:
            license_status = "inactive"

        cursor.execute("""
            UPDATE license_records
            SET license_status = %s,
                status = %s
            WHERE id = %s
        """, (
            license_status,
            status,
            record_id
        ))


        conn.commit()
        return {"message": "Updated successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            cursor.close()
            conn.close()