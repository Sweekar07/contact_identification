from tortoise import Tortoise
import os

ENV = os.getenv("ENV", "prod")
if ENV == "dev":
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

async def init_db():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["app.models"]},
    )
    await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()