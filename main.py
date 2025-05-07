from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from pydantic import BaseModel
from datetime import date

app = FastAPI()

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


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
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
        SELECT lr.id, * AS company, o.name AS operator, cmp.serial_number, l.paid, l.expire_date, lr.license_status, lr.status
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

        # Insert into companies
        cursor.execute("""
            INSERT INTO companies (name, code, email, mobile, director)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (data.company_name, data.company_code, data.email, data.mobile, data.director))
        company_id = cursor.fetchone()[0]

        # Insert into operators
        cursor.execute("""
            INSERT INTO operators (name)
            VALUES (%s) RETURNING id
        """, (data.operator_name,))
        operator_id = cursor.fetchone()[0]

        # Insert into computers
        cursor.execute("""
            INSERT INTO computers (serial_number)
            VALUES (%s) RETURNING id
        """, (data.serial_number,))
        computer_id = cursor.fetchone()[0]

        # Insert into licenses
        cursor.execute("""
            INSERT INTO licenses (paid, expire_date)
            VALUES (%s, %s) RETURNING id
        """, (data.paid, data.expire_date))
        license_id = cursor.fetchone()[0]

        # Insert into main table with calculated status
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