from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from .app.database import Base, engine
from .app.models import Ledger, Tasks, Users  # noqa: F401
from .app.routes.ledger import router as ledger_router
from .app.routes.ai import router as ai_router
from .app.routes.tasks import router as tasks_router
from .app.routes.users import router as users_router

app = FastAPI(
    title="MASAR API",
    version="1.0.0",
    description="API for users, tasks, points transfers, and task reward escrow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(tasks_router)
app.include_router(ledger_router)
app.include_router(ai_router)

frontend_directory = Path(__file__).resolve().parent.parent / "frontend"
if frontend_directory.is_dir():
    app.mount("/ui", StaticFiles(directory=frontend_directory, html=True), name="frontend")


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    task_columns = {column["name"] for column in inspect(engine).get_columns("tasks")}
    pricing_columns = {
        "region": "VARCHAR(100) NOT NULL DEFAULT 'نابلس'",
        "profession": "VARCHAR(100) NOT NULL DEFAULT 'كهرباء'",
        "demand": "FLOAT NOT NULL DEFAULT 5.5",
        "supply": "FLOAT NOT NULL DEFAULT 5.5",
    }
    with engine.begin() as connection:
        for name, definition in pricing_columns.items():
            if name not in task_columns:
                connection.execute(text(f"ALTER TABLE tasks ADD COLUMN {name} {definition}"))


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "MASAR API is running", "status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
