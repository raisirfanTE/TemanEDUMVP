import os
from contextlib import contextmanager

import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base

load_dotenv()


@st.cache_resource
def get_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required. Example: postgresql+psycopg2://user:pass@localhost:5432/temanedu")
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
