from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from recall.core.config import get_settings
from recall.models.device import Device, DeviceLog

settings = get_settings()


class DeviceService:
    def __init__(self, db: Session):
        self.db = db

    def register(
        self, device_id: str, name: str, ip: str | None, version: str | None
    ) -> Device:
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            device = Device(id=device_id, name=name)
            self.db.add(device)
        device.status = "online"
        device.ip = ip
        device.version = version
        device.last_seen = datetime.utcnow()
        self.db.commit()
        self.db.refresh(device)
        return device

    def heartbeat(self, device_id: str, metrics: dict | None = None) -> Device | None:
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return None
        device.last_seen = datetime.utcnow()
        device.status = "online"
        device.metrics = metrics
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_config(self, device_id: str) -> dict:
        return {
            "device_id": device_id,
            "heartbeat_interval": 30,
            "fallback_content": "default",
        }

    def add_log(
        self, device_id: str, level: str, action: str, message: str
    ) -> DeviceLog:
        log = DeviceLog(
            device_id=device_id, level=level, action=action, message=message
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def mark_presence(self) -> int:
        devices = self.db.query(Device).all()
        now = datetime.utcnow()
        changed = 0
        for device in devices:
            if not device.last_seen:
                new_status = "unreachable"
            elif now - device.last_seen > timedelta(
                seconds=settings.heartbeat_timeout_seconds
            ):
                new_status = "offline"
            else:
                new_status = "online"
            if device.status != new_status:
                changed += 1
                device.status = new_status
        self.db.commit()
        return changed

    def list_devices(self) -> list[Device]:
        return self.db.query(Device).all()
