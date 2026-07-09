"""
Cart Abandonment Funnel Analysis - Visualization Layer
Reads from funnel.db (built from ecommerce_funnel_events.csv) and produces:
1. Overall funnel chart
2. Conversion rate by device (the key finding)
3. Conversion rate by traffic source
"""



import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

df = pd.read_csv("ecommerce_funnel_events.csv")
conn = sqlite3.connect("funnel.db")
df.to_sql("funnel_events", conn, if_exists="replace", index=False)
conn.close()
# ---------- 1. Overall funnel ----------
funnel_df = pd.read_sql_query("""
    SELECT event_stage, COUNT(DISTINCT session_id) AS sessions
    FROM funnel_events
    GROUP BY event_stage
""", conn)

stage_order = ["view_product", "add_to_cart", "checkout_start", "purchase"]
funnel_df["event_stage"] = pd.Categorical(funnel_df["event_stage"], categories=stage_order, ordered=True)
funnel_df = funnel_df.sort_values("event_stage")

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(funnel_df["event_stage"].astype(str), funnel_df["sessions"], color="#2E86AB")
ax.invert_yaxis()
ax.set_xlabel("Sessions")
ax.set_title("E-Commerce Funnel: Sessions at Each Stage", fontsize=13, fontweight="bold")
for bar, val in zip(bars, funnel_df["sessions"]):
    pct = val / funnel_df["sessions"].iloc[0] * 100
    ax.text(val + 150, bar.get_y() + bar.get_height()/2, f"{val:,} ({pct:.1f}%)",
            va="center", fontsize=10)
plt.tight_layout()
plt.savefig("chart_1_overall_funnel.png", dpi=150)
plt.close()

# ---------- 2. Conversion rate by device (KEY FINDING) ----------
device_df = pd.read_sql_query("""
    WITH session_stages AS (
        SELECT session_id, device,
            MAX(CASE WHEN event_stage = 'view_product' THEN 1 ELSE 0 END) AS viewed,
            MAX(CASE WHEN event_stage = 'checkout_start' THEN 1 ELSE 0 END) AS checked_out,
            MAX(CASE WHEN event_stage = 'purchase' THEN 1 ELSE 0 END) AS purchased
        FROM funnel_events GROUP BY session_id, device
    )
    SELECT device,
        SUM(viewed) AS sessions,
        ROUND(100.0 * SUM(purchased) / SUM(viewed), 2) AS overall_conv_pct,
        ROUND(100.0 * SUM(purchased) / NULLIF(SUM(checked_out), 0), 2) AS checkout_conv_pct
    FROM session_stages GROUP BY device
""", conn)

device_df = device_df.sort_values("checkout_conv_pct")

fig, ax = plt.subplots(figsize=(8, 5))
colors = ["#E63946" if d == "mobile" else "#2E86AB" for d in device_df["device"]]
bars = ax.bar(device_df["device"], device_df["checkout_conv_pct"], color=colors)
ax.set_ylabel("Checkout Completion Rate (%)")
ax.set_title("Checkout Conversion Rate by Device\n(Mobile lags significantly behind desktop)",
             fontsize=13, fontweight="bold")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
for bar, val in zip(bars, device_df["checkout_conv_pct"]):
    ax.text(bar.get_x() + bar.get_width()/2, val + 1.5, f"{val}%",
            ha="center", fontweight="bold")
plt.tight_layout()
plt.savefig("chart_2_device_conversion.png", dpi=150)
plt.close()

# ---------- 3. Conversion by traffic source ----------
source_df = pd.read_sql_query("""
    WITH session_stages AS (
        SELECT session_id, traffic_source,
            MAX(CASE WHEN event_stage = 'view_product' THEN 1 ELSE 0 END) AS viewed,
            MAX(CASE WHEN event_stage = 'purchase' THEN 1 ELSE 0 END) AS purchased
        FROM funnel_events GROUP BY session_id, traffic_source
    )
    SELECT traffic_source, ROUND(100.0*SUM(purchased)/SUM(viewed),2) AS conv_pct
    FROM session_stages GROUP BY traffic_source ORDER BY conv_pct DESC
""", conn)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(source_df["traffic_source"], source_df["conv_pct"], color="#457B9D")
ax.set_ylabel("Overall Conversion Rate (%)")
ax.set_title("Conversion Rate by Traffic Source", fontsize=13, fontweight="bold")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
plt.xticks(rotation=20)
for bar, val in zip(bars, source_df["conv_pct"]):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.3, f"{val}%", ha="center", fontweight="bold")
plt.tight_layout()
plt.savefig("chart_3_traffic_source_conversion.png", dpi=150)
plt.close()

conn.close()
print("Saved 3 charts: chart_1_overall_funnel.png, chart_2_device_conversion.png, chart_3_traffic_source_conversion.png")
