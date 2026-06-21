"""Pagina 3 -- Circadiaans ritme: uurlijkse stressbasislijn per deelnemer."""
import numpy as np
import plotly.graph_objects as go
from shiny import module, reactive, render, ui as _ui
from shinywidgets import output_widget, render_widget

from utils.chart_helpers import ACCENT, GRID_COLOR, PLAYLIST_COLORS, TEXT_SECONDARY, chart_layout, empty_figure
from utils.data_loader import PARTICIPANTS, AppData, expected_stress
from utils.mood_valence import mood_is_improvement


def _stress_color(normalized: float, alpha: float = 0.75) -> str:
    """Map 0.0 (calm) → 1.0 (peak stress) to a green→orange→red colour."""
    n = max(0.0, min(1.0, normalized))
    if n < 0.5:
        t = n * 2
        r = int(22  + (230 - 22)  * t)
        g = int(163 + (159 - 163) * t)
        b = int(74  + (0   - 74)  * t)
    else:
        t = (n - 0.5) * 2
        r = int(230 + (220 - 230) * t)
        g = int(159 + (38  - 159) * t)
        b = int(0   + (38  - 0)   * t)
    return f"rgba({r},{g},{b},{alpha})"


def _tod_label(h: int) -> str:
    if h < 6:  return "Nacht"
    if h < 9:  return "Vroege ochtend"
    if h < 12: return "Ochtend"
    if h < 14: return "Middag"
    if h < 18: return "Namiddag"
    if h < 21: return "Avond"
    return "Late avond"


def _build_stress_timeline(hb_df, sessions_df=None) -> go.Figure:
    """
    24-hour stress timeline: per-hour coloured bars (green→red) with ±1σ envelope,
    night/dawn/dusk shading with band labels, daily-mean reference line, and
    golden/peak annotations. Y-axis starts near the data minimum so the arc is
    visually apparent. Session dots float above bars with rich hover.
    """
    if hb_df is None or hb_df.empty:
        return empty_figure("Geen circadiane basislijn beschikbaar voor deze deelnemer")

    hours = hb_df["hour"].values
    mean  = hb_df["mean_stress"].values
    std   = hb_df["std_stress"].values

    # Derive golden / peak from waking hours for in-chart annotations
    waking      = hb_df[hb_df["hour"].between(6, 23)]
    if waking.empty:
        waking = hb_df
    golden_h    = int(waking.loc[waking["mean_stress"].idxmin(), "hour"])
    peak_h      = int(waking.loc[waking["mean_stress"].idxmax(), "hour"])
    golden_mean = float(waking.loc[waking["mean_stress"].idxmin(), "mean_stress"])
    peak_mean   = float(waking.loc[waking["mean_stress"].idxmax(), "mean_stress"])
    peak_std    = float(hb_df.loc[hb_df["hour"] == peak_h, "std_stress"].iloc[0])
    daily_mean  = float(mean.mean())

    mn, mx = float(mean.min()), float(mean.max())
    colour_rng = mx - mn if mx > mn else 1.0
    bar_colors = [_stress_color((float(s) - mn) / colour_rng, alpha=0.85) for s in mean]

    # Y-axis: start near the data minimum so the arc is visually legible
    y_min = max(0.0, mn - max(5.0, (mx - mn) * 0.5))
    y_max = mx + max(8.0, (mx - mn) * 0.8)   # room for annotations

    fig = go.Figure()

    # ── Time-of-day shading bands ────────────────────────────────────────────
    for x0, x1 in [(0, 6), (22, 24)]:
        fig.add_vrect(x0=x0 - 0.5, x1=x1 - 0.5,
                      fillcolor="rgba(30,41,59,0.12)", line_width=0, layer="below")
    fig.add_vrect(x0=5.5, x1=8.5,
                  fillcolor="rgba(251,191,36,0.08)", line_width=0, layer="below")
    fig.add_vrect(x0=17.5, x1=21.5,
                  fillcolor="rgba(124,58,237,0.07)", line_width=0, layer="below")

    # ── Band labels (inside shading, paper-relative y so they sit at the bottom) ──
    _band_labels = [
        (2.5,  "nacht",    "rgba(50,70,120,0.40)"),
        (7.0,  "ochtend",  "rgba(180,120,20,0.40)"),
        (13.0, "middag",   "rgba(100,100,100,0.28)"),
        (19.5, "avond",    "rgba(90,50,160,0.38)"),
        (23.0, "nacht",    "rgba(50,70,120,0.40)"),
    ]
    for bx, blabel, bcolor in _band_labels:
        fig.add_annotation(
            x=bx, y=0.04, yref="paper",
            text=blabel, showarrow=False,
            font=dict(size=9, color=bcolor, family="Figtree,sans-serif"),
            xanchor="center", yanchor="bottom",
        )

    # ── Daily mean reference line ────────────────────────────────────────────
    fig.add_hline(
        y=daily_mean,
        line_color="rgba(120,120,120,0.40)",
        line_dash="dash",
        line_width=1.5,
        annotation_text=f"daggemiddelde  {daily_mean:.0f} pt",
        annotation_position="top left",
        annotation_font_size=10,
        annotation_font_color="rgba(100,100,100,0.65)",
    )

    # ── Per-hour coloured bars with rich hover ───────────────────────────────
    vs_mean = mean - daily_mean
    bar_custom = list(zip(
        std,
        [_tod_label(h) for h in hours],
        vs_mean,
        mean - std,
        mean + std,
    ))
    fig.add_trace(go.Bar(
        x=hours,
        y=mean,
        marker_color=bar_colors,
        marker_line_width=0,
        width=0.85,
        name="Gem. stress per uur",
        customdata=bar_custom,
        hovertemplate=(
            "<b>%{x:02d}:00</b>  ·  %{customdata[1]}<br>"
            "Gem. stress: <b>%{y:.1f} pt</b><br>"
            "Normaal bereik: %{customdata[3]:.0f}–%{customdata[4]:.0f} pt  (±1σ)<br>"
            "vs. daggemiddelde: <b>%{customdata[2]:+.1f} pt</b>"
            "<extra></extra>"
        ),
        showlegend=False,
    ))

    # ── ±1σ envelope ────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=np.concatenate([hours, hours[::-1]]),
        y=np.concatenate([mean + std, (mean - std)[::-1]]),
        fill="toself",
        fillcolor="rgba(255,255,255,0.20)",
        line=dict(color="rgba(160,160,160,0.35)", width=1.2),
        showlegend=False,
        hoverinfo="skip",
    ))

    # ── Golden hour and peak stress annotations ──────────────────────────────
    # kalmst: if at edge hours (>20), offset label left so it stays in frame
    kalmst_ax = -52 if golden_h >= 20 else 0
    fig.add_annotation(
        x=golden_h, y=golden_mean,
        text="🟢 kalmst",
        showarrow=True, arrowhead=2, arrowcolor="#15803D",
        ax=kalmst_ax, ay=-32,
        font=dict(size=10, color="#15803D"),
        bgcolor="rgba(255,255,255,0.80)", borderpad=3,
        xanchor="right" if golden_h >= 20 else "center",
    )
    fig.add_annotation(
        x=peak_h, y=peak_mean,
        text="⚠ piek",
        showarrow=True, arrowhead=2, arrowcolor="#D4850A",
        ax=0, ay=-32,
        font=dict(size=10, color="#D4850A"),
        bgcolor="rgba(255,255,255,0.80)", borderpad=3,
        xanchor="center",
    )

    # ── Session overlay dots ─────────────────────────────────────────────────
    if sessions_df is not None and not sessions_df.empty and "hour_of_day" in sessions_df.columns:
        import pandas as pd
        _NL = {"Calm": "Kalm", "Neutral": "Neutraal", "Energy": "Energiek"}
        rng_jitter = np.random.default_rng(seed=42)
        for playlist, color in PLAYLIST_COLORS.items():
            mask = sessions_df["playlist"].str.strip().str.capitalize() == playlist
            sub  = sessions_df[mask]
            if sub.empty:
                continue
            jitter = rng_jitter.uniform(-0.20, 0.20, len(sub))
            nl = _NL.get(playlist, playlist)
            delta_col = pd.to_numeric(
                sub.get("mood_delta", pd.Series(dtype=float)), errors="coerce"
            ) if "mood_delta" in sub.columns else pd.Series([float("nan")] * len(sub), index=sub.index)
            delta_strs = [
                f"+{d:.1f} pt" if d >= 0 else f"{d:.1f} pt" if not pd.isna(d) else "—"
                for d in delta_col
            ]
            mood_labels = sub["mood_before"].fillna("—").astype(str).tolist() if "mood_before" in sub.columns else ["—"] * len(sub)
            fig.add_trace(go.Scatter(
                x=sub["hour_of_day"].values + jitter,
                y=sub["pre_stress_mean"],
                mode="markers",
                marker=dict(color=color, size=9, line=dict(color="white", width=1.5)),
                name=f"{nl}-sessie",
                customdata=list(zip(
                    sub["hour_of_day"].values,
                    sub["date"].astype(str).str[:10] if "date" in sub.columns else ["—"] * len(sub),
                    delta_strs,
                    mood_labels,
                )),
                hovertemplate=(
                    f"<b>{nl}-sessie</b><br>"
                    "Datum: %{customdata[1]}<br>"
                    "%{customdata[0]:.0f}:00 · Pre-stress: %{y:.1f} pt<br>"
                    "Stemming voor: %{customdata[3]}<br>"
                    "Stemmingsdelta: %{customdata[2]}"
                    "<extra></extra>"
                ),
                showlegend=True,
            ))

    fig.update_layout(**chart_layout(
        xaxis=dict(
            tickvals=list(range(0, 24, 3)),
            ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)],
            range=[-0.5, 23.5],
            gridcolor=GRID_COLOR,
        ),
        yaxis=dict(title="Stress", gridcolor=GRID_COLOR, range=[y_min, y_max]),
        height=290,
        bargap=0.05,
        legend=dict(orientation="h", y=-0.26, font_size=11),
        margin=dict(t=68, b=40, l=44, r=16),
    ))

    return fig


def _build_circadian_chart(hb_df, session_df) -> go.Figure:
    if hb_df is None or hb_df.empty:
        return empty_figure("Geen circadiane basislijn beschikbaar voor deze deelnemer")

    hours = hb_df["hour"].values
    mean  = hb_df["mean_stress"].values
    std   = hb_df["std_stress"].values

    fig = go.Figure()

    # +-1 sigma-band
    fig.add_trace(go.Scatter(
        x=np.concatenate([hours, hours[::-1]]),
        y=np.concatenate([mean + std, (mean - std)[::-1]]),
        fill="toself",
        fillcolor="rgba(34,197,94,0.10)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Gemiddelde lijn
    fig.add_trace(go.Scatter(
        x=hours, y=mean,
        mode="lines",
        line=dict(color=ACCENT, width=2),
        name="Jouw gemiddelde stress",
        hovertemplate="Uur %{x}:00 — Gem. stress: %{y:.1f}<extra></extra>",
    ))

    # Sessie-overlay
    if session_df is not None and not session_df.empty and "hour_of_day" in session_df.columns:
        import pandas as pd
        _NL = {"Calm": "Kalm", "Neutral": "Neutraal", "Energy": "Energiek"}
        for playlist, color in PLAYLIST_COLORS.items():
            mask = session_df["playlist"].str.strip().str.capitalize() == playlist
            sub  = session_df[mask]
            if sub.empty:
                continue
            rng    = np.random.default_rng(seed=42)
            jitter = rng.uniform(-0.25, 0.25, len(sub))

            date_col   = sub["date"].astype(str).str[:10] if "date" in sub.columns else pd.Series(["—"] * len(sub), index=sub.index)
            delta_col  = pd.to_numeric(sub.get("mood_delta", pd.Series(dtype=float)), errors="coerce") if "mood_delta" in sub.columns else pd.Series([float("nan")] * len(sub), index=sub.index)
            delta_strs = [f"+{d:.1f} pt" if d >= 0 else f"{d:.1f} pt" if not pd.isna(d) else "—" for d in delta_col]

            mood_labels = sub["mood_before"].fillna("—").astype(str).tolist() if "mood_before" in sub.columns else ["—"] * len(sub)

            if "post_stress_mean" in sub.columns:
                post_stress_vals = pd.to_numeric(sub["post_stress_mean"], errors="coerce")
                post_stress_strs = [f"{v:.1f}" if not pd.isna(v) else "—" for v in post_stress_vals]
            else:
                post_stress_strs = ["—"] * len(sub)

            customdata = list(zip(
                sub["hour_of_day"].values,
                date_col.values,
                delta_strs,
                mood_labels,
                post_stress_strs,
            ))

            nl = _NL.get(playlist, playlist)
            fig.add_trace(go.Scatter(
                x=sub["hour_of_day"].values + jitter,
                y=sub["pre_stress_mean"],
                mode="markers",
                marker=dict(color=color, size=10, line=dict(color="white", width=1.5)),
                name=f"{nl}-sessie",
                hovertemplate=(
                    f"<b>{nl}-sessie</b><br>"
                    "Datum: %{customdata[1]}<br>"
                    "Uur: %{customdata[0]}:00<br>"
                    "Stemming voor: %{customdata[3]}<br>"
                    "Pre-stress: %{y:.1f}<br>"
                    "Post-stress: %{customdata[4]}<br>"
                    "Stemmingsdelta: %{customdata[2]}<br>"
                    "<i>Klik voor meer details</i><extra></extra>"
                ),
                customdata=customdata,
            ))

    fig.update_layout(**chart_layout(
        xaxis=dict(
            title="Uur van de dag",
            tickvals=list(range(0, 24, 3)),
            ticktext=[f"{h}:00" for h in range(0, 24, 3)],
            range=[-0.5, 23.5],
            gridcolor=GRID_COLOR,
        ),
        yaxis=dict(title="Stress (0-100)", gridcolor=GRID_COLOR),
        height=360,
        legend=dict(orientation="h", y=-0.22),
    ))
    return fig


def _compute_stats(hb_df, session_df):
    if hb_df is None or hb_df.empty:
        return "—", "—", "—", None, None
    waking = hb_df[hb_df["hour"].between(6, 23)]
    if waking.empty:
        waking = hb_df
    calmest_row  = waking.loc[waking["mean_stress"].idxmin()]
    calmest      = f"{int(calmest_row['hour'])}:00"
    golden_stress = float(calmest_row["mean_stress"])
    stressed_row  = waking.loc[waking["mean_stress"].idxmax()]
    peak_h        = int(stressed_row["hour"])
    peak          = f"{peak_h}-{peak_h + 2}:00"
    peak_stress   = float(stressed_row["mean_stress"])
    dev_str       = "—"
    if session_df is not None and not session_df.empty and "baseline_deviation_entry" in session_df.columns:
        import pandas as pd
        dev = pd.to_numeric(session_df["baseline_deviation_entry"], errors="coerce").mean()
        if not pd.isna(dev):
            dev_str = f"+{dev:.1f} pt" if dev >= 0 else f"{dev:.1f} pt"
    return calmest, peak, dev_str, golden_stress, peak_stress


# ---------------------------------------------------------------------------
# Module UI
# ---------------------------------------------------------------------------

@module.ui
def ui():
    return _ui.div(
        # 1.1 Hero: full viewport height so chart is below the fold
        _ui.div(
            _ui.div("Jouw Circadiaans Ritme", class_="mt-h1"),
            _ui.p(
                "Hoe verhoudt jouw stressniveau zich tot jouw eigen basislijn op elk uur van de dag?",
                class_="mt-body mt-secondary",
                style="margin-top:8px; margin-bottom:24px; max-width:560px; margin-left:auto; margin-right:auto;",
            ),
            _ui.div(
                _ui.div("Wat is dit?", class_="mt-caption", style="font-weight:600; margin-bottom:6px;"),
                _ui.p(
                    "We vergelijken jouw sessie-stress met JOUW typische stress op datzelfde uur "
                    "op niet-sessiedagen. Dit corrigeert voor je natuurlijke dagritme.",
                    class_="mt-caption mt-secondary",
                    style="margin-bottom:4px;",
                ),
                _ui.span(
                    "afwijking = pre_stress − verwacht_stress_op_dat_uur",
                    style=(
                        "font-family:'JetBrains Mono','Roboto Mono',monospace; "
                        "font-size:0.8rem; color:var(--text-tertiary); font-style:italic;"
                    ),
                ),
                style=(
                    "background:var(--bg-elevated); "
                    "padding:12px 16px; border-radius:6px; max-width:600px; margin:0 auto;"
                ),
            ),
            # Scroll indicator
            _ui.div(
                "↓ jouw persoonlijk stressritme",
                style=(
                    "padding-top:72px; padding-bottom:20px; "
                    "color:var(--text-tertiary); font-size:0.8125rem; letter-spacing:0.07em;"
                ),
            ),
            style=(
                "text-align:center; padding:32px var(--page-margin) 0; "
                "display:flex; flex-direction:column; align-items:center;"
            ),
        ),

        # Hoofdgrafiek
        _ui.div(
            _ui.div(
                _ui.div(
                    _ui.output_text("chart_title"),
                    class_="mt-h3",
                    style="margin-bottom:4px;",
                ),
                _ui.div(
                    "Groen band = ±1σ normaalvariatie op niet-sessiedagen. Gekleurde stippen = sessies.",
                    class_="mt-caption mt-secondary",
                    style="margin-bottom:4px;",
                ),
                _ui.div(
                    "Klik op een sessie-punt voor sessiedetails ↓",
                    class_="mt-caption",
                    style="color:var(--accent); margin-bottom:16px; font-style:italic;",
                ),
                output_widget("circadian_chart"),
                _ui.output_ui("dot_detail_panel"),
                class_="mt-section-card",
                style="padding:32px 48px;",
            ),
            style="padding:0 var(--page-margin);",
        ),

        # 24-uur tijdlijn + statistieken
        _ui.div(
            _ui.output_ui("clock_hero_ui"),
            style="padding:24px var(--page-margin) 8px;",
        ),

        # Afwijkingscalculator
        _ui.output_ui("deviation_calculator_ui"),
    )


# ---------------------------------------------------------------------------
# Module server
# ---------------------------------------------------------------------------

@module.server
def server(input, output, session, app_data: AppData, selected_participant=None):
    selected     = selected_participant if selected_participant is not None else reactive.Value("bosbes")
    selected_dot: reactive.Value[dict | None] = reactive.Value(None)

    @reactive.Calc
    def current_data():
        import pandas as pd
        p  = selected()
        hb = app_data.hourly_baselines.get(p)
        fm = app_data.feature_matrix
        sf = pd.DataFrame()
        if fm is not None and not fm.empty and "participant" in fm.columns:
            sf = fm[fm["participant"] == p].copy()
        if sf.empty:
            sf_raw = app_data.session_features.get(p)
            sf = sf_raw.copy() if sf_raw is not None and not sf_raw.empty else pd.DataFrame()
        sb = app_data.session_biometrics.get(p, pd.DataFrame())
        if not sf.empty and not sb.empty and "date" in sf.columns and "date" in sb.columns:
            extra_cols = [c for c in ("mood_before", "mood_after", "post_stress_mean") if c in sb.columns]
            if extra_cols:
                sf = sf.merge(
                    sb[["date"] + extra_cols].drop_duplicates("date"),
                    on="date", how="left", suffixes=("", "_sb"),
                )
        return hb, sf

    @reactive.Effect
    def _clear_dot_on_participant_change():
        selected()
        selected_dot.set(None)

    @reactive.Effect
    @reactive.event(input.circadian_clear_dot)
    def _on_clear_dot():
        selected_dot.set(None)

    @output
    @render.text
    def chart_title():
        return f"Uurlijkse stressbasislijn — {selected().capitalize()}"

    @output
    @render_widget
    def circadian_chart():
        hb, sf = current_data()
        if hb is None or (hasattr(hb, "empty") and hb.empty):
            return empty_figure(f"Geen data beschikbaar voor {selected()}")
        fw = go.FigureWidget(_build_circadian_chart(hb, sf))

        def _on_click(trace, points, selector):
            if not points.point_inds:
                return
            idx = points.point_inds[0]
            cd  = trace.customdata[idx]
            dot = {
                "date":        str(cd[1]),
                "hour":        int(float(cd[0])),
                "delta":       str(cd[2]),
                "mood_before": str(cd[3]) if len(cd) > 3 else "—",
                "post_stress": str(cd[4]) if len(cd) > 4 else "—",
                "playlist":    trace.name,
                "pre_stress":  float(trace.y[idx]),
            }
            if selected_dot() == dot:
                selected_dot.set(None)
            else:
                selected_dot.set(dot)

        for trace in fw.data:
            if hasattr(trace, "on_click"):
                trace.on_click(_on_click)
        return fw

    @output
    @render_widget
    def stress_timeline():
        hb, sf = current_data()
        if hb is None or (hasattr(hb, "empty") and hb.empty):
            return empty_figure(f"Geen data beschikbaar voor {selected()}")
        return _build_stress_timeline(hb, sf if not sf.empty else None)

    @output
    @render.ui
    def clock_hero_ui():
        import pandas as pd
        hb, sf = current_data()
        if hb is None or (hasattr(hb, "empty") and hb.empty):
            return _ui.div()
        waking = hb[hb["hour"].between(6, 23)]
        if waking.empty:
            waking = hb

        golden_h      = int(waking.loc[waking["mean_stress"].idxmin(), "hour"])
        peak_h        = int(waking.loc[waking["mean_stress"].idxmax(), "hour"])
        golden_stress = float(waking.loc[waking["mean_stress"].idxmin(), "mean_stress"])
        peak_stress   = float(waking.loc[waking["mean_stress"].idxmax(), "mean_stress"])

        dev_val = None
        dev_str = "—"
        if not sf.empty and "baseline_deviation_entry" in sf.columns:
            dev = pd.to_numeric(sf["baseline_deviation_entry"], errors="coerce").mean()
            if not pd.isna(dev):
                dev_val = dev
                dev_str = f"+{dev:.1f} pt" if dev >= 0 else f"{dev:.1f} pt"

        dev_color = "#22c55e" if (dev_val is not None and dev_val < -2) else \
                    "#ef4444" if (dev_val is not None and dev_val > 2) else "var(--text-primary)"

        diff = peak_stress - golden_stress
        def _hour_period(h: int) -> str:
            if h < 6:  return "'s nachts"
            if h < 12: return "'s ochtends"
            if h < 18: return "'s middags"
            return "'s avonds"
        insight = (
            f"Jouw stress is het laagst om {golden_h:02d}:00 ({golden_stress:.0f} pt, "
            f"{_hour_period(golden_h)}) en piekt rond {peak_h:02d}:00 ({peak_stress:.0f} pt, "
            f"{_hour_period(peak_h)}). Dat verschil van {diff:.0f} pt is jouw dagritme."
        )

        # Below-chart row: title+insight (flex:2) + KPI blocks (flex:1 each)
        def _kpi(dot_color, label, time_str, stress_val):
            return _ui.div(
                _ui.div(
                    _ui.HTML(
                        f'<span style="display:inline-block;width:7px;height:7px;'
                        f'border-radius:50%;background:{dot_color};margin-right:5px;'
                        f'vertical-align:middle;"></span>'
                    ),
                    _ui.span(label, style="font-size:0.65rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-tertiary);"),
                    style="display:flex; align-items:center; margin-bottom:4px;",
                ),
                _ui.div(time_str, style="font-size:1.25rem; font-weight:700; font-family:'Figtree',sans-serif; line-height:1.1; margin-bottom:2px;"),
                _ui.div(f"{stress_val:.0f} gem. pt", style="font-size:0.8rem; color:var(--text-secondary);"),
                style=(
                    f"flex:1; min-width:120px; padding:12px 14px; "
                    f"border-radius:calc(var(--radius-card) - 4px); "
                    f"background:var(--bg-elevated); border-left:3px solid {dot_color};"
                ),
            )

        below_row = _ui.div(
            # Title + insight text
            _ui.div(
                _ui.div("Jouw 24-uurs stressritme", class_="mt-h2", style="margin-bottom:6px;"),
                _ui.p(insight, style="font-size:0.8125rem; color:var(--text-tertiary); line-height:1.6; margin:0;"),
                style="flex:2; min-width:200px;",
            ),
            _kpi("#15803D", "Gouden uur", f"{golden_h:02d}:00", golden_stress),
            _kpi("#D4850A", "Piekstress", f"{peak_h:02d}–{peak_h+2:02d}:00", peak_stress),
            _ui.div(
                _ui.div(
                    _ui.span("Pre-sessie afwijking", style="font-size:0.65rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-tertiary);"),
                    style="margin-bottom:4px;",
                ),
                _ui.div(dev_str, style=f"font-size:1.25rem; font-weight:700; font-family:'Figtree',sans-serif; color:{dev_color}; line-height:1.1;"),
                _ui.div("gem. afwijking bij sessies", style="font-size:0.8rem; color:var(--text-secondary);"),
                style=(
                    "flex:1; min-width:120px; padding:12px 14px; "
                    "border-radius:calc(var(--radius-card) - 4px); "
                    "background:var(--bg-elevated); border-left:3px solid var(--border-strong);"
                ),
            ),
            style="display:flex; gap:16px; align-items:flex-start; flex-wrap:wrap; margin-top:20px;",
        )

        return _ui.div(
            output_widget("stress_timeline"),
            below_row,
            class_="mt-section-card",
            style="padding:28px 40px;",
        )

    @output
    @render.ui
    def dot_detail_panel():
        import pandas as pd
        dot = selected_dot()
        if dot is None:
            return _ui.div()

        p        = selected()
        hb, sf   = current_data()
        sb       = app_data.session_biometrics.get(p)
        date_str = dot["date"][:10]

        if sb is not None and not sb.empty and "date" in sb.columns:
            mask = sb["date"].astype(str).str[:10] == date_str
            rows = sb[mask]
        else:
            rows = None

        def _safe(row, col):
            v = row.get(col) if hasattr(row, "get") else getattr(row, col, None)
            if v is None:
                return "—"
            try:
                f = float(v)
                return "—" if pd.isna(f) else f"{f:.1f}"
            except (TypeError, ValueError):
                return str(v)

        playlist_nl = dot["playlist"].replace("-sessie", "")
        delta_str   = dot["delta"]
        delta_val   = None
        try:
            raw = delta_str.replace(" pt", "").replace("+", "")
            delta_val = float(raw)
        except ValueError:
            pass

        if rows is not None and not rows.empty:
            row             = rows.iloc[0]
            mood_voor       = _safe(row, "mood_before_score")
            mood_na         = _safe(row, "mood_after_score")
            mood_label_voor = str(row.get("mood_before", "—")) if hasattr(row, "get") else "—"
            mood_label_na   = str(row.get("mood_after",  "—")) if hasattr(row, "get") else "—"
            pre_stress      = _safe(row, "pre_stress_mean")
            post_stress     = _safe(row, "post_stress_mean")
            improved = mood_is_improvement(
                mood_label_voor, row.get("mood_before_score"),
                mood_label_na,   row.get("mood_after_score"),
            )
            delta_color = (
                "#22c55e" if improved is True
                else "#ef4444" if improved is False
                else "var(--text-tertiary)"
            )
        else:
            mood_voor       = "—"
            mood_na         = "—"
            mood_label_voor = dot.get("mood_before", "—")
            mood_label_na   = "—"
            pre_stress      = f"{dot['pre_stress']:.1f}"
            post_stress     = dot.get("post_stress", "—")
            delta_color = (
                "#22c55e" if delta_val is not None and delta_val > 0
                else "#ef4444" if delta_val is not None and delta_val < 0
                else "var(--text-tertiary)"
            )

        hour           = dot.get("hour", 17)
        pre_stress_val = dot.get("pre_stress")
        deviation_str  = "—"
        dev_color      = "var(--text-tertiary)"
        if pre_stress_val is not None:
            exp_val, _ = expected_stress(app_data, p, hour)
            if exp_val is not None:
                dev        = pre_stress_val - exp_val
                sign       = "+" if dev >= 0 else ""
                deviation_str = f"{sign}{dev:.1f} pt"
                dev_color  = "#ef4444" if dev > 5 else ("#22c55e" if dev < -5 else "var(--text-tertiary)")

        comparison_str = "—"
        pl_key = playlist_nl.strip()
        if not sf.empty and "playlist" in sf.columns and "pre_stress_mean" in sf.columns:
            pl_mask = sf["playlist"].str.strip().str.capitalize() == pl_key.capitalize()
            pl_mean = pd.to_numeric(sf.loc[pl_mask, "pre_stress_mean"], errors="coerce").mean()
            if not pd.isna(pl_mean) and pre_stress_val is not None:
                diff = pre_stress_val - pl_mean
                sign = "+" if diff >= 0 else ""
                comparison_str = f"{sign}{diff:.1f} pt vs. gem. {pl_key}-sessie"

        def _detail_col(label, value, sub="", value_style=""):
            return _ui.div(
                _ui.div(label, class_="mt-caption mt-secondary"),
                _ui.div(value, class_="mt-body",
                        style=value_style if value_style else ""),
                _ui.div(sub, class_="mt-caption mt-tertiary", style="color:var(--text-tertiary); margin-top:2px;") if sub else _ui.div(),
                style="flex:1; min-width:100px;",
            )

        return _ui.div(
            _ui.div(
                _ui.div(
                    _ui.div(f"Sessie {date_str}", class_="mt-h3"),
                    _ui.input_action_button(
                        "circadian_clear_dot", "×",
                        style=(
                            "background:none; border:none; "
                            "color:var(--text-tertiary); font-size:20px; "
                            "cursor:pointer; line-height:1; padding:0;"
                        ),
                    ),
                    style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;",
                ),
                _ui.div(
                    _detail_col("Afspeellijst", playlist_nl),
                    _detail_col("Pre-stress", pre_stress, "Garmin voor sessie"),
                    _detail_col("Post-stress", post_stress, "Garmin na sessie"),
                    _detail_col("Circad. afwijking", deviation_str, f"op {hour:02d}:00 vs. basislijn", value_style=f"color:{dev_color}; font-weight:600;"),
                    _detail_col("vs. gemiddelde", comparison_str),
                    _detail_col("Stemming voor", f"{mood_label_voor} ({mood_voor})", "label (score/10)"),
                    _detail_col("Stemming na",   f"{mood_label_na} ({mood_na})",   "label (score/10)"),
                    _detail_col("Stemmingsdelta", delta_str if delta_str else "—", value_style=f"color:{delta_color}; font-weight:600;"),
                    style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:12px;",
                ),
                _ui.div(
                    "→ Ga naar Sessie-replay voor de volledige minuut-grafiek",
                    style=(
                        "font-size:0.8125rem; color:var(--accent); cursor:pointer; "
                        "text-decoration:underline; text-underline-offset:3px;"
                    ),
                    onclick="mtNavTo('profiel','Sessie-replay')",
                ),
                class_="mt-callout",
                style="margin-top:16px;",
            ),
        )

    @output
    @render.ui
    def deviation_calculator_ui():
        p = selected()
        if not app_data.has_circadian.get(p, False):
            return _ui.div()
        return _ui.div(
            _ui.div(
                _ui.div(
                    # Left — inputs
                    _ui.div(
                        _ui.div("Is mijn stress normaal voor dit uur?", class_="mt-h3",
                                style="margin-bottom:10px;"),
                        _ui.p(
                            "Vul je huidige stressniveau in en het uur van de dag — "
                            "dan zie je direct hoe dit zich verhoudt tot jouw typische stress op dat moment.",
                            class_="mt-body mt-secondary",
                            style="margin-bottom:20px;",
                        ),
                        _ui.div(
                            _ui.input_select(
                                "dev_hour", "Huidig uur",
                                choices={str(h): f"{h:02d}:00" for h in range(6, 24)},
                                selected="17",
                                width="160px",
                            ),
                            style="margin-bottom:16px;",
                        ),
                        _ui.div(
                            _ui.input_numeric(
                                "dev_stress", "Mijn stressniveau (0–100)",
                                value=55, min=0, max=100, step=1,
                                width="160px",
                            ),
                        ),
                        style="flex:1;",
                    ),
                    # Right — live result
                    _ui.div(
                        _ui.output_ui("dev_result"),
                        style="flex:1; min-width:220px;",
                    ),
                    style="display:flex; gap:48px; align-items:flex-start; flex-wrap:wrap;",
                ),
                class_="mt-section-card",
            ),
            style="padding:0 var(--page-margin) 32px;",
        )

    @output
    @render.ui
    def dev_result():
        p      = selected()
        try:
            hour   = int(input.dev_hour())
        except (TypeError, ValueError):
            hour = 17
        try:
            stress = float(input.dev_stress())
        except (TypeError, ValueError):
            return _ui.div()

        exp, std = expected_stress(app_data, p, hour)
        if exp is None:
            return _ui.div(
                f"Geen basislijn beschikbaar voor {p.capitalize()} op {hour:02d}:00.",
                class_="mt-caption mt-secondary",
            )

        dev   = stress - exp
        sign  = "+" if dev >= 0 else ""
        color = "#ef4444" if dev > 5 else ("#22c55e" if dev < -5 else "var(--text-tertiary)")

        if dev > 5:
            meaning = f"Je bent {dev:.1f} pt méér gespannen dan normaal op {hour:02d}:00. Een kalme afspeellijst kan helpen."
        elif dev < -5:
            meaning = f"Je bent {abs(dev):.1f} pt mínder gespannen dan normaal op {hour:02d}:00 — geen reden voor interventie."
        else:
            meaning = f"Je zit binnen ±5 pt van jouw normaal op {hour:02d}:00 — geen opvallende afwijking."

        return _ui.div(
            _ui.div(
                _ui.div("Verwachte stress op dit uur", class_="mt-caption mt-secondary",
                        style="margin-bottom:4px;"),
                _ui.div(
                    f"{exp:.1f}",
                    style=(
                        "font-family:'Sora',sans-serif; font-weight:700; font-size:2rem; "
                        "color:var(--text-primary); line-height:1;"
                    ),
                ),
                _ui.div(f"±{std:.1f} sigma — jouw normaal op {hour:02d}:00",
                        class_="mt-caption mt-tertiary", style="margin-top:4px;"),
                style="margin-bottom:20px;",
            ),
            _ui.div(
                _ui.div("Jouw afwijking", class_="mt-caption mt-secondary",
                        style="margin-bottom:4px;"),
                _ui.div(
                    f"{sign}{dev:.1f} pt",
                    style=f"font-family:'Sora',sans-serif; font-weight:700; font-size:2rem; color:{color}; line-height:1;",
                ),
                style="margin-bottom:16px;",
            ),
            _ui.div(meaning, class_="mt-body mt-secondary", style="margin-bottom:12px;"),
            _ui.div(
                f"afwijking = {stress:.0f} (huidig) − {exp:.1f} (verwacht op {hour:02d}:00) = {sign}{dev:.1f}",
                style=(
                    "font-family:'JetBrains Mono','Roboto Mono',monospace; "
                    "font-size:0.8rem; color:var(--text-tertiary); font-style:italic; margin-top:4px;"
                ),
            ),
        )
