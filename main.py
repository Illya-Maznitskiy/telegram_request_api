from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

from models import Role, User, Request
from database import SessionLocal

# Constants
SECRET_KEY = "83daa0256a2289b0fb23693bf1f6034d44396675749244721a2b20e896e11662"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# FastAPI app instance
app = FastAPI()

# OAuth2 for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password):
    return pwd_context.hash(plain_password)


def authenticate_user(db, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.hashed_password):
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


# Create user in the database function
def create_user_in_db(
    db: Session, username: str, password: str, role_name: str
):
    hashed_password = hash_password(password)
    user_role = db.query(Role).filter(Role.name == role_name).first()
    if not user_role:
        user_role = Role(name=role_name)
        db.add(user_role)
        db.commit()
        db.refresh(user_role)

    new_user = User(
        username=username,
        hashed_password=hashed_password,
        role_id=user_role.id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# Pydantic models
class UserCreate(BaseModel):
    username: str
    password: str
    role_name: str


class UserRead(BaseModel):
    username: str
    role_id: int


class Token(BaseModel):
    access_token: str
    token_type: str


class RequestCreate(BaseModel):
    bottoken: str
    chatid: str
    message: str


# API Endpoints
@app.post("/token", response_model=Token)
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


@app.post("/users", response_model=UserRead)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    new_user = create_user_in_db(
        db, user.username, user.password, role_name=user.role_name
    )
    return new_user


@app.get("/requests", dependencies=[Depends(oauth2_scheme)])
async def get_requests(db: Session = Depends(get_db)):
    return {"message": "Role-based access control here"}


@app.post("/requests", dependencies=[Depends(oauth2_scheme)])
async def create_request(
    request: RequestCreate, db: Session = Depends(get_db)
):
    new_request = Request(
        bottoken=request.bottoken,
        chatid=request.chatid,
        message=request.message,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return {"message": "Request received and processed"}
