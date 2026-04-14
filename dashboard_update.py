"""
============================================================
  MASTER MARKETING DASHBOARD — Orchestrator

  Dit is het hoofdscript dat alle modules aanstuurt.
  Elke databron heeft zijn eigen module:

    config.py            : Instellingen, credentials, opmaak
    utils.py             : Hulpfuncties (formattering, sheets helpers)
    ga4.py               : Google Analytics 4 (Overzicht, Verkeersbronnen, Gedrag)
    meta_ads.py          : Meta Ads (Overzicht, Campagnes, Adsets, Ads)
    facebook_organic.py  : Facebook Organic (Pagina, Posts)
    instagram.py         : Instagram (Account, Posts, Stories)
    kpi.py               : KPI Overzicht, Customer Journey, 30d vergelijking
    html_dashboard.py    : HTML dashboard generatie

  Gebruik:
    Alles draaien:           python dashboard_update.py
    Alleen HTML testen:      python html_dashboard.py

  Installatie:
    pip install -r requirements.txt
============================================================
"""

import os
import subprocess
import datetime
from pathlib import Path

import gspread
from google.analytics.data_v1beta import BetaAnalyticsDataClient

from config import (
    SLEUTEL_BESTAND, SPREADSHEET_ID,
    PERIODE_DAGEN, ALLEEN_OP_MAANDAG,
)

# ── Data modules ──
from ga4 import haal_ga4_overzicht, haal_ga4_verkeersbronnen, haal_ga4_gedrag
from meta_ads import (
    haal_meta_ads_overzicht, haal_meta_ads_campagnes,
    haal_meta_ads_adsets, haal_meta_ads_ads,
)
from facebook_organic import haal_facebook_organic
from instagram import haal_instagram
from kpi import schrijf_kpi_overzicht, schrijf_journey_overzicht, haal_30d_data
from html_dashboard import genereer_html


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

    # ── GA4 ──
    (ga4_users, ga4_sessies, ga4_conv,
     ga4_conv_rate, ga4_bounce, ga4_eng_rate,
     ga4_gem_duur, ga4_new_users) = haal_ga4_overzicht(
        ga4_client, spreadsheet, start_datum, vandaag)
    ga4_return_users = haal_ga4_verkeersbronnen(
        ga4_client, spreadsheet, start_datum, vandaag)
    haal_ga4_gedrag(ga4_client, spreadsheet, start_datum, vandaag)

    # ── Meta Ads ──
    (meta_spend, meta_leads, meta_cpl,
     meta_impressies, meta_bereik, meta_freq,
     meta_klikken, meta_ctr, meta_cpm,
     lead_leads, lead_cpl, lead_spend,
     lead_freq, lead_bereik, lead_impressies, lead_cpm, lead_ctr,
     klik_klikken, klik_cpc, klik_spend,
     klik_freq, klik_bereik, klik_impressies, klik_cpm, klik_ctr) = haal_meta_ads_overzicht(spreadsheet, vandaag)
    haal_meta_ads_campagnes(spreadsheet, vandaag)
    haal_meta_ads_adsets(spreadsheet, vandaag)
    haal_meta_ads_ads(spreadsheet, vandaag)

    # ── Social Organic ──
    (fb_fans_added, fb_net_groei,
     fb_fans, fb_bereik_uniek,
     fb_engagements, fb_vertoningen,
     fb_video_views, fb_neg_feedback,
     fb_likes, fb_comments, fb_shares,
     fb_posts, fb_eng_rate) = haal_facebook_organic(spreadsheet, vandaag)
    (ig_volgers, ig_bereik, ig_eng,
     ig_eng_rate, ig_posts, ig_new_followers,
     ig_likes, ig_comments, ig_saves, ig_shares) = haal_instagram(spreadsheet, vandaag)

    # ── 30-dagen vergelijkingsdata ──
    print("\n[30d vergelijking] Ophalen...")
    d30 = haal_30d_data(ga4_client)

    # ── Historisch overzicht ──
    schrijf_kpi_overzicht(
        spreadsheet, vandaag,
        ga4_users, ga4_sessies, ga4_conv,
        meta_spend, meta_leads,
        fb_fans_added, fb_fans,
        fb_bereik_uniek, fb_engagements,
        ig_volgers, ig_eng, ig_bereik,
    )

    # ── Customer Journey overzicht ──
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
        d30=d30,
    )

    # ── HTML dashboard ──
    html_pad = genereer_html(
        vandaag,
        ga4_users, ga4_new_users, ga4_sessies, ga4_conv,
        ga4_conv_rate, ga4_bounce, ga4_eng_rate, ga4_gem_duur,
        meta_spend, meta_leads, meta_cpl, meta_impressies,
        meta_bereik, meta_freq, meta_klikken, meta_ctr,
        ig_volgers, ig_bereik, ig_eng, ig_eng_rate, ig_posts, ig_new_followers,
        fb_fans, fb_bereik_uniek, fb_engagements, fb_fans_added, fb_net_groei,
        ig_likes=ig_likes, ig_comments=ig_comments, ig_saves=ig_saves, ig_shares=ig_shares,
        fb_vertoningen=fb_vertoningen, fb_video_views=fb_video_views, fb_neg_feedback=fb_neg_feedback,
        fb_likes=fb_likes, fb_comments=fb_comments, fb_shares=fb_shares,
        fb_posts=fb_posts, fb_eng_rate=fb_eng_rate,
        lead_leads=lead_leads, lead_cpl=lead_cpl, lead_spend=lead_spend,
        lead_freq=lead_freq, lead_bereik=lead_bereik, lead_impressies=lead_impressies,
        lead_cpm=lead_cpm, lead_ctr=lead_ctr,
        klik_klikken=klik_klikken, klik_cpc=klik_cpc, klik_spend=klik_spend,
        klik_freq=klik_freq, klik_bereik=klik_bereik, klik_impressies=klik_impressies,
        klik_cpm=klik_cpm, klik_ctr=klik_ctr,
        d30=d30,
    )

    print("\n" + "=" * 56)
    print("  ✓ DASHBOARD KLAAR")
    print("=" * 56)
    print(f"  -> https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"  -> {html_pad}")
    print("=" * 56)

    # ── HTML naar GitHub pushen ──
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
