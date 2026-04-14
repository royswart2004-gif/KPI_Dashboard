"""
KPI Overzicht, Customer Journey en 30-dagen vergelijkingsdata.
Bevat: historisch KPI-overzicht, journey sheet, 30d trend data.
"""

import time
import requests
import gspread

from google.analytics.data_v1beta.types import (
    DateRange, Metric, RunReportRequest,
)

from config import (
    GA4_PROPERTY_ID, META_AD_ACC_ID, META_TOKEN,
    IG_ACCOUNT_ID, PERIODE_DAGEN,
    STIJL_SECTIETITEL, STIJL_HEADER, STIJL_RIJ_GRIJS,
)
from utils import haal_of_maak_sheet, schrijf_paginatitel, stel_kolombreedte_in


def schrijf_kpi_overzicht(spreadsheet, vandaag,
                           ga4_users, ga4_sessies, ga4_conv,
                           meta_spend, meta_leads,
                           fb_fans_added, fb_fans,
                           fb_bereik_uniek, fb_engagements,
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
        ws.format("A1:N1", {**STIJL_SECTIETITEL,
                             "textFormat": {**STIJL_SECTIETITEL["textFormat"], "fontSize": 13}})
        ws.merge_cells("A1:N1")
        ws.update([[
            "Datum", "GA4 Gebruikers", "GA4 Sessies", "GA4 Conversies",
            "Meta Spend", "Meta Leads",
            "FB Nieuwe volgers", "FB Volgers totaal", "FB Bereik", "FB Engagement",
            "IG Volgers", "IG Engagement", "IG Bereik",
        ]], "A2", value_input_option="USER_ENTERED")
        ws.format("A2:M2", STIJL_HEADER)
        stel_kolombreedte_in(ws, [(i, 150) for i in range(13)])
        print(f"  + Nieuw tabblad aangemaakt: '{naam}'")

    ws.append_row([
        vandaag,
        ga4_users, ga4_sessies, ga4_conv,
        round(meta_spend, 2), meta_leads,
        fb_fans_added, fb_fans, fb_bereik_uniek, fb_engagements,
        ig_volgers, ig_eng, ig_bereik,
    ], value_input_option="USER_ENTERED")
    print(f"  ✓ Nieuwe rij toegevoegd")


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
                               fb_fans_added, fb_net_groei,
                               # 30-dagen vergelijking
                               d30=None):
    d30 = d30 or {}

    def vgl(waarde_7d, totaal_30d, omgekeerd=False, factor=7/30):
        """Geeft % verschil string terug voor in de sheet."""
        try:
            gem = float(totaal_30d) * factor
            if gem == 0:
                return ""
            diff = ((float(waarde_7d) - gem) / gem) * 100
            pijl = "▲" if diff >= 0 else "▼"
            return f"{pijl} {abs(diff):.1f}%"
        except (TypeError, ValueError):
            return ""

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
        "Instagram + Facebook (28d) + Meta Ads (7d)", "",
        "Instagram + Facebook (28d)", "",
        "GA4 Website", "",
        "GA4 Conversies + Meta Leads", "",
    ]], "A5", value_input_option="USER_ENTERED")
    ws.format("A5:H5", {"textFormat": {"italic": True, "fontSize": 9},
                         "horizontalAlignment": "CENTER",
                         "backgroundColor": {"red": 0.95, "green": 0.97, "blue": 1.0}})

    # ============================================================
    # FASE 1 — BEWUSTWORDING (kolom A)
    # ============================================================
    bereik_totaal = ig_bereik + fb_bereik_uniek
    cpm_label     = f"EUR {meta_cpm:.2f}" if isinstance(meta_cpm, float) else str(meta_cpm)

    fase1 = [
        ["Totaal bereik (alle kanalen)",  f"{bereik_totaal:,}",  ""],
        ["├ Instagram bereik",            f"{ig_bereik:,}",      vgl(ig_bereik, d30.get("ig_bereik_30", 0), factor=1)],
        ["├ Facebook bereik (28d)",       f"{fb_bereik_uniek:,}", ""],
        ["└ Meta Ads bereik",             f"{meta_bereik:,}",    vgl(meta_bereik, d30.get("meta_bereik_30", 0))],
        ["", "", ""],
        ["Meta Ads impressies",           f"{meta_impressies:,}", vgl(meta_impressies, d30.get("meta_impr_30", 0))],
        ["Meta Ads frequentie",           f"{meta_freq}x gezien", ""],
        ["Meta Ads CPM",                  cpm_label,              ""],
        ["", "", ""],
        ["Instagram nieuwe volgers",      f"+{ig_new_followers}", ""],
        ["Facebook nieuwe volgers",       f"+{fb_fans_added}",    ""],
    ]

    # ============================================================
    # FASE 2 — INTERESSE (kolom C)
    # ============================================================
    eng_totaal = ig_eng + fb_engagements
    ig_eng_str = f"{ig_eng_rate}%" if ig_eng_rate != "—" else "—"

    fase2 = [
        ["Totaal engagement",             f"{eng_totaal:,}",      ""],
        ["├ Instagram engagement",        f"{ig_eng:,}",          ""],
        ["└ Facebook engagement",         f"{fb_engagements:,}",  ""],
        ["", "", ""],
        ["Instagram engagement rate",     ig_eng_str,             ""],
        ["Instagram posts geanalyseerd",  str(ig_posts),          ""],
        ["", "", ""],
        ["Meta Ads CTR",                  f"{meta_ctr}%",         vgl(meta_ctr, d30.get("meta_ctr_30", 0))],
        ["Meta Ads klikken",              f"{meta_klikken:,}",    vgl(meta_klikken, d30.get("meta_klikken_30", 0))],
        ["", "", ""],
        ["", "", ""],
    ]

    # ============================================================
    # FASE 3 — OVERWEGING (kolom E)
    # ============================================================
    bounce_str   = f"{ga4_bounce}" if ga4_bounce != "—" else "—"
    eng_r_str    = f"{ga4_engagement_rate}" if ga4_engagement_rate != "—" else "—"

    fase3 = [
        ["Website sessies",               f"{ga4_sessies:,}",     vgl(ga4_sessies, d30.get("ga4_sessies_30", 0))],
        ["Website gebruikers",            f"{ga4_users:,}",       vgl(ga4_users, d30.get("ga4_users_30", 0))],
        ["└ Nieuw",                       f"{ga4_new_users:,}",   vgl(ga4_new_users, d30.get("ga4_new_30", 0))],
        ["└ Terugkerend",                 f"{ga4_return_users:,}",""],
        ["", "", ""],
        ["Gem. sessieduur",               str(ga4_gem_duur),      ""],
        ["Engagement rate",               eng_r_str,              ""],
        ["Bounce rate",                   bounce_str,             ""],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
    ]

    # ============================================================
    # FASE 4 — ACTIE (kolom G)
    # ============================================================
    cpl_str = f"EUR {meta_cpl:.2f}" if isinstance(meta_cpl, float) else str(meta_cpl)
    conv_r  = f"{ga4_conv_rate}%" if ga4_conv_rate != "—" else "—"
    leads_totaal = meta_leads

    fase4 = [
        ["Totaal conversies (GA4)",       str(ga4_conv),          vgl(ga4_conv, d30.get("ga4_conv_30", 0))],
        ["Conv. rate",                    conv_r,                 ""],
        ["", "", ""],
        ["Meta Ads leads",                str(meta_leads),        vgl(meta_leads, d30.get("meta_leads_30", 0))],
        ["Cost per lead (CPL)",           cpl_str,                ""],
        ["Meta Ads spend",                f"EUR {meta_spend:.2f}", vgl(meta_spend, d30.get("meta_spend_30", 0))],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
    ]

    # ---- Schrijf alle fase-data in kolommen (3 per fase: label | waarde | % vs 30d) ----
    max_rijen = max(len(fase1), len(fase2), len(fase3), len(fase4))
    start_rij = 7

    STIJL_POS = {"textFormat": {"bold": True, "foregroundColor": {"red": 0.1, "green": 0.7, "blue": 0.3}}}
    STIJL_NEG = {"textFormat": {"bold": True, "foregroundColor": {"red": 0.9, "green": 0.2, "blue": 0.2}}}
    STIJL_VGL = {"textFormat": {"fontSize": 9}, "horizontalAlignment": "CENTER"}

    alle_rijen = []
    for i in range(max_rijen):
        def cel(fase, idx): return fase[i][idx] if i < len(fase) else ""
        rij_data = [
            cel(fase1,0), cel(fase1,1), cel(fase1,2),
            cel(fase2,0), cel(fase2,1), cel(fase2,2),
            cel(fase3,0), cel(fase3,1), cel(fase3,2),
            cel(fase4,0), cel(fase4,1), cel(fase4,2),
        ]
        alle_rijen.append(rij_data)

    time.sleep(2)
    ws.update(alle_rijen, f"A{start_rij}", value_input_option="USER_ENTERED")

    format_ranges = []
    # Kolom letters: A=label, B=waarde, C=%, D=label, E=waarde, F=%, G=label, H=waarde, I=%, J=label, K=waarde, L=%
    cols = [("A","B","C"), ("D","E","F"), ("G","H","I"), ("J","K","L")]
    fases_data = [fase1, fase2, fase3, fase4]

    for i in range(max_rijen):
        rij_num = start_rij + i
        for (lbl_col, val_col, pct_col), fase_data in zip(cols, fases_data):
            pct_str = fase_data[i][2] if i < len(fase_data) else ""
            format_ranges.append({"range": f"{lbl_col}{rij_num}", "format": STIJL_LABEL})
            format_ranges.append({"range": f"{val_col}{rij_num}", "format": STIJL_KPI_GROOT})
            if pct_str.startswith("▲"):
                format_ranges.append({"range": f"{pct_col}{rij_num}", "format": {**STIJL_VGL, **STIJL_POS}})
            elif pct_str.startswith("▼"):
                format_ranges.append({"range": f"{pct_col}{rij_num}", "format": {**STIJL_VGL, **STIJL_NEG}})
            else:
                format_ranges.append({"range": f"{pct_col}{rij_num}", "format": STIJL_VGL})

    time.sleep(2)
    ws.batch_format(format_ranges)

    # ---- Funnel samenvatting onderaan ----
    funnel_rij = start_rij + max_rijen + 2
    time.sleep(1)
    ws.update([[
        "FUNNEL SAMENVATTING", "", "", "", "", "", "", "", "", "", "", ""
    ]], f"A{funnel_rij}", value_input_option="USER_ENTERED")
    ws.format(f"A{funnel_rij}:L{funnel_rij}", {
        "backgroundColor": {"red": 0.05, "green": 0.12, "blue": 0.25},
        "textFormat": {"bold": True, "fontSize": 12,
                       "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER",
    })
    ws.merge_cells(f"A{funnel_rij}:L{funnel_rij}")

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
    ws.format(f"A{funnel_rij+1}:L{funnel_rij+1}", STIJL_HEADER)
    for i in range(1, len(funnel_data)):
        rij = funnel_rij + 1 + i
        if i % 2 == 0:
            ws.format(f"A{rij}:L{rij}", STIJL_RIJ_GRIJS)

    # Kolombreedte (3 kolommen per fase: label | waarde | % vs 30d)
    stel_kolombreedte_in(ws, [
        (0, 220), (1, 140), (2, 90),
        (3, 220), (4, 140), (5, 90),
        (6, 220), (7, 140), (8, 90),
        (9, 220), (10, 140), (11, 90),
    ])

    print(f"  ✓ JOURNEY — Overzicht geschreven")


def haal_30d_data(ga4_client):
    """Haalt 30-daagse totalen op voor GA4 en Meta Ads als vergelijkingsbasis."""
    data = {}

    # GA4 — 30 dagen
    try:
        req = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            metrics=[
                Metric(name="totalUsers"), Metric(name="newUsers"),
                Metric(name="sessions"), Metric(name="conversions"),
                Metric(name="engagementRate"), Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"), Metric(name="screenPageViews"),
            ],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        )
        res = ga4_client.run_report(req)
        if res.rows:
            r = res.rows[0]
            data["ga4_users_30"]    = int(r.metric_values[0].value)
            data["ga4_new_30"]      = int(r.metric_values[1].value)
            data["ga4_sessies_30"]  = int(r.metric_values[2].value)
            data["ga4_conv_30"]     = int(float(r.metric_values[3].value))
            data["ga4_eng_30"]      = round(float(r.metric_values[4].value) * 100, 1)
            data["ga4_bounce_30"]   = round(float(r.metric_values[5].value) * 100, 1)
            data["ga4_duur_30"]     = round(float(r.metric_values[6].value), 1)
        print("  ✓ GA4 30d vergelijking opgehaald")
    except Exception as e:
        print(f"  ⚠ GA4 30d fout: {e}")

    # Meta Ads — 30 dagen
    try:
        url    = f"https://graph.facebook.com/v18.0/{META_AD_ACC_ID}/insights"
        params = {
            "access_token": META_TOKEN,
            "date_preset": "last_30d",
            "fields": "spend,impressions,reach,inline_link_clicks,ctr,cpm,cpc,actions",
        }
        res = requests.get(url, params=params).json()
        d = res.get("data", [{}])[0] if res.get("data") else {}
        if d:
            data["meta_spend_30"]    = float(d.get("spend", 0))
            data["meta_impr_30"]     = int(d.get("impressions", 0))
            data["meta_bereik_30"]   = int(d.get("reach", 0))
            data["meta_klikken_30"]  = int(d.get("inline_link_clicks", 0))
            data["meta_ctr_30"]      = round(float(d.get("ctr", 0)), 2)
            data["meta_cpm_30"]      = round(float(d.get("cpm", 0)), 2)
            leads_30 = sum(int(a.get("value", 0)) for a in d.get("actions", [])
                           if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"))
            data["meta_leads_30"]    = leads_30
            data["meta_cpl_30"]      = round(data["meta_spend_30"] / leads_30, 2) if leads_30 > 0 else None
        print("  ✓ Meta Ads 30d vergelijking opgehaald")
    except Exception as e:
        print(f"  ⚠ Meta 30d fout: {e}")

    # Instagram — 28 dagen bereik (API geeft altijd 28d)
    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/insights",
            params={
                "metric": "reach",
                "period": "days_28",
                "access_token": META_TOKEN,
            }, timeout=10
        ).json()
        if "data" in r and r["data"]:
            ig_val = r["data"][0].get("values", [{}])[-1].get("value", 0)
            data["ig_bereik_30"] = int(ig_val)  # 28d, gebruiken als proxy voor 30d
        print("  ✓ Instagram 28d bereik opgehaald")
    except Exception as e:
        print(f"  ⚠ Instagram 28d fout: {e}")

    # Meta Ads — 30 dagen split per campagne-type (lead vs klik)
    LEAD_OBJECTIVES = {"LEAD_GENERATION", "OUTCOME_LEADS"}
    KLIK_OBJECTIVES = {"LINK_CLICKS", "TRAFFIC", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT"}
    try:
        url    = f"https://graph.facebook.com/v18.0/{META_AD_ACC_ID}/insights"
        params = {
            "access_token": META_TOKEN,
            "date_preset": "last_30d",
            "fields": "campaign_name,objective,spend,impressions,reach,inline_link_clicks,actions",
            "level": "campaign",
        }
        res = requests.get(url, params=params, timeout=15).json()
        l_spend = l_leads = l_impr = l_bereik = l_klik = 0
        k_spend = k_klik = k_impr = k_bereik = 0
        for c in res.get("data", []):
            obj     = c.get("objective", "").upper()
            c_spend = float(c.get("spend", 0))
            c_klik  = int(c.get("inline_link_clicks", 0))
            c_impr  = int(c.get("impressions", 0))
            c_bereik = int(c.get("reach", 0))
            c_leads = sum(int(a.get("value", 0)) for a in c.get("actions", [])
                          if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"))
            if obj in LEAD_OBJECTIVES:
                l_spend += c_spend; l_leads += c_leads
                l_impr += c_impr; l_bereik += c_bereik; l_klik += c_klik
            elif obj in KLIK_OBJECTIVES:
                k_spend += c_spend; k_klik += c_klik
                k_impr += c_impr; k_bereik += c_bereik
            else:
                if c_leads > 0:
                    l_spend += c_spend; l_leads += c_leads
                    l_impr += c_impr; l_bereik += c_bereik
                else:
                    k_spend += c_spend; k_klik += c_klik
                    k_impr += c_impr; k_bereik += c_bereik
        data["lead_spend_30"]  = l_spend
        data["lead_leads_30"]  = l_leads
        data["lead_impr_30"]   = l_impr
        data["lead_bereik_30"] = l_bereik
        data["lead_klik_30"]   = l_klik
        data["lead_cpl_30"]    = round(l_spend / l_leads, 2) if l_leads > 0 else None
        data["lead_freq_30"]   = round(l_impr / l_bereik, 2) if l_bereik > 0 else None
        data["lead_cpm_30"]    = round(l_spend / l_impr * 1000, 2) if l_impr > 0 else None
        data["lead_ctr_30"]    = round(l_klik / l_impr * 100, 2) if l_impr > 0 else None
        data["klik_spend_30"]  = k_spend
        data["klik_klik_30"]   = k_klik
        data["klik_impr_30"]   = k_impr
        data["klik_bereik_30"] = k_bereik
        data["klik_cpc_30"]    = round(k_spend / k_klik, 2) if k_klik > 0 else None
        data["klik_freq_30"]   = round(k_impr / k_bereik, 2) if k_bereik > 0 else None
        data["klik_cpm_30"]    = round(k_spend / k_impr * 1000, 2) if k_impr > 0 else None
        data["klik_ctr_30"]    = round(k_klik / k_impr * 100, 2) if k_impr > 0 else None
        print("  ✓ Meta Ads 30d lead/klik split opgehaald")
    except Exception as e:
        print(f"  ⚠ Meta 30d lead/klik split fout: {e}")

    return data
