"""Generiše potpisane QR linkove za stolove (privremeno, dok admin panel ne stigne).

Upotreba:  python scripts/qr_links.py [broj_stolova]
Zahteva pokrenut sistem (docker compose up) i isti QR_SECRET kao orders servis.
"""
import hashlib
import hmac
import json
import os
import sys
import urllib.request

GATEWAY = os.environ.get("TABLR_GATEWAY", "http://localhost:8000")
GUEST_APP = os.environ.get("TABLR_GUEST", "http://localhost:5173")
QR_SECRET = os.environ.get("QR_SECRET", "dev-secret-change-in-prod")


def sign(cafe_id: str, table: int) -> str:
    message = f"{cafe_id}:{table}".encode()
    return hmac.new(QR_SECRET.encode(), message, hashlib.sha256).hexdigest()


def main() -> None:
    tables = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    with urllib.request.urlopen(f"{GATEWAY}/api/menu/cafes") as resp:
        cafes = json.load(resp)
    for cafe in cafes:
        print(f"\n=== {cafe['name']} ===")
        for table in range(1, tables + 1):
            url = (f"{GUEST_APP}/?cafe={cafe['id']}&table={table}"
                   f"&sig={sign(cafe['id'], table)}")
            print(f"  Sto {table}: {url}")


if __name__ == "__main__":
    main()
