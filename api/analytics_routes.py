from fastapi import APIRouter
from api.db import get_db_conn
from psycopg2.extras import RealDictCursor

router = APIRouter()

@router.get("/analytics/admin/overview")
def overview():

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT COUNT(*) total_sent
        FROM email_events
    """)

    data = cur.fetchone()

    cur.close()
    conn.close()

    return data