import os
from contextlib import contextmanager

import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base

load_dotenv()


def _database_url_from_secrets() -> str | None:
    try:
        if "DATABASE_URL" in st.secrets:
            value = str(st.secrets["DATABASE_URL"]).strip()
            if value:
                return value
        if "database" in st.secrets and "url" in st.secrets["database"]:
            value = str(st.secrets["database"]["url"]).strip()
            if value:
                return value
    except Exception:
        return None
    return None


@st.cache_resource
def get_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL") or _database_url_from_secrets()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required. Set env var or Streamlit secret "
            "'DATABASE_URL' (example: postgresql+psycopg2://user:pass@host:5432/db?sslmode=require)."
        )
    return create_engine(database_url, pool_pre_ping=True)


@st.cache_resource
def get_session_factory() -> sessionmaker:
    # Keep loaded attributes accessible after commit/context exit for Streamlit flows
    # that pass ORM rows into pure-Python logic outside the DB session scope.
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def db_session() -> Session:
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_schema() -> None:
    Base.metadata.create_all(bind=get_engine())
