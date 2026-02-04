#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def main(outdir: Path, pilot_start_week: int = 25) -> None:
    raw = outdir / "data" / "raw"
    proc = outdir / "data" / "processed"
    proc.mkdir(parents=True, exist_ok=True)

    dim_member = pd.read_csv(raw/"dim_member.csv")
    dim_week = pd.read_csv(raw/"dim_week.csv")
    fact_activity = pd.read_csv(raw/"fact_activity_weekly.csv")
    fact_spotify = pd.read_csv(raw/"fact_spotify_weekly.csv")
    fact_retention = pd.read_csv(raw/"fact_retention_monthly.csv")

    pre_weeks = list(range(pilot_start_week-4, pilot_start_week))
    post_weeks = list(range(pilot_start_week, pilot_start_week+8))
    focus_weeks = pre_weeks + post_weeks

    act_focus = fact_activity[fact_activity["week_id"].isin(focus_weeks)].copy()
    spot_focus = fact_spotify[fact_spotify["week_id"].isin(focus_weeks)].copy()

    spot_agg = spot_focus.groupby(["member_id","week_id"]).agg({
        "listening_minutes":"sum",
        "sessions":"sum",
        "skip_rate":"mean",
        "genre_share_amapiano":"mean",
        "genre_share_afrohouse":"mean",
        "genre_share_hiphop":"mean",
        "genre_share_pop":"mean",
        "genre_share_gospel":"mean",
    }).reset_index()

    mw = act_focus.merge(spot_agg, on=["member_id","week_id"], how="left")
    mw.fillna({
        "listening_minutes":0.0,
        "sessions":0,
        "genre_share_amapiano":0.0,
        "genre_share_afrohouse":0.0,
        "genre_share_hiphop":0.0,
        "genre_share_pop":0.0,
        "genre_share_gospel":0.0,
    }, inplace=True)

    keep = ["member_id","age_band","region","plan_type","digital_affinity_score","device_type",
            "baseline_propensity","treatment_eligible","reward_adopted","adopt_week_id"]
    mw = mw.merge(dim_member[keep], on="member_id", how="left")
    mw = mw.merge(dim_week[["week_id","week_start_date","month","year","quarter"]], on="week_id", how="left")

    mw["period"] = np.where(mw["week_id"] < pilot_start_week, "pre", "post")
    mw["eligible"] = mw["treatment_eligible"]
    mw["treated"] = mw["reward_adopted"]
    mw["steps_k"] = (mw["steps"]/1000).round(2)

    def period_mean(s: pd.Series, mw_df: pd.DataFrame, period: str) -> float:
        return s[mw_df.loc[s.index, "period"] == period].mean()

    ms = mw.groupby("member_id").agg(
        age_band=("age_band","first"),
        region=("region","first"),
        plan_type=("plan_type","first"),
        digital_affinity_score=("digital_affinity_score","first"),
        baseline_propensity=("baseline_propensity","first"),
        eligible=("eligible","first"),
        treated=("treated","first"),
        avg_points_pre=("vitality_points", lambda s: period_mean(s, mw, "pre")),
        avg_points_post=("vitality_points", lambda s: period_mean(s, mw, "post")),
        avg_steps_pre=("steps_k", lambda s: period_mean(s, mw, "pre")),
        avg_steps_post=("steps_k", lambda s: period_mean(s, mw, "post")),
        avg_listen_pre=("listening_minutes", lambda s: period_mean(s, mw, "pre")),
        avg_listen_post=("listening_minutes", lambda s: period_mean(s, mw, "post")),
    ).reset_index()

    ms["points_uplift"] = (ms["avg_points_post"] - ms["avg_points_pre"]).round(2)
    ms["steps_uplift_k"] = (ms["avg_steps_post"] - ms["avg_steps_pre"]).round(2)
    ms["listen_uplift"] = (ms["avg_listen_post"] - ms["avg_listen_pre"]).round(2)

    last = fact_retention[fact_retention["month_id"]==fact_retention["month_id"].max()][["member_id","active_flag","churn_flag","reason_code"]]
    ms = ms.merge(last, on="member_id", how="left")

    mw.to_csv(proc/"member_week_pilot.csv", index=False)
    ms.to_csv(proc/"member_summary.csv", index=False)

    try:
        mw.to_parquet(proc/"member_week_pilot.parquet", index=False)
        ms.to_parquet(proc/"member_summary.parquet", index=False)
    except Exception:
        pass

    print(f"Wrote processed tables to: {proc.resolve()}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=Path("."))
    ap.add_argument("--pilot_start_week", type=int, default=25)
    args = ap.parse_args()
    main(args.outdir, args.pilot_start_week)
