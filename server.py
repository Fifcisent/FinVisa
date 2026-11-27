"""Serve the FinVista demo and its local simulated-market API."""

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from invest_generator import WindDrivenMarket

PROJECT_ROOT = Path(__file__).resolve().parent
MARKET = WindDrivenMarket()
DISCLAIMER = (
    "Демонстрационный проект: предустановленные балансы, операции, курсы, ставки "
    "и котировки синтетические; акции могут резко падать и расти. Данные не являются "
    "реальными финансовыми данными, "
    "рекомендацией или предложением. Сервис не подключается к биржам и не "
    "проводит реальные финансовые операции. Используйте только вымышленные "
    "данные; не вводите реальные персональные или банковские сведения. "
    "Профили сохраняются в браузере посетителя и не отправляются серверным API. "
    "При публичном доступе через туннель Cloudflare может обрабатывать сетевые "
    "метаданные. Проект предназначен для обучения и не предназначен для незаконной деятельности."
)


class FinVistaRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self):
        request_path = urlsplit(self.path).path
        if request_path == "/api/market":
            snapshot = MARKET.snapshot()
            payload = {
                "updatedAt": snapshot.timestamp.isoformat(),
                "wind": snapshot.wind,
                "windChange": snapshot.wind_change,
                "prices": snapshot.prices,
                "priceChangesPct": snapshot.price_changes_pct,
                "disclaimer": DISCLAIMER,
            }
            response = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(response)
            return

        if request_path not in {"/", "/finvista_v1.2_0.html", "/finvista_grafic.css"}:
            self.send_error(404)
            return

        if request_path == "/":
            self.path = "/finvista_v1.2_0.html"
        super().do_GET()


def main():
    MARKET.start()
    try:
        with ThreadingHTTPServer(
            ("127.0.0.1", 8000),
            FinVistaRequestHandler,
        ) as server:
            print("FinVista доступен только на этом компьютере: http://127.0.0.1:8000")
            print("Для временного доступа друга запустите python public_demo.py.")
            print(f"ВАЖНО: {DISCLAIMER}")
            print("Для остановки нажмите Ctrl+C.")
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер FinVista остановлен.")
    finally:
        MARKET.stop()


if __name__ == "__main__":
    main()
