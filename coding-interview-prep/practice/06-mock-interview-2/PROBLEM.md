# Mock Interview 2: E-Commerce Supply Chain Analytics

## ⏱ SET A 60-MINUTE TIMER BEFORE STARTING

## The Interviewer Prompt

> "An e-commerce company is having issues with inventory management and order fulfillment. 
> They want to understand which products are frequently out of stock, which warehouses 
> are underperforming, and predict demand patterns. Can you build a data pipeline to 
> support their operations team?"

---

## Phase 1: Discovery (0–10 min)

**Clarifying questions to ask**:
- How many products, warehouses, and orders?
- What's the time range?
- What does "underperforming" mean? (Late shipments? Low fill rate? High return rate?)
- Do they want real-time or daily batch analysis?
- Any specific KPIs they already track?
- Who consumes this — operations managers? executives? automated alerts?

**Suggested scope**:
- 1,000 products across 20 categories, 10 warehouses, 200,000 orders, 12 months
- Focus on: stockout frequency, fulfillment time, warehouse utilization
- Batch pipeline

## Phase 2: Generate Dataset (10–20 min)

**products** (1,000 rows)
- product_id, product_name, category, unit_price, weight_kg, supplier_id

**warehouses** (10 rows)
- warehouse_id, warehouse_name, city, state, capacity_units

**inventory** (10,000 rows — product × warehouse snapshots)
- inventory_id, product_id, warehouse_id, quantity_on_hand, reorder_point, snapshot_date
- Some products at 0 quantity (stockouts!)

**orders** (200,000 rows)
- order_id, customer_id, product_id, warehouse_id, order_date, quantity, 
  ship_date, delivery_date, order_status (completed/cancelled/returned)

**Realistic distributions**:
- 80/20 rule: 20% of products generate 80% of orders
- Some warehouses are slower (ship_date - order_date varies by warehouse)
- ~3% cancelled, ~5% returned
- Seasonal patterns: more orders in Nov-Dec (holiday)
- Some product-warehouse combos have 0 inventory (stockout scenarios)

## Phase 3: Build Pipeline (20–45 min)

### Silver
- Clean and validate all tables
- Calculate `fulfillment_days = DATEDIFF(ship_date, order_date)`
- Calculate `delivery_days = DATEDIFF(delivery_date, order_date)`
- Flag: orders where fulfillment_days > 5 (SLA breach)

### Gold — Build at least 2:

**gold.warehouse_performance** (one row per warehouse)
```
- warehouse_id, name, city
- total_orders_fulfilled
- avg_fulfillment_days, median_fulfillment_days
- sla_breach_count, sla_breach_rate
- cancellation_rate, return_rate
- current_utilization (total inventory / capacity)
- rank by performance
```

**gold.product_demand** (one row per product per month)
```
- product_id, name, category, month
- total_orders, total_quantity, total_revenue
- avg_inventory_on_hand
- stockout_days (days where quantity_on_hand = 0)
- month_over_month_growth
```

**gold.stockout_risk** (products at risk of stockout)
```
- Products where current inventory < reorder_point
- Products with high order velocity + low inventory
- Include: days_of_inventory_remaining (current_qty / avg_daily_demand)
```

## Phase 4: Discuss (45–60 min)

- How would you add real-time inventory tracking?
- How would you set up automated alerts for stockout risk?
- How would this pipeline integrate with a demand forecasting ML model?
- If they added 100 warehouses and 1M products, what changes?

---

## Self-Review After Completion

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Clarifying questions quality | | |
| Data generation (realistic?) | | |
| Silver cleaning thoroughness | | |
| Gold business value | | |
| Narration quality | | |
| Time management | | |
| Bug recovery (if any) | | |
| Total time | _____ min | Target: < 60 min |
