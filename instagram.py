"""
Instagram data ophalen en naar Google Sheets schrijven.
Bevat: Account info, insights, media/post engagement, content types, stories.
"""

import time
import datetime
import requests

from config import IG_ACCOUNT_ID, META_TOKEN, STIJL_KPI_WAARDE
from utils import (
    haal_of_maak_sheet, schrijf_blok,
    schrijf_paginatitel, stel_kolombreedte_in,
)


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
            "metric": "reach,impressions,profile_views,follower_count",
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

    cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=28)

    for post in res_media.get("data", []):
        p_time_str = post.get("timestamp", "")[:19]
        try:
            p_time = datetime.datetime.strptime(p_time_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            p_time = cutoff  # als parse faalt, neem cutoff aan
        if p_time < cutoff:
            continue

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
            metrics = "reach,shares,saved,likes,comments"

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
        weergaven = ins.get("plays", 0)

        totaal_eng  = likes + comments + shares + saves
        eng_rate    = round((totaal_eng / bereik * 100), 2) if bereik > 0 else "—"

        post_rijen.append([
            datum, soort, caption,
            likes, comments, shares, saves,
            bereik, weergaven, 0,
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
            "metric": "exits,taps_forward,taps_back,replies",
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
    return (volgers, totaal_bereik, totaal_eng_sum, gem_eng, len(post_rijen), ig_new_followers_totaal,
            totaal_likes, totaal_comments, totaal_saves, totaal_shares)
