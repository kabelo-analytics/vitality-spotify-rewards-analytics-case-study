# Vitality × Spotify Rewards — Product Analytics Case Study

This case study models an opt-in partnership between a Vitality-style rewards programme and Spotify Africa — evaluating whether music engagement rewards drive measurable improvements in physical activity and member retention.

Product analytics case study examining whether a Spotify rewards integration drives activity and retention improvements in a wellness programme. Pilot measurement design, warehouse-style data model, Python pipeline. Synthetic dataset.

This repo demonstrates:
- Warehouse-style data modelling (dimensions + facts)
- Experiment-style pilot window (4 weeks pre, 8 weeks post)
- Raw to processed pipeline
- Reproducible report figures (PNG)
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
- Product Owner (engagement and habit loop design)
- Partnerships Lead (commercial ROI)
- Analytics Lead (measurement integrity)
- Marketing (segment targeting)

---

Built by Kabelo Makua · kabelo-analytics · https://km-webdvlpr.github.io/III.IV/
