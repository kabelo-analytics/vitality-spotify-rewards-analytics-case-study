#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def main(outdir: Path) -> None:
    proc = outdir / "data" / "processed"
    figs = outdir / "reports" / "figures"
    figs.mkdir(parents=True, exist_ok=True)

    mw = pd.read_csv(proc/"member_week_pilot.csv")
    ms = pd.read_csv(proc/"member_summary.csv")

    plt.figure()
    mw.groupby(["period","treated"])["vitality_points"].mean().unstack().plot(kind="bar")
    plt.ylabel("Avg weekly vitality points")
    plt.tight_layout()
    plt.savefig(figs/"avg_points_pre_post_treated.png", dpi=160)
    plt.close()

    plt.figure()
    ms[ms["eligible"]==1].groupby("treated")["points_uplift"].mean().plot(kind="bar")
    plt.ylabel("Avg points uplift (post - pre)")
    plt.tight_layout()
    plt.savefig(figs/"points_uplift_treated_vs_not.png", dpi=160)
    plt.close()

    plt.figure()
    ms.groupby("treated")["churn_flag"].mean().plot(kind="bar")
    plt.ylabel("Churn rate (final month)")
    plt.tight_layout()
    plt.savefig(figs/"churn_rate_by_treated.png", dpi=160)
    plt.close()

    plt.figure()
    ms.sample(min(4000, len(ms)), random_state=753).plot.scatter(x="listen_uplift", y="points_uplift")
    plt.xlabel("Listening uplift (minutes)")
    plt.ylabel("Points uplift")
    plt.tight_layout()
    plt.savefig(figs/"listen_uplift_vs_points_uplift_scatter.png", dpi=160)
    plt.close()

    print(f"Wrote figures to: {figs.resolve()}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=Path("."))
    args = ap.parse_args()
    main(args.outdir)
