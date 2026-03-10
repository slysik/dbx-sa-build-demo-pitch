# Likely Interviewer Prompts

Based on the prep guide, the interviewer gives you a **prompt to generate a dataset** 
and then you build a pipeline. Here are realistic prompts they might use, across verticals:

---

## Financial Services (FinServ)
1. **Credit card fraud detection**: "Build a pipeline to analyze credit card transactions and flag potential fraud"
2. **Loan portfolio risk**: "A bank wants to assess risk across their loan portfolio — build a pipeline to analyze loan performance"  
3. **Anti-money laundering**: "Build a pipeline to detect suspicious transaction patterns across customer accounts"
4. **Customer churn**: "A retail bank is losing customers — build analytics to identify at-risk customers"

## Healthcare
5. **Claims anomaly detection**: "A health insurer wants to find billing anomalies in their claims data"
6. **Patient readmission**: "A hospital network wants to reduce 30-day readmission rates — build a feature pipeline"
7. **Drug interaction analysis**: "A pharmacy chain wants to flag potential drug interaction risks"

## Retail / E-Commerce
8. **Inventory optimization**: "An e-commerce company has stockout problems — build supply chain analytics"
9. **Customer segmentation**: "A retailer wants to segment customers by purchasing behavior for targeted marketing"
10. **Product recommendation features**: "Build a feature pipeline for a product recommendation engine"

## Manufacturing / IoT
11. **Predictive maintenance**: "A manufacturer wants to predict equipment failures from sensor data"
12. **Quality control**: "Build a pipeline to track product defect rates across manufacturing lines"

## Media / Telecom
13. **Streaming engagement**: "A media company wants to understand viewer engagement patterns"
14. **Network performance**: "A telecom provider needs to analyze call quality metrics across cell towers"

---

## What They All Have in Common

Regardless of vertical, you'll always need:

1. **Synthetic data generation** → Python + Faker
2. **Data cleaning** → Silver (dedup, type casting, null handling, validation)
3. **Business aggregations** → Gold (GROUP BY, window functions, feature engineering)
4. **Explain execution** → How Spark runs it, how it scales

The domain changes but the PATTERN is the same. Master the pattern, not the domain.

---

## Your Claude/Pi Prompt Template

When you get the interviewer's prompt, use this template to generate code:

```
Generate a Databricks notebook that:

1. Creates a synthetic [DOMAIN] dataset using Faker with:
   - [TABLE 1]: [N] rows with columns [list columns]
   - [TABLE 2]: [N] rows with columns [list columns]
   - Use realistic distributions (log-normal for amounts, weighted choices for categories)
   - Seed random generators for reproducibility
   - Save as Delta tables

2. Silver layer SQL transforms:
   - Deduplicate on primary keys
   - Cast amounts to DECIMAL(12,2)
   - Validate and clean: nulls, bad values, string normalization
   - Add Delta table constraints

3. Gold layer SQL for business analytics:
   - [AGGREGATION TABLE 1]: one row per [entity] with key metrics
   - [AGGREGATION TABLE 2]: [describe the business need]
   - Use window functions for [running averages / rankings / etc.]

Include detailed comments explaining what each block does.
Use Python only for data generation, SQL for all transforms.
```
