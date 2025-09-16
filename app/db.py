from sqlmodel import SQLModel, create_engine, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as s:
        yield s

def init_db():
    SQLModel.metadata.create_all(engine)
