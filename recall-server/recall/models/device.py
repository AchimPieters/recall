from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from recall.db.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="offline", nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )

    logs: Mapped[list["DeviceLog"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class DeviceLog(Base):
    __tablename__ = "device_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    level: Mapped[str] = mapped_column(String(32), default="info")
    action: Mapped[str] = mapped_column(String(128), default="log")
    message: Mapped[str] = mapped_column(String(4096))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    device: Mapped[Device] = relationship(back_populates="logs")
