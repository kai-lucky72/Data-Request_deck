#!/usr/bin/env python3
"""Generate a large, CLEAN episodes CSV for load-testing your import and analytics queries.

    python3 generate_episodes.py 200000 > episodes_large.csv

Rows are valid and unique; IDs start at EP-100000 so they do not collide with episodes.csv.
"""
import csv, random, sys
from datetime import datetime, timedelta

n = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
random.seed(1)
robots = ["arm-01", "arm-02", "arm-03", "mobile-01", "humanoid-01"]
tasks = ["pick cup", "place cup on shelf", "open drawer", "fold towel", "pour water", "stack blocks", "wipe table"]
ops = ["Aline", "Eric", "Diane", "Patrick", "Jeanne", "Kevin"]
quality = ["good"] * 6 + ["usable"] * 3 + ["bad"]
start = datetime(2025, 9, 1, 8, 0)
w = csv.writer(sys.stdout)
w.writerow(["episode_id", "robot_id", "task_name", "recorded_at", "duration_seconds", "operator_name", "quality"])
for i in range(n):
    rec = start + timedelta(minutes=random.randint(0, 365 * 24 * 60))
    w.writerow([f"EP-{100000 + i}", random.choice(robots), random.choice(tasks),
                rec.strftime("%Y-%m-%dT%H:%M:%S"), random.randint(8, 120),
                random.choice(ops), random.choice(quality)])
