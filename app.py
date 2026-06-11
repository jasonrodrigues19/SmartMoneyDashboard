
import streamlit as st
import pandas as pd
import requests

@st.cache_data(ttl=3600)
def get_politician_trades():
    api_key = st.secrets.get("FMP_API_KEY", "")

    if not api_key:
        return pd.DataFrame()

    url = "https://financialmodelingprep.com/stable/house-disclosure-latest"
    params = {"apikey": api_key}

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df = df.rename(columns={
        "disclosureDate": "date",
        "representative": "politician",
        "symbol": "ticker",
        "assetDescription": "company",
        "transaction": "transaction",
        "amount": "amount_range"
    })

    keep = ["date", "politician", "ticker", "company", "transaction", "amount_range"]
    df = df[[c for c in keep if c in df.columns]]

    df["signal_type"] = "Politician trade"
    return df

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

st.set_page_config(page_title="Smart Money Dashboard", layout="wide")

WATCHLIST = ["RKLB", "KTOS", "AVAV", "BKSY", "NVDA", "AVGO", "TSM", "ANET", "SMH", "KORU"]

st.title("Smart Money Dashboard")
st.caption("Tracks insider buys, politician trades, 13F hedge fund filings, and watchlist matches.")

# -----------------------------
# Scoring Model
# -----------------------------
def score_signal(row):
    score = 0
    signal = str(row.get("signal_type", "")).lower()
    role = str(row.get("role", "")).lower()
    ticker = str(row.get("ticker", "")).upper()
    value = float(row.get("value", 0) or 0)

    if ticker in WATCHLIST:
        score += 20
    if "insider" in signal:
        score += 20
    if "ceo" in role:
        score += 30
    elif "cfo" in role:
        score += 25
    elif "director" in role:
        score += 15
    if value >= 250000:
        score += 20
    elif value >= 100000:
        score += 10
    if "politician" in signal:
        score += 10
    if "13f" in signal or "hedge" in signal:
        score += 15
    return min(score, 100)

# -----------------------------
# SEC Company Ticker Map
# -----------------------------
@st.cache_data(ttl=86400)
def load_sec_ticker_map():
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "SmartMoneyDashboard contact@example.com"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    rows = []
    for _, v in data.items():
        rows.append({
            "ticker": v["ticker"].upper(),
            "company": v["title"],
            "cik": str(v["cik_str"]).zfill(10)
        })
    return pd.DataFrame(rows)

def get_cik_for_ticker(ticker):
    tickers = load_sec_ticker_map()
    match = tickers[tickers["ticker"] == ticker.upper()]
    if match.empty:
        return None
    return match.iloc[0]["cik"]

# -----------------------------
# SEC Insider Form 4 Pull
# -----------------------------
@st.cache_data(ttl=3600)
def get_recent_form4_for_ticker(ticker):
    cik = get_cik_for_ticker(ticker)
    if not cik:
        return pd.DataFrame()

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": "SmartMoneyDashboard contact@example.com"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession = filings.get("accessionNumber", [])
    primary_doc = filings.get("primaryDocument", [])

    rows = []
    for form, date, acc, doc in zip(forms, dates, accession, primary_doc):
        if form == "4":
            rows.append({
                "date": date,
                "ticker": ticker.upper(),
                "company": data.get("name", ""),
                "signal_type": "Insider Form 4",
                "role": "Insider",
                "value": 0,
                "source": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}"
            })
    return pd.DataFrame(rows)

def load_insider_watchlist():
    frames = []
    for ticker in WATCHLIST:
        try:
            df = get_recent_form4_for_ticker(ticker)
            frames.append(df)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame(columns=["date", "ticker", "company", "signal_type", "role", "value", "source"])
    out = pd.concat(frames, ignore_index=True)
    out["score"] = out.apply(score_signal, axis=1)
    return out.sort_values(["date", "score"], ascending=[False, False])

# -----------------------------
# Manual upload sections
# -----------------------------
def upload_section(label, expected_cols):
    st.subheader(label)
    file = st.file_uploader(f"Upload CSV for {label}", type=["csv"], key=label)
    if file:
        df = pd.read_csv(file)
    else:
        df = pd.DataFrame(columns=expected_cols)
    return df

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Daily Signals", "Insider Buys", "Politicians", "Hedge Funds / 13F", "Watchlist"
])

with tab1:
    st.header("Top Daily Signals")
    insider_df = load_insider_watchlist()
    st.dataframe(insider_df.head(50), use_container_width=True)

    if not insider_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Signals found", len(insider_df))
        col2.metric("Watchlist matches", insider_df["ticker"].nunique())
        col3.metric("Highest score", int(insider_df["score"].max()))

with tab2:
    st.header("Insider Buys / Form 4")
    st.caption("Live SEC Form 4 feed for your watchlist. This currently lists Form 4 filings; transaction parsing can be added next.")
    insider_df = load_insider_watchlist()
    st.dataframe(insider_df, use_container_width=True)

with tab3:
    st.header("Politician Trades")

    try:
        pol = get_politician_trades()

        if pol.empty:
            st.warning("No politician trade data loaded. Check your API key.")
        else:
            pol["score"] = pol.apply(score_signal, axis=1)
            st.dataframe(pol, use_container_width=True)

    except Exception as e:
        st.error(f"Could not load politician trades: {e}")

with tab4:
    funds = upload_section("Hedge Funds / 13F", [
        "filing_date", "fund", "ticker", "company", "action", "value", "percent_portfolio", "source"
    ])
    if not funds.empty:
        funds["signal_type"] = "13F hedge fund"
        funds["score"] = funds.apply(score_signal, axis=1)
    st.dataframe(funds, use_container_width=True)

with tab5:
    st.header("Your Watchlist")
    watch = pd.DataFrame({
        "ticker": WATCHLIST,
        "theme": [
            "Space", "Defense", "Defense drones", "Space imaging", "AI/Semiconductors",
            "Semiconductors", "Semiconductors", "AI networking", "Semiconductor ETF", "Leveraged Korea"
        ]
    })
    st.dataframe(watch, use_container_width=True)

st.sidebar.title("Settings")
st.sidebar.write("Watchlist")
st.sidebar.write(", ".join(WATCHLIST))
st.sidebar.info("Next upgrade: parse actual Form 4 buy/sell amounts, add email alerts, and connect politician trade APIs.")
