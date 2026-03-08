from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from recall.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    device: Mapped[Device] = relationship(back_populates="logs")


class DeviceGroup(Base):
    __tablename__ = "device_groups"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_device_groups_org_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )


class DeviceGroupMember(Base):
    __tablename__ = "device_group_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("device_groups.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    level: Mapped[str] = mapped_column(String(32), nullable=False, default="warning")
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    message: Mapped[str] = mapped_column(String(4096), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class DeviceScreenshot(Base):
    __tablename__ = "device_screenshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
