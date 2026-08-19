"""Page « Monitoring » : tableau de bord avancé de l'activité du projet.

Ce tableau de bord agrège :
- l'état temps réel du backend (`/health`, `/models`, `/health/detail`) ;
- des **KPIs étendus** : durée de séance, débit, volume, taux de succès ;
- les **latences par modèle / endpoint** (moyenne, écart-type, P50/P90/P95/P99) ;
- des **répartitions d'usage** (par modèle, par endpoint) et des **distributions** ;
- des **tendances** (moyenne mobile, volume, disponibilité) ;
- le **diagnostic moteur** (uptime, mémoire, config) ;
- le **journal complet** des requêtes, filtrable, réponses incluses ;
- un **export JSON** des données brutes.

L'historique provient du module :mod:`monitoring` (fichier JSON persistant),
alimenté automatiquement par le client HTTP (:mod:`api_client`).
"""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

import monitoring
from api_client import MODEL_ICONS, MODEL_LABELS, ApiError, get_health, get_health_detail
from services import cached_models
from ui import availability_badge

# Libellés lisibles pour les routes.
_PATH_LABELS = {
    "/health": "Santé",
    "/models": "Modèles",
    "/summarize": "Résumer",
    "/compare": "Comparer",
    "/summarize-file": "Résumer fichier",
}


def _path_label(path: str) -> str:
    return _PATH_LABELS.get(path, path)


def _load_frame(records: list[dict]) -> pd.DataFrame:
    """Convertit l'historique brut en DataFrame prêt pour l'analyse."""
    rows = []
    for r in records:
        model = r.get("model")
        if model == "compare":
            model = "Comparaison"
        rows.append(
            {
                "timestamp": pd.to_datetime(r.get("timestamp"), utc=True),
                "path": _path_label(r.get("path")),
                "route": r.get("path"),
                "method": r.get("method"),
                "model": model or "—",
                "status": r.get("status_code"),
                "ok": r.get("ok"),
                "duration_ms": r.get("duration_ms"),
                "inference_ms": r.get("inference_ms"),
                "in_chars": r.get("input_chars"),
                "out_chars": r.get("output_chars"),
                "error": r.get("error"),
                "summary": r.get("summary_preview"),
            }
        )
    return pd.DataFrame(rows)


def _percentiles(series: pd.Series) -> tuple[float, float, float]:
    """P50 / P95 / min d'une série de durées (NaN si vide)."""
    s = series.dropna()
    if s.empty:
        return float("nan"), float("nan"), float("nan")
    return s.quantile(0.5), s.quantile(0.95), s.min()


def _filter_period(records: list[dict], hours: float | None) -> list[dict]:
    """Ne garde que les enregistrements plus récents que ``hours`` heures."""
    if not hours:
        return records
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
    out = []
    for r in records:
        try:
            ts = pd.to_datetime(r.get("timestamp"), utc=True)
        except Exception:
            continue
        if ts >= cutoff:
            out.append(r)
    return out


def _fmt_hms(seconds: float) -> str:
    """Formate une durée en secondes sous forme lisible (jours, heures, min, s)."""
    if seconds is None or seconds != seconds:
        return "—"
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}j {h:02d}h {m:02d}m"
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _fmt_pct(value: float) -> str:
    """Formate un pourcentage lisible, ou « — » si NaN."""
    if value != value:
        return "—"
    return f"{value:.0f}%"


def _quantiles(series: pd.Series) -> dict[str, float]:
    """Statistiques descriptives d'une série : moy, std, min, P50/P90/P95/P99, max."""
    s = series.dropna()
    if s.empty:
        return {"count": 0, "mean": None, "std": None, "min": None,
                "p50": None, "p90": None, "p95": None, "p99": None, "max": None}
    return {
        "count": int(s.size),
        "mean": round(s.mean(), 1),
        "std": round(s.std(), 1),
        "min": round(s.min(), 1),
        "p50": round(s.quantile(0.50), 1),
        "p90": round(s.quantile(0.90), 1),
        "p95": round(s.quantile(0.95), 1),
        "p99": round(s.quantile(0.99), 1),
        "max": round(s.max(), 1),
    }
def availability_label(available: bool, mode: str | None) -> str:
    """Libellé court de disponibilité d'un modèle pour les tuiles KPI."""
    if not available:
        return "Indisponible"
    return {"trained": "Entraîné", "fine_tuned": "Fine-tuné",
            "zero_shot": "Zero-shot"}.get(mode, "OK")


def render_kpis(base: str) -> None:
    """Ligne de KPIs : santé API, modèles, synthèse du journal."""
    try:
        start = time.perf_counter()
        health = get_health(base)
        health_ms = (time.perf_counter() - start) * 1000
        health_ok = health.get("status") == "ok"
    except ApiError:
        health_ms = None
        health_ok = False

    models_available: dict[str, tuple[bool, str | None]] = {}
    try:
        for info in cached_models(base):
            name = info.get("name")
            if name:
                models_available[name] = (info.get("available", False),
                                          (info.get("detail") or {}).get("mode"))
    except ApiError:
        pass

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    t5_ = models_available.get("t5", (False, None))
    scratch_ = models_available.get("scratch", (False, None))
    m1.metric("API", "En ligne" if health_ok else "Injoignable", border=True,
              delta_color="normal" if health_ok else "inverse")
    m2.metric("Latence API", f"{health_ms:.0f} ms" if health_ms is not None else "—",
              border=True)
    m3.metric("T5", availability_label(*t5_), border=True,
              delta="✓" if t5_[0] else "✗",
              delta_color="normal" if t5_[0] else "inverse")
    m4.metric("Scratch", availability_label(*scratch_), border=True,
              delta="✓" if scratch_[0] else "✗",
              delta_color="normal" if scratch_[0] else "inverse")

    records = monitoring.all_records()
    if not records:
        m5.metric("Requêtes", "0", border=True)
        m6.metric("Taux de succès", "—", border=True)
        return

    frame = _load_frame(records)
    total = len(frame)
    ok_count = int(frame["ok"].sum())
    success = (ok_count / total * 100) if total else 0.0
    avg_dur = frame["duration_ms"].mean()
    m5.metric("Requêtes", f"{total}", border=True,
              delta=f"{success:.0f}% succès",
              delta_color="normal" if success >= 80 else "off")
    m6.metric("Latence moy.", f"{avg_dur:.0f} ms" if avg_dur == avg_dur else "—",
              border=True)


def render_extended_kpis(records: list[dict]) -> None:
    """KPIs « activité » : durée de séance, débit, volume, latence P95, totaux."""
    st.markdown("### :material/timeline: Activité de la séance")
    if not records:
        st.caption("Aucune activité enregistrée pour l'instant.")
        return

    frame = _load_frame(records).sort_values("timestamp")
    first = frame["timestamp"].iloc[0]
    last = frame["timestamp"].iloc[-1]
    span_h = max((last - first).total_seconds() / 3600, 1e-6)
    rate = len(frame) / (span_h * 60)
    total_inf = frame["inference_ms"].sum() / 1000
    ok_count = int(frame["ok"].sum())
    inf = frame[frame["route"].isin(["/summarize", "/compare", "/summarize-file"])]
    p95_all = _quantiles(frame["duration_ms"])["p95"]
    p95_inf = _quantiles(inf["inference_ms"])["p95"] if not inf.empty else None
    avg_out = frame["out_chars"].dropna().mean()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Début", first.strftime("%H:%M:%S"), border=True)
    c2.metric("Fenêtre", _fmt_hms((last - first).total_seconds()), border=True)
    c3.metric("Débit", f"{rate:.1f} req/min", border=True)
    c4.metric("Inférence cumulée", f"{total_inf:.1f} s", border=True)
    c5.metric("Succès", _fmt_pct(ok_count / len(frame) * 100), border=True)
    c6.metric("Sortie moy.", f"{avg_out:.0f}" if avg_out == avg_out else "—",
              border=True)

    c7, c8, c9, c10 = st.columns(4)
    c7.metric("Latence P95", f"{p95_all:.0f} ms" if p95_all == p95_all else "—",
              border=True)
    c8.metric("Inférence P95", f"{p95_inf:.0f} ms" if p95_inf == p95_inf else "—",
              border=True)
    c9.metric("Inférences", f"{len(inf)}", border=True)
    files_ = int((frame["route"] == "/summarize-file").sum())
    c10.metric("Fichiers", f"{files_}", border=True)
def render_usage(records: list[dict]) -> None:
    """Répartition de l'usage : volumes par modèle, par endpoint et taux de succès."""
    st.markdown("### :material/pie_chart: Répartition de l'usage")
    frame = _load_frame(records)
    if frame.empty:
        st.caption("Aucune donnée.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Par modèle**")
        st.bar_chart(frame["model"].value_counts().rename("Requêtes"))
    with col_b:
        st.markdown("**Par endpoint**")
        st.bar_chart(frame["path"].value_counts().rename("Requêtes"))

    st.markdown("**Détail par endpoint**")
    rows = []
    for route, grp in frame.groupby("route"):
        q = _quantiles(grp["duration_ms"])
        rows.append({
            "Endpoint": _path_label(route),
            "Requêtes": q["count"],
            "Succès": _fmt_pct(grp["ok"].mean() * 100),
            "Moy (ms)": q["mean"],
            "P95 (ms)": q["p95"],
            "Max (ms)": q["max"],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    inf = frame[frame["route"].isin(["/summarize", "/compare", "/summarize-file"])]
    if not inf.empty:
        st.markdown("**Statistiques de latence (totale) par modèle**")
        rows = []
        for model, grp in inf.groupby("model"):
            q = _quantiles(grp["duration_ms"])
            rows.append({
                "Modèle": model,
                "N": q["count"],
                "Moy": q["mean"],
                "Écart-type": q["std"],
                "Min": q["min"],
                "P50": q["p50"],
                "P90": q["p90"],
                "P95": q["p95"],
                "P99": q["p99"],
                "Max": q["max"],
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)


def render_distributions(records: list[dict]) -> None:
    """Histogrammes : distribution des latences et des tailles d'entrée/sortie."""
    st.markdown("### :material/bar_chart: Distributions")
    frame = _load_frame(records)
    if frame.empty:
        st.caption("Aucune donnée.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        dur = frame["duration_ms"].dropna()
        if not dur.empty:
            st.markdown("**Distribution des latences (totales)**")
            bins = pd.cut(dur, 10).value_counts().sort_index()
            st.bar_chart(pd.Series(bins.values, index=bins.index.astype(str), name="N"))
    with col_b:
        inf = frame[frame["route"].isin(["/summarize"])]["inference_ms"].dropna()
        if not inf.empty:
            st.markdown("**Distribution inférence (Résumer)**")
            bins = pd.cut(inf, 10).value_counts().sort_index()
            st.bar_chart(pd.Series(bins.values, index=bins.index.astype(str), name="N"))

    sizes = frame[frame["in_chars"].notna()]
    if not sizes.empty:
        sc = st.columns(2)
        with sc[0]:
            st.markdown("**Taille d'entrée (chars)**")
            h = pd.cut(sizes["in_chars"], 10).value_counts().sort_index()
            st.bar_chart(pd.Series(h.values, index=h.index.astype(str), name="N"))
        with sc[1]:
            out = sizes["out_chars"].dropna()
            if not out.empty:
                st.markdown("**Taille de sortie (chars)**")
                h = pd.cut(out, 10).value_counts().sort_index()
                st.bar_chart(pd.Series(h.values, index=h.index.astype(str), name="N"))


def render_trends(records: list[dict]) -> None:
    """Tendances : moyenne mobile de latence, volume et succès par tranche de temps."""
    st.markdown("### :material/trending_up: Tendances")
    frame = _load_frame(records).sort_values("timestamp")
    if frame.empty:
        st.caption("Aucune donnée.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Latence moyenne mobile (30 req)**")
        mov = frame["duration_ms"].rolling(30, min_periods=1).mean()
        df = pd.DataFrame({"Latence (ms)": mov.values}, index=frame["timestamp"])
        st.line_chart(df)
    with col_b:
        st.markdown("**Volume par tranche (10 min)**")
        vol = frame.set_index("timestamp").resample("10min").size()
        st.bar_chart(vol.rename("Requêtes"))

    st.markdown("**Taux de succès par tranche (30 min)**")
    ok = frame.set_index("timestamp").resample("30min")["ok"].mean().fillna(0)
    st.bar_chart((ok * 100).rename("Succès (%)"))
def render_model_perf(records: list[dict]) -> None:
    """Tableau des performances (latence) par modèle, pour les endpoint d'inférence."""
    st.markdown("### :material/query_stats: Performances par modèle")
    frame = _load_frame(records)
    eff = ["/summarize", "/compare", "/summarize-file"]
    if frame.empty or not frame["route"].isin(eff).any():
        st.caption("Aucune donnée — effectuez quelques inférences (Résumer / Comparer) "
                   "pour peupler ce tableau.")
        return

    inf = frame[frame["route"].isin(eff)].copy()
    rows = []
    for (model, route), grp in inf.groupby(["model", "route"]):
        dur = grp["duration_ms"].dropna()
        inf_ms = grp["inference_ms"].dropna()
        p50, p95, mn = _percentiles(dur)
        rows.append({
            "Modèle": model,
            "Endpoint": _path_label(route),
            "N°": len(grp),
            "Moy. totale (ms)": round(dur.mean(), 0) if not dur.empty else None,
            "P50 (ms)": round(p50, 0) if p50 == p50 else None,
            "P95 (ms)": round(p95, 0) if p95 == p95 else None,
            "Min (ms)": round(mn, 0) if mn == mn else None,
            "Inférence moy. (ms)": round(inf_ms.mean(), 0) if not inf_ms.empty else None,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)


def render_charts(records: list[dict]) -> None:
    """Graphiques temporels et source entrée/sortie."""
    frame = _load_frame(records)
    if frame.empty:
        return

    st.markdown("### :material/ssid_chart: Latence au fil du temps")
    chart = frame.sort_values("timestamp").tail(200).set_index("timestamp")
    st.line_chart(chart[["duration_ms"]].rename(
        columns={"duration_ms": "Latence (ms)"}))

    inf = frame[frame["route"].isin(["/summarize", "/compare", "/summarize-file"])].copy()
    if not inf.empty and inf["in_chars"].notna().any():
        st.markdown("### :material/compare_arrows: Entrée vs sortie (inférence)")
        sc = inf.dropna(subset=["in_chars"]).copy()
        sc["Entrée (chars)"] = sc["in_chars"]
        sc["Sortie (chars)"] = sc["out_chars"].fillna(0)
        st.scatter_chart(sc, x="Entrée (chars)", y="Sortie (chars)", color="model")

    st.markdown("### :material/bar_chart: Latence moyenne par endpoint")
    avg = frame.groupby("path")["duration_ms"].mean().sort_values()
    if not avg.empty:
        st.bar_chart(avg)


def render_availability(records: list[dict]) -> None:
    """Disponibilité de l'API observée à travers les /health mesurés."""
    st.markdown("### :material/sensors: Disponibilité observée")
    frame = _load_frame(records)
    health = frame[frame["route"] == "/health"]
    if health.empty:
        st.caption("Aucune sonde /health mesurée pour l'instant.")
        return
    up = health["ok"].mean() * 100
    c1, c2, c3 = st.columns(3)
    c1.metric("Sondes", f"{len(health)}", border=True)
    c2.metric("Disponibilité", _fmt_pct(up), border=True,
              delta_color="normal" if up >= 90 else "inverse")
    c3.metric("Moy. latence /health", f"{health['duration_ms'].mean():.0f} ms",
              border=True)
    avail = health.set_index("timestamp").resample("10min")["ok"].mean().fillna(0)
    st.line_chart((avail * 100).rename("Dispo (%)"))
def render_errors(records: list[dict]) -> None:
    """Tableau des erreurs : volume, endpoints concernés et derniers messages."""
    st.markdown("### :material/error: Erreurs")
    frame = _load_frame(records)
    failed = frame[frame["ok"] == False]  # noqa: E712
    if failed.empty:
        st.success("Aucune erreur enregistrée. 🎉", icon=":material/verified:")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Échecs", f"{len(failed)}", border=True)
    c2.metric("HTTP (>=400)", f"{int(failed['status'].notna().sum())}", border=True)
    c3.metric("Injoignables", f"{int(failed['status'].isna().sum())}", border=True)

    st.markdown("**Derniers échecs**")
    recent = failed.sort_values("timestamp", ascending=False).head(20)
    rows = [{
        "Horodatage": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        "Endpoint": _path_label(r["route"]),
        "Modèle": r["model"],
        "Code": r["status"],
        "Erreur": (r["error"] or "")[:160],
    } for _, r in recent.iterrows()]
    st.dataframe(pd.DataFrame(rows), hide_index=True)


def render_engine(base: str) -> None:
    """Diagnostic du moteur backend via /health/detail (uptime, mémoire, config)."""
    st.markdown("### :material/monitor_heart: Santé du moteur")
    try:
        d = get_health_detail(base)
    except ApiError as exc:
        st.caption(f"Backend injoignable : {exc.message}")
        return

    srv = d.get("server") or {}
    gen = d.get("generation") or {}
    cks = d.get("checkpoints") or {}
    cols = st.columns(5)
    cols[0].metric("Uptime", _fmt_hms(d.get("uptime_s")), border=True)
    cols[1].metric("Python", srv.get("python", "—"), border=True)
    cols[2].metric("Mémoire RSS", f"{srv.get('memory_rss_mb', '—')} Mo", border=True)
    cols[3].metric("CPU", f"{srv.get('cpu_count', '—')} cœurs", border=True)
    cols[4].metric("Host", srv.get("host", "—"), border=True)

    st.markdown("**Configuration de génération**")
    g = st.columns(4)
    g[0].metric("max_source", gen.get("max_source_tokens", "—"), border=True)
    g[1].metric("max_target", gen.get("max_target_tokens", "—"), border=True)
    g[2].metric("Beams", gen.get("num_beams", "—"), border=True)
    g[3].metric("No-repeat n-gram", gen.get("no_repeat_ngram_size", "—"), border=True)

    with st.expander("Chemins des checkpoints", icon=":material/folder:"):
        st.write(cks)


def render_log(records: list[dict]) -> None:
    """Journal détaillé et filtrable des requêtes, avec aperçus des réponses."""
    st.markdown("### :material/receipt_long: Journal des requêtes")
    frame = _load_frame(records)
    if frame.empty:
        st.caption("Le journal est vide. Les requêtes y apparaissent dès que vous "
                   "utilisez l'application (Résumer / Comparer / Fichier).")
        return

    f1, f2, f3 = st.columns(3)
    path_sel = f1.multiselect("Endpoint", sorted(frame["path"].unique()), key="mon_path")
    status_sel = f2.multiselect("Code HTTP",
                                sorted(x for x in frame["status"].dropna().unique()),
                                key="mon_status")
    model_sel = f3.multiselect("Modèle", sorted(frame["model"].unique()), key="mon_model")

    df = frame
    if path_sel:
        df = df[df["path"].isin(path_sel)]
    if status_sel:
        df = df[df["status"].isin(status_sel)]
    if model_sel:
        df = df[df["model"].isin(model_sel)]
    df = df.sort_values("timestamp", ascending=False).head(200)

    table = df[[
        "timestamp", "method", "path", "model", "status",
        "duration_ms", "inference_ms", "in_chars", "out_chars", "error",
    ]].copy()
    table["timestamp"] = table["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    table.columns = [
        "Horodatage", "Méthode", "Endpoint", "Modèle", "Code",
        "Durée (ms)", "Inférence (ms)", "Entrée (chars)", "Sortie (chars)", "Erreur",
    ]
    st.dataframe(
        table,
        hide_index=True,
        column_config={"Erreur": st.column_config.TextColumn(width="medium")},
    )

    with st.expander("Détail des réponses (aperçus)", icon=":material/code:"):
        for _, r in df.head(50).iterrows():
            icon = ":green-badge[OK]" if r["ok"] else ":red-badge[ERREUR]"
            st.markdown(
                f"- **`{r['method']} {r['route']}`** {icon} "
                f"· {r['model']} · `{r['status']}` · {r['duration_ms']:.0f} ms"
            )
            if r["summary"]:
                st.caption(f"→ {r['summary'][:220]}")
            elif r["error"]:
                st.caption(f"→ :red[{r['error'][:220]}]")

    st.caption(f"{len(df)} enregistrement(s) affiché(s).")
# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.markdown("## :material/monitor_heart: Monitoring")
st.caption(
    "Tableau de bord de l'activité du projet : état du backend, latences, "
    "répartitions, tendances et historique détaillé de chaque requête."
)

col_a, col_b, col_c = st.columns([1, 1, 2])
if col_a.button("Rafraîchir", icon=":material/refresh:", type="primary",
                use_container_width=True):
    st.rerun()
if col_b.button("Vider l'historique", icon=":material/delete:",
                use_container_width=True):
    monitoring.clear()
    st.toast("Historique effacé.", icon=":material/check_circle:")
    st.rerun()
col_c.caption("Le journal est conservé sur disque (`.metrics/requests.json`) et "
              "survit aux rechargements.")

period = st.selectbox(
    "Période analysée",
    ["Toutes", "Dernière heure", "6 heures", "24 heures", "7 jours"],
    index=0,
    key="mon_period",
)
hours = {"Toutes": None, "Dernière heure": 1, "6 heures": 6,
         "24 heures": 24, "7 jours": 168}[period]

base = st.session_state.api_base
render_kpis(base)

records = _filter_period(monitoring.all_records(), hours)

render_extended_kpis(records)
render_usage(records)
render_distributions(records)
render_trends(records)
render_model_perf(records)
render_charts(records)
render_availability(records)
render_errors(records)
render_engine(base)

st.markdown("### :material/view_module: État détaillé des modèles")
try:
    models = cached_models(base)
    cols = st.columns(max(len(models), 1))
    for col, info in zip(cols, models):
        with col:
            with st.container(border=True):
                name = info.get("name", "?")
                st.markdown(f"**{MODEL_ICONS.get(name, '')} "
                            f"{MODEL_LABELS.get(name, name)}**")
                availability_badge(info.get("available", False),
                                   mode=(info.get("detail") or {}).get("mode"))
                detail = info.get("detail") or {}
                st.caption(f"Paramètres : {detail.get('parameters', '—')}")
except ApiError as exc:
    st.error(exc.message, icon=":material/error:")

render_log(records)

with st.expander("Données brutes (JSON)", icon=":material/data_object:"):
    raw = monitoring.all_records()
    st.download_button("Télécharger le JSON",
                       data=monitoring.dump(raw), mime="application/json",
                       file_name="monitoring.json")
    st.json(raw[-100:])