"""
Hulpfuncties voor het Marketing Dashboard.
Formattering, Google Sheets helpers, en gedeelde utilities.
"""

import time
import gspread
from gspread.utils import rowcol_to_a1

from config import (
    STIJL_SECTIETITEL, STIJL_HEADER, STIJL_TOTAAL,
    STIJL_RIJ_GRIJS, STIJL_LEEG,
)


def format_tijd(seconden):
    m, s = divmod(int(float(seconden)), 60)
    return f"{m}m {s}s"


def pct(teller, noemer, decimalen=1):
    if noemer and float(noemer) > 0:
        return f"{round((float(teller) / float(noemer)) * 100, decimalen)}%"
    return "—"


def eur(waarde):
    return f"EUR {float(waarde):.2f}" if waarde not in ("—", None, "") else "—"


def kolom_letter(n):
    return rowcol_to_a1(1, n)[:-1]


def haal_of_maak_sheet(spreadsheet, naam):
    try:
        ws = spreadsheet.worksheet(naam)
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=naam, rows=500, cols=30)
        print(f"  + Nieuw tabblad: '{naam}'")
    return ws


def stel_kolombreedte_in(ws, kolom_breedtes):
    requests_body = [{
        "updateDimensionProperties": {
            "range": {
                "sheetId": ws.id,
                "dimension": "COLUMNS",
                "startIndex": col,
                "endIndex": col + 1,
            },
            "properties": {"pixelSize": breedte},
            "fields": "pixelSize",
        }
    } for col, breedte in kolom_breedtes]
    if requests_body:
        time.sleep(2)
        ws.spreadsheet.batch_update({"requests": requests_body})


def schrijf_blok(ws, start_rij, titel, headers, rijen,
                 totaal_rij=None, num_kolommen=None):
    n_cols   = num_kolommen or len(headers)
    eind_col = kolom_letter(n_cols)

    alle_rijen = [[titel]] + [headers] + rijen
    if totaal_rij:
        alle_rijen.append(totaal_rij)
    alle_rijen.append([""])

    for i, rij in enumerate(alle_rijen):
        if len(rij) < n_cols:
            alle_rijen[i] = list(rij) + [""] * (n_cols - len(rij))

    time.sleep(2)
    ws.update(alle_rijen, f"A{start_rij}", value_input_option="USER_ENTERED")
    time.sleep(1)
    try:
        ws.unmerge_cells(f"A{start_rij}:{eind_col}{start_rij}")
    except Exception:
        pass
    ws.merge_cells(f"A{start_rij}:{eind_col}{start_rij}")

    huidige_rij   = start_rij
    format_ranges = []

    format_ranges.append({"range": f"A{huidige_rij}:{eind_col}{huidige_rij}", "format": STIJL_SECTIETITEL})
    huidige_rij += 1
    format_ranges.append({"range": f"A{huidige_rij}:{eind_col}{huidige_rij}", "format": STIJL_HEADER})
    huidige_rij += 1

    for i in range(len(rijen)):
        if i % 2 == 1:
            format_ranges.append({"range": f"A{huidige_rij}:{eind_col}{huidige_rij}", "format": STIJL_RIJ_GRIJS})
        huidige_rij += 1

    if totaal_rij:
        format_ranges.append({"range": f"A{huidige_rij}:{eind_col}{huidige_rij}", "format": STIJL_TOTAAL})
        huidige_rij += 1

    format_ranges.append({"range": f"A{huidige_rij}:{eind_col}{huidige_rij}", "format": STIJL_LEEG})
    huidige_rij += 1

    time.sleep(2)
    ws.batch_format(format_ranges)

    print(f"  ✓ Blok '{titel}' ({len(rijen)} rijen)")
    return huidige_rij


def schrijf_paginatitel(ws, tekst, breedte_col="H"):
    time.sleep(0.5)
    ws.update([[tekst]], "A1", value_input_option="USER_ENTERED")
    ws.format(f"A1:{breedte_col}1", {"textFormat": {"bold": True, "fontSize": 14}})
    ws.merge_cells(f"A1:{breedte_col}1")


def pct_diff(waarde_7d, totaal_30d, factor=7/30):
    """Berekent % verschil tussen 7d waarde en het 7d-equivalent van 30d gemiddelde."""
    try:
        gem_30d = float(totaal_30d) * factor
        if gem_30d == 0:
            return None, None
        diff = ((float(waarde_7d) - gem_30d) / gem_30d) * 100
        return round(diff, 1), round(gem_30d, 1)
    except (TypeError, ValueError):
        return None, None
