from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt

# Importing models from models.py
from .models import Role, User, Request, Log
from .database import SessionLocal

# Constants
DATABASE_URL = (
    "postgresql://admin_user:admin_password@localhost:5432/fastapi_project_db"
)
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# FastAPI app instance
app = FastAPI()

# OAuth2 for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Utility functions
def authenticate_user(db, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if (
        user and user.hashed_password == password
    ):  # Replace with secure hashing
        return user
    return None


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Script to create admin user on startup
@app.on_event("startup")
async def create_admin_user():
    db = SessionLocal()
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    if not admin_role:
        # Create Admin role if it doesn't exist
        admin_role = Role(name="Admin")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

    # Check if admin user exists
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        # Create admin user if it doesn't exist
        hashed_password = (
            "adminpassword"  # Replace with a secure hash for production
        )
        admin_user = User(
            username="admin",
            hashed_password=hashed_password,
            role_id=admin_role.id,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    db.close()


# Routes
@app.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/requests", dependencies=[Depends(oauth2_scheme)])
async def get_requests(db: Session = Depends(get_db)):
    # Implement role-based filtering
    return {"message": "Role-based access control here"}


@app.post("/requests", dependencies=[Depends(oauth2_scheme)])
async def create_request(
    bottoken: str,
    chatid: str,
    message: str,
    db: Session = Depends(get_db),
):
    # Save request to the database and send to Telegram
    return {"message": "Request received and processed"}
