"""SQLite database — session and result storage"""
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, select

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "husim.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String)
    algorithm: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="running")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String)
    metrics_json: Mapped[str] = mapped_column(Text)  # Stored as JSON
    task_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_time: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeatherConfig(Base):
    __tablename__ = "weather_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String)
    weather_json: Mapped[str] = mapped_column(Text)
    optimized_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String, default="bilgi")  # bilgi | uyarı | kritik (info | warning | critical)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")


async def save_session(simulation_id: str, scenario_id: str, algorithm: str):
    async with AsyncSessionLocal() as db:
        session = Session(id=simulation_id, scenario_id=scenario_id, algorithm=algorithm)
        db.add(session)
        await db.commit()


async def update_session_status(simulation_id: str, status: str):
    async with AsyncSessionLocal() as db:
        result = await db.get(Session, simulation_id)
        if result:
            result.status = status
            if status in ("completed", "failed", "stopped"):
                result.finished_at = datetime.utcnow()
            await db.commit()


async def save_result(simulation_id: str, metrics: dict):
    async with AsyncSessionLocal() as db:
        result = Result(
            session_id=simulation_id,
            metrics_json=json.dumps(metrics, ensure_ascii=False),
            task_completed=metrics.get("task_completed", False),
            completion_time=metrics.get("completion_time", 0.0),
            risk_score=metrics.get("risk_score", 0.0),
        )
        db.add(result)
        await db.commit()


async def save_weather_config(simulation_id: str, weather: dict, optimized: dict):
    async with AsyncSessionLocal() as db:
        wc = WeatherConfig(
            session_id=simulation_id,
            weather_json=json.dumps(weather, ensure_ascii=False),
            optimized_json=json.dumps(optimized, ensure_ascii=False),
        )
        db.add(wc)
        await db.commit()


async def get_history(limit: int = 50) -> list[dict]:
    async with AsyncSessionLocal() as db:
        stmt = select(Session).order_by(Session.created_at.desc()).limit(limit)
        sessions = (await db.execute(stmt)).scalars().all()

        history = []
        for s in sessions:
            # Get metrics
            res_stmt = select(Result).where(Result.session_id == s.id).limit(1)
            res = (await db.execute(res_stmt)).scalar_one_or_none()

            # Get weather configuration
            wc_stmt = select(WeatherConfig).where(WeatherConfig.session_id == s.id).limit(1)
            wc = (await db.execute(wc_stmt)).scalar_one_or_none()

            history.append({
                "id": s.id,
                "scenario_id": s.scenario_id,
                "algorithm": s.algorithm,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                "metrics": json.loads(res.metrics_json) if res else None,
                "weather": json.loads(wc.weather_json) if wc else None,
            })

        return history
