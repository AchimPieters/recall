import subprocess  # nosec B404
from recall.models.device import DeviceLog


class SystemService:
    def __init__(self, db):
        self.db = db

    def _audit(self, action: str, message: str) -> None:
        self.db.add(
            DeviceLog(device_id="system", level="audit", action=action, message=message)
        )
        self.db.commit()

    def reboot(self, confirmed: bool, actor: str) -> dict:
        if not confirmed:
            return {"ok": False, "reason": "confirmation_required"}
        self._audit("reboot", f"requested_by={actor}")
        try:
            proc = subprocess.run(
                ["systemctl", "reboot"], capture_output=True, text=True, timeout=15
            )  # nosec B603,B607
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "reboot command timed out"}
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }

    def update(self, confirmed: bool, actor: str) -> dict:
        if not confirmed:
            return {"ok": False, "reason": "confirmation_required"}
        self._audit("update", f"requested_by={actor}")
        try:
            proc = subprocess.run(
                ["bash", "/opt/recall/update.sh"],
                capture_output=True,
                text=True,
                timeout=300,
            )  # nosec B603,B607
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "update command timed out"}
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
