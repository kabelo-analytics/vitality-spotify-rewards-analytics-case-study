#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_SEED = 753

def main(outdir: Path, n_members: int, n_weeks: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    raw = outdir / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    pilot_start = 25
    pre_weeks = list(range(pilot_start-4, pilot_start))
    post_weeks = list(range(pilot_start, pilot_start+8))

    regions = ["Gauteng","Western Cape","KwaZulu-Natal","Eastern Cape","Free State","Mpumalanga","Limpopo","North West","Northern Cape"]
    age_bands = ["18-24","25-34","35-44","45-54","55-64","65+"]
    plan_types = ["Essential","Classic","Plus","Executive"]
    device_types = ["Wearable","Phone","GymScanner","Mixed"]
    channels = ["app","email","sms","social"]
    reward_types = ["music_subscription_discount","premium_trial","playlist_challenge_bonus"]

    member_ids = np.arange(1, n_members+1)
    age_band = rng.choice(age_bands, size=n_members, p=[0.10,0.30,0.25,0.18,0.12,0.05])
    region = rng.choice(regions, size=n_members, p=[0.30,0.14,0.20,0.10,0.06,0.06,0.06,0.05,0.03])
    plan_type = rng.choice(plan_types, size=n_members, p=[0.35,0.35,0.20,0.10])
    join_date = (pd.Timestamp("2026-02-04") - pd.to_timedelta(rng.integers(30, 365*6, size=n_members), unit="D")).date.astype(str)

    digital_affinity = np.clip(rng.normal(0,1,size=n_members), -2.5, 2.5)
    digital_affinity_score = (((digital_affinity - digital_affinity.min())/(digital_affinity.max()-digital_affinity.min()))*100).round().astype(int)
    device_type = rng.choice(device_types, size=n_members, p=[0.35,0.25,0.10,0.30])

    age_effect = pd.Series(age_band).map({"18-24":0.25,"25-34":0.20,"35-44":0.10,"45-54":0.00,"55-64":-0.10,"65+":-0.25}).values
    plan_effect = pd.Series(plan_type).map({"Essential":-0.05,"Classic":0.00,"Plus":0.05,"Executive":0.08}).values
    region_effect = pd.Series(region).map({
        "Gauteng":0.05,"Western Cape":0.06,"KwaZulu-Natal":0.02,"Eastern Cape":-0.02,"Free State":-0.01,
        "Mpumalanga":-0.01,"Limpopo":-0.02,"North West":-0.01,"Northern Cape":-0.03
    }).values
    baseline_propensity = np.clip(rng.normal(0,1,size=n_members) + age_effect + plan_effect + region_effect + digital_affinity*0.15, -3, 3)

    dim_member = pd.DataFrame({
        "member_id": member_ids,
        "age_band": age_band,
        "region": region,
        "plan_type": plan_type,
        "join_date": join_date,
        "digital_affinity_score": digital_affinity_score,
        "device_type": device_type,
        "baseline_propensity": baseline_propensity.round(3),
    })
    dim_member["stratum"] = dim_member["age_band"] + "|" + dim_member["plan_type"]

    # Time dimensions
    start_week = pd.Timestamp("2025-05-05")
    weeks = pd.date_range(start_week, periods=n_weeks, freq="W-MON")
    dim_week = pd.DataFrame({
        "week_id": np.arange(1, n_weeks+1),
        "week_start_date": weeks.date.astype(str),
        "month": weeks.month,
        "year": weeks.year,
        "quarter": ((weeks.month-1)//3 + 1).astype(int)
    })
    months = pd.date_range("2025-05-01", periods=12, freq="MS")
    dim_month = pd.DataFrame({
        "month_id": np.arange(1, len(months)+1),
        "month_start": months.date.astype(str),
        "month": months.month,
        "year": months.year
    })

    dim_reward = pd.DataFrame({
        "reward_id":[1,2,3],
        "partner":["Spotify Africa"]*3,
        "reward_type": reward_types,
        "reward_tier":["Silver","Gold","Gold"],
        "points_cost":[150,300,100]
    })
    dim_content_category = pd.DataFrame({
        "category_id":[1,2,3,4],
        "content_category":["music","podcast","audiobook","mixed"]
    })

    # Campaign exposure (sparse)
    age_young = pd.Series(age_band).isin(["18-24","25-34"]).astype(int).values
    exp_base = np.clip(0.08 + (digital_affinity_score/100)*0.18 + age_young*0.05, 0.05, 0.35)

    exp_rows=[]
    for w in range(1, n_weeks+1):
        seasonal = 1.0 + 0.10*np.sin(2*np.pi*(w/52.0)) + 0.05*np.cos(2*np.pi*(w/26.0))
        prob = np.clip(exp_base*seasonal, 0.02, 0.40)
        exposed = rng.random(n_members) < prob
        ch = rng.choice(channels, size=n_members, p=[0.55,0.25,0.10,0.10])
        impressions = np.where(exposed, rng.integers(1,12,size=n_members), 0)
        clicks = np.where(exposed, rng.binomial(n=np.clip(impressions,0,10), p=np.clip(0.03 + (digital_affinity_score/100)*0.06, 0.02, 0.12)), 0)
        exp_rows.append(pd.DataFrame({
            "member_id": member_ids[exposed],
            "week_id": w,
            "channel": ch[exposed],
            "impressions": impressions[exposed],
            "clicks": clicks[exposed],
        }))
    fact_campaign_exposure = pd.concat(exp_rows, ignore_index=True)

    # Eligibility: stratified randomization
    eligible = np.zeros(n_members, dtype=int)
    for _, idx in dim_member.groupby("stratum").groups.items():
        idx = np.array(list(idx))
        eligible[idx] = rng.binomial(1, 0.5, size=len(idx))
    dim_member["treatment_eligible"] = eligible

    # Adoption depends on affinity + exposure (not outcomes)
    exp_post = fact_campaign_exposure[fact_campaign_exposure["week_id"].isin(post_weeks)].groupby("member_id")["impressions"].sum()
    dim_member = dim_member.merge(exp_post.rename("impressions_post8w"), on="member_id", how="left")
    dim_member["impressions_post8w"] = dim_member["impressions_post8w"].fillna(0).astype(int)

    z = (-2.0
         + 0.02*dim_member["digital_affinity_score"].values
         + 0.015*dim_member["impressions_post8w"].values
         + 0.35*age_young
         + 0.10*pd.Series(plan_type).isin(["Plus","Executive"]).astype(int).values)
    p_adopt = np.clip(1/(1+np.exp(-z)), 0.01, 0.75)
    dim_member["reward_adopted"] = ((rng.random(n_members) < p_adopt) & (dim_member["treatment_eligible"].values==1)).astype(int)

    # Reward events
    pilot_date0 = pd.Timestamp(dim_week.loc[dim_week.week_id==pilot_start,"week_start_date"].iloc[0])
    events=[]
    eligible_members = dim_member.loc[dim_member["treatment_eligible"]==1, "member_id"].values
    events.append(pd.DataFrame({
        "member_id": eligible_members,
        "event_date": str(pilot_date0.date()),
        "reward_id": 1,
        "event_type":"eligible",
        "points_spent":0
    }))
    adopters = dim_member.loc[dim_member["reward_adopted"]==1, "member_id"].values
    adopt_dates = pilot_date0 + pd.to_timedelta(rng.integers(0,14,size=len(adopters)), unit="D")
    events.append(pd.DataFrame({
        "member_id": adopters,
        "event_date": adopt_dates.date.astype(str),
        "reward_id": rng.choice([1,2,3], size=len(adopters), p=[0.55,0.30,0.15]),
        "event_type":"adopted",
        "points_spent":0
    }))
    redeem_prob = np.clip(0.35 + 0.003*dim_member.set_index("member_id").loc[adopters,"digital_affinity_score"].values, 0.35, 0.70)
    redeemed = adopters[rng.random(len(adopters)) < redeem_prob]
    redeem_dates = pilot_date0 + pd.to_timedelta(rng.integers(7,56,size=len(redeemed)), unit="D")
    redeem_reward = rng.choice([1,2,3], size=len(redeemed), p=[0.35,0.45,0.20])
    points_spent = dim_reward.set_index("reward_id").loc[redeem_reward,"points_cost"].values
    events.append(pd.DataFrame({
        "member_id": redeemed,
        "event_date": redeem_dates.date.astype(str),
        "reward_id": redeem_reward,
        "event_type":"redeemed",
        "points_spent":points_spent
    }))
    fact_reward_events = pd.concat(events, ignore_index=True)

    # Spotify latent users + weekly (sparse)
    spotify_user_latent = rng.random(n_members) < np.clip(0.35 + 0.002*dim_member["digital_affinity_score"].values + 0.10*age_young, 0.10, 0.85)
    dim_member["spotify_user_latent"] = spotify_user_latent.astype(int)
    base_minutes = np.clip(40 + 2.2*dim_member["digital_affinity_score"].values + 18*age_young + rng.normal(0,25,size=n_members), 0, 900)

    adopt_evt = fact_reward_events[fact_reward_events["event_type"]=="adopted"].copy()
    adopt_evt["event_date"] = pd.to_datetime(adopt_evt["event_date"])
    week_starts = pd.to_datetime(dim_week["week_start_date"])
    adopt_evt["week_id"] = adopt_evt["event_date"].apply(lambda d: int((week_starts<=d).sum())).clip(1,n_weeks)
    dim_member = dim_member.merge(adopt_evt.groupby("member_id")["week_id"].min().rename("adopt_week_id"), on="member_id", how="left")

    platform_categories=["music","podcast","audiobook","mixed"]
    spotify_rows=[]
    for w in range(1, n_weeks+1):
        active_prob = np.where(dim_member["spotify_user_latent"].values==1, 0.55, 0.10)
        active_prob = np.where(dim_member["reward_adopted"].values==1, np.maximum(active_prob, 0.70), active_prob)
        active = rng.random(n_members) < active_prob

        seasonal = 1.0 + 0.08*np.sin(2*np.pi*(w/52.0))
        minutes = base_minutes*seasonal + rng.normal(0,35,size=n_members)
        aw = dim_member["adopt_week_id"].fillna(10**9).values
        weeks_since = w - aw
        ramp = np.clip(weeks_since/4.0, 0, 1)
        minutes = np.clip(minutes*(1 + np.where(weeks_since>=0, 0.08*ramp, 0.0)), 0, 1200)

        sessions = np.maximum(0, (minutes/25 + rng.normal(0,1.5,size=n_members))).round().astype(int)
        skip_rate = np.clip(rng.normal(0.22,0.07,size=n_members) - 0.0008*dim_member["digital_affinity_score"].values, 0.05, 0.60)
        category = rng.choice(platform_categories, size=n_members, p=[0.72,0.18,0.03,0.07])

        amap_boost = (pd.Series(region).isin(["Gauteng","KwaZulu-Natal"]).astype(int).values*0.10 + age_young*0.08)
        amap_share = np.clip(rng.beta(2,6,size=n_members) + amap_boost, 0, 0.85)
        afro_share = np.clip(rng.beta(2,8,size=n_members) + pd.Series(region).isin(["Western Cape"]).astype(int).values*0.06, 0, 0.70)
        hiphop_share = np.clip(rng.beta(2,7,size=n_members) + pd.Series(age_band).isin(["18-24"]).astype(int).values*0.05, 0, 0.70)
        pop_share = np.clip(rng.beta(3,7,size=n_members), 0, 0.75)
        gospel_share = np.clip(rng.beta(2,10,size=n_members) + pd.Series(age_band).isin(["55-64","65+"]).astype(int).values*0.08, 0, 0.70)
        total = amap_share+afro_share+hiphop_share+pop_share+gospel_share
        scale = np.where(total>0.95, 0.95/total, 1.0)
        amap_share*=scale; afro_share*=scale; hiphop_share*=scale; pop_share*=scale; gospel_share*=scale

        mask = active
        spotify_rows.append(pd.DataFrame({
            "member_id": member_ids[mask],
            "week_id": w,
            "listening_minutes": minutes[mask].round(1),
            "sessions": sessions[mask],
            "skip_rate": skip_rate[mask].round(3),
            "content_category": category[mask],
            "genre_share_amapiano": amap_share[mask].round(3),
            "genre_share_afrohouse": afro_share[mask].round(3),
            "genre_share_hiphop": hiphop_share[mask].round(3),
            "genre_share_pop": pop_share[mask].round(3),
            "genre_share_gospel": gospel_share[mask].round(3),
        }))
    fact_spotify_weekly = pd.concat(spotify_rows, ignore_index=True)

    # Activity weekly (dense with missingness)
    base_steps = np.clip(6500 + 1200*baseline_propensity + rng.normal(0,1800,size=n_members), 800, 22000)
    base_workouts = np.clip(1.2 + 0.6*baseline_propensity + rng.normal(0,0.8,size=n_members), 0, 9)
    base_gym = np.clip(0.8 + 0.4*baseline_propensity + rng.normal(0,0.6,size=n_members), 0, 8)
    miss_p = pd.Series(device_type).map({"Wearable":0.05,"Phone":0.10,"GymScanner":0.07,"Mixed":0.06}).values

    act_rows=[]
    for w in range(1, n_weeks+1):
        seasonal = 1.0 + 0.10*np.cos(2*np.pi*(w/52.0))
        steps = base_steps*seasonal + rng.normal(0,1400,size=n_members)
        workouts = base_workouts*seasonal + rng.normal(0,0.6,size=n_members)
        gym_visits = base_gym*seasonal + rng.normal(0,0.5,size=n_members)

        missing = rng.random(n_members) < miss_p
        steps = np.where(missing, np.nan, np.clip(steps, 0, 30000))
        workouts = np.where(missing, np.nan, np.clip(workouts, 0, 14))
        gym_visits = np.where(missing, np.nan, np.clip(gym_visits, 0, 14))

        aw = dim_member["adopt_week_id"].fillna(10**9).values
        weeks_since = w - aw
        ramp = np.clip(weeks_since/3.0, 0, 1)
        uplift = np.where(weeks_since>=0, 0.04*ramp, 0.0)
        steps = steps*(1+uplift); workouts = workouts*(1+uplift); gym_visits = gym_visits*(1+uplift)

        points = (np.nan_to_num(steps)/1000*8 + np.nan_to_num(workouts)*35 + np.nan_to_num(gym_visits)*20)
        bonus = rng.binomial(1, 0.08 + 0.001*digital_affinity_score) * rng.integers(20,120,size=n_members)
        points = np.clip(points + bonus, 0, 1800).round().astype(int)

        act_rows.append(pd.DataFrame({
            "member_id": member_ids,
            "week_id": w,
            "steps": np.round(steps,0),
            "workouts_logged": np.round(workouts,1),
            "gym_visits": np.round(gym_visits,1),
            "vitality_points": points
        }))
    fact_activity_weekly = pd.concat(act_rows, ignore_index=True)

    # Retention monthly (simple)
    post_points = fact_activity_weekly[fact_activity_weekly["week_id"].isin(post_weeks)].groupby("member_id")["vitality_points"].mean()
    eng = dim_member.set_index("member_id").join(post_points.rename("points_post"), how="left").fillna(0)
    age_churn = pd.Series(age_band).map({"18-24":0.06,"25-34":0.05,"35-44":0.04,"45-54":0.03,"55-64":0.025,"65+":0.02}).values
    plan_churn = pd.Series(plan_type).map({"Essential":0.05,"Classic":0.04,"Plus":0.03,"Executive":0.025}).values
    eng_effect = np.clip(-0.00003*eng["points_post"].values, -0.05, 0)
    adopt_effect = -0.006*dim_member["reward_adopted"].values
    base_churn = np.clip(age_churn + plan_churn + 0.02 + eng_effect + adopt_effect, 0.01, 0.16)

    ret_rows=[]
    active=np.ones(n_members, dtype=int)
    for m in range(1, 13):
        churned = (rng.random(n_members) < base_churn) & (active==1)
        active = np.where(churned, 0, active)
        reason = np.where(churned, rng.choice(["price_sensitivity","low_engagement","moved_provider","unknown"], size=n_members, p=[0.35,0.30,0.15,0.20]), None)
        ret_rows.append(pd.DataFrame({
            "member_id": member_ids,
            "month_id": m,
            "active_flag": active,
            "churn_flag": churned.astype(int),
            "reason_code": reason
        }))
    fact_retention_monthly = pd.concat(ret_rows, ignore_index=True)

    # Write CSVs
    dim_member.drop(columns=["stratum"]).to_csv(raw/"dim_member.csv", index=False)
    dim_week.to_csv(raw/"dim_week.csv", index=False)
    dim_month.to_csv(raw/"dim_month.csv", index=False)
    dim_reward.to_csv(raw/"dim_reward.csv", index=False)
    dim_content_category.to_csv(raw/"dim_content_category.csv", index=False)

    fact_activity_weekly.to_csv(raw/"fact_activity_weekly.csv", index=False)
    fact_spotify_weekly.to_csv(raw/"fact_spotify_weekly.csv", index=False)
    fact_campaign_exposure.to_csv(raw/"fact_campaign_exposure.csv", index=False)
    fact_reward_events.to_csv(raw/"fact_reward_events.csv", index=False)
    fact_retention_monthly.to_csv(raw/"fact_retention_monthly.csv", index=False)

    print(f"Wrote raw tables to: {raw.resolve()}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=Path("."))
    ap.add_argument("--n_members", type=int, default=8000)
    ap.add_argument("--n_weeks", type=int, default=52)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()
    main(args.outdir, args.n_members, args.n_weeks, args.seed)
