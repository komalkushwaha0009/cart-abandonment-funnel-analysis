"""
Generates a realistic e-commerce funnel dataset for cart abandonment analysis.
Simulates user sessions moving through: view_product -> add_to_cart -> checkout_start -> purchase
with realistic drop-off rates that vary by device type and traffic source.
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

N_SESSIONS = 15000

devices = ["mobile", "desktop", "tablet"]
device_weights = [0.58, 0.35, 0.07]  # mobile-heavy traffic, realistic for e-commerce

sources = ["organic_search", "paid_ads", "email", "direct", "social"]
source_weights = [0.35, 0.25, 0.15, 0.15, 0.10]

regions = ["North", "South", "East", "West"]

# Different drop-off dynamics by device (mobile checkout is historically worse)
# These are the probabilities of moving to the NEXT stage
stage_progression = {
    "mobile":  {"view_to_cart": 0.28, "cart_to_checkout": 0.55, "checkout_to_purchase": 0.62},
    "desktop": {"view_to_cart": 0.35, "cart_to_checkout": 0.68, "checkout_to_purchase": 0.80},
    "tablet":  {"view_to_cart": 0.30, "cart_to_checkout": 0.60, "checkout_to_purchase": 0.70},
}

# Paid ads traffic converts slightly worse at top of funnel (cold traffic)
source_modifier = {
    "organic_search": 1.05,
    "paid_ads": 0.85,
    "email": 1.20,
    "direct": 1.10,
    "social": 0.80,
}

avg_order_value_range = (15, 220)

rows = []
start_date = datetime(2025, 10, 1)

for i in range(N_SESSIONS):
    session_id = f"S{100000 + i}"
    user_id = f"U{random.randint(10000, 45000)}"  # some repeat users naturally
    device = np.random.choice(devices, p=device_weights)
    source = np.random.choice(sources, p=source_weights)
    region = random.choice(regions)
    session_date = start_date + timedelta(days=random.randint(0, 89),
                                           hours=random.randint(0, 23),
                                           minutes=random.randint(0, 59))

    probs = stage_progression[device]
    mod = source_modifier[source]

    # Stage 1: everyone views a product (that's what defines a session here)
    stage = "view_product"
    event_time = session_date
    rows.append([session_id, user_id, device, source, region, stage, event_time])

    if random.random() < min(probs["view_to_cart"] * mod, 0.95):
        stage = "add_to_cart"
        event_time += timedelta(minutes=random.randint(1, 8))
        rows.append([session_id, user_id, device, source, region, stage, event_time])

        if random.random() < min(probs["cart_to_checkout"] * mod, 0.95):
            stage = "checkout_start"
            event_time += timedelta(minutes=random.randint(1, 6))
            rows.append([session_id, user_id, device, source, region, stage, event_time])

            if random.random() < min(probs["checkout_to_purchase"] * mod, 0.95):
                stage = "purchase"
                event_time += timedelta(minutes=random.randint(1, 10))
                order_value = round(random.uniform(*avg_order_value_range), 2)
                rows.append([session_id, user_id, device, source, region, stage, event_time, order_value])

# Build dataframe - purchase rows have an extra order_value column
df_rows = []
for r in rows:
    if len(r) == 7:
        df_rows.append(r + [np.nan])
    else:
        df_rows.append(r)

df = pd.DataFrame(df_rows, columns=["session_id", "user_id", "device", "traffic_source",
                                     "region", "event_stage", "event_timestamp", "order_value"])

df = df.sort_values(["session_id", "event_timestamp"]).reset_index(drop=True)
df.to_csv("ecommerce_funnel_events.csv", index=False)

print(f"Generated {len(df)} events across {df['session_id'].nunique()} sessions")
print(df['event_stage'].value_counts())
print("\nSaved to ecommerce_funnel_events.csv")
