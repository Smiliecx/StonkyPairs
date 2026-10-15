"""
Download ~6 years of daily, dividend-adjusted closing prices for the
S&P 500 plus a set of ETFs (and any extra tickers you list), and save:

    <out>/prices.csv   rows = dates, columns = tickers (adjusted close)
    <out>/tickers.csv  ticker, name, sector, industry, type
    <out>/meta.json    download date, counts, tickers that failed

Runs weekly on GitHub Actions (see .github/workflows/update-prices.yml),
or by hand:  python download_prices.py --out data
"""

import argparse
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Hedge-friendly ETFs: broad market, sectors, themes, factors, rates, commodities.
ETFS = {
    "SPY": "S&P 500", "QQQ": "Nasdaq-100", "IWM": "Russell 2000", "DIA": "Dow 30",
    "RSP": "S&P 500 Equal Weight",
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy", "XLV": "Health Care",
    "XLI": "Industrials", "XLY": "Consumer Discretionary", "XLP": "Consumer Staples",
    "XLU": "Utilities", "XLB": "Materials", "XLRE": "Real Estate", "XLC": "Communication Services",
    "SMH": "Semiconductors", "SOXX": "Semiconductors (iShares)", "IGV": "Software",
    "SKYY": "Cloud Computing", "XBI": "Biotech", "IBB": "Biotech (iShares)",
    "KRE": "Regional Banks", "KBE": "Banks", "ITB": "Homebuilders", "XHB": "Homebuilders (SPDR)",
    "XRT": "Retail", "XOP": "Oil & Gas E&P", "OIH": "Oil Services", "JETS": "Airlines",
    "ITA": "Aerospace & Defense", "PAVE": "Infrastructure", "TAN": "Solar", "ICLN": "Clean Energy",
    "GDX": "Gold Miners", "COPX": "Copper Miners",
    "MTUM": "Momentum factor", "QUAL": "Quality factor", "USMV": "Min Volatility factor",
    "VLUE": "Value factor", "IWF": "Russell 1000 Growth", "IWD": "Russell 1000 Value",
    "TLT": "20+ Yr Treasuries", "IEF": "7-10 Yr Treasuries", "HYG": "High Yield Bonds",
    "GLD": "Gold", "SLV": "Silver", "USO": "Crude Oil", "UUP": "US Dollar",
    "EFA": "Developed ex-US", "EEM": "Emerging Markets", "FXI": "China Large-Cap",
}

# Drop duplicate share classes (keep one of each pair).
DUPLICATES = {"GOOG", "FOX", "NWS"}


def load_sp500():
    html = requests.get(SP500_URL, headers={"User-Agent": "Mozilla/5.0 (price-downloader)"}, timeout=30).text
    table = pd.read_html(io.StringIO(html))[0]
    table["Symbol"] = table["Symbol"].str.replace(".", "-", regex=False)
    rows = []
    for _, r in table.iterrows():
        if r["Symbol"] in DUPLICATES:
            continue
        rows.append({"ticker": r["Symbol"], "name": r["Security"], "sector": r["GICS Sector"],
                     "industry": r["GICS Sub-Industry"], "type": "stock"})
    return rows


def load_extra(path):
    """extra_tickers.txt: one ticker per line, optional '# comment'."""
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        t = line.split("#")[0].strip().upper()
        if t:
            rows.append({"ticker": t, "name": t, "sector": "Other", "industry": "Other", "type": "stock"})
    return rows


def download(tickers, start, chunk=60, retries=3, pause=5):
    frames, failed = [], []
    for i in range(0, len(tickers), chunk):
        batch = tickers[i:i + chunk]
        for attempt in range(retries):
            try:
                df = yf.download(batch, start=start, auto_adjust=True, progress=False,
                                 threads=True, group_by="column")
                close = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]].rename(columns={"Close": batch[0]})
                frames.append(close)
                break
            except Exception as e:  # network hiccup / rate limit
                print(f"  batch {i // chunk + 1}: attempt {attempt + 1} failed ({e}); retrying")
                time.sleep(pause * (attempt + 1))
        print(f"  downloaded {min(i + chunk, len(tickers))}/{len(tickers)}")
        time.sleep(1)
    prices = pd.concat(frames, axis=1) if frames else pd.DataFrame()
    prices = prices.loc[:, ~prices.columns.duplicated()]
    for t in tickers:
        if t not in prices.columns or prices[t].notna().sum() < 20:
            failed.append(t)
    prices = prices.drop(columns=[t for t in failed if t in prices.columns])
    return prices.sort_index(), failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--years", type=float, default=6.0)
    ap.add_argument("--extra", default="extra_tickers.txt")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    info = load_sp500() + load_extra(args.extra)
    info += [{"ticker": t, "name": n, "sector": "ETF", "industry": n, "type": "etf"} for t, n in ETFS.items()]
    seen, uniq = set(), []
    for r in info:
        if r["ticker"] not in seen:
            seen.add(r["ticker"])
            uniq.append(r)
    tickers = [r["ticker"] for r in uniq]
    print(f"Universe: {len(tickers)} tickers")

    start = (pd.Timestamp.today() - pd.DateOffset(days=int(args.years * 365.25))).strftime("%Y-%m-%d")
    prices, failed = download(tickers, start)
    prices.index.name = "date"
    prices = prices.dropna(how="all")
    prices.round(4).to_csv(out / "prices.csv")

    pd.DataFrame([r for r in uniq if r["ticker"] in prices.columns]).to_csv(out / "tickers.csv", index=False)
    meta = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "first_date": str(prices.index.min().date()), "last_date": str(prices.index.max().date()),
        "n_tickers": int(prices.shape[1]), "n_days": int(prices.shape[0]), "failed": failed,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    if prices.shape[1] < 0.8 * len(tickers):
        raise SystemExit(f"Too many failures ({len(failed)}); not publishing.")


if __name__ == "__main__":
    main()
