"""
Configuratie en styling voor het Marketing Dashboard.
Alle constanten, API-credentials en opmaakstijlen staan hier.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Zorg voor UTF-8 output op Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Laad .env bestand (credentials buiten de code)
load_dotenv()


# ============================================================
# API INSTELLINGEN
# ============================================================

GA4_PROPERTY_ID   = "281651243"
SPREADSHEET_ID    = "1LrGHSwQr2YGvL-cZiS1_MCWLfH8CQjDxjZwYvCn2Bu0"
SLEUTEL_BESTAND   = str(Path(__file__).parent / "google_keys.json")

META_AD_ACC_ID    = os.getenv("META_AD_ACC_ID", "act_456865435092610")
META_TOKEN        = os.getenv("META_TOKEN", "EAASjOk1bOfkBQ4sTd7SH8aELOMZC3suR9wdQJZBZBR4Y9CZAZCUxSoT02H9fZCG4uanKjhWgFuwnyaOaY2q3zxPdqzAoZBl9udQqWZARw6BZA107ehSMFjwED9slhzyKcSFxODUEBtjX4lfy991yNUU2D3nYGDJi8aYRL669LH2nfnFJNV6f5sCAffsw7A1f1GgZDZD")

FB_TOKEN          = os.getenv("FB_TOKEN", "EAASjOk1bOfkBQ3fhkrPVXCFhLeCP3KPyNzOqZBd1kxz2dsC5tiFRg6IdLocSoSWruTFyfObF2JFpidfXw8zyNH9vXcjxZCTOItlhUB8ZBptpPcUxV3lIGvczJ0W34xErP4MYz1bqihYowPxwLOyX1afPOF6yFdZBdZBM7Tz5Pa5nbYZBuI2beBBzOl0UFVZBQZDZD")
FB_PAGE_ID        = os.getenv("FB_PAGE_ID", "130663027026797")

IG_ACCOUNT_ID     = os.getenv("IG_ACCOUNT_ID", "17841417992851224")

PERIODE_DAGEN     = 7
ALLEEN_OP_MAANDAG = True


# ============================================================
# OPMAAK — Google Sheets stijlen
# ============================================================

STIJL_SECTIETITEL = {
    "backgroundColor": {"red": 0.11, "green": 0.20, "blue": 0.36},
    "textFormat": {"bold": True, "fontSize": 11,
                   "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
    "horizontalAlignment": "LEFT",
}
STIJL_HEADER = {
    "backgroundColor": {"red": 0.23, "green": 0.44, "blue": 0.71},
    "textFormat": {"bold": True,
                   "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
    "horizontalAlignment": "CENTER",
}
STIJL_TOTAAL = {
    "backgroundColor": {"red": 0.81, "green": 0.87, "blue": 0.95},
    "textFormat": {"bold": True},
}
STIJL_RIJ_GRIJS = {
    "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.96},
}
STIJL_KPI_WAARDE = {
    "textFormat": {"bold": True, "fontSize": 13},
    "horizontalAlignment": "CENTER",
}
STIJL_LEEG = {
    "backgroundColor": {"red": 1, "green": 1, "blue": 1},
}
