from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from recall.core.auth import AuthUser, get_current_user, require_role
from recall.db.database import get_db
from recall.services.settings_service import SettingsService
from recall.services.system_service import SystemService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", dependencies=[Depends(require_role("admin", "operator", "viewer"))])
def get_settings(db: Session = Depends(get_db)):
    return SettingsService(db).get_all()


@router.post("", dependencies=[Depends(require_role("admin", "operator"))])
def set_settings(payload: dict, db: Session = Depends(get_db)):
    return SettingsService(db).set_many(payload)


@router.post("/apply", dependencies=[Depends(require_role("admin", "operator"))])
def apply_settings(payload: dict, confirmed: bool = False, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    data = SettingsService(db).set_many(payload)
    SystemService(db)._audit("settings_apply", f"confirmed={confirmed},requested_by={user.username}")
    return {"applied": confirmed, "settings": data}
