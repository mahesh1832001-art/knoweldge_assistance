
from sqlalchemy import text
from app.db.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT VERSION()"))
        print("MySQL connected successfully!")
        print("MySQL version:", result.scalar())
except Exception as error:
    print("MySQL connection failed:", error)
