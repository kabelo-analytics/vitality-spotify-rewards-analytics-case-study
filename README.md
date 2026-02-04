# Vitality Spotify Rewards Analytics Case Study (Synthetic)

A portfolio-grade **product analytics** case study simulating an **opt-in** partnership between a Vitality-style rewards program and **Spotify Africa**.

This repo demonstrates:
- warehouse-style data modeling (dimensions + facts)
- experiment-style pilot window (4 weeks pre, 8 weeks post)
- raw → processed pipeline
- reproducible report figures (PNG)
- Power BI-friendly tables

> **All data is synthetic.** It illustrates analytics methods and system design only.

## Run

```bash
pip install -r requirements.txt
python src/run_all.py
```

## Data layout

### `data/raw/` (source-of-truth tables)
Dimensions: `dim_member`, `dim_week`, `dim_month`, `dim_reward`, `dim_content_category`  
Facts: `fact_activity_weekly`, `fact_spotify_weekly`, `fact_campaign_exposure`, `fact_reward_events`, `fact_retention_monthly`

### `data/processed/` (analysis-ready)
- `member_week_pilot.csv` / `.parquet`
- `member_summary.csv` / `.parquet`

### `reports/figures/`
Auto-generated PNGs for the case study report.

## Stakeholders
- Product Owner (engagement / habit loops)
- Partnerships Lead (ROI & economics)
- Analytics Lead (measurement & bias control)
- Legal/Privacy (opt-in model)
- Marketing (campaign execution)
