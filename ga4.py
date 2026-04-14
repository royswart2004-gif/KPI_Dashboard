"""
GA4 (Google Analytics 4) data ophalen en naar Google Sheets schrijven.
Bevat: Overzicht, Verkeersbronnen, Gedrag.
"""

from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, OrderBy
)

from config import GA4_PROPERTY_ID, PERIODE_DAGEN, STIJL_KPI_WAARDE
from utils import (
    format_tijd, haal_of_maak_sheet, schrijf_blok,
    schrijf_paginatitel, stel_kolombreedte_in,
)


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
