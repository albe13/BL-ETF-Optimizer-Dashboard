"""Design system of the BL ETF Optimizer dashboard: palette, Plotly template, CSS, number formatting and page components.

Colour roles follow the validated reference palette of the data-visualization method (categorical slots in fixed order, blue/red
diverging pair with a neutral midpoint, blue sequential ramp, reserved status colours). Strategy and ETF colours are assigned to
entities once and never re-cycled, so a line keeps its colour on every page.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from bldash.core import registry as R

# ----------------------------------------------------------------------------------------------------------------------- palette (light)
SLOTS: List[str] = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]   # validated categorical order
BLUE_RAMP: Dict[int, str] = {100: "#cde2fb", 150: "#b7d3f6", 200: "#9ec5f4", 250: "#86b6ef", 300: "#6da7ec", 350: "#5598e7", 400: "#3987e5", 450: "#2a78d6",
                             500: "#256abf", 550: "#1c5cab", 600: "#184f95", 650: "#104281", 700: "#0d366b"}
INK, INK2, MUTED, GRID, AXIS, SURFACE, PLANE = "#172B4D", "#64748B", "#7C8BA1", "#E2E8F0", "#CBD5E1", "#FFFFFF", "#F5F7FA"
SIDEBAR_BG, SIDEBAR_SELECTED, SIDEBAR_TEXT = "#142238", "#263B57", "#F1F5F9"             # also set natively in .streamlit/config.toml
POS, NEG, NEUTRAL = "#2a78d6", "#d03b3b", "#F1F5F9"            # diverging poles (blue = positive, red = negative), neutral midpoint
GOOD, WARN, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
DIVERGING = [[0.0, "#104281"], [0.25, "#6da7ec"], [0.5, NEUTRAL], [0.75, "#ec835a"], [1.0, "#b91c1c"]]
SEQUENTIAL = [[0.0, BLUE_RAMP[100]], [0.5, BLUE_RAMP[400]], [1.0, BLUE_RAMP[700]]]

BL1_COLOR, BL2_COLOR, BENCHMARK_COLOR = "#2563EB", "#0D9488", "#94A3B8"
STRATEGY_COLORS: Dict[str, str] = {
    R.BL1: BL1_COLOR, R.BL2: BL2_COLOR, R.BENCHMARK: BENCHMARK_COLOR,
    "BL2_EQUILIBRIUM_ONLY": SLOTS[6], "BL2_EQUILIBRIUM_ONLY_H1": BLUE_RAMP[300], "BL2_EXPERIMENTAL_REVISED_MACRO": SLOTS[1],
    "ABL_H1_BL2_VIEWS": SLOTS[3], "ABL_H6_BL2_VIEWS": SLOTS[4], "ABL_BL1_VIEWS_BL2_ALLOCATION": SLOTS[5], "ABL_RELATIVE_ONLY": SLOTS[7],
    "ABL_COMMON_ONLY": BLUE_RAMP[650], "ABL_DIAG_OMEGA": MUTED, "ABL_IC_EFF_LOW": BLUE_RAMP[250], "ABL_IC_EFF_HIGH": BLUE_RAMP[550],
}
STRATEGY_DASH: Dict[str, str] = {R.BENCHMARK: "dash"}
ETF_COLORS: Dict[str, str] = {"Equity": SLOTS[0], "Government Bonds": SLOTS[6], "Investment Grade Credit": SLOTS[2], "Gold": SLOTS[3],
                              "Private Equity Proxy": SLOTS[1], "Emerging Debt": SLOTS[5], "Securitized": SLOTS[4], "Real Estate": SLOTS[7],
                              "Inflation Linked": BLUE_RAMP[650], "Convertibles": BLUE_RAMP[250]}
ETF_DASH: Dict[str, str] = {"Inflation Linked": "dash", "Convertibles": "dot"}      # secondary encoding for the two ramp-step colours
QUADRANT_COLORS: Dict[str, str] = {"GOLDILOCKS": SLOTS[2], "REFLATION": SLOTS[3], "STAGFLATION": SLOTS[7], "DISINFLATIONARY_SLOWDOWN": SLOTS[0],
                                   "UNCLASSIFIED_ZERO": MUTED, "UNAVAILABLE": GRID, "nan": GRID}
QUADRANT_LABELS: Dict[str, str] = {"GOLDILOCKS": "Goldilocks", "REFLATION": "Reflation", "STAGFLATION": "Stagflation",
                                   "DISINFLATIONARY_SLOWDOWN": "Disinflationary slowdown", "UNCLASSIFIED_ZERO": "Unclassified (zero)", "UNAVAILABLE": "Unavailable", "nan": "Unavailable"}
FONT = "Inter, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"


def strategy_color(s: str) -> str:
    return STRATEGY_COLORS.get(s, MUTED)


def strategy_label(s: str) -> str:
    return R.STRATEGY_LABELS.get(s, s)


# ----------------------------------------------------------------------------------------------------------------------- plotly template
def _template() -> go.layout.Template:
    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font=dict(family=FONT, size=12, color=INK2),
        title=dict(font=dict(size=14, color=INK, family=FONT), x=0, xanchor="left", pad=dict(l=0, b=6)),
        margin=dict(l=10, r=14, t=44, b=10), hovermode="x unified",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=GRID, font=dict(family=FONT, size=11, color=INK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=11, color=INK2), bgcolor="rgba(0,0,0,0)", itemwidth=30),
        xaxis=dict(showgrid=False, linecolor=AXIS, linewidth=1, ticks="outside", tickcolor=AXIS, ticklen=4, tickfont=dict(size=11, color=MUTED), zeroline=False,
                   title=dict(font=dict(size=11, color=MUTED))),
        yaxis=dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, linecolor="rgba(0,0,0,0)", tickfont=dict(size=11, color=MUTED),
                   title=dict(font=dict(size=11, color=MUTED))),
        colorway=[BL1_COLOR, BL2_COLOR, BENCHMARK_COLOR, SLOTS[1], SLOTS[6], SLOTS[3], SLOTS[4], SLOTS[5], SLOTS[7]],
    )
    return t


pio.templates["bl"] = _template()
pio.templates.default = "bl"


def finish(fig: go.Figure, height: int = 380, title: str = "", ytitle: str = "", yfmt: str = "", xtitle: str = "", log: bool = False,
           legend: bool = True, hover: str = "x unified") -> go.Figure:
    fig.update_layout(height=height, hovermode=hover, showlegend=legend, margin=dict(l=10, r=14, t=44 if title else 28, b=10))
    if title:
        fig.update_layout(title_text=title)
    if log:
        fig.update_yaxes(type="log")
    if ytitle:
        fig.update_yaxes(title_text=ytitle)
    if yfmt:
        fig.update_yaxes(tickformat=yfmt)
    if xtitle:
        fig.update_xaxes(title_text=xtitle)
    return fig


def plot(fig: go.Figure, key: Optional[str] = None) -> None:
    st.plotly_chart(fig, use_container_width=True, key=key, config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
                                                                     "toImageButtonOptions": {"format": "png", "scale": 2}})


def line_chart(series: Dict[str, pd.Series], colors: Optional[Dict[str, str]] = None, dash: Optional[Dict[str, str]] = None, labels: Optional[Dict[str, str]] = None,
               yfmt: str = ".2f", height: int = 380, title: str = "", ytitle: str = "", xtitle: str = "", log: bool = False, hover_fmt: Optional[str] = None,
               end_labels: bool = False, width: float = 2.0, fill_zero: Optional[str] = None) -> go.Figure:
    fig = go.Figure()
    colors = colors or {}
    dash = dash or {}
    labels = labels or {}
    hf = hover_fmt or yfmt
    for i, (name, s) in enumerate(series.items()):
        s = s.dropna()
        lab = labels.get(name, strategy_label(name))
        col = colors.get(name, STRATEGY_COLORS.get(name, ETF_COLORS.get(name, SLOTS[i % len(SLOTS)])))
        fig.add_trace(go.Scatter(x=s.index, y=s.to_numpy(), name=lab, mode="lines", line=dict(color=col, width=width, dash=dash.get(name, STRATEGY_DASH.get(name, ETF_DASH.get(name, "solid")))),
                                 fill="tozeroy" if fill_zero == name else None, hovertemplate=f"{lab}: %{{y:{hf}}}<extra></extra>"))
        if end_labels and len(s):
            fig.add_annotation(x=s.index[-1], y=float(s.iloc[-1]), text=lab, showarrow=False, xanchor="left", xshift=6, font=dict(size=10, color=col), align="left")
    return finish(fig, height, title, ytitle, yfmt, xtitle, log)


def bar_chart(x: Sequence, y: Sequence, title: str = "", yfmt: str = ".2%", height: int = 340, color=None, orientation: str = "v", signed: bool = True,
              text: bool = False, labels: Optional[Sequence[str]] = None, ytitle: str = "") -> go.Figure:
    """x = categories, y = values (for both orientations); horizontal bars list the categories top-down."""
    cats, vals = list(x), [float(v) if v is not None else float("nan") for v in y]
    if color is None:
        cols = [POS if (not math.isnan(v) and v >= 0) else NEG for v in vals] if signed else [SLOTS[0]] * len(vals)
    else:
        cols = color if isinstance(color, (list, tuple)) else [color] * len(vals)
    hover = "%{x}: %{y:" + yfmt + "}" if orientation == "v" else "%{y}: %{x:" + yfmt + "}"
    bx, by = (cats, vals) if orientation == "v" else (vals, cats)
    fig = go.Figure(go.Bar(x=bx, y=by, orientation=orientation, marker=dict(color=cols, cornerradius=3, line=dict(width=0)), hovertemplate=hover + "<extra></extra>",
                           text=[f"{v:{yfmt}}" for v in vals] if text else None, textposition="outside", textfont=dict(size=10, color=INK2), customdata=labels))
    finish(fig, height, title, ytitle, yfmt if orientation == "v" else "", "", hover="closest", legend=False)
    if orientation == "h":
        fig.update_xaxes(tickformat=yfmt, showgrid=True, gridcolor=GRID)
        fig.update_yaxes(showgrid=False, autorange="reversed")
    fig.update_layout(bargap=0.28)
    return fig


def grouped_bar(categories: Sequence[str], groups: Dict[str, Sequence[float]], colors: Dict[str, str], title: str = "", yfmt: str = ".1%", height: int = 380,
                orientation: str = "h", labels: Optional[Dict[str, str]] = None, ytitle: str = "") -> go.Figure:
    fig = go.Figure()
    labels = labels or {}
    for name, vals in groups.items():
        lab = labels.get(name, strategy_label(name))
        if orientation == "h":
            fig.add_trace(go.Bar(y=list(categories), x=list(vals), orientation="h", name=lab, marker=dict(color=colors.get(name, MUTED), cornerradius=2, line=dict(width=0)),
                                 hovertemplate=f"{lab} · %{{y}}: %{{x:{yfmt}}}<extra></extra>"))
        else:
            fig.add_trace(go.Bar(x=list(categories), y=list(vals), name=lab, marker=dict(color=colors.get(name, MUTED), cornerradius=2, line=dict(width=0)),
                                 hovertemplate=f"{lab} · %{{x}}: %{{y:{yfmt}}}<extra></extra>"))
    finish(fig, height, title, ytitle, yfmt if orientation == "v" else "", hover="closest")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    if orientation == "h":
        fig.update_xaxes(tickformat=yfmt, showgrid=True, gridcolor=GRID)
        fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


def stacked_area(W: pd.DataFrame, title: str = "", height: int = 400, colors: Optional[Dict[str, str]] = None, yfmt: str = ".0%", legend: bool = True) -> go.Figure:
    fig = go.Figure()
    colors = colors or ETF_COLORS
    for a in [c for c in R.ASSETS if c in W.columns]:
        fig.add_trace(go.Scatter(x=W.index, y=W[a].to_numpy(), name=R.ASSET_SHORT.get(a, a), mode="lines", stackgroup="one",
                                 line=dict(width=0.8, color=SURFACE), fillcolor=colors.get(a, MUTED), hovertemplate=f"{a}: %{{y:.1%}}<extra></extra>"))
    finish(fig, height, title, "weight", yfmt, legend=legend)
    fig.update_layout(legend=dict(traceorder="normal"))
    return fig


def heatmap(df: pd.DataFrame, title: str = "", height: int = 420, zmid: Optional[float] = 0.0, fmt: str = ".2f", colorscale=None, zmin=None, zmax=None,
            xlabels: Optional[Sequence[str]] = None, ylabels: Optional[Sequence[str]] = None, colorbar_title: str = "", text: bool = False) -> go.Figure:
    xl = list(xlabels) if xlabels is not None else [c.strftime("%Y-%m") if isinstance(c, pd.Timestamp) else str(c) for c in df.columns]
    yl = list(ylabels) if ylabels is not None else [i.strftime("%Y-%m") if isinstance(i, pd.Timestamp) else str(i) for i in df.index]
    fig = go.Figure(go.Heatmap(z=df.to_numpy(), x=xl, y=yl, colorscale=colorscale or DIVERGING, zmid=zmid, zmin=zmin, zmax=zmax, xgap=1, ygap=1,
                               colorbar=dict(title=colorbar_title, thickness=10, len=0.9, tickfont=dict(size=10)),
                               hovertemplate="%{y} · %{x}: %{z:" + fmt + "}<extra></extra>",
                               text=df.to_numpy() if text else None, texttemplate=("%{text:" + fmt + "}") if text else None, textfont=dict(size=10)))
    finish(fig, height, title, hover="closest", legend=False)
    fig.update_yaxes(showgrid=False, autorange="reversed" if ylabels is not None or not isinstance(df.index[0], pd.Timestamp) else True)
    fig.update_xaxes(showgrid=False)
    return fig


def histogram(values: Dict[str, pd.Series], title: str = "", height: int = 320, xfmt: str = ".0%", nbins: int = 25) -> go.Figure:
    fig = go.Figure()
    for name, s in values.items():
        fig.add_trace(go.Histogram(x=s.dropna().to_numpy(), nbinsx=nbins, name=strategy_label(name), marker=dict(color=strategy_color(name), line=dict(width=1, color=SURFACE)),
                                   opacity=0.75, hovertemplate=f"{strategy_label(name)} · %{{x:{xfmt}}}: %{{y}} months<extra></extra>"))
    finish(fig, height, title, "months", "", hover="closest")
    fig.update_layout(barmode="overlay", bargap=0.05)
    fig.update_xaxes(tickformat=xfmt)
    return fig


# ----------------------------------------------------------------------------------------------------------------------- formatting
def _num(x) -> bool:
    try:
        return x is not None and not isinstance(x, str) and not (isinstance(x, float) and math.isnan(x)) and not pd.isna(x)
    except Exception:
        return False


def fmt_pct(x, d: int = 2, sign: bool = False) -> str:
    return (f"{float(x):+.{d}%}" if sign else f"{float(x):.{d}%}") if _num(x) else "n/a"


def fmt_pp(x, d: int = 1) -> str:
    return f"{100 * float(x):+.{d}f} pp" if _num(x) else "n/a"


def fmt_bp(x, d: int = 0, sign: bool = False) -> str:
    return (f"{1e4 * float(x):+.{d}f} bp" if sign else f"{1e4 * float(x):.{d}f} bp") if _num(x) else "n/a"


def fmt_num(x, d: int = 2, sign: bool = False) -> str:
    return (f"{float(x):+.{d}f}" if sign else f"{float(x):.{d}f}") if _num(x) else "n/a"


def fmt_eur(x, d: int = 0) -> str:
    return f"EUR {float(x):,.{d}f}" if _num(x) else "n/a"


def fmt_date(x) -> str:
    try:
        return pd.Timestamp(x).date().isoformat()
    except Exception:
        return "n/a"


def fmt_month(x) -> str:
    try:
        return pd.Timestamp(x).strftime("%b %Y")
    except Exception:
        return "n/a"


# ----------------------------------------------------------------------------------------------------------------------- CSS and components
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {{ --bl-ink:{INK}; --bl-ink2:{INK2}; --bl-muted:{MUTED}; --bl-line:{GRID}; --bl-card:{SURFACE}; --bl-plane:{PLANE}; --bl-accent:{BLUE_RAMP[550]};
        --bl-side:{SIDEBAR_BG}; --bl-side-sel:{SIDEBAR_SELECTED}; --bl-side-ink:{SIDEBAR_TEXT}; }}
html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stDataFrame {{ font-family: {FONT}; }}
.block-container {{ padding-top: 2.6rem; padding-bottom: 3rem; max-width: 1480px; }}
h1, h2, h3 {{ font-family: {FONT}; letter-spacing: -0.01em; color: var(--bl-ink); }}
h1 {{ font-size: 1.85rem !important; font-weight: 650 !important; margin-bottom: 0.2rem !important; }}
h2 {{ font-size: 1.25rem !important; font-weight: 600 !important; margin-top: 1.4rem !important; }}
h3 {{ font-size: 1.02rem !important; font-weight: 600 !important; margin-top: 1.0rem !important; }}
[data-testid="stMetric"] {{ background: var(--bl-card); border: 1px solid var(--bl-line); border-radius: 10px; padding: 12px 14px 10px 14px; }}
[data-testid="stMetricLabel"] p {{ font-size: 0.78rem; color: var(--bl-ink2); text-transform: none; letter-spacing: 0; }}
[data-testid="stMetricValue"] {{ font-size: 1.45rem; font-weight: 600; color: var(--bl-ink); }}
[data-testid="stMetricDelta"] {{ font-size: 0.8rem; }}
section[data-testid="stSidebar"] {{ background: var(--bl-side); }}
/* Streamlit opens the sidebar at a hard-coded 256px (inline style) — 22px short of a full YYYY-MM-DD in the date selector. Only that untouched
   default is widened: a user-resized width is a different inline value and is left alone; collapse (max-width 0) and the 90%-of-window cap still apply. */
section[data-testid="stSidebar"][style*="width: 256px"] {{ width: 288px !important; }}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: var(--bl-side-ink); opacity: 0.78; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: var(--bl-side-sel); border-radius: 8px; }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ font-weight: 600; }}
[data-testid="stSidebarNav"] a:hover {{ background: rgba(38,59,87,0.6); }}
section[data-testid="stSidebar"] .stMarkdown p {{ font-size: 0.86rem; }}
.bl-kicker {{ font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--bl-accent); margin-bottom: 0.15rem; }}
.bl-subtitle {{ font-size: 1.02rem; color: var(--bl-ink2); margin-bottom: 0.9rem; max-width: 980px; line-height: 1.45; }}
.bl-section {{ display:flex; align-items: baseline; gap: 10px; border-bottom: 1px solid var(--bl-line); padding-bottom: 6px; margin: 1.5rem 0 0.9rem 0; }}
.bl-section .t {{ font-size: 1.12rem; font-weight: 600; color: var(--bl-ink); }}
.bl-section .s {{ font-size: 0.86rem; color: var(--bl-muted); }}
.bl-card {{ background: var(--bl-card); border: 1px solid var(--bl-line); border-radius: 10px; padding: 14px 16px; height: 100%; }}
.bl-card .lab {{ font-size: 0.76rem; color: var(--bl-ink2); margin-bottom: 4px; }}
.bl-card .val {{ font-size: 1.5rem; font-weight: 600; color: var(--bl-ink); line-height: 1.15; }}
.bl-card .sub {{ font-size: 0.76rem; color: var(--bl-muted); margin-top: 4px; }}
.bl-card .swatch {{ display:inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }}
.bl-badge {{ display:inline-block; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--bl-line); color: var(--bl-ink2); background: var(--bl-card); margin-right: 6px; }}
.bl-badge.good {{ color:#0a6f0a; border-color:#9fd89f; background:#f1faf1; }}
.bl-badge.warn {{ color:#8a5a00; border-color:#f1d27a; background:#fff8e6; }}
.bl-badge.bad {{ color:#9b1c1c; border-color:#f0b3b3; background:#fff1f1; }}
.bl-badge.info {{ color:#1c5cab; border-color:#b7d3f6; background:#eef5fd; }}
.bl-note {{ border-left: 3px solid var(--bl-accent); background: #f3f7fd; padding: 10px 14px; border-radius: 6px; font-size: 0.88rem; color: var(--bl-ink2); margin: 0.4rem 0 0.9rem 0; line-height: 1.45; }}
.bl-note.warn {{ border-left-color: {WARN}; background: #fff8e6; }}
.bl-note.bad {{ border-left-color: {CRITICAL}; background: #fff1f1; }}
.bl-note.good {{ border-left-color: {GOOD}; background: #f1faf1; }}
.bl-small {{ font-size: 0.78rem; color: var(--bl-muted); line-height: 1.4; }}
.bl-step {{ background: var(--bl-card); border: 1px solid var(--bl-line); border-radius: 10px; padding: 12px 14px; height: 100%; }}
.bl-step .n {{ font-size: 0.7rem; font-weight: 700; color: var(--bl-accent); letter-spacing: 0.08em; }}
.bl-step .h {{ font-size: 0.95rem; font-weight: 600; color: var(--bl-ink); margin: 2px 0 4px 0; }}
.bl-step .b {{ font-size: 0.8rem; color: var(--bl-ink2); line-height: 1.4; }}
.bl-flow {{ display:flex; gap: 8px; align-items: stretch; flex-wrap: wrap; }}
.bl-flow .box {{ flex: 1 1 140px; background: var(--bl-card); border: 1px solid var(--bl-line); border-radius: 10px; padding: 10px 12px; min-width: 140px; }}
.bl-flow .box .h {{ font-size: 0.82rem; font-weight: 600; color: var(--bl-ink); }}
.bl-flow .box .b {{ font-size: 0.76rem; color: var(--bl-ink2); line-height: 1.35; margin-top: 3px; }}
.bl-flow .arrow {{ align-self: center; color: var(--bl-muted); font-size: 1.1rem; padding: 0 2px; }}
div[data-testid="stDataFrame"] {{ border: 1px solid var(--bl-line); border-radius: 8px; }}
[data-testid="stPlotlyChart"] {{ background: var(--bl-card); border: 1px solid var(--bl-line); border-radius: 10px; overflow: hidden; }}
.stTabs [data-baseweb="tab"] {{ font-size: 0.9rem; font-weight: 500; }}
.bl-legend {{ display:flex; flex-wrap: wrap; justify-content: center; gap: 6px 16px; margin: 0 0 0.6rem 0; font-size: 0.8rem; color: var(--bl-ink2); }}
.bl-legend .it {{ display:inline-flex; align-items: center; white-space: nowrap; }}
.bl-legend .sw {{ display:inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 6px; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", kicker: str = "") -> None:
    if kicker:
        st.markdown(f'<div class="bl-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f'<div class="bl-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def section(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="bl-section"><span class="t">{title}</span><span class="s">{subtitle}</span></div>', unsafe_allow_html=True)


def note(text: str, kind: str = "info") -> None:
    st.markdown(f'<div class="bl-note {kind}">{text}</div>', unsafe_allow_html=True)


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="bl-badge {kind}">{text}</span>'


def badges(items: Iterable) -> None:
    st.markdown(" ".join(badge(t, k) for t, k in items), unsafe_allow_html=True)


def cards(items: List[Dict[str, str]], cols: Optional[int] = None) -> None:
    """items: dicts with label, value, sub (optional), color (optional swatch)."""
    n = cols or len(items)
    columns = st.columns(n)
    for col, it in zip(columns, items):
        sw = f'<span class="swatch" style="background:{it["color"]}"></span>' if it.get("color") else ""
        vstyle = ' style="font-size:1.05rem"' if len(str(it["value"])) > 16 else ""
        col.markdown(f'<div class="bl-card"><div class="lab">{sw}{it["label"]}</div><div class="val"{vstyle}>{it["value"]}</div><div class="sub">{it.get("sub", "")}</div></div>',
                     unsafe_allow_html=True)


def flow(boxes: List[Dict[str, str]]) -> None:
    html = '<div class="bl-flow">'
    for i, b in enumerate(boxes):
        if i:
            html += '<div class="arrow">→</div>'
        html += f'<div class="box"><div class="h">{b["h"]}</div><div class="b">{b["b"]}</div></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def steps(items: List[Dict[str, str]], cols: int = 3) -> None:
    for i in range(0, len(items), cols):
        row = st.columns(cols)
        for col, it in zip(row, items[i:i + cols]):
            col.markdown(f'<div class="bl-step"><div class="n">{it["n"]}</div><div class="h">{it["h"]}</div><div class="b">{it["b"]}</div></div>', unsafe_allow_html=True)


def shared_legend(*figs: go.Figure) -> None:
    """One HTML legend for several figures that hide their own: built from the figures' traces (name + fill/line colour), so it cannot drift from the charts."""
    items: Dict[str, str] = {}
    for fig in figs:
        for tr in fig.data:
            col = getattr(tr, "fillcolor", None) or (tr.line.color if getattr(tr, "line", None) is not None else None) or MUTED
            items.setdefault(tr.name, col)
    st.markdown('<div class="bl-legend">' + "".join(f'<span class="it"><span class="sw" style="background:{c}"></span>{n}</span>' for n, c in items.items()) + "</div>",
                unsafe_allow_html=True)


def small(text: str) -> None:
    st.markdown(f'<div class="bl-small">{text}</div>', unsafe_allow_html=True)


def table(df: pd.DataFrame, formats: Optional[Dict[str, str]] = None, height: Optional[int] = None, hide_index: bool = False, key: Optional[str] = None) -> None:
    """Styled table: `formats` maps column -> python format string (e.g. '{:.2%}'); unlisted numeric columns keep their raw values."""
    kw = {"width": "stretch", "hide_index": hide_index}
    if height is not None:
        kw["height"] = int(height)
    if key is not None:
        kw["key"] = key
    if formats:
        sty = df.style.format({c: f for c, f in formats.items() if c in df.columns}, na_rep="n/a")
        st.dataframe(sty, **kw)
    else:
        st.dataframe(df, **kw)


def source_note(store, keys: Sequence[str]) -> None:
    parts = []
    for k in keys:
        e = R.ENTRY_BY_KEY.get(k)
        if e is None:
            continue
        rid = store.run_ids.get(e.source, e.source)
        parts.append(f"`{e.path}` ({rid})")
    st.caption("Source: " + " · ".join(parts) + ". Published, hash-verified artifacts displayed as stored; any derived quantity is labelled.")


def research_banner() -> None:
    note("<b>Historical, in-sample results.</b> Every figure is read from frozen, hash-verified runs. The 2019–2026 window is the sample the models were "
         "developed on; nothing here is evidence of predictive power or of future performance. BL 2.0 runs in a research configuration whose "
         "parameters are provisional. Returns are EUR total-return valuation proxies net of a uniform 10 bp one-way transaction cost.", "info")
