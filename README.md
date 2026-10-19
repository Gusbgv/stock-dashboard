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

## Deploy on Vercel
1. Push this folder to a public GitHub repo (e.g. `Gusbgv/stock-dashboard`).
2. On vercel.com choose **Add New > Project**, import the repo, leave Framework Preset as **Other**, and click **Deploy**.
   `vercel.json` tells Vercel to run `app.py` as a Python function. No environment variables are needed.
3. Every later `git push` redeploys automatically.
