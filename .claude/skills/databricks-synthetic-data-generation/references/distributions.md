# Distribution Patterns for Synthetic Data

## Table of Contents

- [Non-Linear Distributions](#non-linear-distributions)
- [Distribution Selection Guide](#distribution-selection-guide)
- [Time-Based Patterns](#time-based-patterns)
- [Row Coherence](#row-coherence)

## Non-Linear Distributions

**Never use uniform distributions** - real data is rarely uniform.

```python
# BAD - Uniform (unrealistic)
prices = np.random.uniform(10, 1000, size=N_ORDERS)

# GOOD - Log-normal (realistic for prices, salaries, order amounts)
prices = np.random.lognormal(mean=4.5, sigma=0.8, size=N_ORDERS)

# GOOD - Pareto/power law (popularity, wealth, page views)
popularity = (np.random.pareto(a=2.5, size=N_PRODUCTS) + 1) * 10

# GOOD - Exponential (time between events, resolution time)
resolution_hours = np.random.exponential(scale=24, size=N_TICKETS)

# GOOD - Weighted categorical
regions = np.random.choice(
    ['North', 'South', 'East', 'West'],
    size=N_CUSTOMERS,
    p=[0.40, 0.25, 0.20, 0.15]
)
```

## Distribution Selection Guide

| Data Type | Distribution | numpy Function | Example Parameters |
|-----------|-------------|----------------|-------------------|
| Prices, salaries, order amounts | Log-normal | `np.random.lognormal(mean, sigma, size)` | mean=4.5, sigma=0.8 |
| Popularity, wealth, page views | Pareto/Power law | `(np.random.pareto(a, size) + 1) * scale` | a=2.5, scale=10 |
| Time between events | Exponential | `np.random.exponential(scale, size)` | scale=24 (hours) |
| Categories with known ratios | Weighted choice | `np.random.choice(items, size, p=weights)` | p=[0.4, 0.3, 0.2, 0.1] |
| Counts (orders per customer) | Poisson | `np.random.poisson(lam, size)` | lam=5 |
| Scores, ratings | Beta (scaled) | `np.random.beta(a, b, size) * scale` | a=2, b=5, scale=5 |
| Popularity ranking (Zipf) | Zipf | `np.random.zipf(a, size)` | a=2.0 |
| Seasonal multipliers | Sinusoidal | `1 + amplitude * np.sin(2*pi*day/365)` | amplitude=0.3 |

### Zipf Distribution (Power Law for Rankings)

Zipf is ideal for "the rich get richer" patterns - a few items dominate, most are rare:

```python
# Product popularity: top 10% of products get ~80% of orders
product_ranks = np.random.zipf(a=2.0, size=N_ORDERS)
# Clip to valid product range
product_indices = np.clip(product_ranks, 1, N_PRODUCTS) - 1
product_ids = [f"PROD-{idx:05d}" for idx in product_indices]
```

### Log-Normal for Financial Values

Log-normal naturally produces the "most values small, some very large" pattern seen in financial data:

```python
# Enterprise orders: median ~$1,100, some up to $50K+
enterprise_amounts = np.random.lognormal(mean=7, sigma=0.8, size=n)

# Pro tier: median ~$150, max ~$5K
pro_amounts = np.random.lognormal(mean=5, sigma=0.7, size=n)

# Free tier: median ~$33, max ~$500
free_amounts = np.random.lognormal(mean=3.5, sigma=0.6, size=n)
```

### Seasonal Patterns with Sinusoidal Functions

```python
import math

def seasonal_multiplier(date, peak_month=12, amplitude=0.3):
    """Peak in December (peak_month=12), trough in June."""
    day_of_year = date.timetuple().tm_yday
    # Shift so peak aligns with peak_month
    phase = 2 * math.pi * (day_of_year / 365 - peak_month / 12)
    return 1 + amplitude * math.cos(phase)
```

## Time-Based Patterns

Add weekday/weekend effects, holidays, seasonality, and event spikes:

```python
import holidays

# Load holiday calendar
US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])

def get_daily_multiplier(date):
    """Calculate volume multiplier for a given date."""
    multiplier = 1.0

    # Weekend drop
    if date.weekday() >= 5:
        multiplier *= 0.6

    # Holiday drop (even lower than weekends)
    if date in US_HOLIDAYS:
        multiplier *= 0.3

    # Q4 seasonality (higher in Oct-Dec)
    multiplier *= 1 + 0.15 * (date.month - 6) / 6

    # Incident spike
    if INCIDENT_START <= date <= INCIDENT_END:
        multiplier *= 3.0

    # Random noise
    multiplier *= np.random.normal(1, 0.1)

    return max(0.1, multiplier)

# Distribute tickets across dates with realistic patterns
date_range = pd.date_range(START_DATE, END_DATE, freq='D')
daily_volumes = [int(BASE_DAILY_TICKETS * get_daily_multiplier(d)) for d in date_range]
```

### Layering Multiple Time Effects

Combine multiple temporal patterns for maximum realism:

```python
def composite_multiplier(date):
    """Layer multiple time effects."""
    m = 1.0
    m *= 0.6 if date.weekday() >= 5 else 1.0          # Weekday/weekend
    m *= 0.3 if date in US_HOLIDAYS else 1.0            # Holidays
    m *= seasonal_multiplier(date)                       # Seasonal
    m *= 3.0 if INCIDENT_START <= date <= INCIDENT_END else 1.0  # Events
    m *= np.random.normal(1, 0.1)                        # Noise
    return max(0.1, m)
```

## Row Coherence

Attributes within a row should correlate logically. Never generate fields independently when they should be related.

```python
def generate_ticket(customer_id, tier, date):
    """Generate a coherent ticket where attributes correlate."""

    # Priority correlates with tier
    if tier == 'Enterprise':
        priority = np.random.choice(['Critical', 'High', 'Medium'], p=[0.3, 0.5, 0.2])
    else:
        priority = np.random.choice(['Critical', 'High', 'Medium', 'Low'], p=[0.05, 0.2, 0.45, 0.3])

    # Resolution time correlates with priority
    resolution_scale = {'Critical': 4, 'High': 12, 'Medium': 36, 'Low': 72}
    resolution_hours = np.random.exponential(scale=resolution_scale[priority])

    # CSAT correlates with resolution time
    if resolution_hours < 4:
        csat = np.random.choice([4, 5], p=[0.3, 0.7])
    elif resolution_hours < 24:
        csat = np.random.choice([3, 4, 5], p=[0.2, 0.5, 0.3])
    else:
        csat = np.random.choice([1, 2, 3, 4], p=[0.1, 0.3, 0.4, 0.2])

    return {
        "customer_id": customer_id,
        "priority": priority,
        "resolution_hours": round(resolution_hours, 1),
        "csat_score": csat,
        "created_at": date,
    }
```

### Common Coherence Rules

| Parent Field | Dependent Field | Relationship |
|-------------|----------------|--------------|
| Tier (Enterprise/Pro/Free) | Order amount | Log-normal with higher mean for higher tiers |
| Tier | Priority distribution | Enterprise skews Critical/High |
| Priority | Resolution time | Higher priority = faster resolution |
| Resolution time | CSAT score | Faster resolution = higher satisfaction |
| Date (incident period) | Category distribution | Incident-related categories spike |
| Date (incident period) | CSAT | Satisfaction degrades during incidents |
| Region | Currency / locale | Match regional conventions |
