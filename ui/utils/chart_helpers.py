"""Shared Plotly layout factories and color constants."""
import plotly.graph_objects as go

# Design system tokens — light mode
BG_BASE     = "#f4f2ee"
BG_CARD     = "#ffffff"
BG_ELEVATED = "#ede9e3"
ACCENT      = "#16a34a"
TEXT_PRIMARY   = "#111827"
TEXT_SECONDARY = "#6b7280"
TEXT_TERTIARY  = "#9ca3af"
STRESS_RED  = "#dc2626"
GRID_COLOR  = "rgba(0,0,0,0.06)"
ZERO_COLOR  = "rgba(0,0,0,0.10)"

# Legacy aliases
BG_PRIMARY   = BG_BASE
ACCENT_GREEN = ACCENT
BORDER       = "rgba(0,0,0,0.08)"

# Okabe-Ito colorblind-safe palette — matches notebooks/ml/*.ipynb
# Calm=#56B4E9 (sky blue), Neutral=#009E73 (bluish green), Energy=#E69F00 (orange)
PLAYLIST_COLORS = {
    "Calm":    "#56B4E9",
    "Neutral": "#009E73",
    "Energy":  "#E69F00",
}

# General Okabe-Ito sequence for non-playlist categorical charts
CHART_COLORS = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

# Standard layout to apply to all Plotly charts
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family="DM Sans, sans-serif",
        color=TEXT_SECONDARY,
        size=13,
    ),
    title_font=dict(
        family="Sora, sans-serif",
        size=18,
        color=TEXT_PRIMARY,
    ),
    xaxis=dict(
        gridcolor=GRID_COLOR,
        zerolinecolor=ZERO_COLOR,
        tickfont=dict(color=TEXT_TERTIARY, size=12),
        title_font=dict(color=TEXT_SECONDARY, family="DM Sans, sans-serif"),
    ),
    yaxis=dict(
        gridcolor=GRID_COLOR,
        zerolinecolor=ZERO_COLOR,
        tickfont=dict(color=TEXT_TERTIARY, size=12),
        title_font=dict(color=TEXT_SECONDARY, family="DM Sans, sans-serif"),
    ),
    margin=dict(l=48, r=24, t=48, b=40),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_SECONDARY, size=12),
        borderwidth=0,
    ),
    hoverlabel=dict(
        bgcolor=BG_CARD,
        font_color=TEXT_PRIMARY,
        bordercolor=BORDER,
    ),
    modebar=dict(
        remove=[
            "zoom2d", "pan2d", "select2d", "lasso2d",
            "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
            "toImage",
        ],
        bgcolor="rgba(0,0,0,0)",
        color=TEXT_SECONDARY,
    ),
)


def chart_layout(**overrides) -> dict:
    """Base Plotly layout for all MoodTune charts."""
    base = dict(PLOTLY_LAYOUT)
    base.update(overrides)
    return base


def empty_figure(message: str = "Geen data beschikbaar") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False,
        font=dict(color=TEXT_SECONDARY, size=14),
    )
    fig.update_layout(**chart_layout(xaxis=dict(visible=False), yaxis=dict(visible=False)))
    return fig
