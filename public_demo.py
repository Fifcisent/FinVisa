"""Run the local demo behind a Cloudflare Quick Tunnel."""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_ADDRESS = ("127.0.0.1", 8000)
CLOUDFLARE_DOWNLOADS = "https://developers.cloudflare.com/tunnel/downloads/"


def find_cloudflared() -> Optional[str]:
    executable = shutil.which("cloudflared")
    if executable:
        return executable

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        local_executable = (
            Path(local_app_data) / "Programs" / "cloudflared" / "cloudflared.exe"
        )
        if local_executable.is_file():
            return str(local_executable)
    return None


def wait_for_server(process: subprocess.Popen, timeout_seconds: float = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("FinVista server stopped before it became ready.")
        try:
            with socket.create_connection(LOCAL_ADDRESS, timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError("FinVista server did not start within 30 seconds.")


def stop_process(process: Optional[subprocess.Popen]) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main() -> int:
    cloudflared = find_cloudflared()
    if cloudflared is None:
        print(
            "Сначала установите cloudflared для Windows с официальной страницы: "
            f"{CLOUDFLARE_DOWNLOADS}",
            file=sys.stderr,
        )
        return 1

    server_process = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "server.py")],
        cwd=str(PROJECT_ROOT),
    )
    tunnel_process = None
    try:
        wait_for_server(server_process)
        command = [
            cloudflared,
            "tunnel",
            "--url",
            "http://127.0.0.1:8000",
        ]
        print("Запускаю публичный демо-доступ без email-ограничения.")
        print("Любой, у кого есть ссылка, сможет открыть сайт.")
        print("Не вводите реальные персональные или банковские данные.")
        print("Cloudflare может обрабатывать сетевые метаданные.")
        print("Скопируйте ссылку trycloudflare.com из вывода cloudflared.")
        print("Остановите туннель сочетанием Ctrl+C; ссылка перестанет работать.")
        tunnel_process = subprocess.Popen(command, cwd=str(PROJECT_ROOT))
        return tunnel_process.wait()
    except KeyboardInterrupt:
        print("\nЗавершаю публичный демо-доступ.")
        return 0
    finally:
        stop_process(tunnel_process)
        stop_process(server_process)


if __name__ == "__main__":
    raise SystemExit(main())
