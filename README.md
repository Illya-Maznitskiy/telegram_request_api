# Telegram Request API


## Description
This project is FastAPI service powered by PostgreSQL, featuring role-based access control, request handling, data storage, and Telegram messaging integration.


## Technologies Used
- Python
- FastAPI
- PostgreSQL


## Features
- Role-based access control (Admin, Manager, User).
- Save and process JSON requests with PostgreSQL.
- Send messages and log responses via Telegram API.


## Setup
To install the project locally on your computer, execute the following commands in a terminal:
```bash
git clone https://github.com/Illya-Maznitskiy/telegram_request_api.git
cd telegram_request_api
python -m venv venv
venv\Scripts\activate (on Windows)
source venv/bin/activate (on macOS)
pip install -r requirements.txt
```

## Database
Ensure you have PostgreSQL installed

Open the terminal and log into PostgreSQL using the following command:
```bash
psql -U postgres
```

Create DB with command:
```bash
CREATE DATABASE fastapi_project_db;
```

Add an admin user to the DB:
```bash
CREATE USER admin_user WITH PASSWORD 'admin_password' SUPERUSER;
```

Grant access to the fastapi_project_db database:
```bash
GRANT ALL PRIVILEGES ON DATABASE fastapi_project_db TO admin_user;
```


# Migrations
Create and apply migrations with commands:
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```


## Access
- To run the server use the command:
```bash
uvicorn main:app --reload
```

## API Endpoints
You can check and test the endpoints with URL [http://127.0.0.1:8000/docs/](http://127.0.0.1:8000/docs/)


## Screenshots:
### Structure
![](screenshots/.png)
