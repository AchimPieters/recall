import psutil
from fastapi import APIRouter, Depends
from recall.core.auth import require_role

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("", dependencies=[Depends(require_role("admin", "operator", "viewer"))])
def monitor():
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": vm.percent,
        "disk_usage": disk.percent,
    }
