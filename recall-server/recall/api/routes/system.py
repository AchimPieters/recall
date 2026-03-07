from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from recall.core.auth import AuthUser, get_current_user, require_role
from recall.db.database import get_db
from recall.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/reboot", dependencies=[Depends(require_role("admin"))])
def reboot(confirmed: bool = False, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    return SystemService(db).reboot(confirmed, user.username)


@router.post("/update", dependencies=[Depends(require_role("admin"))])
def update(confirmed: bool = False, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    return SystemService(db).update(confirmed, user.username)
