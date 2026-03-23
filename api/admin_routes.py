from fastapi import APIRouter, HTTPException
from api.db import get_db_conn

router = APIRouter()

@router.get("/admin/users")
def list_users():

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT email,role,created_date
        FROM usersdata
        ORDER BY created_date DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows