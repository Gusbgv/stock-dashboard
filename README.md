# Big Tech Stock Comparison Dashboard

Gustavo Garcia-Vargas | Developed for CPS*5745

Interactive Plotly Dash dashboard comparing Apple, Microsoft, NVIDIA, Amazon, Alphabet and Meta
using live Yahoo Finance data (via `yfinance`, refreshed hourly). Shared company and date-range
filters drive seven comparison charts plus an auto-generated "Key differences" section.

## Charts
1. Cumulative return since start of range (%), rebased to 0%
2. Adjusted closing price (USD, log scale)
3. 30-day rolling annualized volatility (%)
4. Drawdown from peak within range (%)
5. Distribution of daily returns (box plot, %)
6. Average daily dollar volume (USD billions)
7. Correlation heatmap of daily returns

## Run locally
```
pip install -r requirements.txt
python app.py        # open http://127.0.0.1:8050
```

## Deploy free on Render (public URL, no sign-in for viewers)
1. Create a public GitHub repo (e.g. `stock-dashboard`) and push these files to it.
2. Go to https://render.com, sign in with GitHub, choose **New > Web Service**, pick the repo.
3. Settings: Runtime **Python**, Build `pip install -r requirements.txt`,
   Start `gunicorn app:server --workers 1 --threads 4 --timeout 120`, Instance **Free**.
   (Or choose **New > Blueprint** and Render reads `render.yaml` for you.)
4. Deploy. Your URL will look like `https://big-tech-stock-dashboard.onrender.com`.

Note: free Render services sleep after 15 minutes idle; the first visit after that takes about
a minute to wake. Open the link yourself right before your professor is likely to check it.
