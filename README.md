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
git clone link
cd telegram_request_api
python -m venv venv
venv\Scripts\activate (on Windows)
source venv/bin/activate (on macOS)
pip install -r requirements.txt
```


## Access
- To run the server use the command:
```bash
uvicorn main:app --reload
```

## API Endpoints
###  Service
- POST: **`/`**             - Add a new 


## Screenshots:
### Structure
![](screenshots/.png)
