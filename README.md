# 📇 Contact Identification API (FastAPI + Tortoise ORM)

A lightweight microservice to manage contact unification using email and phone number combinations.

---

## 🟢 Live link
```
https://bitespeed-tag1.onrender.com/docs
```

## 🚀 Features

- Identify primary and secondary contact relationships
- Handles deduplication based on phone and email
- Auto-merges primary contacts if needed
- PostgreSQL support with Tortoise ORM
- Async-safe with transactional DB operations

---

## 📁 Project Structure

```
app/
├── models.py # Tortoise ORM models
├── routes.py # API endpoints
├── schemas.py # Pydantic request/response schemas
├── services.py # Business logic
├── config.py # DB config via ENV
├── main.py # FastAPI app entrypoint
.env # Environment variables
README.md # You're here
```

## ⚙️ .env Configuration

Create a `.env` file in the root directory:

```dotenv
ENVIRONMENT=prod
DATABASE_URL=postgres://user:password@localhost:5432/yourdb
```

## 📦 Install Dependencies

```
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 🧪 Running in Development

To run locally using a Docker container
```
docker-compose up --build
```

To stop the Docker container
```
docker-compose down
```

## 📡 API Endpoints

```
POST /identify

Payload:
json
{
  "email": "user@example.com",
  "phoneNumber": "9876543210"
}
```

```
Response:
json
{
  "contact": {
    "primaryContactId": 1,
    "emails": ["user@example.com"],
    "phoneNumbers": ["9876543210"],
    "secondaryContactIds": [2, 3]
  }
}
```