-- ============================================================
-- CART ABANDONMENT FUNNEL ANALYSIS
-- Dataset: funnel_events (one row per event per session)
-- Stages: view_product -> add_to_cart -> checkout_start -> purchase
-- ============================================================
create database CART_ABANDONMENT_FUNNEL_ANALYSIS;
use CART_ABANDONMENT_FUNNEL_ANALYSIS;

-- QUERY 1: Overall funnel conversion (how many sessions reach each stage
-- ------------------------------------------------------------

SELECT
    event_stage,
    COUNT(DISTINCT session_id) AS sessions,
    ROUND(100.0 * COUNT(DISTINCT session_id) /
        (SELECT COUNT(DISTINCT session_id) FROM ecommerce_funnel_events), 2) AS pct_of_total_sessions
FROM ecommerce_funnel_events
GROUP BY event_stage
ORDER BY
    CASE event_stage
        WHEN 'view_product' THEN 1
        WHEN 'add_to_cart' THEN 2
        WHEN 'checkout_start' THEN 3
        WHEN 'purchase' THEN 4
    END;


-- QUERY 2: Stage-to-stage drop-off rate (where do we lose the most people?)
-- ------------------------------------------------------------
-- This uses conditional aggregation to pivot stages into columns per session,
-- then calculates the % who moved from one stage to the next.

WITH session_stages AS (
    SELECT
        session_id,
        MAX(CASE WHEN event_stage = 'view_product' THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN event_stage = 'add_to_cart' THEN 1 ELSE 0 END) AS carted,
        MAX(CASE WHEN event_stage = 'checkout_start' THEN 1 ELSE 0 END) AS checked_out,
        MAX(CASE WHEN event_stage = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM ecommerce_funnel_events
    GROUP BY session_id
)
SELECT
    SUM(viewed) AS total_viewed,
    SUM(carted) AS total_carted,
    SUM(checked_out) AS total_checked_out,
    SUM(purchased) AS total_purchased,
    ROUND(100.0 * SUM(carted) / SUM(viewed), 2) AS view_to_cart_pct,
    ROUND(100.0 * SUM(checked_out) / NULLIF(SUM(carted), 0), 2) AS cart_to_checkout_pct,
    ROUND(100.0 * SUM(purchased) / NULLIF(SUM(checked_out), 0), 2) AS checkout_to_purchase_pct
FROM session_stages;


-- QUERY 3: Conversion rate broken down by DEVICE (the key business question)
-- ------------------------------------------------------------
WITH session_stages AS (
    SELECT
        session_id,
        device,
        MAX(CASE WHEN event_stage = 'view_product' THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN event_stage = 'add_to_cart' THEN 1 ELSE 0 END) AS carted,
        MAX(CASE WHEN event_stage = 'checkout_start' THEN 1 ELSE 0 END) AS checked_out,
        MAX(CASE WHEN event_stage = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM ecommerce_funnel_events
    GROUP BY session_id, device
)
SELECT
    device,
    SUM(viewed) AS sessions,
    SUM(purchased) AS purchases,
    ROUND(100.0 * SUM(purchased) / SUM(viewed), 2) AS overall_conversion_pct,
    ROUND(100.0 * SUM(carted) / SUM(viewed), 2) AS view_to_cart_pct,
    ROUND(100.0 * SUM(checked_out) / NULLIF(SUM(carted), 0), 2) AS cart_to_checkout_pct,
    ROUND(100.0 * SUM(purchased) / NULLIF(SUM(checked_out), 0), 2) AS checkout_to_purchase_pct
FROM session_stages
GROUP BY device
ORDER BY overall_conversion_pct;


-- QUERY 4: Revenue lost estimate — if checkout_to_purchase matched the BEST device's rate
-- ------------------------------------------------------------
-- This is the "so what" query: quantifies the opportunity in dollars.

WITH session_stages AS (
    SELECT
        session_id,
        device,
        MAX(CASE WHEN event_stage = 'checkout_start' THEN 1 ELSE 0 END) AS checked_out,
        MAX(CASE WHEN event_stage = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM ecommerce_funnel_events
    GROUP BY session_id, device
),
avg_order_value AS (
    SELECT AVG(order_value) AS aov FROM ecommerce_funnel_events WHERE event_stage = 'purchase'
),
device_checkout_rate AS (
    SELECT
        device,
        SUM(checked_out) AS checkouts,
        SUM(purchased) AS purchases,
        1.0 * SUM(purchased) / NULLIF(SUM(checked_out), 0) AS checkout_conv_rate
    FROM session_stages
    GROUP BY device
)
SELECT
    device,
    checkouts,
    purchases,
    ROUND(checkout_conv_rate * 100, 2) AS current_checkout_conv_pct,
    ROUND((SELECT MAX(checkout_conv_rate) FROM device_checkout_rate) * 100, 2) AS best_device_conv_pct,
    ROUND((checkouts * (SELECT MAX(checkout_conv_rate) FROM device_checkout_rate)) - purchases, 0) AS additional_purchases_possible,
    ROUND(((checkouts * (SELECT MAX(checkout_conv_rate) FROM device_checkout_rate)) - purchases) *
        (SELECT aov FROM avg_order_value), 2) AS estimated_revenue_left_on_table
FROM device_checkout_rate
ORDER BY estimated_revenue_left_on_table DESC;


-- QUERY 5: Conversion by traffic source (where should marketing spend focus?)
-- ------------------------------------------------------------
WITH session_stages AS (
    SELECT
        session_id,
        traffic_source,
        MAX(CASE WHEN event_stage = 'view_product' THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN event_stage = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM ecommerce_funnel_events
    GROUP BY session_id, traffic_source
)
SELECT
    traffic_source,
    SUM(viewed) AS sessions,
    SUM(purchased) AS purchases,
    ROUND(100.0 * SUM(purchased) / SUM(viewed), 2) AS conversion_pct
FROM session_stages
GROUP BY traffic_source
ORDER BY conversion_pct DESC;


-- QUERY 6: Time-to-purchase — how long does a successful session take end-to-end?
-- ------------------------------------------------------------
WITH session_times AS (
    SELECT
        session_id,
        MIN(event_timestamp) AS first_event,
        MAX(event_timestamp) AS last_event
    FROM ecommerce_funnel_events
    WHERE session_id IN (
        SELECT session_id FROM ecommerce_funnel_events WHERE event_stage = 'purchase'
    )
    GROUP BY session_id
)
SELECT
    ROUND(AVG(DATEDIFF(MINUTE, first_event, last_event) * 1.0), 2) AS avg_minutes_to_purchase,
    MIN(DATEDIFF(MINUTE, first_event, last_event)) AS min_minutes,
    MAX(DATEDIFF(MINUTE, first_event, last_event)) AS max_minutes
FROM session_times;
