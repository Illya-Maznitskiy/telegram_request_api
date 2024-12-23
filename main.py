from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv
import os


from models import Role, User, Request
from database import SessionLocal


load_dotenv()


# Constants
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = "@request_api_telegram_bot"


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


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    try:
        # Decode the token and extract username
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        # Validate token and username
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch user from database
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    # Handle token validation errors
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_role(user: User, role_name: str):
    # Check if user's role matches the required role
    if user.role.name != role_name:
        # Raise an exception if roles do not match
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied for {role_name} role",
        )


# Utility functions
def verify_password(plain_password, hashed_password):
    # Verify if the plain password matches the hashed password
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password):
    # Hash the plain password for secure storage
    return pwd_context.hash(plain_password)


def authenticate_user(db, username: str, password: str):
    # Fetch user by username and verify the password
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_access_token(data: dict, expires_delta: timedelta = None):
    # Create and encode an access token with optional expiration time
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_user_in_db(
    db: Session, username: str, password: str, role_name: str
):
    # Hash password and create a new user with a specific role in the database
    hashed_password = hash_password(password)
    user_role = db.query(Role).filter(Role.name == role_name).first()
    if not user_role:
        # If role doesn't exist, create it
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
    # Authenticate user using provided username and password
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Raise error if credentials are invalid
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set expiration time for access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Create access token for authenticated user
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Return the access token and token type
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users", response_model=UserRead)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Define allowed roles in lowercase
    allowed_roles = ["admin", "manager", "user"]

    # Validate role (case-insensitive)
    role_lower = user.role_name.lower()
    if role_lower not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Choose one of: "
            f"{', '.join([role.capitalize() for role in allowed_roles])}",
        )

    # Check if username is already registered
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Create and return the new user
    new_user = create_user_in_db(
        db, user.username, user.password, role_name=role_lower.capitalize()
    )
    return new_user


@app.get("/requests")
async def get_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin: Return all requests
    if current_user.role.name == "Admin":
        return db.query(Request).all()

    # Manager: Return requests from users managed by this manager
    if current_user.role.name == "Manager":
        # Filter by `managed_user_ids` (users under the manager)
        managed_users = (
            db.query(User.id).filter(User.manager_id == current_user.id).all()
        )
        managed_user_ids = [user[0] for user in managed_users]
        return (
            db.query(Request)
            .filter(Request.user_id.in_(managed_user_ids))
            .all()
        )

    # User: Return only their own requests
    if current_user.role.name == "User":
        return (
            db.query(Request).filter(Request.user_id == current_user.id).all()
        )

    # Default: Access denied
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
    )


@app.post("/requests")
async def create_request(
    request: RequestCreate,  # Accepts request data (bottoken, chatid, message)
    db: Session = Depends(get_db),  # Database session dependency
    current_user: User = Depends(
        get_current_user
    ),  # Gets the current authenticated user
):
    # Create a new request record in the database with provided data
    new_request = Request(
        bottoken=request.bottoken,
        chatid=request.chatid,
        message=request.message,
        user_id=current_user.id,  # Associates request with the current user
    )

    # Add the new request to the session and commit to save it in the database
    db.add(new_request)
    db.commit()
    db.refresh(new_request)  # Refresh the object to get the updated values

    # Return success message after creating the request
    return {"message": "Request created"}


# Telegram Bot Functions


def handle_response(text: str) -> str:
    if "hello" in text.lower():
        return "Hello! How can I help you today?"
    elif "help" in text.lower():
        return "Please ask me anything, I am here to help!"
    else:
        return "I'm sorry, I didn't understand that."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Thanks for chatting with me! I am a API bot!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I am a FastAPI bot! I process JSON requests."
    )


async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("This is a custom command!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract message details
    chat_id = update.message.chat.id
    text = update.message.text

    # Print the received message for debugging
    print(f'User {chat_id} sent: "{text}"')

    # Save the message to the database
    db = next(get_db())  # Get the database session
    new_request = Request(
        bottoken=os.getenv("TELEGRAM_TOKEN"),  # Use your bot token
        chatid=str(chat_id),  # Store chat ID as a string
        message=text,
    )

    # Add and commit to the database
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Log the saved message to confirm it's in the database
    print(f"Saved message from chat {chat_id} to DB.")

    # Generate a response based on the message content
    response = handle_response(text)

    # Send a reply to the user
    await update.message.reply_text(response)


if __name__ == "__main__":
    print("Starting bot...")
    application = Application.builder().token(TOKEN).build()

    # Add handlers for bot commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("custom", custom_command))

    # Add handler for messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Run the bot
    print("Polling...")
    application.run_polling(poll_interval=3)
