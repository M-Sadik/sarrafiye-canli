"""Sarrafiye Canlı - Altınkaynak, Hakan Altın ve Harem Altın fiyatlarını
arka planda çekip tek bir JSON uç noktasında (/api/prices) sunar.

Çalıştırma:  python app.py      (varsayılan port 8000, PORT ortam değişkeni ile değişir)
"""
import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import websocket  # pip install websocket-client

POLL_SECONDS = 5
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Ürün satırları: (anahtar, etiket, grup, altınkaynak kodu, hakan kodu, harem kodu)
PRODUCTS = [
    ("has",        "Has Altın",          "Gram",     "HH_T", "GAUTRY",       "ALTIN"),
    ("gram",       "Gram Altın (24 ayar)", "Gram",   "GA",   "1GR.995TRY",   "KULCEALTIN"),
    ("ayar22",     "22 Ayar",            "Gram",     "B_T",  "22AYARALTIN",  "AYAR22"),
    ("ayar18",     "18 Ayar",            "Gram",     "P18",  "18AYARALTIN",  None),
    ("ayar14",     "14 Ayar",            "Gram",     "P14",  "14AYARALTIN",  "AYAR14"),
    ("ceyrek_y",   "Çeyrek",             "Yeni",     "PC",   "YCEYREKTL",    "CEYREK_YENI"),
    ("yarim_y",    "Yarım",              "Yeni",     "PY",   "YYARIMTL",     "YARIM_YENI"),
    ("tam_y",      "Tam",                "Yeni",     "PT",   "YTAMTL",       "TEK_YENI"),
    ("ata_y",      "Ata (Cumhuriyet)",   "Yeni",     "PA",   "YATATL",       "ATA_YENI"),
    ("gremse_y",   "Gremse",             "Yeni",     "PG",   "YGREMSETL",    "GREMESE_YENI"),
    ("ata5_y",     "Ata Beşli",          "Yeni",     "PA5",  "YATABESLITL",  "ATA5_YENI"),
    ("ceyrek_e",   "Çeyrek",             "Eski",     "EC",   "ECEYREKTL",    "CEYREK_ESKI"),
    ("yarim_e",    "Yarım",              "Eski",     "EY",   "EYARIMTL",     "YARIM_ESKI"),
    ("tam_e",      "Tam",                "Eski",     "ET",   "ETAMTL",       "TEK_ESKI"),
    ("ata_e",      "Ata (Cumhuriyet)",   "Eski",     None,   "EATATL",       "ATA_ESKI"),
    ("gremse_e",   "Gremse",             "Eski",     "EG",   "EGREMSETL",    "GREMESE_ESKI"),
    ("ata5_e",     "Ata Beşli",          "Eski",     None,   "EATABESLITL",  "ATA5_ESKI"),
    ("resat",      "Reşat",              "Diğer",    "PR",   "RESATLIRATL",  None),
    ("hamit",      "Hamit",              "Diğer",    "PH",   None,           None),
]

SOURCES = {
    "ak": {"name": "Altınkaynak", "url": "https://www.altinkaynak.com"},
    "hk": {"name": "Hakan Altın", "url": "https://www.hakanaltin.com"},
    "hr": {"name": "Harem Altın", "url": "https://www.haremaltin.com"},
}

lock = threading.Lock()
# kaynak -> {"prices": {kod: (alış, satış)}, "updated": epoch, "source_time": str, "error": str|None}
state = {k: {"prices": {}, "updated": 0, "source_time": None, "error": None} for k in SOURCES}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def http_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def tr_num(s):
    """'6.523,87' -> 6523.87"""
    return float(str(s).replace(".", "").replace(",", "."))


def set_source(key, prices, source_time=None, merge=False):
    with lock:
        st = state[key]
        if merge:
            st["prices"].update(prices)
        else:
            st["prices"] = prices
        st["updated"] = time.time()
        st["source_time"] = source_time
        st["error"] = None


def set_error(key, err):
    with lock:
        state[key]["error"] = str(err)[:200]


# --- Altınkaynak: herkese açık JSON ---------------------------------------
def poll_altinkaynak():
    data = http_json("https://static.altinkaynak.com/public/Gold")
    prices = {x["Kod"]: (tr_num(x["Alis"]), tr_num(x["Satis"])) for x in data}
    set_source("ak", prices, data[0].get("GuncellenmeZamani") if data else None)


# --- Hakan Altın: sitenin kullandığı fiyat API'si --------------------------
def poll_hakan():
    data = http_json(
        "https://api.hakanaltin.net/api/history/latest",
        {"Origin": "https://www.hakanaltin.com", "Referer": "https://www.hakanaltin.com/"},
    )
    if not data.get("success"):
        raise RuntimeError("Hakan API başarısız yanıt")
    prices = {x["symbol_id"]: (float(x["last_bid_price"]), float(x["last_ask_price"])) for x in data["data"]}
    set_source("hk", prices, data.get("lastUpdated"))


def poller(key, fn):
    while True:
        try:
            fn()
        except Exception as e:  # ağ hatası vb. -> son fiyatlar korunur
            set_error(key, e)
        time.sleep(POLL_SECONDS)


# --- Harem Altın: socket.io (EIO=4) canlı yayını ---------------------------
def harem_loop():
    url = "wss://hrmsocketonly.haremaltin.com/socket.io/?EIO=4&transport=websocket"
    while True:
        ws = None
        try:
            ws = websocket.create_connection(
                url, timeout=30, origin="https://www.haremaltin.com", header=[f"User-Agent: {UA}"]
            )
            while True:
                msg = ws.recv()
                if not msg:
                    continue
                if msg[0] == "0":          # engine.io open -> socket.io bağlan
                    ws.send("40")
                elif msg == "2":           # ping -> pong
                    ws.send("3")
                elif msg.startswith("42"):  # olay
                    name, payload = json.loads(msg[2:])[:2]
                    if name != "price_changed":
                        continue
                    prices = {}
                    for code, d in (payload.get("data") or {}).items():
                        try:
                            prices[code] = (float(d["alis"]), float(d["satis"]))
                        except (KeyError, TypeError, ValueError):
                            pass
                    t = (payload.get("meta") or {}).get("time")
                    src_time = datetime.fromtimestamp(t / 1000, timezone.utc).isoformat() if t else None
                    set_source("hr", prices, src_time, merge=True)
                elif msg.startswith("41"):  # sunucu bağlantıyı kapattı
                    break
        except Exception as e:
            set_error("hr", e)
        finally:
            try:
                ws and ws.close()
            except Exception:
                pass
        time.sleep(3)


def build_payload():
    with lock:
        snap = {k: {**v, "prices": dict(v["prices"])} for k, v in state.items()}
    rows = []
    for key, label, group, ak, hk, hr in PRODUCTS:
        cells = {}
        for src, code in (("ak", ak), ("hk", hk), ("hr", hr)):
            p = snap[src]["prices"].get(code) if code else None
            cells[src] = {"alis": p[0], "satis": p[1]} if p and p[0] > 0 and p[1] > 0 else None
        if any(cells.values()):
            rows.append({"key": key, "label": label, "group": group, "prices": cells})
    now = time.time()
    sources = {
        k: {
            **SOURCES[k],
            "ok": snap[k]["updated"] > 0 and now - snap[k]["updated"] < 60,
            "age": round(now - snap[k]["updated"], 1) if snap[k]["updated"] else None,
            "sourceTime": snap[k]["source_time"],
            "error": snap[k]["error"],
        }
        for k in SOURCES
    }
    return {"serverTime": now_iso(), "interval": POLL_SECONDS, "sources": sources, "rows": rows}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STATIC_DIR, **kw)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/prices":
            body = json.dumps(build_payload(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.split("?")[0] == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass  # sessiz


def main():
    threading.Thread(target=poller, args=("ak", poll_altinkaynak), daemon=True).start()
    threading.Thread(target=poller, args=("hk", poll_hakan), daemon=True).start()
    threading.Thread(target=harem_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8000"))
    print(f"Sarrafiye Canlı: http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
