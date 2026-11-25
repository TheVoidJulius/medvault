import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.seed_data import seed_database_if_empty
from app.db.session import Base, SessionLocal, engine


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_database_if_empty(db)
        print(f"Database seed status: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
