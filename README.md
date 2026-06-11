
# Smart Money Streamlit Dashboard

This dashboard tracks:
- SEC Form 4 insider filings
- Politician trades via CSV upload
- Hedge fund / 13F trades via CSV upload
- Watchlist signal scoring

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `app.py` — main Streamlit dashboard
- `requirements.txt` — Python dependencies
- `sample_politician_trades.csv` — sample upload format
- `sample_13f_trades.csv` — sample upload format

## Current Watchlist

RKLB, KTOS, AVAV, BKSY, NVDA, AVGO, TSM, ANET, SMH, KORU

## Next upgrades

1. Parse SEC Form 4 XML for true insider buy/sell value.
2. Add Capitol Trades / Quiver / Senate disclosure data source.
3. Add 13F manager tracking for Berkshire, Pershing Square, Scion, Appaloosa, Duquesne, Coatue, Tiger Global.
4. Add email alerts.
5. Deploy on Streamlit Community Cloud.
