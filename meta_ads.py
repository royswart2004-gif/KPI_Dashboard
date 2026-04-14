"""
Meta Ads data ophalen en naar Google Sheets schrijven.
Bevat: Overzicht + Funnel, Campagnes, Adsets, Ads (Creative).
"""

import requests

from config import META_AD_ACC_ID, META_TOKEN, PERIODE_DAGEN, STIJL_KPI_WAARDE
from utils import (
    eur, pct, haal_of_maak_sheet, schrijf_blok,
    schrijf_paginatitel, stel_kolombreedte_in,
)


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

    # Split per campagne-type: leads vs klikken
    LEAD_OBJECTIVES = {"LEAD_GENERATION", "OUTCOME_LEADS"}
    KLIK_OBJECTIVES = {"LINK_CLICKS", "TRAFFIC", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT"}

    res_camp = requests.get(
        f"https://graph.facebook.com/v18.0/{META_AD_ACC_ID}/insights",
        params={
            "access_token": META_TOKEN,
            "date_preset": f"last_{PERIODE_DAGEN}d",
            "fields": "campaign_name,objective,spend,impressions,reach,frequency,inline_link_clicks,cpm,ctr,actions",
            "level": "campaign",
        },
        timeout=15
    ).json()

    lead_spend = lead_leads = lead_impressies = lead_bereik = lead_klikken = 0
    klik_spend = klik_klikken = klik_impressies = klik_bereik = 0
    for c in res_camp.get("data", []):
        obj       = c.get("objective", "").upper()
        c_spend   = float(c.get("spend", 0))
        c_klik    = int(c.get("inline_link_clicks", 0))
        c_impr    = int(c.get("impressions", 0))
        c_bereik  = int(c.get("reach", 0))
        c_leads   = sum(int(a.get("value", 0)) for a in c.get("actions", [])
                        if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"))
        if obj in LEAD_OBJECTIVES:
            lead_spend      += c_spend
            lead_leads      += c_leads
            lead_impressies += c_impr
            lead_bereik     += c_bereik
            lead_klikken    += c_klik
        elif obj in KLIK_OBJECTIVES:
            klik_spend      += c_spend
            klik_klikken    += c_klik
            klik_impressies += c_impr
            klik_bereik     += c_bereik
        else:
            # onbekend type: tel mee bij meest passende
            if c_leads > 0:
                lead_spend += c_spend; lead_leads += c_leads
                lead_impressies += c_impr; lead_bereik += c_bereik
            else:
                klik_spend += c_spend; klik_klikken += c_klik
                klik_impressies += c_impr; klik_bereik += c_bereik

    lead_cpl  = round(lead_spend / lead_leads, 2)       if lead_leads      > 0 else "—"
    klik_cpc  = round(klik_spend / klik_klikken, 2)     if klik_klikken    > 0 else "—"
    lead_freq = round(lead_impressies / lead_bereik, 2)  if lead_bereik     > 0 else "—"
    klik_freq = round(klik_impressies / klik_bereik, 2)  if klik_bereik     > 0 else "—"
    lead_cpm  = round(lead_spend / lead_impressies * 1000, 2) if lead_impressies > 0 else "—"
    klik_cpm  = round(klik_spend / klik_impressies * 1000, 2) if klik_impressies > 0 else "—"
    lead_ctr  = round(lead_klikken / lead_impressies * 100, 2) if lead_impressies > 0 else "—"
    klik_ctr  = round(klik_klikken / klik_impressies * 100, 2) if klik_impressies > 0 else "—"

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

    # Split samenvatting in sheet
    vr = schrijf_blok(ws, vr, "Split: Lead-campagnes vs Klik-campagnes",
        ["Type", "Spend", "Resultaat", "Kosten per resultaat"],
        [
            ["Lead-campagnes", eur(lead_spend), f"{lead_leads} leads", eur(lead_cpl)],
            ["Klik-campagnes", eur(klik_spend), f"{klik_klikken} klikken", eur(klik_cpc)],
        ], num_kolommen=4)

    stel_kolombreedte_in(ws, [(i, 140) for i in range(15)])
    print(f"  -> EUR {spend:.2f} spend | {leads} leads (CPL {eur(lead_cpl)}) | {klik_klikken} klikken (CPC {eur(klik_cpc)})")
    return (spend, leads, cpl, impressies, bereik, freq, klikken, ctr, cpm,
            lead_leads, lead_cpl, lead_spend,
            lead_freq, lead_bereik, lead_impressies, lead_cpm, lead_ctr,
            klik_klikken, klik_cpc, klik_spend,
            klik_freq, klik_bereik, klik_impressies, klik_cpm, klik_ctr)


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
