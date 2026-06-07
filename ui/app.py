"""MoodTune — Shiny for Python entrypoint."""
from pathlib import Path

from shiny import App, reactive, render, ui

from modules import circadian, home, model, music_browser, pipeline, recommendation, recovery, results, science, session_replay
from utils.data_loader import APP_DATA, PARTICIPANTS

_DATA_LEVEL = {
    "bosbes":      ("vol",          "Volledige biometrische data"),
    "kokosnoot":   ("vol",          "Volledige biometrische data"),
    "limoen":      ("gedeeltelijk", "Gedeeltelijke data (geen stresssensor)"),
    "peer":        ("gedeeltelijk", "Gedeeltelijke data (geen biometrie)"),
    "kiwi":        ("geen",         "Alleen stemming-check-ins"),
    "watermeloen": ("geen",         "Alleen stemming-check-ins"),
}

_FRUIT_EMOJI = {
    "bosbes":      "🫐",
    "kokosnoot":   "🥥",
    "limoen":      "🍋",
    "peer":        "🍐",
    "kiwi":        "🥝",
    "watermeloen": "🍉",
}

_DOT_COLOR = {
    "vol":          "#16a34a",   # green — full data
    "gedeeltelijk": "#f59e0b",   # amber — partial
    "geen":         "#d1d5db",   # muted — check-ins only
}

app_ui = ui.page_navbar(
    ui.nav_panel("Home", home.ui("home")),
    ui.nav_panel("Jouw Profiel",
        ui.navset_pill(
            ui.nav_panel("Resultaten",        results.ui("results")),
            ui.nav_panel("Sessie-replay",     session_replay.ui("replay")),
            ui.nav_panel("Circadiaans ritme", circadian.ui("circadian")),
            ui.nav_panel("Herstelanalyse",    recovery.ui("recovery")),
            ui.nav_panel("Jouw Muziek",       music_browser.ui("music")),
        ),
    ),
    ui.nav_panel("Aanbevelingen", recommendation.ui("rec")),
    ui.nav_panel("Achtergrond",
        ui.navset_pill(
            ui.nav_panel("Wetenschap",   science.ui("science")),
            ui.nav_panel("Model & Data", model.ui("model")),
            ui.nav_panel("Pipeline",     pipeline.ui("pipeline")),
        ),
    ),
    title="MoodTune",
    header=ui.div(
        ui.tags.head(
            ui.tags.link(rel="icon", type="image/svg+xml", href="favicon.svg"),
            ui.tags.link(rel="stylesheet", href="styles.css"),
            ui.busy_indicators.use(spinners=True, pulse=True),
        ),
        ui.output_ui("global_participant_bar"),
    ),
    footer=ui.div(
        ui.div(
            ui.output_ui("now_playing_title"),
            ui.div(),
            ui.div(),
            class_="now-playing-bar",
        ),
    ),
)


def server(input, output, session):
    selected_participant = reactive.Value("bosbes")
    now_playing          = reactive.Value(None)

    for _p in PARTICIPANTS:
        def _make_obs(participant=_p):
            @reactive.Effect
            @reactive.event(input[f"g_pill_{participant}"])
            def _():
                selected_participant.set(participant)
        _make_obs()

    @output
    @render.ui
    def global_participant_bar():
        curr = selected_participant()
        chips = []
        for p in PARTICIPANTS:
            lvl, tip = _DATA_LEVEL.get(p, ("geen", ""))
            emoji     = _FRUIT_EMOJI.get(p, "")
            is_active = p == curr
            # Active: subtle green tint, darker text, no border
            # Inactive: transparent, muted text, no border
            # Hover is handled purely by opacity (CSS class below)
            chip_style = (
                "display:inline-flex; align-items:center; gap:5px; "
                "padding:4px 14px; border-radius:999px; cursor:pointer; "
                "font-family:'DM Sans',sans-serif; font-weight:500; font-size:0.875rem; "
                "transition:opacity 0.15s ease; border:none; white-space:nowrap; "
                + (
                    "background:var(--accent-muted); color:var(--text-accent); font-weight:600;"
                    if is_active else
                    "background:transparent; color:var(--text-secondary);"
                )
            )
            chips.append(
                ui.input_action_button(
                    f"g_pill_{p}",
                    ui.HTML(f'{emoji} {p.capitalize()}'),
                    style=chip_style,
                    title=tip,
                    class_="participant-chip",
                )
            )
        legend = ui.HTML(
            '<span title="'
            "Vol (🫐🥥) — volledige Garmin biometrie&#10;"
            "Gedeeltelijk (🍋🍐) — gedeeltelijke data&#10;"
            "Geen (🥝🍉) — alleen stemming-check-ins"
            '" style="cursor:help; color:var(--text-tertiary); font-size:0.8125rem; '
            'margin-left:6px; user-select:none; flex-shrink:0;">ⓘ</span>'
        )
        return ui.div(
            ui.span(
                "Deelnemer",
                style="font-size:0.6875rem; font-weight:600; color:var(--text-tertiary); "
                      "text-transform:uppercase; letter-spacing:0.08em; white-space:nowrap; "
                      "margin-right:8px; flex-shrink:0;",
            ),
            *chips,
            legend,
            style=(
                "display:flex; flex-wrap:wrap; align-items:center; gap:4px; "
                "padding:8px var(--page-margin, 80px); "
                "background:var(--bg-base); "
                "border-bottom:1px solid var(--border-default); "
                "position:sticky; top:64px; z-index:190;"
            ),
        )

    home.server("home",       app_data=APP_DATA, now_playing=now_playing,
                              selected_participant=selected_participant)
    science.server("science")
    pipeline.server("pipeline",   app_data=APP_DATA)
    circadian.server("circadian", app_data=APP_DATA, selected_participant=selected_participant)
    recommendation.server("rec",  app_data=APP_DATA, selected_participant=selected_participant)
    session_replay.server("replay", app_data=APP_DATA, selected_participant=selected_participant)
    results.server("results",   app_data=APP_DATA, selected_participant=selected_participant)
    model.server("model",       app_data=APP_DATA)
    recovery.server("recovery", app_data=APP_DATA, selected_participant=selected_participant)
    music_browser.server("music", app_data=APP_DATA, selected_participant=selected_participant)

    @output
    @render.ui
    def now_playing_title():
        import pandas as pd
        state = now_playing()
        if state is None:
            return ui.TagList(
                ui.HTML('<script>(function(){ var b = document.querySelector(".now-playing-bar"); if(b) b.removeAttribute("data-playlist"); })();</script>'),
                ui.div(
                    ui.div(
                        ui.div(
                            style="width:44px; height:44px; border-radius:6px; flex-shrink:0; "
                                  "background:var(--bg-card); border:1px solid var(--border-subtle);",
                        ),
                        ui.div(
                            ui.div("Selecteer een afspeellijst", class_="now-playing-title"),
                            ui.div("MoodTune", class_="now-playing-artist"),
                            style="min-width:0;",
                        ),
                        class_="now-playing-track",
                    ),
                ),
            )

        pl_type = state["playlist_type"]
        pl_lower = pl_type.lower()
        playlist_nl = {
            "Calm":    "Kalme afspeellijst",
            "Neutral": "Neutrale afspeellijst",
            "Energy":  "Energieke afspeellijst",
        }.get(pl_type, pl_type)

        _COVER_GRAD = {
            "Calm":    "linear-gradient(135deg, #1a2a4a, #0a1525)",
            "Neutral": "linear-gradient(135deg, #2a1a4a, #160a2f)",
            "Energy":  "linear-gradient(135deg, #4a2a1a, #2f1508)",
        }
        _PL_COLORS = {"calm": "#2563eb", "neutral": "#7c3aed", "energy": "#ea6c0a"}

        # Track count + duration from playlist df
        df = state.get("df")
        if df is not None and not df.empty:
            n_tracks = len(df)
            try:
                total_min = int(pd.to_numeric(df["duration_ms"], errors="coerce").sum() / 60000)
                meta_str = f"{n_tracks} nrs · {total_min} min"
            except Exception:
                meta_str = f"{n_tracks} nrs"
        else:
            meta_str = ""

        art_style = (
            f"width:44px; height:44px; border-radius:6px; flex-shrink:0; "
            f"background:{_COVER_GRAD.get(pl_type, _COVER_GRAD['Calm'])}; "
            f"display:flex; align-items:center; justify-content:center; font-size:1.25rem;"
        )
        pl_color = _PL_COLORS.get(pl_lower, "#16a34a")

        # JS: set data-playlist on bar for CSS color-coding
        js_attr = ui.HTML(
            f'<script>(function(){{ var b = document.querySelector(".now-playing-bar"); '
            f'if(b) b.setAttribute("data-playlist", "{pl_lower}"); }})();</script>'
        )

        return ui.TagList(
            js_attr,
            ui.div(
                ui.span("🎵", style=art_style),
                ui.div(
                    ui.div(
                        ui.span(playlist_nl, class_="now-playing-title",
                                style=f"color:{pl_color}; font-weight:600;"),
                    ),
                    ui.div(
                        f"{_FRUIT_EMOJI.get(state['participant'], '')} "
                        f"{state['participant'].capitalize()}"
                        + (f"  ·  {meta_str}" if meta_str else ""),
                        class_="now-playing-artist",
                    ),
                    style="min-width:0;",
                ),
                class_="now-playing-track",
            ),
        )


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
