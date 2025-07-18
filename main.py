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

from typing import Optional


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

@app.get("/tutorial", response_class=HTMLResponse)
def tutorial_page(request: Request):
    return templates.TemplateResponse("tutorial.html", {"request": request})

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
        SELECT lr.id, c.name AS company, c.director, o.name AS operator, c.mobile AS phone,
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
        SELECT lr.id, c.name  AS company, c.director AS director, o.name AS operator, c.mobile AS phone, cmp.serial_number, l.paid, l.expire_date, lr.license_status, lr.status, l.edit_pdf
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
    address: Optional[str] = None
    operator_name: str
    serial_number: str
    mac_address: Optional[str] = None
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
            # ✅ Optional: update address, email, phone, director if provided
            cursor.execute("""
                UPDATE companies
                SET email = %s, mobile = %s, director = %s, address = %s
                WHERE id = %s
            """, (data.email, data.mobile, data.director, data.address, company_id))
        else:
            cursor.execute("""
                INSERT INTO companies (name, code, email, mobile, director, address)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (data.company_name, data.company_code, data.email, data.mobile, data.director, data.address))
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
        # Check or Insert Computer
        # Try to get existing computer by serial number
        cursor.execute("SELECT id FROM computers WHERE serial_number = %s", (data.serial_number,))
        result = cursor.fetchone()

        if result:
            computer_id = result[0]
            # Update MAC address if it's different
            cursor.execute("""
                UPDATE computers
                SET mac_address = %s
                WHERE id = %s
            """, (data.mac_address, computer_id))
        else:
            cursor.execute("""
                INSERT INTO computers (serial_number, mac_address)
                VALUES (%s, %s) RETURNING id
            """, (data.serial_number, data.mac_address))
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

def log_request(conn, message: str, error_detail: str = None, company_name: str = None, machine_name: str = None, request_info: str = None):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO logs (endpoint, method, message, error_detail, company_name, machine_name, request_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                "/api/verify_license", "POST", message, error_detail, company_name, machine_name, request_info
            ))
            conn.commit()
    except Exception as e:
        print("⚠️ Logging failed:", e)




from fastapi import Request, Form
import socket

@app.post("/api/verify_license")
def verify_license(
    request: Request,
    company_name: str = Form(...),
    company_id: str = Form(...),
    measurer: str = Form(...),
    machine_name: str = Form(...),
    mac_address: Optional[str] = Form(None),
    address: Optional[str] = Form(None)
):
    conn = None
    cursor = None

    # Extract client IP
    client_ip = request.client.host
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    request_info = f"company_name={company_name}, company_id={company_id}, measurer={measurer}, machine_name={machine_name}, mac_address={mac_address}, address={address}, ip={client_ip}"

    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Base SQL and parameters
        sql = """
            SELECT lr.id, c.name as company_name, c.code as company_id, 
                   o.name as measurer, cmp.serial_number as machine_name,
                   c.address, l.edit_pdf
            FROM license_records lr
            JOIN companies c ON lr.company_fk = c.id
            JOIN operators o ON lr.operator_fk = o.id
            JOIN computers cmp ON lr.computer_fk = cmp.id
            JOIN licenses l ON lr.license_fk = l.id
            WHERE LOWER(TRIM(c.name)) = LOWER(TRIM(%s))
              AND LOWER(TRIM(c.code)) = LOWER(TRIM(%s))
              AND LOWER(TRIM(o.name)) = LOWER(TRIM(%s))
              AND LOWER(TRIM(cmp.serial_number)) = LOWER(TRIM(%s))
        """
        params = [company_name, company_id, measurer, machine_name]

        # Optional MAC address
        if mac_address:
            sql += " AND LOWER(TRIM(cmp.mac_address)) = LOWER(TRIM(%s))"
            params.append(mac_address)

        # Optional address
        if address:
            sql += " AND LOWER(TRIM(c.address)) = LOWER(TRIM(%s))"
            params.append(address)

        sql += " AND lr.license_status = 'active' AND lr.status = 'enabled'"

        # Execute query
        cursor.execute(sql, params)
        result = cursor.fetchone()

        if result:
            log_request(conn, "✅ License verified", None, result["company_name"], result["machine_name"], request_info)
            return {
                "valid": True,
                "company_name": result["company_name"],
                "company_id": result["company_id"],
                "measurer": result["measurer"],
                "machine_name": result["machine_name"],
                "edit_pdf": result["edit_pdf"],
                "address": result.get("address"),
                "ip_address": client_ip
            }
        else:
            log_request(conn, "❌ License verification failed", "No active license matched", company_name, machine_name, request_info)
            return {
                "valid": False,
                "reason": "No active license found matching the provided details.",
                "ip_address": client_ip
            }

    except Exception as e:
        log_request(conn, "❌ License verification exception", str(e), company_name, machine_name, request_info)
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
                   c.email,
                    c.address
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
        result = f"{row['company_name']}\n{row['company_id']}\n{row['measurer']}\n{row['phone']}\n{row['email']}\n{row['address']}"
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
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id, endpoint, method, message, error_detail, company_name, machine_name, request_info, created_at
            FROM logs
            ORDER BY created_at DESC
        """)
        logs = cursor.fetchall()
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

editable_fields = {
    "companies": ["name", "code", "email", "mobile", "director", "address"],
    "operators": ["name"],
    "computers": ["serial_number", "mac_address"]
}
from fastapi import Path

@app.get("/api/editable/{table}")
def get_table_rows(table: str = Path(...)):
    if table not in editable_fields:
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SELECT id, {', '.join(editable_fields[table])} FROM {table} ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"fields": editable_fields[table], "rows": rows}

@app.post("/api/editable/{table}/update")
def update_table_row(
    table: str,
    id: int = Body(...),
    data: dict = Body(...)
):
    if table not in editable_fields:
        raise HTTPException(status_code=400, detail="Invalid table name")

    set_clause = ", ".join([f"{k} = %s" for k in data if k in editable_fields[table]])
    values = [data[k] for k in data if k in editable_fields[table]]

    if not set_clause:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE {table} SET {set_clause} WHERE id = %s", values + [id])
    conn.commit()
    cur.close()
    conn.close()
    return {"message": f"{table.capitalize()} updated"}

@app.post("/api/editable/{table}/insert")
def insert_table_row(
    table: str,
    data: dict = Body(...)
):
    if table not in editable_fields:
        raise HTTPException(status_code=400, detail="Invalid table name")

    fields = [k for k in data if k in editable_fields[table]]
    if not fields:
        raise HTTPException(status_code=400, detail="No valid fields to insert")

    placeholders = ", ".join(["%s"] * len(fields))
    field_names = ", ".join(fields)
    values = [data[f] for f in fields]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {table} ({field_names}) VALUES ({placeholders})")
    conn.commit()
    cur.close()
    conn.close()
    return {"message": f"{table.capitalize()} row added"}

@app.delete("/api/editable/{table}/{id}")
def delete_table_row(table: str, id: int = Path(...)):
    if table not in editable_fields:
        raise HTTPException(status_code=400, detail="Invalid table name")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"message": f"{table.capitalize()} entry deleted"}
