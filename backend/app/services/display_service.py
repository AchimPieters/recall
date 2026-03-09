import subprocess  # nosec B404


class DisplayService:
    @staticmethod
    def detect() -> dict:
        proc = subprocess.run(
            ["xrandr", "--query"], capture_output=True, text=True
        )  # nosec B603,B607
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip()}
        outputs = [line for line in proc.stdout.splitlines() if " connected" in line]
        return {"ok": True, "outputs": outputs}
