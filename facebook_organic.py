"""
Facebook Organic data ophalen en naar Google Sheets schrijven.
Bevat: Pagina-statistieken, volgers groei, post-level engagement.
"""

import time
import datetime
import requests

from config import FB_TOKEN, FB_PAGE_ID, PERIODE_DAGEN, STIJL_KPI_WAARDE
from utils import (
    format_tijd, haal_of_maak_sheet, schrijf_blok,
    schrijf_paginatitel, stel_kolombreedte_in,
)


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
        return 0, 0, 0, 0, 0, 0, 0, 0

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
        return 0, 0, 0, 0, 0, 0, 0, 0

    PAGE_ID  = selected_page["id"]
    PAT      = selected_page["access_token"]   # Page Access Token
    pagina_naam = selected_page["name"]
    print(f"  -> Pagina gevonden: {pagina_naam} (ID: {PAGE_ID})")

    # STAP 2: Totaal volgers
    p_res = requests.get(
        f"https://graph.facebook.com/v22.0/{PAGE_ID}",
        params={"fields": "fan_count,followers_count", "access_token": PAT}
    ).json()
    fan_count  = p_res.get("fan_count", 0)
    followers  = p_res.get("followers_count", 0)

    # Nieuwe volgers (followers, niet likes) over afgelopen PERIODE_DAGEN
    volgers_groei = 0
    for metric_naam in ["page_daily_follows", "page_follows"]:
        try:
            r = requests.get(
                f"https://graph.facebook.com/v22.0/{PAGE_ID}/insights",
                params={
                    "metric": metric_naam,
                    "period": "day",
                    "access_token": PAT,
                    "since": int((datetime.datetime.now() - datetime.timedelta(days=PERIODE_DAGEN)).timestamp()),
                    "until": int(datetime.datetime.now().timestamp()),
                },
                timeout=10
            ).json()
            if "error" not in r and "data" in r and r["data"]:
                volgers_groei = sum(
                    v.get("value", 0) if isinstance(v.get("value"), (int, float)) else 0
                    for entry in r["data"]
                    for v in entry.get("values", [])
                )
                print(f"  -> Nieuwe volgers ({PERIODE_DAGEN}d, {metric_naam}): {volgers_groei:+}")
                break
            else:
                err = r.get("error", {}).get("message", "geen data")
                print(f"  -> {metric_naam} niet beschikbaar: {err}")
        except Exception as e:
            print(f"  ⚠ {metric_naam} fout: {e}")

    fans_added = volgers_groei

    # STAP 3: Paginastatistieken via insights (elk apart voor robuustheid)
    werkende_metrics = []
    fb_bereik_uniek = fb_engagements = 0
    fb_vertoningen = fb_video_views = fb_neg_feedback = 0

    # Overige pagina-metrics (page_video_views en page_views_total zijn deprecated per 30-06-2026)
    for metric in [
        "page_engaged_users",
        "page_media_view",
    ]:
        try:
            r = requests.get(
                f"https://graph.facebook.com/v22.0/{PAGE_ID}/insights",
                params={
                    "metric": metric,
                    "period": "day",
                    "access_token": PAT,
                    "since": int((datetime.datetime.now() - datetime.timedelta(days=28)).timestamp()),
                    "until": int(datetime.datetime.now().timestamp()),
                },
                timeout=10
            ).json()
            if "error" in r:
                print(f"    ⚠ {metric}: {r['error'].get('message','onbekend')}")
            elif "data" in r and r["data"]:
                totaal = sum(
                    v.get("value", 0) if isinstance(v.get("value"), (int, float))
                    else sum(v.get("value", {}).values()) if isinstance(v.get("value"), dict)
                    else 0
                    for entry in r["data"]
                    for v in entry.get("values", [])
                )
                werkende_metrics.append([metric, int(totaal), "28 dagen gesommeerd"])
                if metric == "page_engaged_users":               fb_engagements  = int(totaal)
                if metric == "page_media_view":                  fb_video_views  = int(totaal)
            else:
                print(f"    ⚠ {metric}: geen data teruggekomen")
        except Exception as e:
            print(f"    ⚠ {metric}: exception: {e}")

    net_groei = fans_added

    # STAP 4: Posts ophalen met Page Access Token (laatste 28 dagen)
    # Probeer insights als nested field (werkt niet altijd bij NPE pagina's)
    res_posts = requests.get(
        f"https://graph.facebook.com/v22.0/{PAGE_ID}/posts",
        params={
            "fields": "id,message,created_time,permalink_url,status_type,attachments{media},reactions.summary(true),comments.summary(true),shares,insights.metric(post_total_media_view_unique,post_media_view,post_clicks,post_clicks_by_type){values}",
            "access_token": PAT,
            "limit": 50,
        },
        timeout=15
    ).json()
    # Als insights nested field niet werkt, retry zonder
    if "error" in res_posts and "insights" in res_posts.get("error", {}).get("message", "").lower():
        print("  -> Insights nested field niet beschikbaar, retry zonder...")
        res_posts = requests.get(
            f"https://graph.facebook.com/v22.0/{PAGE_ID}/posts",
            params={
                "fields": "id,message,created_time,permalink_url,status_type,attachments{media},reactions.summary(true),comments.summary(true),shares",
                "access_token": PAT,
                "limit": 50,
            },
            timeout=15
        ).json()

    if "error" in res_posts:
        print(f"  ⚠ FB Posts fout: {res_posts['error'].get('message','onbekend')}")

    post_rijen = []
    cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=28)

    for post in res_posts.get("data", []):
        p_time = datetime.datetime.strptime(
            post["created_time"].split("+")[0], "%Y-%m-%dT%H:%M:%S"
        )
        if p_time < cutoff:
            continue

        # Reactions, comments, shares uit post-fields (altijd beschikbaar)
        reactions_data = post.get("reactions", {}).get("summary", {})
        likes    = reactions_data.get("total_count", 0)
        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares   = post.get("shares", {}).get("count", 0)

        # STAP 5: Metrics uit nested insights (indien beschikbaar)
        bereik = vertoningen = post_clicks = video_views = link_clicks = 0
        avg_kijkduur = 0
        insights_data = post.get("insights", {}).get("data", [])
        for item in insights_data:
            val = item.get("values", [{}])[0].get("value", 0) if item.get("values") else 0
            if item.get("name") == "post_total_media_view_unique":
                bereik = val
            elif item.get("name") == "post_media_view":
                vertoningen = val
                video_views = val  # post_media_view vervangt ook post_video_views
            elif item.get("name") == "post_clicks":
                post_clicks = val
            elif item.get("name") == "post_clicks_by_type":
                if isinstance(val, dict):
                    link_clicks = val.get("link clicks", 0)

        eng_totaal = likes + comments + shares
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
            bereik, vertoningen, likes, comments, shares,
            link_clicks, post_clicks, video_views,
            format_tijd(avg_kijkduur / 1000) if avg_kijkduur else "—",
            eng_totaal,
            f"{er}%" if er != "—" else "—",
            fan_count,
            post.get("permalink_url", ""),
        ])

        time.sleep(0.3)  # Kleine pauze per post om rate limit te vermijden

    # Bereik via pagina-level unique media view metric (vervangt deprecated page_impressions_*_unique)
    for metric_naam in ["page_total_media_view_unique"]:
        try:
            r = requests.get(
                f"https://graph.facebook.com/v22.0/{PAGE_ID}/insights",
                params={
                    "metric": metric_naam,
                    "period": "days_28",
                    "access_token": PAT,
                }, timeout=10
            ).json()
            if "error" not in r and "data" in r and r["data"]:
                fb_bereik_uniek = int(r["data"][0].get("values", [{}])[-1].get("value", 0))
                print(f"  -> Bereik via {metric_naam} (28d): {fb_bereik_uniek:,}")
                break
            else:
                err = r.get("error", {}).get("message", "geen data")
                print(f"  -> {metric_naam} niet beschikbaar: {err}")
        except Exception as e:
            print(f"  ⚠ {metric_naam} fout: {e}")

    # Fallback: som van per-post bereik (overschatting, maar beter dan 0)
    if fb_bereik_uniek == 0:
        fb_bereik_posts = sum(r[3] for r in post_rijen) if post_rijen else 0
        if fb_bereik_posts > 0:
            fb_bereik_uniek = fb_bereik_posts
            print(f"  -> Bereik fallback via post insights (som): {fb_bereik_uniek:,}")

    # Post-level totalen (consistent met Instagram)
    fb_engagements = sum(r[12] for r in post_rijen) if post_rijen else fb_engagements
    fb_likes    = sum(r[5] for r in post_rijen) if post_rijen else 0
    fb_comments = sum(r[6] for r in post_rijen) if post_rijen else 0
    fb_shares   = sum(r[7] for r in post_rijen) if post_rijen else 0
    fb_posts    = len(post_rijen)
    fb_eng_rate = round(fb_engagements / fb_bereik_uniek * 100, 2) if fb_bereik_uniek > 0 else "—"
    print(f"  -> Engagement via post data: {fb_engagements:,} ({fb_posts} posts)")

    # ---- Tabblad opbouwen ----
    schrijf_paginatitel(ws, f"FACEBOOK — Org  |  {pagina_naam}  |  Peildatum: {vandaag}", "K")

    vr = schrijf_blok(ws, 3, "Pagina samenvatting",
        ["Pagina naam", "Volgers totaal", "Volgers (followers_count)"],
        [[pagina_naam, fan_count, followers]], num_kolommen=3)
    ws.batch_format([{"range": f"A{vr-2}:C{vr-2}", "format": STIJL_KPI_WAARDE}])

    time.sleep(1)
    vr = schrijf_blok(ws, vr, "Paginastatistieken — afgelopen 28 dagen",
        ["Metric", "Waarde (gesommeerd)", "Periode"],
        werkende_metrics if werkende_metrics else [["Geen data", "", ""]],
        num_kolommen=3)

    vr = schrijf_blok(ws, vr, f"Follower groei — afgelopen {PERIODE_DAGEN} dagen",
        ["Nieuwe volgers (followers)", "Volgers totaal"],
        [[fans_added, followers]], num_kolommen=2)
    ws.batch_format([{"range": f"A{vr-2}:C{vr-2}", "format": STIJL_KPI_WAARDE}])

    time.sleep(1)
    vr = schrijf_blok(ws, vr, f"Posts — detail (afgelopen 28 dagen, {len(post_rijen)} posts)",
        ["Datum", "Type", "Bericht", "Bereik", "Vertoningen", "Likes",
         "Comments", "Shares", "Link clicks", "Post clicks", "Video views",
         "Gem. kijkduur", "Engagement", "Eng. rate", "Totaal volgers", "Link"],
        post_rijen if post_rijen else [["Geen posts gevonden"] + [""] * 15],
        totaal_rij=["✦ TOTAAL", "", "",
                    sum(r[3] for r in post_rijen),
                    sum(r[4] for r in post_rijen),
                    sum(r[5] for r in post_rijen),
                    sum(r[6] for r in post_rijen),
                    sum(r[7] for r in post_rijen),
                    sum(r[8] for r in post_rijen),
                    sum(r[9] for r in post_rijen),
                    sum(r[10] for r in post_rijen),
                    "", "", "", "", ""] if post_rijen else None,
        num_kolommen=16)

    stel_kolombreedte_in(ws, [
        (0,110),(1,140),(2,300),(3,100),(4,110),
        (5,90),(6,100),(7,90),(8,110),(9,100),
        (10,110),(11,120),(12,110),(13,100),(14,130),(15,260)
    ])

    print(f"  -> {len(post_rijen)} posts | volgers: {fan_count} | groei: {net_groei:+} | vertoningen: {fb_vertoningen}")
    return (fans_added, net_groei, followers, fb_bereik_uniek, fb_engagements,
            fb_vertoningen, fb_video_views, fb_neg_feedback,
            fb_likes, fb_comments, fb_shares, fb_posts, fb_eng_rate)
