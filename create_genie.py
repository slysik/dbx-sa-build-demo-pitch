import json
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile="dbc-61514402-8451")

# The serialized_space is a JSON string representing the Genie Space configuration
serialized_space = {
    "tables": [
        {"name": "workspace.payments.gold_payment_metrics", "display_name": "Payment Metrics"},
        {"name": "workspace.payments.silver_payment_transactions", "display_name": "Payment Transactions"}
    ],
    "description": "Wealth Management payments data for exploring transaction volumes, sizes, and daily trends.",
    "instructions": '''
    You are an expert Wealth Management analyst. 
    1. ALWAYS return time series data aggregated to the Daily level unless explicitly asked for Monthly.
    2. Format all currency as USD.
    3. When analyzing transaction status, highlight PENDING and FAILED payments.
    4. For charts, prioritize line charts for trends, bar charts for processor comparisons, and pie charts for status distributions.
    5. Always use `gold_payment_metrics` for aggregations where possible for performance.
    ''',
    "sample_questions": [
        "What is the daily transaction volume trend for the last 30 days?",
        "Show me a breakdown of transaction statuses by processor.",
        "Which payment processor handles the highest total amount?",
        "What is the average transaction size for COMPLETED vs FAILED payments?"
    ]
}

res = w.genie.create_space(
    warehouse_id="4bbaafe9538467a0",
    serialized_space=json.dumps(serialized_space)
)
print("Genie Space Created:", res.space_id)
