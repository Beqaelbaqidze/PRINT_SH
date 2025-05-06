from binascii import Error
from fastapi import FastAPI, HTTPException, Form, Request
from pydantic import BaseModel
import mysql.connector
from typing import Optional
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import date
from decimal import Decimal
from fastapi import Body
import psycopg2
import psycopg2.extras

app = FastAPI()

# Static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MySQL connection
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        user="beqa",
        password="1524Elbaqa",
        database="licenses",
        charset='utf8mb4',
        collation='utf8mb4_general_ci'
    )


@app.on_event("startup")
def create_tables_if_not_exist():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Create companies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL,
                company_id_number VARCHAR(50) UNIQUE NOT NULL,
                mobile_number VARCHAR(20),
                email VARCHAR(255),
                director VARCHAR(255),
                measurer VARCHAR(255)
            ) ENGINE=InnoDB;
        """)

        # Create computers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS computers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                machine_serial_number VARCHAR(100) UNIQUE NOT NULL,
                measurer VARCHAR(255),
                company_id INT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)

        # Create licenses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                computer_id INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                paid BOOLEAN DEFAULT FALSE,
                expire_date DATE NOT NULL,
                FOREIGN KEY (computer_id) REFERENCES computers(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)

        conn.commit()
        print("✅ Tables checked/created successfully.")
    except Error as e:
        print("❌ Error creating tables:", e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# Login route
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})



@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin1234":
        return {"success": True, "message": "Login successful"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Create
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

@app.post("/all/create")
def all_create(data: AllTablesCreate):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM companies WHERE company_id_number = %s", (data.company_id_number,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Company ID already exists.")
        cursor.execute("SELECT id FROM computers WHERE machine_serial_number = %s", (data.machine_serial_number,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Machine serial already exists.")
        cursor.execute("""
            INSERT INTO companies (company_name, company_id_number, mobile_number, email, director, measurer)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data.company_name, data.company_id_number, data.mobile_number,
            data.email, data.director, data.measurer_company
        ))
        company_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO computers (machine_serial_number, measurer, company_id)
            VALUES (%s, %s, %s)
        """, (
            data.machine_serial_number, data.measurer_computer, company_id
        ))
        computer_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO licenses (computer_id, price, paid, expire_date)
            VALUES (%s, %s, %s, %s)
        """, (
            computer_id, data.price, data.paid, data.expire_date
        ))
        conn.commit()
        return {"message": "Inserted successfully."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# Update
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

@app.post("/all/update")
def all_update(data: AllTablesUpdate):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE companies SET company_name=%s, mobile_number=%s, email=%s, director=%s, measurer=%s
            WHERE id=%s
        """, (
            data.company_name, data.mobile_number, data.email,
            data.director, data.measurer_company, data.company_id
        ))
        cursor.execute("""
            UPDATE computers SET machine_serial_number=%s, measurer=%s
            WHERE id=%s
        """, (
            data.machine_serial_number, data.measurer_computer, data.computer_id
        ))
        cursor.execute("""
            UPDATE licenses SET price=%s, paid=%s, expire_date=%s
            WHERE id=%s
        """, (
            data.price, data.paid, data.expire_date, data.license_id
        ))
        conn.commit()
        return {"message": "Updated successfully."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# Delete
@app.delete("/all/delete/{company_id}")
def all_delete(company_id: int):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM companies WHERE id = %s", (company_id,))
        conn.commit()
        return {"message": "Deleted successfully."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# List
@app.get("/all/list")
def get_all_data():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
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
                l.expire_date,
                SUM(CASE WHEN l.paid = 0 AND l.expire_date >= CURDATE() THEN false ELSE true END) AS status       
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
        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


from fastapi import Body

@app.post("/all/filter")
def filter_data(filter: dict = Body(...)):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

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
                l.expire_date,
                SUM(CASE WHEN l.paid = 0 AND l.expire_date >= CURDATE() THEN false ELSE true END) AS status
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
                    query += f" AND {db_field} LIKE %s"
                    params.append(f"%{filter[key]}%")

        cursor.execute(query, params)
        results = cursor.fetchall()

        for row in results:
            for key, value in row.items():
                if isinstance(value, Decimal):
                    row[key] = float(value)
                elif isinstance(value, date):
                    row[key] = value.isoformat()

        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.post("/api/verify_license")
def verify_license(
    company_name: str = Form(...),
    email: str = Form(...),
    machine_name: str = Form(...)
):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

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
              AND c.email = %s
              AND cp.machine_serial_number = %s
        """, (company_name, email, machine_name))

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
        else:
            return {"valid": False}
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()