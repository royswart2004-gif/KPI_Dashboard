"""
HTML Dashboard genereren.
Maakt een single-page HTML dashboard met CSS en Chart.js visualisaties.

Kan standalone getest worden met dummy data:
    python html_dashboard.py
"""

import math
import datetime
from pathlib import Path

from config import PERIODE_DAGEN, SPREADSHEET_ID
from utils import pct_diff


def genereer_html(vandaag,
                  ga4_users, ga4_new_users, ga4_sessies, ga4_conv,
                  ga4_conv_rate, ga4_bounce, ga4_eng_rate, ga4_gem_duur,
                  meta_spend, meta_leads, meta_cpl, meta_impressies,
                  meta_bereik, meta_freq, meta_klikken, meta_ctr,
                  ig_volgers, ig_bereik, ig_eng, ig_eng_rate, ig_posts, ig_new_followers,
                  fb_fans, fb_bereik_uniek, fb_engagements, fb_fans_added, fb_net_groei,
                  ig_likes=0, ig_comments=0, ig_saves=0, ig_shares=0,
                  fb_vertoningen=0, fb_video_views=0, fb_neg_feedback=0,
                  fb_likes=0, fb_comments=0, fb_shares=0, fb_posts=0, fb_eng_rate="—",
                  lead_leads=0, lead_cpl="—", lead_spend=0,
                  lead_freq="—", lead_bereik=0, lead_impressies=0, lead_cpm="—", lead_ctr="—",
                  klik_klikken=0, klik_cpc="—", klik_spend=0,
                  klik_freq="—", klik_bereik=0, klik_impressies=0, klik_cpm="—", klik_ctr="—",
                  d30=None):

    d30 = d30 or {}

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

    def pct_fmt(v):
        if v in ("—", None, ""):
            return "—"
        s = str(v)
        return s if s.endswith("%") else f"{s}%"

    def badge_volgers(waarde):
        try:
            n = int(waarde)
        except (TypeError, ValueError):
            return '<span class="cmp cmp-neu">— geen data</span>'
        if n > 0:
            return f'<span class="cmp cmp-pos">▲ +{n} volgers</span>'
        elif n < 0:
            return f'<span class="cmp cmp-neg">▼ {n} volgers</span>'
        else:
            return '<span class="cmp cmp-gelijk">= 0 volgers</span>'

    def badge(waarde_7d, totaal_30d, factor=7/30, omgekeerd=False):
        """Geeft HTML badge terug met % verschil en 30d gemiddelde."""
        diff, gem = pct_diff(waarde_7d, totaal_30d, factor)
        if diff is None:
            return '<span class="cmp cmp-neu">— geen vergelijking</span>'
        goed = diff >= 0 if not omgekeerd else diff <= 0
        kleur = "cmp-pos" if goed else "cmp-neg"
        pijl  = "▲" if diff >= 0 else "▼"
        gem_str = fmt(gem) if isinstance(gem, float) and gem == int(gem) else str(round(gem, 1))
        return f'<span class="cmp {kleur}">{pijl} {abs(diff):.1f}%</span><span class="cmp-gem">30d gem: {gem_str}</span>'

    def badge_eur(waarde_7d, totaal_30d, factor=7/30, omgekeerd=False):
        diff, gem = pct_diff(waarde_7d, totaal_30d, factor)
        if diff is None:
            return '<span class="cmp cmp-neu">— geen vergelijking</span>'
        goed = diff >= 0 if not omgekeerd else diff <= 0
        kleur = "cmp-pos" if goed else "cmp-neg"
        pijl  = "▲" if diff >= 0 else "▼"
        return f'<span class="cmp {kleur}">{pijl} {abs(diff):.1f}%</span><span class="cmp-gem">30d gem: {eur_fmt(gem)}</span>'

    def mini(waarde_7d, gem_30d, omgekeerd=False):
        """Klein pijltje (▲/▼) naast waarde: groen=beter, rood=slechter dan 30d gem."""
        try:
            w = float(waarde_7d)
            g = float(gem_30d)
        except (TypeError, ValueError):
            return ""
        if g == 0:
            return ""
        diff = ((w - g) / g) * 100
        goed = diff <= 0 if omgekeerd else diff >= 0
        kleur = "#2ecc8a" if goed else "#ff4d6a"
        pijl  = "▲" if diff >= 0 else "▼"
        return f' <span style="font-size:0.58rem;color:{kleur};font-weight:700;" title="30d gem: {g:.2f} ({diff:+.1f}%)">{pijl}</span>'

    # Pre-bereken 30d gemiddelden per dag voor lead/klik
    _f = PERIODE_DAGEN / 30
    lead_spend_30g  = d30.get("lead_spend_30", 0) * _f
    lead_leads_30g  = d30.get("lead_leads_30", 0) * _f
    lead_cpl_30g    = d30.get("lead_cpl_30")
    lead_freq_30g   = d30.get("lead_freq_30")
    lead_bereik_30g = d30.get("lead_bereik_30", 0) * _f
    lead_impr_30g   = d30.get("lead_impr_30", 0) * _f
    lead_cpm_30g    = d30.get("lead_cpm_30")
    lead_ctr_30g    = d30.get("lead_ctr_30")
    klik_spend_30g  = d30.get("klik_spend_30", 0) * _f
    klik_klik_30g   = d30.get("klik_klik_30", 0) * _f
    klik_cpc_30g    = d30.get("klik_cpc_30")
    klik_freq_30g   = d30.get("klik_freq_30")
    klik_bereik_30g = d30.get("klik_bereik_30", 0) * _f
    klik_impr_30g   = d30.get("klik_impr_30", 0) * _f
    klik_cpm_30g    = d30.get("klik_cpm_30")
    klik_ctr_30g    = d30.get("klik_ctr_30")

    html_pad = Path(__file__).parent / "index.html"
    gegenereerd_op = datetime.datetime.now().strftime("%d-%m-%Y om %H:%M")
    nu_tijd        = datetime.datetime.now().strftime("%H:%M")

    bereik_totaal = ig_bereik + fb_bereik_uniek
    eng_totaal    = ig_eng + fb_engagements
    cpl_fmt       = eur_fmt(meta_cpl) if meta_cpl not in ("—", None, "") else "—"

    # CSS funnel — logaritmische breedteberekening
    def funnel_breedte(waarde, maximum):
        if not waarde or not maximum or maximum <= 0:
            return 12
        try:
            w = math.log(max(waarde, 1)) / math.log(max(maximum, 2)) * 100
            return max(12, min(100, round(w, 1)))
        except Exception:
            return 12

    def funnel_drop(huidig, vorige):
        try:
            if vorige and vorige > 0:
                d = (huidig - vorige) / vorige * 100
                return f"{d:+.1f}%"
        except Exception:
            pass
        return ""

    _fn_max = bereik_totaal if bereik_totaal > 0 else 1
    funnel_stappen = [
        ("Bereik",      bereik_totaal,  "#4f9eff", funnel_breedte(bereik_totaal, _fn_max)),
        ("Impressies",  meta_impressies,"#ffaa2e", funnel_breedte(meta_impressies, _fn_max)),
        ("Klikken",     meta_klikken,  "#b06aff", funnel_breedte(meta_klikken, _fn_max)),
        ("Leads",       meta_leads,    "#2ecc8a", funnel_breedte(meta_leads, _fn_max)),
    ]

    def maak_funnel_html():
        rijen = []
        for i, (label, waarde, kleur, breedte) in enumerate(funnel_stappen):
            val_str = f"{int(waarde):,}".replace(",", ".") if isinstance(waarde, (int, float)) else "—"
            vorige_val = funnel_stappen[i-1][1] if i > 0 else None
            drop = funnel_drop(waarde, vorige_val) if i > 0 else ""
            pct_van_bereik = f"{waarde/max(_fn_max,1)*100:.2f}%" if isinstance(waarde, (int,float)) else ""
            drop_html = f'<span class="fn-drop">{drop}</span>' if drop else ""
            rijen.append(f"""
      <div class="fn-row">
        {drop_html}
        <div class="fn-bar" style="width:{breedte}%;background:{kleur}22;border:2px solid {kleur};border-radius:8px;padding:10px 16px;display:flex;justify-content:space-between;align-items:center;">
          <span class="fn-label" style="color:#c8d4ee;font-weight:600;">{label}</span>
          <span class="fn-num" style="color:{kleur};font-size:1.15rem;font-weight:700;">{val_str}</span>
          <span class="fn-pct" style="color:#5a6480;font-size:0.8rem;">{pct_van_bereik}</span>
        </div>
      </div>""")
        return "\n".join(rijen)

    funnel_html = maak_funnel_html()

    # GA4 funnel
    try:
        eng_rate_float = float(str(ga4_eng_rate).replace("%", "").replace(",", "."))
    except (ValueError, TypeError):
        eng_rate_float = 0
    ga4_engaged = round(ga4_sessies * eng_rate_float / 100) if isinstance(ga4_sessies, (int, float)) else 0

    _ga4_max = ga4_sessies if isinstance(ga4_sessies, (int, float)) and ga4_sessies > 0 else 1
    ga4_funnel_stappen = [
        ("Sessies",          ga4_sessies,  "#4f9eff", funnel_breedte(ga4_sessies, _ga4_max)),
        ("Gebruikers",       ga4_users,    "#ffaa2e", funnel_breedte(ga4_users, _ga4_max)),
        ("Engaged sessies",  ga4_engaged,  "#b06aff", funnel_breedte(ga4_engaged, _ga4_max)),
        ("Conversies",       ga4_conv,     "#2ecc8a", funnel_breedte(ga4_conv, _ga4_max)),
    ]

    def maak_ga4_funnel_html():
        rijen = []
        for i, (label, waarde, kleur, breedte) in enumerate(ga4_funnel_stappen):
            val_str = f"{int(waarde):,}".replace(",", ".") if isinstance(waarde, (int, float)) else "—"
            vorige_val = ga4_funnel_stappen[i-1][1] if i > 0 else None
            drop = funnel_drop(waarde, vorige_val) if i > 0 else ""
            pct_van_max = f"{waarde/max(_ga4_max,1)*100:.1f}%" if isinstance(waarde, (int,float)) else ""
            drop_html = f'<span class="fn-drop">{drop}</span>' if drop else ""
            rijen.append(f"""
      <div class="fn-row">
        {drop_html}
        <div class="fn-bar" style="width:{breedte}%;background:{kleur}22;border:2px solid {kleur};border-radius:8px;padding:10px 16px;display:flex;justify-content:space-between;align-items:center;">
          <span class="fn-label" style="color:#c8d4ee;font-weight:600;">{label}</span>
          <span class="fn-num" style="color:{kleur};font-size:1.15rem;font-weight:700;">{val_str}</span>
          <span class="fn-pct" style="color:#5a6480;font-size:0.8rem;">{pct_van_max}</span>
        </div>
      </div>""")
        return "\n".join(rijen)

    ga4_funnel_html = maak_ga4_funnel_html()

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
    color: #8a9bbf;
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

  /* ── Twee-kolom vergelijking ── */
  .cmp-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    padding-top: 9px;
    border-top: 1px solid #1e2445;
    gap: 6px;
    flex-wrap: wrap;
  }}
  .cmp {{
    font-size: 0.88rem;
    font-weight: 800;
    border-radius: 6px;
    padding: 3px 9px;
  }}
  .cmp-pos   {{ background: rgba(46,204,138,0.2);  color: #2ecc8a; }}
  .cmp-neg   {{ background: rgba(255,80,80,0.2);   color: #ff6060; }}
  .cmp-gelijk{{ background: rgba(255,170,46,0.2);  color: #ffaa2e; }}
  .cmp-neu   {{ color: #8a9bbf; font-size: 0.78rem; font-weight: 400; }}
  .cmp-gem {{ font-size: 0.82rem; font-weight: 600; color: #c8d4ee; }}

  /* ── CSS Funnel ── */
  .fn-wrap {{ display: flex; flex-direction: column; align-items: center; gap: 0; width: 100%; }}
  .fn-row  {{ width: 100%; display: flex; flex-direction: column; align-items: center; }}
  .fn-drop {{ color: #5a6480; font-size: 0.78rem; margin: 3px 0; }}

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
  .metric-row .ml {{ color: #c8d4ee; }}
  .metric-row .mv {{ font-weight: 700; color: #ffffff; }}

  /* ── Accent colours per fase ── */
  .f1 .card-value {{ color: #4f9eff; }}
  .f2 .card-value {{ color: #2ecc8a; }}
  .f3 .card-value {{ color: #ffaa2e; }}
  .f4 .card-value {{ color: #b06aff; }}

  .f1 .fase-header {{ box-shadow: 0 4px 20px rgba(79,158,255,0.15); }}
  .f2 .fase-header {{ box-shadow: 0 4px 20px rgba(46,204,138,0.15); }}
  .f3 .fase-header {{ box-shadow: 0 4px 20px rgba(255,170,46,0.15); }}
  .f4 .fase-header {{ box-shadow: 0 4px 20px rgba(176,106,255,0.15); }}

  /* ── Topbar tekst ── */
  .topbar-meta {{ color: #8a9bbf; }}

  /* ── Footer ── */
  .footer {{
    margin-top: 18px;
    text-align: center;
    font-size: 0.7rem;
    color: #8a9bbf;
    padding-top: 14px;
    border-top: 1px solid #131730;
  }}
  .footer a {{ color: #4f9eff; text-decoration: none; }}
  .chart-card {{ padding: 14px 16px; }}
  canvas {{ max-height: 180px; }}

  /* ── Sectie titels ── */
  .sectie-titel {{
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #5a6890;
    margin: 28px 0 12px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .sectie-titel::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: #1a1e38;
  }}

  /* ── Kanaal grid (4 kolommen) ── */
  .kanalen {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }}
  .kanaal {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}

  /* ── Journey grid ── */
  .journey {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }}
  .fase {{
    display: flex;
    flex-direction: column;
    gap: 8px;
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
  /* ── Journey fase kleuren: achtergrond header + accent tekst gekoppeld ── */
  .h-blauw  {{ background: linear-gradient(135deg, #0f2d6b, #1a3d8a); border: 1px solid #2a52b0; }}
  .h-groen  {{ background: linear-gradient(135deg, #0a3528, #0f4a38); border: 1px solid #1a6e52; }}
  .h-amber  {{ background: linear-gradient(135deg, #3d2000, #5a3200); border: 1px solid #8a5c00; }}
  .h-paars  {{ background: linear-gradient(135deg, #2a1060, #3d1a8a); border: 1px solid #6030c0; }}

  /* ── Kanaal kleuren: elke kolom eigen consistent paar ── */
  .h-ga4    {{ background: linear-gradient(135deg, #0f2d6b, #1a3d8a); border: 1px solid #2a52b0; }}
  .h-meta   {{ background: linear-gradient(135deg, #3d1800, #5a2800); border: 1px solid #a04000; }}
  .h-ig     {{ background: linear-gradient(135deg, #3a0a5a, #500a80); border: 1px solid #8020c0; }}
  .h-fb     {{ background: linear-gradient(135deg, #0a3528, #0f4a38); border: 1px solid #1a6e52; }}

  /* Journey: accent kleuren per fase passend bij header */
  .f1 .card-value {{ color: #4f9eff; }}   /* blauw  → h-blauw  */
  .f2 .card-value {{ color: #2ecc8a; }}   /* groen  → h-groen  */
  .f3 .card-value {{ color: #ffaa2e; }}   /* amber  → h-amber  */
  .f4 .card-value {{ color: #b06aff; }}   /* paars  → h-paars  */

  /* Kanalen: accent kleuren passend bij header */
  .k-ga4  .card-value {{ color: #4f9eff; }}   /* blauw  → h-ga4   */
  .k-meta .card-value {{ color: #ff8040; }}   /* oranje → h-meta  */
  .k-ig   .card-value {{ color: #c084fc; }}   /* paars  → h-ig    */
  .k-fb   .card-value {{ color: #2ecc8a; }}   /* groen  → h-fb    */

  /* Gloed onder headers */
  .f1 .fase-header, .k-ga4  .fase-header {{ box-shadow: 0 4px 20px rgba(79,158,255,0.18); }}
  .f2 .fase-header, .k-fb   .fase-header {{ box-shadow: 0 4px 20px rgba(46,204,138,0.18); }}
  .f3 .fase-header               {{ box-shadow: 0 4px 20px rgba(255,170,46,0.18); }}
  .f4 .fase-header               {{ box-shadow: 0 4px 20px rgba(176,106,255,0.18); }}
  .k-meta .fase-header           {{ box-shadow: 0 4px 20px rgba(255,128,64,0.18); }}
  .k-ig   .fase-header           {{ box-shadow: 0 4px 20px rgba(192,132,252,0.18); }}

  @media (max-width: 900px) {{
    .kanalen, .journey {{ grid-template-columns: repeat(2, 1fr); }}
  }}
  @media (max-width: 500px) {{
    .kanalen, .journey {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">Marketing <span>Dashboard</span> &mdash; IVECO Schouten</div>
  <div class="topbar-meta">
    <span>Ads & GA4: {PERIODE_DAGEN} dagen | Social: 28 dagen &nbsp;|&nbsp; {vandaag}</span>
    <a href="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}" target="_blank"
       style="color:#5b8dee;text-decoration:none;">↗ Google Sheets</a>
    <span class="topbar-time">{nu_tijd}</span>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════ -->
<!-- SECTIE 1: CUSTOMER JOURNEY                          -->
<!-- ═══════════════════════════════════════════════════ -->
<div class="sectie-titel">Customer Journey — van zichtbaarheid tot conversie</div>

<div class="journey">

  <!-- ════ FASE 1: BEWUSTWORDING ════ -->
  <div class="fase f1">
    <div class="fase-header h-blauw">
      👁 Bewustwording
      <div class="fase-source">Instagram · Facebook (28d) · Meta Ads (7d)</div>
    </div>

    <div class="card">
      <div class="card-label">Totaal bereik</div>
      <div class="card-value">{fmt(bereik_totaal)}</div>
      <div class="cmp-row"></div>
    </div>

    <div class="card">
      <div class="card-label">Meta Ads impressies</div>
      <div class="card-value">{fmt(meta_impressies)}</div>
      <div class="cmp-row">{badge(meta_impressies, d30.get("meta_impr_30",0))}</div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Instagram bereik</span><span class="mv">{fmt(ig_bereik)}</span></div>
      <div class="metric-row"><span class="ml">Facebook bereik (28d)</span><span class="mv">{fmt(fb_bereik_uniek)}</span></div>
      <div class="metric-row"><span class="ml">Meta Ads bereik ({PERIODE_DAGEN}d)</span><span class="mv">{fmt(meta_bereik)}</span></div>
      <div class="metric-row"><span class="ml">Nieuwe IG volgers</span><span class="mv">+{fmt(ig_new_followers)}</span></div>
      <div class="metric-row"><span class="ml">Nieuwe FB volgers</span><span class="mv">+{fmt(fb_fans_added)}</span></div>
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
      <div class="fase-source">Instagram · Facebook (28d)</div>
    </div>

    <div class="card">
      <div class="card-label">Totaal engagement</div>
      <div class="card-value">{fmt(eng_totaal)}</div>
      <div class="cmp-row"></div>
    </div>

    <div class="card">
      <div class="card-label">Meta Ads klikken</div>
      <div class="card-value">{fmt(meta_klikken)}</div>
      <div class="cmp-row">{badge(meta_klikken, d30.get("meta_klikken_30", 0))}</div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Instagram engagement</span><span class="mv">{fmt(ig_eng)}</span></div>
      <div class="metric-row"><span class="ml">IG engagement rate</span><span class="mv">{pct_fmt(ig_eng_rate)}</span></div>
      <div class="metric-row"><span class="ml">Facebook engagement</span><span class="mv">{fmt(fb_engagements)}</span></div>
      <div class="metric-row"><span class="ml">FB engagement rate</span><span class="mv">{pct_fmt(fb_eng_rate)}</span></div>
      <div class="metric-row"><span class="ml">Meta Ads CTR</span><span class="mv">{f"{meta_ctr}%"}</span></div>
    </div>

    <div class="card chart-card">
      <div class="card-label">Engagement verdeling</div>
      <canvas id="chartEngagement"></canvas>
    </div>
  </div>

  <!-- ════ FASE 3: OVERWEGING ════ -->
  <div class="fase f3">
    <div class="fase-header h-amber">
      🔍 Overweging
      <div class="fase-source">GA4 Website Analytics</div>
    </div>


    <div class="card">
      <div class="card-label">Websitesessies</div>
      <div class="card-value">{fmt(ga4_sessies)}</div>
      <div class="cmp-row">{badge(ga4_sessies, d30.get("ga4_sessies_30", 0))}</div>
    </div>

    <div class="card">
      <div class="card-label">Gebruikers</div>
      <div class="card-value">{fmt(ga4_users)}</div>
      <div class="cmp-row">{badge(ga4_users, d30.get("ga4_users_30", 0))}</div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Terugkerende bezoekers</span><span class="mv">{fmt(ga4_users - ga4_new_users if isinstance(ga4_users, int) and isinstance(ga4_new_users, int) else "—")}</span></div>
      <div class="metric-row"><span class="ml">Bounce rate</span><span class="mv">{ga4_bounce}</span></div>
      <div class="metric-row"><span class="ml">Engagement rate</span><span class="mv">{pct_fmt(ga4_eng_rate)}</span></div>
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
      <div class="cmp-row">{badge(meta_leads, d30.get("meta_leads_30", 0))}</div>
    </div>

    <div class="card">
      <div class="card-label">GA4 conversies</div>
      <div class="card-value">{fmt(ga4_conv)}</div>
      <div class="cmp-row">{badge(ga4_conv, d30.get("ga4_conv_30", 0))}</div>
    </div>

    <div class="metrics">
      <div class="metric-row"><span class="ml">Cost per lead</span><span class="mv">{cpl_fmt}</span></div>
      <div class="metric-row"><span class="ml">GA4 conv. rate</span><span class="mv">{pct_fmt(ga4_conv_rate)}</span></div>
      <div class="metric-row"><span class="ml">Meta Ads uitgegeven</span><span class="mv">{eur_fmt(meta_spend)}</span></div>
    </div>

    <div class="card chart-card" style="justify-content:flex-start;">
      <div class="card-label">Conversie funnel</div>
      <div style="width:100%;margin-top:8px;">
{"".join(f'<div style="margin:4px 0;"><div style="width:{w}%;background:{c}22;border:1px solid {c};border-radius:5px;padding:4px 10px;display:flex;justify-content:space-between;"><span style="color:#c8d4ee;font-size:0.75rem;">{l}</span><span style="color:{c};font-size:0.75rem;font-weight:700;">{fmt(v)}</span></div></div>' for l,v,c,w in funnel_stappen)}
      </div>
    </div>
  </div>

</div><!-- /journey -->

<!-- ═══════════════════════════════════════════════════ -->
<!-- SECTIE 2: KANAAL OVERZICHT                          -->
<!-- ═══════════════════════════════════════════════════ -->
<div class="sectie-titel">Kanaal overzicht — afgelopen {PERIODE_DAGEN} dagen</div>

<div class="kanalen">

  <!-- ── GA4 ── -->
  <div class="kanaal k-ga4">
    <div class="fase-header h-ga4">
      📊 Website — GA4
      <div class="fase-source">Google Analytics 4 · {PERIODE_DAGEN} dagen</div>
    </div>
    <div class="card">
      <div class="card-label">Sessies</div>
      <div class="card-value">{fmt(ga4_sessies)}</div>
      <div class="cmp-row">{badge(ga4_sessies, d30.get("ga4_sessies_30", 0))}</div>
    </div>
    <div class="card">
      <div class="card-label">Gebruikers</div>
      <div class="card-value">{fmt(ga4_users)}</div>
      <div class="cmp-row">{badge(ga4_users, d30.get("ga4_users_30", 0))}</div>
    </div>
    <div class="metrics">
      <div class="metric-row"><span class="ml">Terugkerende bezoekers</span><span class="mv">{fmt(ga4_users - ga4_new_users if isinstance(ga4_users, int) and isinstance(ga4_new_users, int) else "—")}</span></div>
      <div class="metric-row"><span class="ml">Nieuwe bezoekers</span><span class="mv">{fmt(ga4_new_users)}</span></div>
      <div class="metric-row"><span class="ml">Bounce rate</span><span class="mv">{ga4_bounce}</span></div>
      <div class="metric-row"><span class="ml">Engagement rate</span><span class="mv">{pct_fmt(ga4_eng_rate)}</span></div>
      <div class="metric-row"><span class="ml">Gem. sessieduur</span><span class="mv">{ga4_gem_duur}</span></div>
      <div class="metric-row"><span class="ml">Conversies</span><span class="mv">{fmt(ga4_conv)}</span></div>
      <div class="metric-row"><span class="ml">Conv. rate</span><span class="mv">{ga4_conv_rate}</span></div>
    </div>
  </div>

  <!-- ── META ADS ── -->
  <div class="kanaal k-meta">
    <div class="fase-header h-meta">
      📢 Betaald — Meta Ads
      <div class="fase-source">Facebook & Instagram Ads · {PERIODE_DAGEN} dagen</div>
    </div>
    <div class="card">
      <div class="card-label">Totaal uitgegeven</div>
      <div class="card-value">{eur_fmt(meta_spend)}</div>
      <div class="cmp-row">{badge_eur(meta_spend, d30.get("meta_spend_30", 0))}</div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">

      <!-- Lead kolom -->
      <div style="background:#0e1224;border:1px solid #1c2040;border-radius:11px;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#1a2640,#141e36);padding:10px 14px;border-bottom:1px solid #1c2040;display:flex;align-items:center;gap:8px;">
          <span style="font-size:1.1rem;">🎯</span>
          <div>
            <div style="font-size:0.7rem;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:#fff;">Lead</div>
            <div style="font-size:0.62rem;color:#5a6480;font-weight:500;">Leadgeneratie</div>
          </div>
        </div>
        <div style="padding:10px 14px;display:flex;flex-direction:column;gap:6px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Uitgegeven</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{eur_fmt(lead_spend)}{mini(lead_spend, lead_spend_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Resultaat</span>
            <span style="font-size:0.82rem;font-weight:700;color:#2ecc8a;">{fmt(lead_leads)} leads{mini(lead_leads, lead_leads_30g)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">CPL</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{eur_fmt(lead_cpl) if lead_cpl != "—" else "—"}{mini(lead_cpl, lead_cpl_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Frequentie</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{f"{lead_freq}×" if lead_freq != "—" else "—"}{mini(lead_freq, lead_freq_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Bereik</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{fmt(lead_bereik) if lead_bereik else "—"}{mini(lead_bereik, lead_bereik_30g)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Impressies</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{fmt(lead_impressies) if lead_impressies else "—"}{mini(lead_impressies, lead_impr_30g)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">CPM</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{eur_fmt(lead_cpm) if lead_cpm != "—" else "—"}{mini(lead_cpm, lead_cpm_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">CTR</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{f"{lead_ctr}%" if lead_ctr != "—" else "—"}{mini(lead_ctr, lead_ctr_30g)}</span>
          </div>
        </div>
      </div>

      <!-- Klik kolom -->
      <div style="background:#0e1224;border:1px solid #1c2040;border-radius:11px;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#1a2640,#141e36);padding:10px 14px;border-bottom:1px solid #1c2040;display:flex;align-items:center;gap:8px;">
          <span style="font-size:1.1rem;">🖱</span>
          <div>
            <div style="font-size:0.7rem;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:#fff;">Klik</div>
            <div style="font-size:0.62rem;color:#5a6480;font-weight:500;">Websiteverkeer</div>
          </div>
        </div>
        <div style="padding:10px 14px;display:flex;flex-direction:column;gap:6px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Uitgegeven</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{eur_fmt(klik_spend)}{mini(klik_spend, klik_spend_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Resultaat</span>
            <span style="font-size:0.82rem;font-weight:700;color:#4f9eff;">{fmt(klik_klikken)} klikken{mini(klik_klikken, klik_klik_30g)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">CPC</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{eur_fmt(klik_cpc) if klik_cpc != "—" else "—"}{mini(klik_cpc, klik_cpc_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Frequentie</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{f"{klik_freq}×" if klik_freq != "—" else "—"}{mini(klik_freq, klik_freq_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Bereik</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{fmt(klik_bereik) if klik_bereik else "—"}{mini(klik_bereik, klik_bereik_30g)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Impressies</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{fmt(klik_impressies) if klik_impressies else "—"}{mini(klik_impressies, klik_impr_30g)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">CPM</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{eur_fmt(klik_cpm) if klik_cpm != "—" else "—"}{mini(klik_cpm, klik_cpm_30g, omgekeerd=True)}</span>
          </div>
          <div style="height:1px;background:#1c2040;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.67rem;color:#8a9bbf;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">CTR</span>
            <span style="font-size:0.82rem;font-weight:700;color:#dde3f0;">{f"{klik_ctr}%" if klik_ctr != "—" else "—"}{mini(klik_ctr, klik_ctr_30g)}</span>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── INSTAGRAM ── -->
  <div class="kanaal k-ig">
    <div class="fase-header h-ig">
      📸 Organisch — Instagram
      <div class="fase-source">Instagram Business Account · 28 dagen</div>
    </div>
    <div class="card">
      <div class="card-label">Volgers</div>
      <div class="card-value">{fmt(ig_volgers)}</div>
      <div class="cmp-row">{badge_volgers(ig_new_followers)}</div>
    </div>
    <div class="card">
      <div class="card-label">Bereik</div>
      <div class="card-value">{fmt(ig_bereik)}</div>
      <div class="cmp-row">{badge(ig_bereik, d30.get("ig_bereik_30", 0), factor=1)}</div>
    </div>
    <div class="metrics">
      <div class="metric-row"><span class="ml">Engagement</span><span class="mv">{fmt(ig_eng)}</span></div>
      <div class="metric-row"><span class="ml">Engagement rate</span><span class="mv">{pct_fmt(ig_eng_rate)}</span></div>
      <div class="metric-row"><span class="ml">Likes</span><span class="mv">{fmt(ig_likes)}</span></div>
      <div class="metric-row"><span class="ml">Comments</span><span class="mv">{fmt(ig_comments)}</span></div>
      <div class="metric-row"><span class="ml">Shares</span><span class="mv">{fmt(ig_shares)}</span></div>
      <div class="metric-row"><span class="ml">Saves</span><span class="mv">{fmt(ig_saves)}</span></div>
      <div class="metric-row"><span class="ml">Posts geanalyseerd</span><span class="mv">{fmt(ig_posts)}</span></div>
    </div>
  </div>

  <!-- ── FACEBOOK ── -->
  <div class="kanaal k-fb">
    <div class="fase-header h-fb">
      👍 Organisch — Facebook
      <div class="fase-source">Facebook Pagina · 28 dagen</div>
    </div>
    <div class="card">
      <div class="card-label">Volgers</div>
      <div class="card-value">{fmt(fb_fans)}</div>
      <div class="cmp-row">{badge_volgers(fb_fans_added)}</div>
    </div>
    <div class="card">
      <div class="card-label">Bereik (28d)</div>
      <div class="card-value">{fmt(fb_bereik_uniek)}</div>
      <div class="cmp-row"></div>
    </div>
    <div class="metrics">
      <div class="metric-row"><span class="ml">Engagement</span><span class="mv">{fmt(fb_engagements)}</span></div>
      <div class="metric-row"><span class="ml">Engagement rate</span><span class="mv">{pct_fmt(fb_eng_rate)}</span></div>
      <div class="metric-row"><span class="ml">Likes</span><span class="mv">{fmt(fb_likes)}</span></div>
      <div class="metric-row"><span class="ml">Comments</span><span class="mv">{fmt(fb_comments)}</span></div>
      <div class="metric-row"><span class="ml">Shares</span><span class="mv">{fmt(fb_shares)}</span></div>
      <div class="metric-row"><span class="ml">Posts geanalyseerd</span><span class="mv">{fmt(fb_posts)}</span></div>
      <div class="metric-row"><span class="ml">Video views</span><span class="mv">{fmt(fb_video_views)}</span></div>
    </div>
  </div>

</div><!-- /kanalen -->

<!-- ═══════════════════════════════════════════════════ -->
<!-- SECTIE 3: CONVERSIE FUNNEL                          -->
<!-- ═══════════════════════════════════════════════════ -->
<div class="sectie-titel">Conversie funnels</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">

  <div style="background:linear-gradient(160deg,#111428,#0e1224);border:1px solid #1c2040;border-radius:12px;padding:24px 28px;">
    <div style="color:#ff8040;font-size:0.72rem;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">📢 Social — bereik tot lead</div>
    <p style="color:#5a6480;font-size:0.75rem;margin:0 0 16px 0;">Breedte op log-schaal</p>
    <div class="fn-wrap">
{funnel_html}
    </div>
    <div style="margin-top:16px;padding-top:14px;border-top:1px solid #1c2040;">
      <span style="color:#5a6480;font-size:0.8rem;">CPL &nbsp;</span>
      <span style="color:#2ecc8a;font-size:1.2rem;font-weight:700;">{cpl_fmt}</span>
      <span style="color:#5a6480;font-size:0.75rem;margin-left:10px;">{fmt(meta_leads)} leads / {eur_fmt(meta_spend)}</span>
    </div>
  </div>

  <div style="background:linear-gradient(160deg,#111428,#0e1224);border:1px solid #1c2040;border-radius:12px;padding:24px 28px;">
    <div style="color:#4f9eff;font-size:0.72rem;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">🌐 GA4 — sessies tot conversie</div>
    <p style="color:#5a6480;font-size:0.75rem;margin:0 0 16px 0;">Lineaire schaal — website gedrag</p>
    <div class="fn-wrap">
{ga4_funnel_html}
    </div>
    <div style="margin-top:16px;padding-top:14px;border-top:1px solid #1c2040;">
      <span style="color:#5a6480;font-size:0.8rem;">Conv. rate &nbsp;</span>
      <span style="color:#2ecc8a;font-size:1.2rem;font-weight:700;">{ga4_conv_rate}</span>
      <span style="color:#5a6480;font-size:0.75rem;margin-left:10px;">{fmt(ga4_conv)} conversies / {fmt(ga4_sessies)} sessies</span>
    </div>
  </div>

</div>

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
    labels: ['Instagram (28d)', 'Facebook (28d)'],
    datasets: [{{ data: [{ig_bereik}, {fb_bereik_uniek}],
      backgroundColor: ['#4f9eff','#2ecc8a'],
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
    labels: ['Sessies', 'Gebruikers', 'Conversies'],
    datasets: [{{ data: [{ga4_sessies}, {ga4_users}, {ga4_conv}],
      backgroundColor: ['rgba(255,170,46,0.25)','rgba(79,158,255,0.25)','rgba(46,204,138,0.25)'],
      borderColor:     ['#ffaa2e','#4f9eff','#2ecc8a'],
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

</script>

</body>
</html>"""

    with open(html_pad, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  ✓ HTML dashboard opgeslagen: {html_pad}")
    return html_pad


# ============================================================
# STANDALONE TEST — genereer HTML met dummy data
# ============================================================
if __name__ == "__main__":
    print("HTML Dashboard — standalone test met dummy data...")
    pad = genereer_html(
        vandaag="14-04-2026",
        ga4_users=1200, ga4_new_users=800, ga4_sessies=1800, ga4_conv=25,
        ga4_conv_rate="1.39%", ga4_bounce="45.2%", ga4_eng_rate="54.8%", ga4_gem_duur="2m 15s",
        meta_spend=500.0, meta_leads=12, meta_cpl=41.67, meta_impressies=25000,
        meta_bereik=15000, meta_freq=1.67, meta_klikken=350, meta_ctr=1.4,
        ig_volgers=2500, ig_bereik=8000, ig_eng=450, ig_eng_rate=5.6,
        ig_posts=8, ig_new_followers=25,
        fb_fans=3200, fb_bereik_uniek=5000, fb_engagements=200,
        fb_fans_added=15, fb_net_groei=15,
        ig_likes=300, ig_comments=50, ig_saves=60, ig_shares=40,
        fb_likes=120, fb_comments=30, fb_shares=50, fb_posts=5, fb_eng_rate="4.0",
        fb_video_views=800,
        lead_leads=8, lead_cpl=37.50, lead_spend=300.0,
        lead_freq=1.5, lead_bereik=10000, lead_impressies=15000, lead_cpm=20.0, lead_ctr=1.8,
        klik_klikken=200, klik_cpc=1.0, klik_spend=200.0,
        klik_freq=1.8, klik_bereik=8000, klik_impressies=10000, klik_cpm=20.0, klik_ctr=2.0,
    )
    print(f"  Test HTML: {pad}")
    print("  Open index.html in je browser om het resultaat te bekijken.")
