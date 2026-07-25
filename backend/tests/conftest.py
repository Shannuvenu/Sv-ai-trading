from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.main import app

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def registered_user():
    from app.modules.users.models import User
    db = TestingSessionLocal()
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("Password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def auth_headers(registered_user):
    token = create_access_token({"sub": str(registered_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_user():
    from app.modules.users.models import User
    db = TestingSessionLocal()
    user = User(
        email="other@example.com",
        username="otheruser",
        hashed_password=hash_password("Password456"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def second_auth_headers(second_user):
    token = create_access_token({"sub": str(second_user.id)})
    return {"Authorization": f"Bearer {token}"}
