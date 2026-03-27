"""
============================================================
  MASTER MARKETING DASHBOARD — Volledig uitgewerkt
  Tabbladen:
    GA4 — Overzicht        : Top KPI's, sessies, engagement, conversies
    GA4 — Verkeersbronnen  : Kanalen, new/return, source/medium
    GA4 — Gedrag           : Landingspagina's, events, apparaat
    Meta Ads — Overzicht   : KPI samenvatting + funnel
    Meta Ads — Campagnes   : Campagne niveau (spend, CTR, CPL, ROAS)
    Meta Ads — Adsets      : Adset niveau breakdown
    Meta Ads — Ads         : Ad niveau breakdown + creatives
    Facebook Organic       : Bereik, groei, engagement per post
    Instagram              : Volgers, bereik, posts, stories, content types
    KPI Overzicht          : Historisch overzicht per run

  Installatie:
    pip install -r requirements.txt

  Gebruik:
    1. Kopieer google_keys.json naar dezelfde map als dit script
    2. Kopieer .env.example naar .env en vul je tokens in
    3. Run: python dashboard_update.py
============================================================
"""

import os
import sys
import subprocess
import time
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv

# Zorg voor UTF-8 output op Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Laad .env bestand (credentials buiten de code)
load_dotenv()
import gspread
from gspread.utils import rowcol_to_a1
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest,
    OrderBy
)


# ============================================================
# 1. INSTELLINGEN
# ============================================================

GA4_PROPERTY_ID   = "281651243"
SPREADSHEET_ID    = "1LrGHSwQr2YGvL-cZiS1_MCWLfH8CQjDxjZwYvCn2Bu0"
# Pad naar google_keys.json — altijd relatief aan dit script
SLEUTEL_BESTAND   = str(Path(__file__).parent / "google_keys.json")

META_AD_ACC_ID    = os.getenv("META_AD_ACC_ID", "act_456865435092610")
META_TOKEN        = os.getenv("META_TOKEN", "EAASjOk1bOfkBQ4sTd7SH8aELOMZC3suR9wdQJZBZBR4Y9CZAZCUxSoT02H9fZCG4uanKjhWgFuwnyaOaY2q3zxPdqzAoZBl9udQqWZARw6BZA107ehSMFjwED9slhzyKcSFxODUEBtjX4lfy991yNUU2D3nYGDJi8aYRL669LH2nfnFJNV6f5sCAffsw7A1f1GgZDZD")

FB_TOKEN          = os.getenv("FB_TOKEN", "EAASjOk1bOfkBQ3fhkrPVXCFhLeCP3KPyNzOqZBd1kxz2dsC5tiFRg6IdLocSoSWruTFyfObF2JFpidfXw8zyNH9vXcjxZCTOItlhUB8ZBptpPcUxV3lIGvczJ0W34xErP4MYz1bqihYowPxwLOyX1afPOF6yFdZBdZBM7Tz5Pa5nbYZBuI2beBBzOl0UFVZBQZDZD")
FB_PAGE_ID        = os.getenv("FB_PAGE_ID", "130663027026797")

IG_ACCOUNT_ID     = os.getenv("IG_ACCOUNT_ID", "17841417992851224")

PERIODE_DAGEN     = 7
ALLEEN_OP_MAANDAG = True


# ============================================================
# 2. OPMAAK
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


# ============================================================
# 3. HULPFUNCTIES
# ============================================================

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


# ============================================================
# 4. GA4 — OVERZICHT (Top KPI's + conversies)
# ============================================================

def haal_ga4_overzicht(ga4_client, spreadsheet, start_datum, vandaag):
    print(f"\n[GA4 Overzicht] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "GA4 — Overzicht")

    # Rapport 1a: eerste 10 KPI's (GA4 max = 10 per request)
    req1a = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        metrics=[
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="sessions"),
            Metric(name="engagedSessions"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
            Metric(name="conversions"),
            Metric(name="sessionConversionRate"),
            Metric(name="screenPageViews"),
        ],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
    )
    res1a = ga4_client.run_report(req1a)

    # Rapport 1b: pages/sessie apart
    req1b = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        metrics=[Metric(name="screenPageViewsPerSession")],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
    )
    res1b = ga4_client.run_report(req1b)

    kpi_rij = ["—"] * 11
    if res1a.rows:
        r = res1a.rows[0]
        pages_per_sessie = round(float(res1b.rows[0].metric_values[0].value), 2) if res1b.rows else "—"
        kpi_rij = [
            int(r.metric_values[0].value),
            int(r.metric_values[1].value),
            int(r.metric_values[2].value),
            int(r.metric_values[3].value),
            f"{round(float(r.metric_values[4].value) * 100, 1)}%",
            format_tijd(r.metric_values[5].value),
            f"{round(float(r.metric_values[6].value) * 100, 1)}%",
            int(float(r.metric_values[7].value)),
            f"{round(float(r.metric_values[8].value) * 100, 2)}%",
            int(r.metric_values[9].value),
            pages_per_sessie,
        ]

    # Rapport 2: conversies per event
    req2 = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="conversions"), Metric(name="sessionConversionRate")],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="conversions"), desc=True)],
        limit=20,
    )
    res2 = ga4_client.run_report(req2)
    conv_rijen = []
    for row in res2.rows:
        conv = int(float(row.metric_values[0].value))
        if conv > 0:
            conv_rijen.append([
                row.dimension_values[0].value,
                conv,
                f"{round(float(row.metric_values[1].value) * 100, 2)}%",
            ])

    schrijf_paginatitel(ws, f"GA4 — Overzicht  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}", "K")

    vr = schrijf_blok(ws, 3, f"Top KPI's — afgelopen {PERIODE_DAGEN} dagen",
        ["Gebruikers", "Nieuwe gebruikers", "Sessies", "Engaged sessies",
         "Engagement rate", "Gem. sessieduur", "Bounce rate",
         "Conversies", "Conv. rate", "Pageviews", "Pages/sessie"],
        [kpi_rij], num_kolommen=11)
    ws.batch_format([{"range": f"A{vr-2}:K{vr-2}", "format": STIJL_KPI_WAARDE}])

    vr = schrijf_blok(ws, vr, "Conversies per event",
        ["Event naam", "Conversies", "Conv. rate"],
        conv_rijen if conv_rijen else [["Geen conversies gevonden", "", ""]],
        num_kolommen=3)

    stel_kolombreedte_in(ws, [(0,220),(1,160),(2,160),(3,160),(4,160),
                               (5,160),(6,140),(7,130),(8,130),(9,130),(10,150)])
    print(f"  -> {kpi_rij[0]} gebruikers | {kpi_rij[7]} conversies")
    return (kpi_rij[0], kpi_rij[2], kpi_rij[7],
            kpi_rij[8],   # conv rate
            kpi_rij[6],   # bounce rate
            kpi_rij[4],   # engagement rate
            kpi_rij[5],   # gem sessieduur
            kpi_rij[1])   # nieuwe gebruikers


# ============================================================
# 5. GA4 — VERKEERSBRONNEN
# ============================================================

def haal_ga4_verkeersbronnen(ga4_client, spreadsheet, start_datum, vandaag):
    print(f"\n[GA4 Verkeersbronnen] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "GA4 — Verkeersbronnen")

    # Rapport 1: per kanaal
    req1 = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="totalUsers"), Metric(name="sessions"),
            Metric(name="engagedSessions"), Metric(name="engagementRate"),
            Metric(name="conversions"), Metric(name="sessionConversionRate"),
        ],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
    )
    res1 = ga4_client.run_report(req1)

    kanaal_rijen = []
    totaal_users = totaal_sess = totaal_conv = 0
    for row in res1.rows:
        u = int(row.metric_values[0].value)
        s = int(row.metric_values[1].value)
        c = int(float(row.metric_values[4].value))
        totaal_users += u; totaal_sess += s; totaal_conv += c
        kanaal_rijen.append([
            row.dimension_values[0].value, u, s,
            int(row.metric_values[2].value),
            f"{round(float(row.metric_values[3].value)*100,1)}%",
            c,
            f"{round(float(row.metric_values[5].value)*100,2)}%",
        ])

    # Rapport 2: new vs returning
    req2 = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="newVsReturning")],
        metrics=[Metric(name="totalUsers"), Metric(name="sessions"),
                 Metric(name="engagementRate"), Metric(name="conversions")],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
    )
    res2 = ga4_client.run_report(req2)
    nvr_rijen = []
    for row in res2.rows:
        nvr_rijen.append([
            "Nieuwe gebruikers" if row.dimension_values[0].value == "new" else "Terugkerende gebruikers",
            int(row.metric_values[0].value),
            int(row.metric_values[1].value),
            f"{round(float(row.metric_values[2].value)*100,1)}%",
            int(float(row.metric_values[3].value)),
        ])

    # Rapport 3: top source/medium
    req3 = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="sessionSource"), Dimension(name="sessionMedium")],
        metrics=[Metric(name="totalUsers"), Metric(name="sessions"),
                 Metric(name="engagementRate"), Metric(name="conversions")],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=20,
    )
    res3 = ga4_client.run_report(req3)
    sm_rijen = []
    for row in res3.rows:
        sm_rijen.append([
            row.dimension_values[0].value,
            row.dimension_values[1].value,
            int(row.metric_values[0].value),
            int(row.metric_values[1].value),
            f"{round(float(row.metric_values[2].value)*100,1)}%",
            int(float(row.metric_values[3].value)),
        ])

    schrijf_paginatitel(ws, f"GA4 — Verkeersbronnen  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}", "G")

    vr = schrijf_blok(ws, 3, "Sessies per kanaal",
        ["Kanaal", "Gebruikers", "Sessies", "Engaged sessies",
         "Engagement rate", "Conversies", "Conv. rate"],
        kanaal_rijen,
        totaal_rij=["✦ TOTAAL", totaal_users, totaal_sess, "", "", totaal_conv, ""],
        num_kolommen=7)

    vr = schrijf_blok(ws, vr, "Nieuwe vs terugkerende gebruikers",
        ["Type gebruiker", "Gebruikers", "Sessies", "Engagement rate", "Conversies"],
        nvr_rijen, num_kolommen=5)

    vr = schrijf_blok(ws, vr, "Top 20 source / medium",
        ["Source", "Medium", "Gebruikers", "Sessies", "Engagement rate", "Conversies"],
        sm_rijen, num_kolommen=6)

    stel_kolombreedte_in(ws, [(0,200),(1,160),(2,140),(3,160),(4,160),(5,130),(6,130)])
    terugkerend = sum(r[1] for r in nvr_rijen if "Terugkerende" in r[0]) if nvr_rijen else 0
    print(f"  -> {totaal_users} gebruikers | {len(kanaal_rijen)} kanalen")
    return terugkerend


# ============================================================
# 6. GA4 — GEDRAG (Landingspagina's + Events + Apparaat)
# ============================================================

def haal_ga4_gedrag(ga4_client, spreadsheet, start_datum, vandaag):
    print(f"\n[GA4 Gedrag] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "GA4 — Gedrag")

    # Top landingspagina's
    req1 = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="landingPage")],
        metrics=[
            Metric(name="sessions"), Metric(name="totalUsers"),
            Metric(name="engagedSessions"), Metric(name="engagementRate"),
            Metric(name="bounceRate"), Metric(name="conversions"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=25,
    )
    res1 = ga4_client.run_report(req1)
    lp_rijen = []
    for row in res1.rows:
        lp_rijen.append([
            row.dimension_values[0].value[:60],
            int(row.metric_values[0].value),
            int(row.metric_values[1].value),
            int(row.metric_values[2].value),
            f"{round(float(row.metric_values[3].value)*100,1)}%",
            f"{round(float(row.metric_values[4].value)*100,1)}%",
            int(float(row.metric_values[5].value)),
            format_tijd(row.metric_values[6].value),
        ])

    # Top events
    req2 = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount"), Metric(name="totalUsers"),
                 Metric(name="eventCountPerUser")],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
        limit=25,
    )
    res2 = ga4_client.run_report(req2)
    event_rijen = []
    for row in res2.rows:
        event_rijen.append([
            row.dimension_values[0].value,
            int(row.metric_values[0].value),
            int(row.metric_values[1].value),
            round(float(row.metric_values[2].value), 2),
        ])

    # Apparaat + browser
    req3 = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="deviceCategory"), Dimension(name="browser")],
        metrics=[Metric(name="totalUsers"), Metric(name="sessions"),
                 Metric(name="engagementRate"), Metric(name="conversions")],
        date_ranges=[DateRange(start_date=start_datum, end_date="today")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=20,
    )
    res3 = ga4_client.run_report(req3)
    apparaat_rijen = []
    for row in res3.rows:
        apparaat_rijen.append([
            row.dimension_values[0].value,
            row.dimension_values[1].value,
            int(row.metric_values[0].value),
            int(row.metric_values[1].value),
            f"{round(float(row.metric_values[2].value)*100,1)}%",
            int(float(row.metric_values[3].value)),
        ])

    schrijf_paginatitel(ws, f"GA4 — Gedrag  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}", "H")

    vr = schrijf_blok(ws, 3, "Top 25 landingspagina's",
        ["Pagina", "Sessies", "Gebruikers", "Engaged sessies",
         "Engagement rate", "Bounce rate", "Conversies", "Gem. duur"],
        lp_rijen, num_kolommen=8)

    vr = schrijf_blok(ws, vr, "Top 25 events",
        ["Event naam", "Aantal events", "Gebruikers", "Events per gebruiker"],
        event_rijen, num_kolommen=4)

    vr = schrijf_blok(ws, vr, "Apparaat & browser",
        ["Apparaat", "Browser", "Gebruikers", "Sessies", "Engagement rate", "Conversies"],
        apparaat_rijen, num_kolommen=6)

    stel_kolombreedte_in(ws, [(0,300),(1,130),(2,130),(3,150),(4,150),(5,130),(6,120),(7,130)])
    print(f"  -> {len(lp_rijen)} landingspagina's | {len(event_rijen)} events")


# ============================================================
# 7. META ADS — OVERZICHT + FUNNEL
# ============================================================

def haal_meta_ads_overzicht(spreadsheet, vandaag):
    print(f"\n[Meta Ads Overzicht] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "META — Ads Overzicht")

    url    = f"https://graph.facebook.com/v18.0/{META_AD_ACC_ID}/insights"
    params = {
        "access_token": META_TOKEN,
        "date_preset": f"last_{PERIODE_DAGEN}d",
        "fields": (
            "spend,impressions,reach,frequency,"
            "inline_link_clicks,unique_clicks,"
            "actions,"
            "cpm,cpc,ctr,cpp,purchase_roas"
        ),
    }
    res = requests.get(url, params=params).json()

    if "error" in res:
        print(f"  ⚠ {res['error'].get('message','onbekend')}")
        return 0.0, 0

    d = res.get("data", [{}])[0] if res.get("data") else {}

    spend      = float(d.get("spend", 0))
    impressies = int(d.get("impressions", 0))
    bereik     = int(d.get("reach", 0))
    freq       = round(float(d.get("frequency", 0)), 2)
    klikken    = int(d.get("inline_link_clicks", 0))
    uniek_klik = int(d.get("unique_clicks", 0))
    lp_views   = 0  # landing_page_views niet beschikbaar via insights API
    cpm        = round(float(d.get("cpm", 0)), 2)
    cpc        = round(float(d.get("cpc", 0)), 2)
    ctr        = round(float(d.get("ctr", 0)), 2)
    cpp        = round(float(d.get("cpp", 0)), 2)

    # Leads tellen
    leads = 0
    for a in d.get("actions", []):
        if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
            leads += int(a.get("value", 0))

    cpl      = round(spend / leads, 2) if leads > 0 else "—"
    roas_raw = d.get("purchase_roas", [])
    roas     = round(float(roas_raw[0]["value"]), 2) if roas_raw else "—"
    cplv     = round(spend / lp_views, 2) if lp_views > 0 else "—"

    # KPI rij
    kpi_headers = ["Spend", "Impressies", "Bereik", "Frequentie",
                   "Klikken", "Unieke klikken", "LP views", "CPM",
                   "CPC", "CTR", "CPP", "Leads", "CPL", "ROAS", "Cost/LP view"]
    kpi_waarden = [
        eur(spend), f"{impressies:,}", f"{bereik:,}", str(freq),
        f"{klikken:,}", f"{uniek_klik:,}", f"{lp_views:,}",
        eur(cpm), eur(cpc), f"{ctr}%", eur(cpp),
        str(leads), eur(cpl), str(roas), eur(cplv),
    ]

    # Funnel
    funnel_rijen = [
        ["1. Impressies",      impressies, "100%",     "Totaal vertoningen"],
        ["2. Bereik",          bereik,     pct(bereik, impressies), "Unieke mensen bereikt"],
        ["3. Klikken",         klikken,    pct(klikken, impressies), "CTR op impressies"],
        ["4. LP views",        lp_views,   pct(lp_views, klikken),  "Van klik naar pagina"],
        ["5. Leads",           leads,      pct(leads, lp_views),    "Van LP naar lead"],
    ]

    schrijf_paginatitel(ws, f"META — Ads Overzicht  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}", "O")

    vr = schrijf_blok(ws, 3, f"KPI Samenvatting — afgelopen {PERIODE_DAGEN} dagen",
        kpi_headers, [kpi_waarden], num_kolommen=15)
    ws.batch_format([{"range": f"A{vr-2}:O{vr-2}", "format": STIJL_KPI_WAARDE}])

    vr = schrijf_blok(ws, vr, "Funnel: Impressies → Bereik → Klik → LP → Lead",
        ["Stap", "Aantal", "Conversie %", "Toelichting"],
        funnel_rijen, num_kolommen=4)

    stel_kolombreedte_in(ws, [(i, 140) for i in range(15)])
    print(f"  -> EUR {spend:.2f} spend | {leads} leads | CPL {eur(cpl)}")
    return (spend, leads, cpl, impressies, bereik, freq, klikken, ctr, cpm)


# ============================================================
# 8. META ADS — CAMPAGNE NIVEAU
# ============================================================

def haal_meta_ads_campagnes(spreadsheet, vandaag):
    print(f"\n[Meta Ads Campagnes] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "META — Ads Campagnes")

    url    = f"https://graph.facebook.com/v18.0/{META_AD_ACC_ID}/insights"
    params = {
        "access_token": META_TOKEN,
        "date_preset": f"last_{PERIODE_DAGEN}d",
        "fields": (
            "campaign_name,campaign_id,objective,"
            "spend,impressions,reach,frequency,"
            "inline_link_clicks,ctr,cpm,cpc,"
            "actions,purchase_roas"
        ),
        "level": "campaign",
    }
    res = requests.get(url, params=params).json()

    if "error" in res:
        print(f"  ⚠ {res['error'].get('message','onbekend')}")
        return

    rijen = []
    totaal_spend = totaal_impr = totaal_klikken = totaal_leads = 0

    for item in res.get("data", []):
        spend  = float(item.get("spend", 0))
        impr   = int(item.get("impressions", 0))
        klikken = int(item.get("inline_link_clicks", 0))
        freq   = round(float(item.get("frequency", 0)), 2)
        ctr    = round(float(item.get("ctr", 0)), 2)
        cpm    = round(float(item.get("cpm", 0)), 2)
        cpc    = round(float(item.get("cpc", 0)), 2)
        lp     = 0  # landing_page_views niet beschikbaar

        leads = sum(int(a.get("value", 0)) for a in item.get("actions", [])
                    if a.get("action_type") in ("lead","offsite_conversion.fb_pixel_lead"))

        cpl      = round(spend / leads, 2) if leads > 0 else "—"
        roas_raw = item.get("purchase_roas", [])
        roas     = round(float(roas_raw[0]["value"]), 2) if roas_raw else "—"
        cplv     = round(spend / lp, 2) if lp > 0 else "—"

        rijen.append([
            item.get("campaign_name", "—"),
            item.get("objective", "—"),
            eur(spend), f"{impr:,}", f"{freq}x",
            f"{klikken:,}", f"{ctr}%", eur(cpm), eur(cpc),
            f"{lp:,}", eur(cplv), str(leads), eur(cpl), str(roas),
        ])
        totaal_spend += spend; totaal_impr += impr
        totaal_klikken += klikken; totaal_leads += leads

    totaal_cpl = round(totaal_spend / totaal_leads, 2) if totaal_leads > 0 else "—"

    schrijf_paginatitel(ws, f"META — Ads Campagnes  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}", "N")

    schrijf_blok(ws, 3, "Campagnes — detail",
        ["Campagne", "Doel", "Spend", "Impressies", "Freq.",
         "Klikken", "CTR", "CPM", "CPC",
         "LP views", "Cost/LP", "Leads", "CPL", "ROAS"],
        rijen,
        totaal_rij=["✦ TOTAAL", "", eur(totaal_spend), f"{totaal_impr:,}",
                    "", f"{totaal_klikken:,}", "", "", "",
                    "", str(totaal_leads), eur(totaal_cpl), ""],
        num_kolommen=14)

    stel_kolombreedte_in(ws, [(0, 250), (1, 160)] + [(i, 120) for i in range(2, 14)])
    print(f"  -> {len(rijen)} campagnes")


# ============================================================
# 9. META ADS — ADSET NIVEAU
# ============================================================

def haal_meta_ads_adsets(spreadsheet, vandaag):
    print(f"\n[Meta Ads Adsets] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "META — Ads Adsets")

    url    = f"https://graph.facebook.com/v18.0/{META_AD_ACC_ID}/insights"
    params = {
        "access_token": META_TOKEN,
        "date_preset": f"last_{PERIODE_DAGEN}d",
        "fields": (
            "campaign_name,adset_name,"
            "spend,impressions,reach,frequency,"
            "inline_link_clicks,ctr,cpm,cpc,actions"
        ),
        "level": "adset",
    }
    res = requests.get(url, params=params).json()

    if "error" in res:
        print(f"  ⚠ {res['error'].get('message','onbekend')}")
        return

    rijen = []
    for item in res.get("data", []):
        spend   = float(item.get("spend", 0))
        impr    = int(item.get("impressions", 0))
        klikken = int(item.get("inline_link_clicks", 0))
        freq    = round(float(item.get("frequency", 0)), 2)
        ctr     = round(float(item.get("ctr", 0)), 2)
        cpm     = round(float(item.get("cpm", 0)), 2)
        cpc     = round(float(item.get("cpc", 0)), 2)

        leads = sum(int(a.get("value", 0)) for a in item.get("actions", [])
                    if a.get("action_type") in ("lead","offsite_conversion.fb_pixel_lead"))
        cpl = round(spend / leads, 2) if leads > 0 else "—"

        rijen.append([
            item.get("campaign_name", "—"),
            item.get("adset_name", "—"),
            eur(spend), f"{impr:,}", f"{freq}x",
            f"{klikken:,}", f"{ctr}%", eur(cpm), eur(cpc),
            str(leads), eur(cpl),
        ])

    schrijf_paginatitel(ws, f"META — Ads Adsets  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}", "K")

    schrijf_blok(ws, 3, "Adsets — detail per doelgroep",
        ["Campagne", "Adset", "Spend", "Impressies", "Freq.",
         "Klikken", "CTR", "CPM", "CPC", "Leads", "CPL"],
        rijen, num_kolommen=11)

    stel_kolombreedte_in(ws, [(0,200),(1,220)] + [(i,120) for i in range(2,11)])
    print(f"  -> {len(rijen)} adsets")


# ============================================================
# 10. META ADS — AD NIVEAU (Creatives)
# ============================================================

def haal_meta_ads_ads(spreadsheet, vandaag):
    print(f"\n[Meta Ads — Ads] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "META — Ads Creative")

    url    = f"https://graph.facebook.com/v18.0/{META_AD_ACC_ID}/insights"
    params = {
        "access_token": META_TOKEN,
        "date_preset": f"last_{PERIODE_DAGEN}d",
        "fields": (
            "campaign_name,adset_name,ad_name,"
            "spend,impressions,reach,inline_link_clicks,"
            "ctr,cpm,cpc,actions"
        ),
        "level": "ad",
    }
    res = requests.get(url, params=params).json()

    if "error" in res:
        print(f"  ⚠ {res['error'].get('message','onbekend')}")
        return

    rijen = []
    for item in res.get("data", []):
        spend   = float(item.get("spend", 0))
        impr    = int(item.get("impressions", 0))
        bereik  = int(item.get("reach", 0))
        klikken = int(item.get("inline_link_clicks", 0))
        ctr     = round(float(item.get("ctr", 0)), 2)
        cpm     = round(float(item.get("cpm", 0)), 2)
        cpc     = round(float(item.get("cpc", 0)), 2)

        leads = sum(int(a.get("value", 0)) for a in item.get("actions", [])
                    if a.get("action_type") in ("lead","offsite_conversion.fb_pixel_lead"))
        cpl = round(spend / leads, 2) if leads > 0 else "—"

        rijen.append([
            item.get("campaign_name", "—"),
            item.get("adset_name", "—"),
            item.get("ad_name", "—"),
            eur(spend), f"{impr:,}", f"{bereik:,}",
            f"{klikken:,}", f"{ctr}%", eur(cpm), eur(cpc),
            str(leads), eur(cpl),
        ])

    schrijf_paginatitel(ws, f"META — Ads Creative  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}", "L")

    schrijf_blok(ws, 3, "Ad niveau — creative performance",
        ["Campagne", "Adset", "Ad naam", "Spend", "Impressies",
         "Bereik", "Klikken", "CTR", "CPM", "CPC", "Leads", "CPL"],
        rijen, num_kolommen=12)

    stel_kolombreedte_in(ws, [(0,180),(1,180),(2,200)] + [(i,120) for i in range(3,12)])
    print(f"  -> {len(rijen)} ads")


# ============================================================
# 11. FACEBOOK ORGANIC
# ============================================================

def haal_facebook_organic(spreadsheet, vandaag):
    print(f"\n[Facebook Organic] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "FACEBOOK — Org")

    # STAP 1: Haal Page Access Token op via /me/accounts (zoals werkende code)
    accounts_res = requests.get(
        f"https://graph.facebook.com/v22.0/me/accounts",
        params={"access_token": FB_TOKEN}
    ).json()

    if "error" in accounts_res:
        print(f"  ⚠ FB accounts fout: {accounts_res['error'].get('message','onbekend')}")
        return 0, 0, 0, 0, 0

    selected_page = next(
        (p for p in accounts_res.get("data", []) if p["id"] == FB_PAGE_ID),
        None
    )

    if not selected_page:
        # Probeer op naam als ID niet matcht
        selected_page = next(
            (p for p in accounts_res.get("data", [])), None
        )

    if not selected_page:
        print(f"  ⚠ Pagina niet gevonden in accounts")
        return 0, 0, 0, 0, 0

    PAGE_ID  = selected_page["id"]
    PAT      = selected_page["access_token"]   # Page Access Token
    pagina_naam = selected_page["name"]
    print(f"  -> Pagina gevonden: {pagina_naam} (ID: {PAGE_ID})")

    # STAP 2: Totaal fans
    p_res = requests.get(
        f"https://graph.facebook.com/v22.0/{PAGE_ID}",
        params={"fields": "fan_count,followers_count", "access_token": PAT}
    ).json()
    fan_count  = p_res.get("fan_count", 0)
    followers  = p_res.get("followers_count", 0)

    # STAP 3: Paginastatistieken via insights (elk apart voor robuustheid)
    werkende_metrics = []
    fans_added = fans_removed = fb_bereik_uniek = fb_engagements = 0

    for metric in ["page_impressions_unique", "page_post_engagements",
                   "page_fan_adds", "page_fan_removes", "page_views_total"]:
        try:
            r = requests.get(
                f"https://graph.facebook.com/v22.0/{PAGE_ID}/insights/{metric}/day",
                params={
                    "access_token": PAT,
                    "since": int((datetime.datetime.now() - datetime.timedelta(days=28)).timestamp()),
                    "until": int(datetime.datetime.now().timestamp()),
                },
                timeout=10
            ).json()
            if "data" in r and r["data"]:
                totaal = sum(
                    v.get("value", 0) if isinstance(v.get("value"), (int, float))
                    else sum(v.get("value", {}).values()) if isinstance(v.get("value"), dict)
                    else 0
                    for entry in r["data"]
                    for v in entry.get("values", [])
                )
                werkende_metrics.append([metric, int(totaal), "28 dagen gesommeerd"])
                if metric == "page_fan_adds":       fans_added    = int(totaal)
                if metric == "page_fan_removes":    fans_removed  = int(totaal)
                if metric == "page_impressions_unique": fb_bereik_uniek = int(totaal)
                if metric == "page_post_engagements":   fb_engagements  = int(totaal)
        except Exception:
            pass

    net_groei = fans_added - fans_removed

    # STAP 4: Posts ophalen met Page Access Token (laatste 28 dagen)
    res_posts = requests.get(
        f"https://graph.facebook.com/v22.0/{PAGE_ID}/posts",
        params={
            "fields": "id,message,created_time,permalink_url,status_type,attachments{media}",
            "access_token": PAT,
            "limit": 50,
        },
        timeout=15
    ).json()

    if "error" in res_posts:
        print(f"  ⚠ FB Posts fout: {res_posts['error'].get('message','onbekend')}")

    post_rijen = []
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=28)

    for post in res_posts.get("data", []):
        p_time = datetime.datetime.strptime(
            post["created_time"].split("+")[0], "%Y-%m-%dT%H:%M:%S"
        )
        if p_time < cutoff:
            continue

        # STAP 5: Per-post insights met Page Access Token
        i_res = requests.get(
            f"https://graph.facebook.com/v22.0/{post['id']}/insights",
            params={
                "metric": "post_impressions_unique,post_engagements,"
                          "post_reactions_by_type_total,post_activity_by_action_type",
                "access_token": PAT,
            },
            timeout=7
        ).json()

        metrics_post = {
            item["name"]: item["values"][0]["value"]
            for item in i_res.get("data", [])
        }

        bereik    = metrics_post.get("post_impressions_unique", 0)
        reactions = metrics_post.get("post_reactions_by_type_total", {})
        likes     = sum(reactions.values()) if isinstance(reactions, dict) else 0
        activity  = metrics_post.get("post_activity_by_action_type", {})
        shares    = activity.get("share", 0) if isinstance(activity, dict) else 0
        eng_meta  = metrics_post.get("post_engagements", 0)

        # Comments apart ophalen
        c_res    = requests.get(
            f"https://graph.facebook.com/v22.0/{post['id']}/comments",
            params={"summary": "total_count", "access_token": PAT},
            timeout=7
        ).json()
        comments = c_res.get("summary", {}).get("total_count", 0)

        eng_totaal = max(eng_meta, likes + comments + shares)
        er         = round((eng_totaal / bereik * 100), 2) if bereik > 0 else "—"

        # Visual
        visual = ""
        try:
            visual = post["attachments"]["data"][0]["media"]["image"]["src"]
        except Exception:
            pass

        datum   = p_time.strftime("%d-%m-%Y")
        bericht = (post.get("message", "") or "")[:80]
        soort   = post.get("status_type", "bericht")

        post_rijen.append([
            datum, soort, bericht,
            bereik, likes, comments, shares,
            eng_totaal,
            f"{er}%" if er != "—" else "—",
            fan_count,
            post.get("permalink_url", ""),
        ])

        time.sleep(0.3)  # Kleine pauze per post om rate limit te vermijden

    # ---- Tabblad opbouwen ----
    schrijf_paginatitel(ws, f"FACEBOOK — Org  |  {pagina_naam}  |  Peildatum: {vandaag}", "K")

    vr = schrijf_blok(ws, 3, "Pagina samenvatting",
        ["Pagina naam", "Fans (likes)", "Volgers"],
        [[pagina_naam, fan_count, followers]], num_kolommen=3)
    ws.batch_format([{"range": f"A{vr-2}:C{vr-2}", "format": STIJL_KPI_WAARDE}])

    time.sleep(1)
    vr = schrijf_blok(ws, vr, "Paginastatistieken — afgelopen 28 dagen",
        ["Metric", "Waarde (gesommeerd)", "Periode"],
        werkende_metrics if werkende_metrics else [["Geen data", "", ""]],
        num_kolommen=3)

    vr = schrijf_blok(ws, vr, "Follower groei — afgelopen 28 dagen",
        ["Nieuwe volgers", "Ontvolgingen", "Netto groei"],
        [[fans_added, fans_removed, net_groei]], num_kolommen=3)
    ws.batch_format([{"range": f"A{vr-2}:C{vr-2}", "format": STIJL_KPI_WAARDE}])

    time.sleep(1)
    vr = schrijf_blok(ws, vr, f"Posts — detail (afgelopen 28 dagen, {len(post_rijen)} posts)",
        ["Datum", "Type", "Bericht", "Bereik", "Likes",
         "Comments", "Shares", "Engagement", "Eng. rate",
         "Totaal volgers", "Link"],
        post_rijen if post_rijen else [["Geen posts gevonden"] + [""] * 10],
        totaal_rij=["✦ TOTAAL", "", "",
                    sum(r[3] for r in post_rijen),
                    sum(r[4] for r in post_rijen),
                    sum(r[5] for r in post_rijen),
                    sum(r[6] for r in post_rijen),
                    sum(r[7] for r in post_rijen),
                    "", "", ""] if post_rijen else None,
        num_kolommen=11)

    stel_kolombreedte_in(ws, [
        (0,110),(1,140),(2,300),(3,100),(4,90),
        (5,100),(6,90),(7,110),(8,110),(9,130),(10,260)
    ])

    print(f"  -> {len(post_rijen)} posts | fans: {fan_count} | netto groei: {net_groei}")
    return fans_added, net_groei, fan_count, fb_bereik_uniek, fb_engagements


def haal_instagram(spreadsheet, vandaag):
    print(f"\n[Instagram] Ophalen...")
    ws = haal_of_maak_sheet(spreadsheet, "INSTAGRAM — Org")

    # 1. Account info
    res_info = requests.get(
        f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}",
        params={
            "fields": "username,followers_count,follows_count,media_count,biography,website",
            "access_token": META_TOKEN,
        }
    ).json()

    volgers      = res_info.get("followers_count", 0)
    volgend      = res_info.get("follows_count", 0)
    media_aantal = res_info.get("media_count", 0)
    username     = res_info.get("username", "—")

    # 2. Account insights (bereik, impressies, profielbezoeken etc.)
    res_insights = requests.get(
        f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/insights",
        params={
            "metric": "reach,impressions,profile_views,follower_count,website_clicks",
            "period": "days_28",
            "access_token": META_TOKEN,
        }
    ).json()

    insights_rijen = []
    for item in res_insights.get("data", []):
        waarde    = item.get("values", [{}])[-1].get("value", "—")
        peildatum = item.get("values", [{}])[-1].get("end_time", "")[:10]
        insights_rijen.append([item.get("title", item.get("name", "—")), waarde, peildatum])

    # 3. Media ophalen + per-post insights (zoals de werkende code)
    res_media = requests.get(
        f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media",
        params={
            "fields": "id,caption,media_type,media_url,timestamp,permalink,like_count,comments_count",
            "limit": 25,
            "access_token": META_TOKEN,
        }
    ).json()

    post_rijen   = []
    type_stats   = {}
    totaal_likes = totaal_comments = totaal_saves = totaal_shares = totaal_bereik = totaal_eng_sum = 0

    for post in res_media.get("data", []):
        pid    = post["id"]
        datum  = post.get("timestamp", "")[:10]
        soort  = post.get("media_type", "—")
        caption = (post.get("caption", "") or "")[:60]
        likes   = post.get("like_count", 0)
        comments = post.get("comments_count", 0)

        # Per-post insights — metrics afhankelijk van type
        if soort == "VIDEO":
            metrics = "reach,plays,shares,saved"
        else:
            metrics = "reach,shares,saved,total_interactions,follows"

        i_res = requests.get(
            f"https://graph.facebook.com/v19.0/{pid}/insights",
            params={"metric": metrics, "access_token": META_TOKEN},
            timeout=7
        ).json()

        ins = {}
        for item in i_res.get("data", []):
            ins[item["name"]] = item.get("values", [{}])[0].get("value", 0)

        bereik  = ins.get("reach", 0)
        shares  = ins.get("shares", 0)
        saves   = ins.get("saved", 0)
        follows = ins.get("follows", 0)
        weergaven = ins.get("plays") or ins.get("total_interactions") or 0

        totaal_eng  = likes + comments + shares + saves
        eng_rate    = round((totaal_eng / bereik * 100), 2) if bereik > 0 else "—"

        post_rijen.append([
            datum, soort, caption,
            likes, comments, shares, saves,
            bereik, weergaven, follows,
            totaal_eng,
            f"{eng_rate}%" if eng_rate != "—" else "—",
            post.get("permalink", ""),
        ])

        # Per content type aggregeren
        if soort not in type_stats:
            type_stats[soort] = {"posts": 0, "likes": 0, "comments": 0,
                                  "saves": 0, "shares": 0, "bereik": 0, "eng": 0}
        type_stats[soort]["posts"]    += 1
        type_stats[soort]["likes"]    += likes
        type_stats[soort]["comments"] += comments
        type_stats[soort]["saves"]    += saves
        type_stats[soort]["shares"]   += shares
        type_stats[soort]["bereik"]   += bereik
        type_stats[soort]["eng"]      += totaal_eng

        totaal_likes    += likes
        totaal_comments += comments
        totaal_saves    += saves
        totaal_shares   += shares
        totaal_bereik   += bereik
        totaal_eng_sum  += totaal_eng

    gem_eng = round((totaal_eng_sum / totaal_bereik * 100), 2) if totaal_bereik > 0 else "—"

    # Content type samenvatting
    type_rijen = []
    for soort, s in type_stats.items():
        avg_eng = round((s["eng"] / s["bereik"] * 100), 2) if s["bereik"] > 0 else "—"
        type_rijen.append([
            soort, s["posts"], s["likes"], s["comments"],
            s["saves"], s["shares"], s["bereik"],
            f"{avg_eng}%" if avg_eng != "—" else "—",
        ])

    # Stories
    res_stories = requests.get(
        f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/insights",
        params={
            "metric": "story_exits,story_taps_forward,story_taps_back",
            "period": "days_28",
            "access_token": META_TOKEN,
        }
    ).json()
    stories_rijen = []
    for item in res_stories.get("data", []):
        waarde = item.get("values", [{}])[-1].get("value", "—")
        stories_rijen.append([item.get("title", item.get("name", "—")), waarde])

    # ---- Tabblad opbouwen ----
    schrijf_paginatitel(ws, f"INSTAGRAM — Org  |  @{username}  |  Peildatum: {vandaag}", "M")

    vr = schrijf_blok(ws, 3, "Account samenvatting",
        ["Gebruikersnaam", "Volgers", "Volgend", "Totaal posts"],
        [[f"@{username}", volgers, volgend, media_aantal]], num_kolommen=4)
    ws.batch_format([{"range": f"A{vr-2}:D{vr-2}", "format": STIJL_KPI_WAARDE}])

    vr = schrijf_blok(ws, vr, "Account insights — afgelopen 28 dagen",
        ["Metric", "Waarde", "Peildatum"],
        insights_rijen if insights_rijen else [["Geen data", "", ""]],
        num_kolommen=3)

    vr = schrijf_blok(ws, vr, "Engagement per content type",
        ["Type", "Posts", "Likes", "Comments", "Saves", "Shares", "Bereik", "Gem. eng. rate"],
        type_rijen if type_rijen else [["Geen data","","","","","","",""]],
        num_kolommen=8)

    vr = schrijf_blok(ws, vr, "Posts — detail (laatste 25)",
        ["Datum", "Type", "Caption", "Likes", "Comments", "Shares", "Saves",
         "Bereik", "Weergaven", "Nieuwe volgers", "Eng. totaal", "Eng. rate", "Link"],
        post_rijen,
        totaal_rij=["✦ TOTAAL", "", "", totaal_likes, totaal_comments,
                    totaal_shares, totaal_saves, totaal_bereik, "", "",
                    totaal_eng_sum,
                    f"{gem_eng}%" if gem_eng != "—" else "—", ""],
        num_kolommen=13)

    if stories_rijen:
        vr = schrijf_blok(ws, vr, "Stories — afgelopen 28 dagen",
            ["Metric", "Waarde"], stories_rijen, num_kolommen=2)

    stel_kolombreedte_in(ws, [
        (0,110),(1,110),(2,240),(3,90),(4,100),
        (5,90),(6,90),(7,100),(8,110),(9,130),(10,110),(11,110),(12,260)
    ])
    # Bereken totaal nieuwe volgers via posts
    ig_new_followers_totaal = sum(
        r[9] for r in post_rijen if isinstance(r[9], (int, float))
    ) if post_rijen else 0
    print(f"  -> {volgers} volgers | {len(post_rijen)} posts | gem. eng: {gem_eng}%")
    return volgers, totaal_bereik, totaal_eng_sum, gem_eng, len(post_rijen), ig_new_followers_totaal


# ============================================================
# 13. KPI OVERZICHT — Historisch
# ============================================================

def schrijf_kpi_overzicht(spreadsheet, vandaag,
                           ga4_users, ga4_sessies, ga4_conv,
                           meta_spend, meta_leads,
                           fb_fans_added, fb_net_groei,
                           ig_volgers, ig_eng, ig_bereik):
    print("\n[KPI Overzicht] Bijwerken...")
    naam = "KPI — Overzicht"

    try:
        ws         = spreadsheet.worksheet(naam)
        eerste_rij = ws.row_values(1)
        if not eerste_rij:
            raise ValueError("Leeg")
    except (gspread.exceptions.WorksheetNotFound, ValueError):
        ws = spreadsheet.add_worksheet(title=naam, rows=500, cols=20)
        ws.update([["KPI — Overzicht"]], "A1",
                  value_input_option="USER_ENTERED")
        ws.format("A1:M1", {**STIJL_SECTIETITEL,
                             "textFormat": {**STIJL_SECTIETITEL["textFormat"], "fontSize": 13}})
        ws.merge_cells("A1:M1")
        ws.update([[
            "Datum", "GA4 Gebruikers", "GA4 Sessies", "GA4 Conversies",
            "Meta Spend", "Meta Leads",
            "FB Nieuwe volgers", "FB Netto groei",
            "IG Volgers", "IG Engagement", "IG Bereik",
        ]], "A2", value_input_option="USER_ENTERED")
        ws.format("A2:K2", STIJL_HEADER)
        stel_kolombreedte_in(ws, [(i, 150) for i in range(11)])
        print(f"  + Nieuw tabblad aangemaakt: '{naam}'")

    ws.append_row([
        vandaag,
        ga4_users, ga4_sessies, ga4_conv,
        round(meta_spend, 2), meta_leads,
        fb_fans_added, fb_net_groei,
        ig_volgers, ig_eng, ig_bereik,
    ], value_input_option="USER_ENTERED")
    print(f"  ✓ Nieuwe rij toegevoegd")



# ============================================================
# JOURNEY — Overzicht (Customer Journey Samenvatting)
# ============================================================

def schrijf_journey_overzicht(spreadsheet, vandaag,
                               # GA4
                               ga4_users, ga4_sessies, ga4_conv, ga4_conv_rate,
                               ga4_bounce, ga4_engagement_rate, ga4_gem_duur,
                               ga4_new_users, ga4_return_users,
                               # Meta Ads
                               meta_spend, meta_leads, meta_cpl,
                               meta_impressies, meta_bereik, meta_freq,
                               meta_klikken, meta_ctr, meta_cpm,
                               # Instagram
                               ig_volgers, ig_bereik, ig_eng, ig_eng_rate,
                               ig_posts, ig_new_followers,
                               # Facebook
                               fb_fans, fb_bereik_uniek, fb_engagements,
                               fb_fans_added, fb_net_groei):

    print("\n[JOURNEY Overzicht] Schrijven...")
    ws = haal_of_maak_sheet(spreadsheet, "JOURNEY — Overzicht")

    # Kleuren per fase
    FASE_BEWUST    = {"backgroundColor": {"red": 0.17, "green": 0.36, "blue": 0.60},
                      "textFormat": {"bold": True, "fontSize": 12,
                                     "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                      "horizontalAlignment": "CENTER"}
    FASE_INTERESSE = {"backgroundColor": {"red": 0.13, "green": 0.55, "blue": 0.45},
                      "textFormat": {"bold": True, "fontSize": 12,
                                     "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                      "horizontalAlignment": "CENTER"}
    FASE_OVER      = {"backgroundColor": {"red": 0.60, "green": 0.40, "blue": 0.10},
                      "textFormat": {"bold": True, "fontSize": 12,
                                     "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                      "horizontalAlignment": "CENTER"}
    FASE_ACTIE     = {"backgroundColor": {"red": 0.18, "green": 0.50, "blue": 0.18},
                      "textFormat": {"bold": True, "fontSize": 12,
                                     "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                      "horizontalAlignment": "CENTER"}
    FASE_LOYAL     = {"backgroundColor": {"red": 0.40, "green": 0.20, "blue": 0.60},
                      "textFormat": {"bold": True, "fontSize": 12,
                                     "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                      "horizontalAlignment": "CENTER"}

    STIJL_FASE_RIJ = {"backgroundColor": {"red": 0.93, "green": 0.96, "blue": 1.0},
                       "textFormat": {"bold": False}}
    STIJL_KPI_GROOT = {"textFormat": {"bold": True, "fontSize": 14},
                        "horizontalAlignment": "CENTER"}
    STIJL_LABEL    = {"textFormat": {"bold": True, "fontSize": 10},
                       "horizontalAlignment": "LEFT",
                       "backgroundColor": {"red": 0.97, "green": 0.97, "blue": 0.97}}
    STIJL_PIJL     = {"textFormat": {"bold": True, "fontSize": 18},
                       "horizontalAlignment": "CENTER",
                       "backgroundColor": {"red": 1, "green": 1, "blue": 1}}

    # ---- Paginatitel ----
    time.sleep(1)
    ws.update([
        [f"CUSTOMER JOURNEY — IVECO Schouten  |  Periode: {PERIODE_DAGEN} dagen t/m {vandaag}"]
    ], "A1", value_input_option="USER_ENTERED")
    ws.format("A1:H1", {
        "backgroundColor": {"red": 0.05, "green": 0.12, "blue": 0.25},
        "textFormat": {"bold": True, "fontSize": 16,
                       "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER",
    })
    ws.merge_cells("A1:H1")

    # ---- Ondertitel ----
    time.sleep(0.5)
    ws.update([["Van eerste zichtbaarheid tot loyale klant"]], "A2",
              value_input_option="USER_ENTERED")
    ws.format("A2:H2", {
        "backgroundColor": {"red": 0.10, "green": 0.20, "blue": 0.40},
        "textFormat": {"italic": True, "fontSize": 11,
                       "foregroundColor": {"red": 0.8, "green": 0.9, "blue": 1.0}},
        "horizontalAlignment": "CENTER",
    })
    ws.merge_cells("A2:H2")

    # ---- Fase headers (rij 4) ----
    fases = [
        "👁  BEWUSTWORDING",
        "→",
        "💡  INTERESSE",
        "→",
        "🔍  OVERWEGING",
        "→",
        "✅  ACTIE",
        "→",
    ]
    time.sleep(1)
    ws.update([fases], "A4", value_input_option="USER_ENTERED")
    time.sleep(2)
    ws.batch_format([
        {"range": "A4", "format": FASE_BEWUST},
        {"range": "B4", "format": STIJL_PIJL},
        {"range": "C4", "format": FASE_INTERESSE},
        {"range": "D4", "format": STIJL_PIJL},
        {"range": "E4", "format": FASE_OVER},
        {"range": "F4", "format": STIJL_PIJL},
        {"range": "G4", "format": FASE_ACTIE},
        {"range": "H4", "format": STIJL_PIJL},
    ])

    # ---- Bronnen (rij 5) ----
    time.sleep(0.5)
    ws.update([[
        "Instagram + Facebook + Meta Ads", "",
        "Instagram + Facebook Organic", "",
        "GA4 Website", "",
        "GA4 Conversies + Meta Leads", "",
    ]], "A5", value_input_option="USER_ENTERED")
    ws.format("A5:H5", {"textFormat": {"italic": True, "fontSize": 9},
                         "horizontalAlignment": "CENTER",
                         "backgroundColor": {"red": 0.95, "green": 0.97, "blue": 1.0}})

    # ============================================================
    # FASE 1 — BEWUSTWORDING (kolom A)
    # ============================================================
    bereik_totaal = ig_bereik + fb_bereik_uniek + meta_bereik
    cpm_label     = f"EUR {meta_cpm:.2f}" if isinstance(meta_cpm, float) else str(meta_cpm)

    fase1 = [
        ["Totaal bereik (alle kanalen)",  f"{bereik_totaal:,}"],
        ["├ Instagram bereik",            f"{ig_bereik:,}"],
        ["├ Facebook bereik",             f"{fb_bereik_uniek:,}"],
        ["└ Meta Ads bereik",             f"{meta_bereik:,}"],
        ["", ""],
        ["Meta Ads impressies",           f"{meta_impressies:,}"],
        ["Meta Ads frequentie",           f"{meta_freq}x gezien"],
        ["Meta Ads CPM",                  cpm_label],
        ["", ""],
        ["Instagram nieuwe volgers",      f"+{ig_new_followers}"],
        ["Facebook netto groei",          f"+{fb_net_groei}"],
    ]

    # ============================================================
    # FASE 2 — INTERESSE (kolom C)
    # ============================================================
    eng_totaal = ig_eng + fb_engagements
    ig_eng_str = f"{ig_eng_rate}%" if ig_eng_rate != "—" else "—"

    fase2 = [
        ["Totaal engagement",             f"{eng_totaal:,}"],
        ["├ Instagram engagement",        f"{ig_eng:,}"],
        ["└ Facebook engagement",         f"{fb_engagements:,}"],
        ["", ""],
        ["Instagram engagement rate",     ig_eng_str],
        ["Instagram posts geanalyseerd",  str(ig_posts)],
        ["", ""],
        ["Meta Ads CTR",                  f"{meta_ctr}%"],
        ["Meta Ads klikken",              f"{meta_klikken:,}"],
        ["", ""],
        ["", ""],
    ]

    # ============================================================
    # FASE 3 — OVERWEGING (kolom E)
    # ============================================================
    bounce_str   = f"{ga4_bounce}" if ga4_bounce != "—" else "—"
    eng_r_str    = f"{ga4_engagement_rate}" if ga4_engagement_rate != "—" else "—"

    fase3 = [
        ["Website sessies",               f"{ga4_sessies:,}"],
        ["Website gebruikers",            f"{ga4_users:,}"],
        ["└ Nieuw",                       f"{ga4_new_users:,}"],
        ["└ Terugkerend",                 f"{ga4_return_users:,}"],
        ["", ""],
        ["Gem. sessieduur",               str(ga4_gem_duur)],
        ["Engagement rate",               eng_r_str],
        ["Bounce rate",                   bounce_str],
        ["", ""],
        ["", ""],
        ["", ""],
    ]

    # ============================================================
    # FASE 4 — ACTIE (kolom G)
    # ============================================================
    cpl_str = f"EUR {meta_cpl:.2f}" if isinstance(meta_cpl, float) else str(meta_cpl)
    conv_r  = f"{ga4_conv_rate}%" if ga4_conv_rate != "—" else "—"
    leads_totaal = meta_leads

    fase4 = [
        ["Totaal conversies (GA4)",       str(ga4_conv)],
        ["Conv. rate",                    conv_r],
        ["", ""],
        ["Meta Ads leads",                str(meta_leads)],
        ["Cost per lead (CPL)",           cpl_str],
        ["Meta Ads spend",                f"EUR {meta_spend:.2f}"],
        ["", ""],
        ["", ""],
        ["", ""],
        ["", ""],
        ["", ""],
    ]

    # ---- Schrijf alle fase-data in kolommen ----
    max_rijen = max(len(fase1), len(fase2), len(fase3), len(fase4))
    start_rij = 7

    # Bouw alle rijen in één lijst
    alle_rijen = []
    for i in range(max_rijen):
        rij_data = [
            fase1[i][0] if i < len(fase1) else "", fase1[i][1] if i < len(fase1) else "",
            fase2[i][0] if i < len(fase2) else "", fase2[i][1] if i < len(fase2) else "",
            fase3[i][0] if i < len(fase3) else "", fase3[i][1] if i < len(fase3) else "",
            fase4[i][0] if i < len(fase4) else "", fase4[i][1] if i < len(fase4) else "",
        ]
        alle_rijen.append(rij_data)

    # 1 update call voor alle data
    time.sleep(2)
    ws.update(alle_rijen, f"A{start_rij}", value_input_option="USER_ENTERED")

    # Bouw alle format ranges in 1 batch
    format_ranges = []
    for i in range(max_rijen):
        rij_num = start_rij + i
        format_ranges.append({"range": f"A{rij_num}", "format": STIJL_LABEL})
        format_ranges.append({"range": f"B{rij_num}", "format": STIJL_KPI_GROOT})
        format_ranges.append({"range": f"C{rij_num}", "format": STIJL_LABEL})
        format_ranges.append({"range": f"D{rij_num}", "format": STIJL_KPI_GROOT})
        format_ranges.append({"range": f"E{rij_num}", "format": STIJL_LABEL})
        format_ranges.append({"range": f"F{rij_num}", "format": STIJL_KPI_GROOT})
        format_ranges.append({"range": f"G{rij_num}", "format": STIJL_LABEL})
        format_ranges.append({"range": f"H{rij_num}", "format": STIJL_KPI_GROOT})

    # 1 batch_format call voor alle opmaak
    time.sleep(2)
    ws.batch_format(format_ranges)

    # ---- Funnel samenvatting onderaan ----
    funnel_rij = start_rij + max_rijen + 2
    time.sleep(1)
    ws.update([[
        "FUNNEL SAMENVATTING", "", "", "", "", "", "", ""
    ]], f"A{funnel_rij}", value_input_option="USER_ENTERED")
    ws.format(f"A{funnel_rij}:H{funnel_rij}", {
        "backgroundColor": {"red": 0.05, "green": 0.12, "blue": 0.25},
        "textFormat": {"bold": True, "fontSize": 12,
                       "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER",
    })
    ws.merge_cells(f"A{funnel_rij}:H{funnel_rij}")

    # Funnel stappen
    bereik_tot = bereik_totaal if bereik_totaal > 0 else 1
    funnel_data = [
        ["Stap", "Kanaal", "Aantal", "% van bereik", "Benchmark", "Status", "", ""],
        ["Bereik",       "Alle kanalen",      f"{bereik_totaal:,}",  "100%",
         "—",            "📊 Startpunt", "", ""],
        ["Engagement",   "Social organic",    f"{eng_totaal:,}",
         f"{round(eng_totaal/bereik_tot*100,2)}%",
         "1-5%",
         "✅ Goed" if eng_totaal/bereik_tot*100 >= 1 else "⚠ Laag", "", ""],
        ["Websitesessies","GA4",              f"{ga4_sessies:,}",
         f"{round(ga4_sessies/bereik_tot*100,2)}%",
         "2-8%",
         "✅ Goed" if ga4_sessies/bereik_tot*100 >= 2 else "⚠ Laag", "", ""],
        ["Conversies",   "GA4 + Meta",        str(ga4_conv + meta_leads),
         f"{round((ga4_conv+meta_leads)/bereik_tot*100,3)}%",
         "0.5-2%",
         "✅ Goed" if (ga4_conv+meta_leads)/bereik_tot*100 >= 0.5 else "⚠ Laag", "", ""],
    ]

    time.sleep(1)
    ws.update(funnel_data, f"A{funnel_rij+1}", value_input_option="USER_ENTERED")
    ws.format(f"A{funnel_rij+1}:H{funnel_rij+1}", STIJL_HEADER)
    for i in range(1, len(funnel_data)):
        rij = funnel_rij + 1 + i
        if i % 2 == 0:
            ws.format(f"A{rij}:H{rij}", STIJL_RIJ_GRIJS)

    # Kolombreedte
    stel_kolombreedte_in(ws, [
        (0, 240), (1, 160), (2, 220), (3, 160),
        (4, 220), (5, 160), (6, 220), (7, 160),
    ])

    print(f"  ✓ JOURNEY — Overzicht geschreven")

# ============================================================
# 14. HTML DASHBOARD GENEREREN
# ============================================================

def genereer_html(vandaag,
                  ga4_users, ga4_new_users, ga4_sessies, ga4_conv,
                  ga4_conv_rate, ga4_bounce, ga4_eng_rate, ga4_gem_duur,
                  meta_spend, meta_leads, meta_cpl, meta_impressies,
                  meta_bereik, meta_freq, meta_klikken, meta_ctr, meta_cpm,
                  ig_volgers, ig_bereik, ig_eng, ig_eng_rate, ig_posts, ig_new_followers,
                  fb_fans, fb_bereik_uniek, fb_engagements, fb_fans_added, fb_net_groei):

    def fmt(v):
        if v in ("—", None, ""):
            return "—"
        try:
            return f"{int(v):,}".replace(",", ".")
        except (ValueError, TypeError):
            return str(v)

    def eur_fmt(v):
        try:
            return f"€ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return str(v)

    html_pad = Path(__file__).parent / "index.html"
    gegenereerd_op = datetime.datetime.now().strftime("%d-%m-%Y om %H:%M")
    nu_tijd        = datetime.datetime.now().strftime("%H:%M")

    bereik_totaal = ig_bereik + fb_bereik_uniek + meta_bereik
    eng_totaal    = ig_eng + fb_engagements
    cpl_fmt       = eur_fmt(meta_cpl) if meta_cpl not in ("—", None, "") else "—"

    html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Marketing Dashboard — {vandaag}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    background: #080b18;
    color: #dde3f0;
    min-height: 100vh;
    padding: 22px;
  }}

  /* ── Header ── */
  .topbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 22px;
    padding: 14px 20px;
    background: linear-gradient(135deg, #0d1130 0%, #111630 100%);
    border: 1px solid #1e2448;
    border-radius: 14px;
  }}
  .topbar-title {{
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: 0.3px;
    color: #fff;
  }}
  .topbar-title span {{
    background: linear-gradient(90deg, #4f9eff, #a259ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .topbar-meta {{
    font-size: 0.76rem;
    color: #5a6480;
    display: flex;
    gap: 18px;
    align-items: center;
  }}
  .topbar-time {{
    font-size: 1.5rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: -1px;
  }}

  /* ── Journey grid ── */
  .journey {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }}

  /* ── Phase column ── */
  .fase {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .fase-header {{
    border-radius: 12px;
    padding: 14px 18px 12px;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #fff;
  }}
  .fase-source {{
    font-size: 0.67rem;
    font-weight: 500;
    letter-spacing: 0.3px;
    opacity: 0.6;
    margin-top: 3px;
    text-transform: none;
  }}
  .h-blauw {{ background: linear-gradient(135deg, #0f2d6b 0%, #1a3d8a 100%); border: 1px solid #2a52b0; }}
  .h-groen {{ background: linear-gradient(135deg, #0a3528 0%, #0f4a38 100%); border: 1px solid #1a6e52; }}
  .h-geel  {{ background: linear-gradient(135deg, #3a2200 0%, #5a3800 100%); border: 1px solid #8a5c00; }}
  .h-paars {{ background: linear-gradient(135deg, #2a1060 0%, #3d1a8a 100%); border: 1px solid #6030c0; }}

  /* ── KPI card ── */
  .card {{
    background: linear-gradient(160deg, #111428 0%, #0e1224 100%);
    border: 1px solid #1c2040;
    border-radius: 12px;
    padding: 16px 18px;
    flex-shrink: 0;
    transition: border-color 0.2s, transform 0.15s;
  }}
  .card:hover {{ border-color: #3a4880; transform: translateY(-1px); }}
  .card-label {{
    font-size: 0.68rem;
    color: #4a5570;
    font-weight: 700;
    margin-bottom: 7px;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .card-value {{
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1.5px;
  }}
  .card-sub {{
    margin-top: 9px;
    font-size: 0.76rem;
    color: #5a6480;
    border-top: 1px solid #1a1e38;
    padding-top: 8px;
  }}
  .card-sub b {{ color: #c0cce8; }}

  /* ── Metric rows ── */
  .metrics {{
    background: linear-gradient(160deg, #111428 0%, #0e1224 100%);
    border: 1px solid #1c2040;
    border-radius: 12px;
    overflow: hidden;
  }}
  .metric-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 16px;
    border-bottom: 1px solid #161a30;
    font-size: 0.78rem;
    transition: background 0.15s;
  }}
  .metric-row:hover {{ background: #13172e; }}
  .metric-row:last-child {{ border-bottom: none; }}
  .metric-row .ml {{ color: #4e5a78; }}
  .metric-row .mv {{ font-weight: 700; color: #c8d4ee; }}

  /* ── Accent colours per fase ── */
  .f1 .card-value {{ color: #4f9eff; }}
  .f2 .card-value {{ color: #2ecc8a; }}
  .f3 .card-value {{ color: #ffaa2e; }}
  .f4 .card-value {{ color: #b06aff; }}

  .f1 .fase-header {{ box-shadow: 0 4px 20px rgba(79,158,255,0.15); }}
  .f2 .fase-header {{ box-shadow: 0 4px 20px rgba(46,204,138,0.15); }}
  .f3 .fase-header {{ box-shadow: 0 4px 20px rgba(255,170,46,0.15); }}
  .f4 .fase-header {{ box-shadow: 0 4px 20px rgba(176,106,255,0.15); }}

  /* ── Footer ── */
  .footer {{
    margin-top: 18px;
    text-align: center;
    font-size: 0.7rem;
    color: #2a3050;
    padding-top: 14px;
    border-top: 1px solid #131730;
  }}
  .footer a {{ color: #4f9eff; text-decoration: none; }}
  .chart-card {{ padding: 14px 16px; }}
  canvas {{ max-height: 180px; }}

  @media (max-width: 900px) {{
    .journey {{ grid-template-columns: repeat(2, 1fr); }}
  }}
  @media (max-width: 500px) {{
    .journey {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">Marketing <span>Dashboard</span> &mdash; IVECO Schouten</div>
  <div class="topbar-meta">
    <span>Periode: {PERIODE_DAGEN} dagen &nbsp;|&nbsp; {vandaag}</span>
    <a href="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}" target="_blank"
       style="color:#5b8dee;text-decoration:none;">↗ Google Sheets</a>
    <span class="topbar-time">{nu_tijd}</span>
  </div>
</div>

<div class="journey">

  <!-- ════ FASE 1: BEWUSTWORDING ════ -->
  <div class="fase f1">
    <div class="fase-header h-blauw">
      👁 Bewustwording
      <div class="fase-source">Instagram · Facebook · Meta Ads</div>
    </div>

    <div class="card">
      <div class="card-label">Totaal bereik</div>
      <div class="card-value">{fmt(bereik_totaal)}</div>
      <div class="card-sub">Unieke mensen bereikt via alle kanalen</div>
    </div>

    <div class="card">
      <div class="card-label">Meta Ads impressies</div>
      <div class="card-value">{fmt(meta_impressies)}</div>
      <div class="card-sub"><b>{meta_freq}×</b> gemiddeld gezien &nbsp;|&nbsp; CPM <b>{eur_fmt(meta_cpm)}</b></div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Instagram bereik</span><span class="mv">{fmt(ig_bereik)}</span></div>
      <div class="metric-row"><span class="ml">Facebook bereik</span><span class="mv">{fmt(fb_bereik_uniek)}</span></div>
      <div class="metric-row"><span class="ml">Meta Ads bereik</span><span class="mv">{fmt(meta_bereik)}</span></div>
      <div class="metric-row"><span class="ml">Nieuwe IG volgers</span><span class="mv">+{fmt(ig_new_followers)}</span></div>
      <div class="metric-row"><span class="ml">Nieuwe FB fans</span><span class="mv">+{fmt(fb_fans_added)}</span></div>
      <div class="metric-row"><span class="ml">Netto FB groei</span><span class="mv">+{fmt(fb_net_groei)}</span></div>
    </div>

    <div class="card chart-card">
      <div class="card-label">Bereik verdeling</div>
      <canvas id="chartBereik"></canvas>
    </div>
  </div>

  <!-- ════ FASE 2: INTERESSE ════ -->
  <div class="fase f2">
    <div class="fase-header h-groen">
      💡 Interesse
      <div class="fase-source">Instagram · Facebook Organic</div>
    </div>

    <div class="card">
      <div class="card-label">Totaal engagement</div>
      <div class="card-value">{fmt(eng_totaal)}</div>
      <div class="card-sub">Likes, reacties, shares op alle posts</div>
    </div>

    <div class="card">
      <div class="card-label">Meta Ads klikken</div>
      <div class="card-value">{fmt(meta_klikken)}</div>
      <div class="card-sub">CTR <b>{meta_ctr}%</b> &nbsp;|&nbsp; van impressie naar klik</div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Instagram engagement</span><span class="mv">{fmt(ig_eng)}</span></div>
      <div class="metric-row"><span class="ml">IG engagement rate</span><span class="mv">{ig_eng_rate}</span></div>
      <div class="metric-row"><span class="ml">Instagram posts</span><span class="mv">{fmt(ig_posts)}</span></div>
      <div class="metric-row"><span class="ml">Facebook engagement</span><span class="mv">{fmt(fb_engagements)}</span></div>
      <div class="metric-row"><span class="ml">Facebook fans totaal</span><span class="mv">{fmt(fb_fans)}</span></div>
    </div>

    <div class="card chart-card">
      <div class="card-label">Engagement verdeling</div>
      <canvas id="chartEngagement"></canvas>
    </div>
  </div>

  <!-- ════ FASE 3: OVERWEGING ════ -->
  <div class="fase f3">
    <div class="fase-header h-geel">
      🔍 Overweging
      <div class="fase-source">GA4 Website Analytics</div>
    </div>

    <div class="card">
      <div class="card-label">Websitesessies</div>
      <div class="card-value">{fmt(ga4_sessies)}</div>
      <div class="card-sub"><b>{fmt(ga4_users)}</b> gebruikers &nbsp;|&nbsp; <b>{fmt(ga4_new_users)}</b> nieuw</div>
    </div>

    <div class="card">
      <div class="card-label">Gem. sessieduur</div>
      <div class="card-value">{ga4_gem_duur}</div>
      <div class="card-sub">Engagement rate <b>{ga4_eng_rate}</b></div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Terugkerende bezoekers</span><span class="mv">{fmt(ga4_users - ga4_new_users if isinstance(ga4_users, int) and isinstance(ga4_new_users, int) else "—")}</span></div>
      <div class="metric-row"><span class="ml">Bounce rate</span><span class="mv">{ga4_bounce}</span></div>
      <div class="metric-row"><span class="ml">Engagement rate</span><span class="mv">{ga4_eng_rate}</span></div>
      <div class="metric-row"><span class="ml">Sessieduur</span><span class="mv">{ga4_gem_duur}</span></div>
      <div class="metric-row"><span class="ml">Pageviews/sessie</span><span class="mv">—</span></div>
    </div>

    <div class="card chart-card">
      <div class="card-label">Website KPI's</div>
      <canvas id="chartWebsite"></canvas>
    </div>
  </div>

  <!-- ════ FASE 4: ACTIE ════ -->
  <div class="fase f4">
    <div class="fase-header h-paars">
      ✅ Actie
      <div class="fase-source">GA4 Conversies · Meta Leads</div>
    </div>

    <div class="card">
      <div class="card-label">Meta Ads leads</div>
      <div class="card-value">{fmt(meta_leads)}</div>
      <div class="card-sub">CPL <b>{cpl_fmt}</b> &nbsp;|&nbsp; spend <b>{eur_fmt(meta_spend)}</b></div>
    </div>

    <div class="card">
      <div class="card-label">GA4 conversies</div>
      <div class="card-value">{fmt(ga4_conv)}</div>
      <div class="card-sub">Conv. rate <b>{ga4_conv_rate}</b></div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Meta Ads spend</span><span class="mv">{eur_fmt(meta_spend)}</span></div>
      <div class="metric-row"><span class="ml">Cost per lead</span><span class="mv">{cpl_fmt}</span></div>
      <div class="metric-row"><span class="ml">GA4 conv. rate</span><span class="mv">{ga4_conv_rate}</span></div>
      <div class="metric-row"><span class="ml">Instagram volgers</span><span class="mv">{fmt(ig_volgers)}</span></div>
      <div class="metric-row"><span class="ml">IG volgers nieuw</span><span class="mv">+{fmt(ig_new_followers)}</span></div>
    </div>

    <div class="card chart-card">
      <div class="card-label">Conversie funnel</div>
      <canvas id="chartFunnel"></canvas>
    </div>
  </div>

</div><!-- /journey -->

<div class="footer">
  Automatisch gegenereerd op {gegenereerd_op} &nbsp;&mdash;&nbsp;
  <a href="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}" target="_blank">Bekijk volledig rapport in Google Sheets</a>
</div>

<script>
Chart.defaults.color = '#8892a4';
Chart.defaults.font.family = 'Segoe UI, system-ui, sans-serif';
Chart.defaults.font.size = 11;

const GRID = {{ color: 'rgba(255,255,255,0.04)' }};
const LEG  = {{ position: 'bottom', labels: {{ boxWidth: 10, padding: 12, color: '#5a6480' }} }};

// Bereik verdeling — donut
new Chart(document.getElementById('chartBereik'), {{
  type: 'doughnut',
  data: {{
    labels: ['Instagram', 'Facebook', 'Meta Ads'],
    datasets: [{{ data: [{ig_bereik}, {fb_bereik_uniek}, {meta_bereik}],
      backgroundColor: ['#4f9eff','#2ecc8a','#ffaa2e'],
      borderWidth: 2, borderColor: '#080b18', hoverOffset: 8 }}]
  }},
  options: {{
    plugins: {{ legend: LEG }},
    cutout: '68%',
    responsive: true,
  }}
}});

// Engagement verdeling — donut
new Chart(document.getElementById('chartEngagement'), {{
  type: 'doughnut',
  data: {{
    labels: ['Instagram', 'Facebook'],
    datasets: [{{ data: [{ig_eng}, {fb_engagements}],
      backgroundColor: ['#4f9eff','#2ecc8a'],
      borderWidth: 2, borderColor: '#080b18', hoverOffset: 8 }}]
  }},
  options: {{
    plugins: {{ legend: LEG }},
    cutout: '68%',
    responsive: true,
  }}
}});

// Website KPI's — horizontale bar
new Chart(document.getElementById('chartWebsite'), {{
  type: 'bar',
  data: {{
    labels: ['Gebruikers', 'Sessies', 'Conversies'],
    datasets: [{{ data: [{ga4_users}, {ga4_sessies}, {ga4_conv}],
      backgroundColor: ['rgba(79,158,255,0.25)','rgba(255,170,46,0.25)','rgba(46,204,138,0.25)'],
      borderColor:     ['#4f9eff','#ffaa2e','#2ecc8a'],
      borderWidth: 2, borderRadius: 6 }}]
  }},
  options: {{
    indexAxis: 'y',
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: GRID, ticks: {{ color: '#3a4260' }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ color: '#5a6480' }} }}
    }},
    responsive: true,
  }}
}});

// Conversie funnel — bar
new Chart(document.getElementById('chartFunnel'), {{
  type: 'bar',
  data: {{
    labels: ['Bereik', 'Klikken', 'Leads', 'Conversies'],
    datasets: [{{ data: [{bereik_totaal}, {meta_klikken}, {meta_leads}, {ga4_conv}],
      backgroundColor: ['rgba(79,158,255,0.25)','rgba(255,170,46,0.25)','rgba(176,106,255,0.25)','rgba(46,204,138,0.25)'],
      borderColor:     ['#4f9eff','#ffaa2e','#b06aff','#2ecc8a'],
      borderWidth: 2, borderRadius: 6 }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color: '#5a6480' }} }},
      y: {{ grid: GRID, ticks: {{ color: '#3a4260' }} }}
    }},
    responsive: true,
  }}
}});
</script>

</body>
</html>"""

    with open(html_pad, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  ✓ HTML dashboard opgeslagen: {html_pad}")
    return html_pad


# ============================================================
# 15. HOOFDPROGRAMMA
# ============================================================

def main():
    vandaag     = datetime.date.today().strftime("%d-%m-%Y")
    start_datum = f"{PERIODE_DAGEN}daysAgo"

    print("=" * 56)
    print(f"  MASTER DASHBOARD — {vandaag}")
    print("=" * 56)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SLEUTEL_BESTAND
    sheets_client = gspread.service_account(filename=SLEUTEL_BESTAND)
    spreadsheet   = sheets_client.open_by_key(SPREADSHEET_ID)
    ga4_client    = BetaAnalyticsDataClient()

    # GA4
    (ga4_users, ga4_sessies, ga4_conv,
     ga4_conv_rate, ga4_bounce, ga4_eng_rate,
     ga4_gem_duur, ga4_new_users) = haal_ga4_overzicht(
        ga4_client, spreadsheet, start_datum, vandaag)
    ga4_return_users = haal_ga4_verkeersbronnen(
        ga4_client, spreadsheet, start_datum, vandaag)
    haal_ga4_gedrag(ga4_client, spreadsheet, start_datum, vandaag)

    # Meta Ads
    (meta_spend, meta_leads, meta_cpl,
     meta_impressies, meta_bereik, meta_freq,
     meta_klikken, meta_ctr, meta_cpm) = haal_meta_ads_overzicht(spreadsheet, vandaag)
    haal_meta_ads_campagnes(spreadsheet, vandaag)
    haal_meta_ads_adsets(spreadsheet, vandaag)
    haal_meta_ads_ads(spreadsheet, vandaag)

    # Social Organic
    (fb_fans_added, fb_net_groei,
     fb_fans, fb_bereik_uniek,
     fb_engagements) = haal_facebook_organic(spreadsheet, vandaag)
    (ig_volgers, ig_bereik, ig_eng,
     ig_eng_rate, ig_posts,
     ig_new_followers) = haal_instagram(spreadsheet, vandaag)

    # Historisch overzicht
    schrijf_kpi_overzicht(
        spreadsheet, vandaag,
        ga4_users, ga4_sessies, ga4_conv,
        meta_spend, meta_leads,
        fb_fans_added, fb_net_groei,
        ig_volgers, ig_eng, ig_bereik,
    )

    # Customer Journey overzicht
    schrijf_journey_overzicht(
        spreadsheet, vandaag,
        ga4_users, ga4_sessies, ga4_conv, ga4_conv_rate,
        ga4_bounce, ga4_eng_rate, ga4_gem_duur,
        ga4_new_users, ga4_return_users,
        meta_spend, meta_leads, meta_cpl,
        meta_impressies, meta_bereik, meta_freq,
        meta_klikken, meta_ctr, meta_cpm,
        ig_volgers, ig_bereik, ig_eng, ig_eng_rate,
        ig_posts, ig_new_followers,
        fb_fans, fb_bereik_uniek, fb_engagements,
        fb_fans_added, fb_net_groei,
    )

    # HTML dashboard genereren
    html_pad = genereer_html(
        vandaag,
        ga4_users, ga4_new_users, ga4_sessies, ga4_conv,
        ga4_conv_rate, ga4_bounce, ga4_eng_rate, ga4_gem_duur,
        meta_spend, meta_leads, meta_cpl, meta_impressies,
        meta_bereik, meta_freq, meta_klikken, meta_ctr, meta_cpm,
        ig_volgers, ig_bereik, ig_eng, ig_eng_rate, ig_posts, ig_new_followers,
        fb_fans, fb_bereik_uniek, fb_engagements, fb_fans_added, fb_net_groei,
    )

    print("\n" + "=" * 56)
    print("  ✓ DASHBOARD KLAAR")
    print("=" * 56)
    print(f"  -> https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"  -> {html_pad}")
    print("=" * 56)

    # HTML naar GitHub pushen
    print("\n[GitHub] Pushen...")
    repo_map = str(Path(__file__).parent)
    try:
        subprocess.run(["git", "add", "index.html"], cwd=repo_map, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Dashboard update {vandaag}"],
            cwd=repo_map, check=True
        )
        subprocess.run(["git", "push"], cwd=repo_map, check=True)
        print("  ✓ GitHub Pages bijgewerkt")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ Git fout: {e}")


if __name__ == "__main__":
    if ALLEEN_OP_MAANDAG and datetime.datetime.now().weekday() != 0:
        print("Let op: vandaag is geen maandag — dashboard wordt toch bijgewerkt.")
    main()