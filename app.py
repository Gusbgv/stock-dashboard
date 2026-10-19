"""
Big Tech Stock Comparison Dashboard
Gustavo Garcia-Vargas | Developed for CPS*5745

Interactive Plotly Dash app comparing publicly traded companies with
shared company and date-range filters. Data: Yahoo Finance via yfinance
(split- and dividend-adjusted daily prices), refreshed every hour.
"""
import os
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
AUTHOR = "Gustavo Garcia-Vargas"
COURSE = "Developed for CPS*5745"

COMPANIES = {  # ticker -> display name (order fixes each company's color)
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta",
}
DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA"]

# Validated categorical palette, assigned to the company (never to its rank)
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#e87ba4", "#e34948"]
COLOR = {t: PALETTE[i] for i, t in enumerate(COMPANIES)}

KEAN_BLUE = "#003C71"
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#ebeae6", "#ffffff"

HISTORY_YEARS = 5
CACHE_TTL = 60 * 60  # seconds
_cache = {"t": 0.0, "close": None, "volume": None, "error": None}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _demo_data():
    """Synthetic prices, used ONLY for offline testing (DEMO_DATA=1)."""
    rng = np.random.default_rng(7)
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=252 * HISTORY_YEARS)
    close, vol = {}, {}
    for i, t in enumerate(COMPANIES):
        r = rng.normal(0.0006 + i * 0.0001, 0.015 + i * 0.003, len(idx))
        close[t] = 100 * np.exp(np.cumsum(r)) * (1 + i)
        vol[t] = rng.lognormal(17 + i * 0.2, 0.3, len(idx))
    return pd.DataFrame(close, index=idx), pd.DataFrame(vol, index=idx)


def load_data():
    """Download adjusted daily close + volume for every company; cache 1 hour."""
    if _cache["close"] is not None and time.time() - _cache["t"] < CACHE_TTL:
        return _cache["close"], _cache["volume"], _cache["error"]
    if os.environ.get("DEMO_DATA") == "1":
        close, volume = _demo_data()
        _cache.update(t=time.time(), close=close, volume=volume, error=None)
        return close, volume, None
    try:
        import yfinance as yf

        raw = yf.download(
            list(COMPANIES), period=f"{HISTORY_YEARS}y", interval="1d",
            auto_adjust=True, progress=False, group_by="column", threads=True,
        )
        close = raw["Close"].dropna(how="all")
        volume = raw["Volume"].reindex(close.index)
        if close.empty:
            raise ValueError("Yahoo Finance returned no data")
        _cache.update(t=time.time(), close=close, volume=volume, error=None)
    except Exception as exc:  # keep serving the last good copy if there is one
        _cache["error"] = f"Live data refresh failed ({exc}). Showing last loaded data."
        if _cache["close"] is None:
            return pd.DataFrame(), pd.DataFrame(), "Could not load stock data. Please refresh in a minute."
    return _cache["close"], _cache["volume"], _cache["error"]


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------
def base_layout(fig, title, y_title, y_fmt=None, y_type="linear", hover="x unified"):
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", y=0.97, yanchor="top", font=dict(size=16, color=INK)),
        template="plotly_white",
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=12, color=INK_2),
        margin=dict(l=64, r=20, t=88, b=40),
        hovermode=hover,
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0, title=None),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(
        title=dict(text=y_title, font=dict(color=INK_2)), gridcolor=GRID, zeroline=False,
        tickformat=y_fmt, type=y_type, tickfont=dict(color=MUTED),
    )
    return fig


def empty_fig(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=MUTED))
    fig.update_layout(template="plotly_white", height=360, xaxis_visible=False, yaxis_visible=False)
    return fig


def line_chart(df, title, y_title, y_fmt, hover_fmt, y_type="linear", zero_line=False):
    fig = go.Figure()
    for t in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[t], mode="lines", name=COMPANIES[t],
            line=dict(width=2, color=COLOR[t]),
            hovertemplate=f"{COMPANIES[t]}: %{{y:{hover_fmt}}}<extra></extra>",
        ))
    base_layout(fig, title, y_title, y_fmt, y_type)
    if zero_line:
        fig.add_hline(y=0, line=dict(color=MUTED, width=1))
    return fig


# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------
dash_app = Dash(__name__, title="Big Tech Stock Comparison")
server = dash_app.server
app = server  # WSGI entry point used by Vercel (and gunicorn)

PRESETS = {"3M": 91, "6M": 182, "YTD": None, "1Y": 365, "3Y": 365 * 3, "5Y": 365 * 5}


def card(graph_id, note):
    return html.Div(className="card", children=[
        dcc.Graph(id=graph_id, style={"height": "380px"},
                  config={"displaylogo": False, "responsive": True}),
        html.P(note, className="note"),
    ])


def serve_layout():
    today = date.today()
    return html.Div(className="page", children=[
        html.Header(className="header", children=[
            html.Div([
                html.H1("Big Tech Stock Comparison Dashboard"),
                html.P(f"{AUTHOR}  |  {COURSE}", className="byline"),
            ]),
            html.Div(id="data-stamp", className="stamp"),
        ]),

        html.Section(className="filters", children=[
            html.Div(className="filter", children=[
                html.Label("Companies (choose 3 or more)", htmlFor="tickers"),
                dcc.Dropdown(
                    id="tickers", multi=True, value=DEFAULT_TICKERS, clearable=False,
                    options=[{"label": f"{n} ({t})", "value": t} for t, n in COMPANIES.items()],
                ),
            ]),
            html.Div(className="filter", children=[
                html.Label("Date range", htmlFor="dates"),
                dcc.DatePickerRange(
                    id="dates", display_format="MMM D, YYYY",
                    start_date=today - timedelta(days=365), end_date=today,
                    min_date_allowed=today - timedelta(days=365 * HISTORY_YEARS), max_date_allowed=today,
                ),
            ]),
            html.Div(className="filter", children=[
                html.Label("Quick range"),
                dcc.RadioItems(id="preset", options=list(PRESETS), value="1Y",
                               inline=True, className="preset"),
            ]),
        ]),

        html.Div(id="alert"),
        html.Div(id="selection-summary", className="selection"),

        html.Div(className="grid", children=[
            card("fig-return", "All companies rebased to 0% on the first day of the range, so growth compares fairly regardless of share price."),
            card("fig-price", "Log scale: equal vertical distances mean equal percentage moves, so stocks priced very differently stay comparable."),
            card("fig-vol", "Annualized standard deviation of daily returns over a rolling 30-trading-day window. Higher means a bumpier ride."),
            card("fig-drawdown", "How far each stock sits below its own highest close within the range. 0% means a new high."),
            card("fig-dist", "Spread of single-day returns. The box covers the middle 50% of days; points beyond the whiskers are unusually large moves."),
            card("fig-dollarvol", "Average shares traded per day times price, in billions of US dollars: how much money changes hands daily."),
            card("fig-corr", "Correlation of daily returns between each pair (1 = always move together, 0 = unrelated)."),
        ]),

        html.Section(className="insights", children=[
            html.H2("Key differences revealed"),
            html.Div(id="insights"),
        ]),

        html.Footer(className="footer", children=[
            html.P(f"{AUTHOR}  |  {COURSE}"),
            html.P("Data: Yahoo Finance via yfinance, split- and dividend-adjusted daily closes, refreshed hourly. "
                   "For educational purposes only, not investment advice."),
        ]),
    ])


dash_app.layout = serve_layout


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
@dash_app.callback(Output("dates", "start_date"), Output("dates", "end_date"), Input("preset", "value"))
def apply_preset(preset):
    end = date.today()
    start = date(end.year, 1, 1) if preset == "YTD" else end - timedelta(days=PRESETS[preset])
    return start, end


@dash_app.callback(
    Output("fig-return", "figure"), Output("fig-price", "figure"), Output("fig-vol", "figure"),
    Output("fig-drawdown", "figure"), Output("fig-dist", "figure"), Output("fig-dollarvol", "figure"),
    Output("fig-corr", "figure"), Output("insights", "children"), Output("alert", "children"),
    Output("data-stamp", "children"), Output("selection-summary", "children"),
    Input("tickers", "value"), Input("dates", "start_date"), Input("dates", "end_date"),
)
def update(tickers, start, end):
    close_all, vol_all, err = load_data()
    alert = html.Div(err, className="alert") if err else None
    if close_all.empty:
        blank = empty_fig("Data unavailable")
        return (*[blank] * 7, None, alert, "", "")

    tickers = [t for t in COMPANIES if t in (tickers or [])]  # keep fixed color order
    stamp = f"Latest trading day: {close_all.index.max():%b %d, %Y}"
    names = ", ".join(COMPANIES[t] for t in tickers) or "none"
    summary = f"Showing: {names}  |  {pd.to_datetime(start):%b %d, %Y} to {pd.to_datetime(end):%b %d, %Y}"

    if len(tickers) < 3:
        msg = "Select at least three companies to compare."
        blank = empty_fig(msg)
        return (*[blank] * 7, html.P(msg), alert, stamp, summary)

    # Pull one extra month before the start so rolling volatility is defined from day one
    pad_start = pd.to_datetime(start) - pd.Timedelta(days=45)
    close_pad = close_all.loc[pad_start:end, tickers].dropna(how="all")
    close = close_pad.loc[start:end]
    volume = vol_all.loc[start:end, tickers]
    if len(close) < 5:
        blank = empty_fig("Choose a longer date range (at least one week).")
        return (*[blank] * 7, None, alert, stamp, summary)

    rets = close.pct_change().dropna(how="all")

    # 1 Cumulative return (%)
    cum = close.divide(close.bfill().iloc[0]) - 1
    f1 = line_chart(cum, "Cumulative Return Since Start of Range", "Return (%)", ".0%", "+.1%", zero_line=True)

    # 2 Adjusted close price, log scale
    f2 = line_chart(close, "Adjusted Closing Price (log scale)", "Price (USD, log scale)", "$,.0f", "$,.2f", y_type="log")
    lo, hi = np.nanmin(close.values), np.nanmax(close.values)
    nice = [m * 10 ** e for e in range(-1, 6) for m in (1, 2, 5)]
    ticks = [v for v in nice if lo / 1.3 <= v <= hi * 1.3]
    f2.update_yaxes(tickvals=ticks, ticktext=[f"${v:,.0f}" for v in ticks])

    # 3 Rolling 30-day annualized volatility
    vol30 = (close_pad.pct_change().rolling(30).std() * np.sqrt(252)).loc[start:end]
    f3 = line_chart(vol30, "30-Day Rolling Volatility (annualized)", "Volatility (%)", ".0%", ".1%")
    f3.update_yaxes(rangemode="tozero")

    # 4 Drawdown from peak
    dd = close / close.cummax() - 1
    f4 = line_chart(dd, "Drawdown from Peak Within Range", "Below peak (%)", ".0%", ".1%", zero_line=True)

    # 5 Daily return distribution (box)
    f5 = go.Figure()
    for t in tickers:
        f5.add_trace(go.Box(
            y=rets[t] * 100, name=COMPANIES[t], marker=dict(color=COLOR[t], size=4),
            line=dict(width=1.5), boxmean=True, hoverinfo="y",
        ))
    base_layout(f5, "Distribution of Daily Returns", "Daily return (%)", None, hover="closest")
    f5.update_yaxes(ticksuffix="%")
    f5.update_layout(showlegend=False)
    f5.add_hline(y=0, line=dict(color=MUTED, width=1))

    # 6 Average daily dollar volume ($B), sorted descending
    dv = (close * volume).mean() / 1e9
    dv = dv.sort_values(ascending=False)
    f6 = go.Figure(go.Bar(
        x=[COMPANIES[t] for t in dv.index], y=dv.values,
        marker=dict(color=[COLOR[t] for t in dv.index], cornerradius=4),
        text=[f"${v:,.1f}B" for v in dv.values], textposition="outside",
        textfont=dict(color=INK_2), cliponaxis=False,
        hovertemplate="%{x}: $%{y:,.2f}B per day<extra></extra>",
    ))
    base_layout(f6, "Average Daily Dollar Volume Traded", "USD (billions)", "$,.0f", hover="closest")
    f6.update_yaxes(ticksuffix="B", rangemode="tozero")
    f6.update_layout(bargap=0.35, showlegend=False)

    # 7 Correlation heatmap of daily returns
    corr = rets.corr()
    labels = [COMPANIES[t] for t in corr.columns]
    f7 = go.Figure(go.Heatmap(
        z=corr.values, x=labels, y=labels, zmin=-1, zmax=1,
        colorscale=[[0, "#d95926"], [0.5, "#f0efec"], [1, "#2a78d6"]],
        text=np.round(corr.values, 2), texttemplate="%{text:.2f}",
        textfont=dict(color=INK), xgap=2, ygap=2,
        hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>",
        colorbar=dict(title="Correlation", thickness=12),
    ))
    base_layout(f7, "Correlation of Daily Returns", "", None, hover="closest")
    f7.update_xaxes(type="category")
    f7.update_yaxes(type="category", autorange="reversed", showgrid=False, title=None)

    insights = build_insights(tickers, cum, vol30, dd, rets, dv, corr)
    return f1, f2, f3, f4, f5, f6, f7, insights, alert, stamp, summary


def build_insights(tickers, cum, vol30, dd, rets, dv, corr):
    """Plain-language comparison generated from the current filter selection."""
    n = COMPANIES
    total = cum.iloc[-1].sort_values(ascending=False)
    avg_vol = vol30.mean().sort_values(ascending=False)
    worst_dd = dd.min().sort_values()
    best_day, worst_day = rets.max(), rets.min()
    pairs = [(a, b, corr.loc[a, b]) for i, a in enumerate(tickers) for b in tickers[i + 1:]]
    hi_pair = max(pairs, key=lambda p: p[2])
    lo_pair = min(pairs, key=lambda p: p[2])
    big_day_t = (best_day - worst_day).idxmax()

    items = [
        f"Performance: {n[total.index[0]]} led the group with a {total.iloc[0]:+.1%} return over the range, "
        f"while {n[total.index[-1]]} trailed at {total.iloc[-1]:+.1%}, a gap of "
        f"{(total.iloc[0] - total.iloc[-1]) * 100:.1f} percentage points.",
        f"Risk: {n[avg_vol.index[0]]} was the most volatile (about {avg_vol.iloc[0]:.0%} annualized on average) and "
        f"{n[avg_vol.index[-1]]} the steadiest (about {avg_vol.iloc[-1]:.0%}).",
        f"Drawdowns: {n[worst_dd.index[0]]} suffered the deepest drop from its peak ({worst_dd.iloc[0]:.1%}), "
        f"compared with {worst_dd.iloc[-1]:.1%} for {n[worst_dd.index[-1]]}.",
        f"Extreme days: {n[big_day_t]} had the widest daily range, from {worst_day[big_day_t]:+.1%} "
        f"to {best_day[big_day_t]:+.1%} in a single session.",
        f"Trading activity: {n[dv.index[0]]} saw the most money traded per day (about ${dv.iloc[0]:,.1f}B), "
        f"versus ${dv.iloc[-1]:,.1f}B for {n[dv.index[-1]]}.",
        f"Co-movement: {n[hi_pair[0]]} and {n[hi_pair[1]]} moved together most closely (correlation {hi_pair[2]:.2f}), "
        f"while {n[lo_pair[0]]} and {n[lo_pair[1]]} were the least linked ({lo_pair[2]:.2f}), "
        f"so holding that pair offers the most diversification within this group.",
    ]
    return html.Ul([html.Li(i) for i in items])


if __name__ == "__main__":
    dash_app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
