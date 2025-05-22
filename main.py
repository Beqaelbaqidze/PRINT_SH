from fastapi import FastAPI, HTTPException, Query, Request, Form
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

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Simple hardcoded credentials
    if username == "Printsh" and password == "Printsh1524":
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid credentials"
    })


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if request.session.get("user") != "Printsh":
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/records/filter")
def filter_records(
    search: str = Query("")
):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    wildcard = f"%{search.lower()}%"
    cursor.execute("""
        SELECT lr.id, c.name AS company, c.director, o.name AS operator,
                cmp.serial_number, l.paid, l.expire_date, l.edit_pdf,
                lr.license_status, lr.status
        FROM license_records lr
        LEFT JOIN companies c ON lr.company_fk = c.id
        LEFT JOIN operators o ON lr.operator_fk = o.id
        LEFT JOIN computers cmp ON lr.computer_fk = cmp.id
        LEFT JOIN licenses l ON lr.license_fk = l.id
        WHERE LOWER(c.name) LIKE %s
           OR LOWER(c.director) LIKE %s
           OR LOWER(o.name) LIKE %s
           OR LOWER(cmp.serial_number) LIKE %s
           OR LOWER(lr.status) LIKE %s
           OR LOWER(lr.license_status) LIKE %s
        ORDER BY lr.id
    """, [wildcard]*6)

    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

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
        SELECT lr.id, c.name  AS company, c.director AS director, o.name AS operator, cmp.serial_number, l.paid, l.expire_date, lr.license_status, lr.status, l.edit_pdf
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
    status: str = Body(...),
    edit_pdf: bool = Body(...)
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
        expire_date = %s,
        edit_pdf = %s
    WHERE id = (
        SELECT license_fk FROM license_records WHERE id = %s
    )
""", (paid, expire_date, edit_pdf, record_id))


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

from fastapi import Form

def create_logs_table_if_not_exists(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                endpoint TEXT,
                method TEXT,
                message TEXT,
                error_detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


@app.post("/api/verify_license")
def verify_license(
    company_name: str = Form(...),
    company_id: str = Form(...),
    measurer: str = Form(...),
    machine_name: str = Form(...)
):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        create_logs_table_if_not_exists(conn)  # Ensure logs table exists
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT lr.id, c.name as company_name, c.code as company_id, 
                o.name as measurer, cmp.serial_number as machine_name,
                l.edit_pdf
            FROM license_records lr
            JOIN companies c ON lr.company_fk = c.id
            JOIN operators o ON lr.operator_fk = o.id
            JOIN computers cmp ON lr.computer_fk = cmp.id
            JOIN licenses l ON lr.license_fk = l.id
            WHERE LOWER(TRIM(c.name)) = LOWER(TRIM(%s))
              AND LOWER(TRIM(c.code)) = LOWER(TRIM(%s))
              AND LOWER(TRIM(o.name)) = LOWER(TRIM(%s))
              AND LOWER(TRIM(cmp.serial_number)) = LOWER(TRIM(%s))
              AND lr.license_status = 'active'
              AND lr.status = 'enabled'
        """, (company_name, company_id, measurer, machine_name))

        result = cursor.fetchone()
        if result:
            return {
                "valid": True,
                "company_name": result["company_name"],
                "company_id": result["company_id"],
                "measurer": result["measurer"],
                "machine_name": result["machine_name"],
                "edit_pdf": result["edit_pdf"]
            }
        else:
            return {
                "valid": False,
                "reason": "No active license found matching the provided details."
            }

    except Exception as e:
        try:
            if conn:
                create_logs_table_if_not_exists(conn)  # Ensure table exists again if reconnecting
                with conn.cursor() as log_cursor:
                    log_cursor.execute("""
                        INSERT INTO logs (endpoint, method, message, error_detail)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        "/api/verify_license", "POST",
                        "License verification failed.",
                        str(e)
                    ))
                    conn.commit()
        except Exception as log_error:
            print("⚠️ Logging failed:", log_error)

        raise HTTPException(status_code=500, detail="Internal Server Error. Logged.")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

from fastapi.responses import PlainTextResponse

@app.get("/api/operators/by-machine", response_class=PlainTextResponse)
def get_operators_by_machine(machine_name: str = Query(...)):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT o.name
            FROM license_records lr
            JOIN operators o ON lr.operator_fk = o.id
            JOIN computers cmp ON lr.computer_fk = cmp.id
            WHERE LOWER(TRIM(cmp.serial_number)) = LOWER(TRIM(%s))
              AND lr.license_status = 'active'
              AND lr.status = 'enabled'
        """, (machine_name,))

        rows = cursor.fetchall()
        # Return as plain text (one per line)
        return "\n".join([row[0] for row in rows])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if conn:
            cursor.close()
            conn.close()

@app.get("/api/license/autofill", response_class=PlainTextResponse)
def autofill_from_machine(machine_name: str = Query(...)):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT o.name AS measurer,
                   c.name AS company_name,
                   c.code AS company_id,
                   c.mobile AS phone,
                   c.email
            FROM license_records lr
            JOIN operators o ON lr.operator_fk = o.id
            JOIN companies c ON lr.company_fk = c.id
            JOIN computers cmp ON lr.computer_fk = cmp.id
            WHERE LOWER(TRIM(cmp.serial_number)) = LOWER(TRIM(%s))
              AND lr.license_status = 'active'
              AND lr.status = 'enabled'
            LIMIT 1
        """, (machine_name,))

        row = cursor.fetchone()
        if not row:
            return "❌ No active license found."

        # Return plain text for easy parsing in ArcMap
        result = f"{row['company_name']}\n{row['company_id']}\n{row['measurer']}\n{row['phone']}\n{row['email']}"
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if conn:
            cursor.close()
            conn.close()


@app.get("/api/logs")
def get_logs():
    conn = None
    try:
        conn = get_connection()
        create_logs_table_if_not_exists(conn)  # Make sure table exists
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT * FROM logs ORDER BY created_at DESC")
        logs = cursor.fetchall()
        return {"logs": logs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")

    finally:
        if conn:
            cursor.close()
            conn.close()
