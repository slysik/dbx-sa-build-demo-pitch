# Discord Integration Setup

**Goal:** Get real-time churn detection alerts + report distribution via Discord

---

## Step 1: Create Discord Server (if you don't have one)

1. Go to https://discord.com/
2. Click "Create a Server"
3. Name it: `Banking Churn Detection` (or your choice)
4. Create a channel: `#churn-alerts` (for critical alerts)
5. Create a channel: `#reports` (for weekly reports)

---

## Step 2: Get Discord Webhook URL

A webhook lets our system send messages to Discord automatically.

### For the #churn-alerts channel:

1. **Right-click** the `#churn-alerts` channel
2. Select **Edit Channel**
3. Go to **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Name it: `Databricks Churn Alerts`
6. Click **Copy Webhook URL**
7. Save it somewhere safe (you'll use it next)

**Example URL format:**
```
https://discordapp.com/api/webhooks/1234567890/abcd-efgh-ijkl-mnop
```

### For the #reports channel:

Repeat the same process, name it `Databricks Report Distribution`

---

## Step 3: Send Your First Report to Discord

### Option A: Email + Discord (Recommended)

```bash
# First, set up email credentials (one-time)
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="your-app-password"  # Google App Password, not Gmail password

# Then send report to both email and Discord
python3 scripts/send_report.py \
  --email slysik@gmail.com \
  --discord-webhook "https://discordapp.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
```

### Option B: Discord Only

```bash
python3 scripts/send_report.py \
  --email slysik@gmail.com \
  --discord-webhook "https://discordapp.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
```

---

## Step 4: Automate Daily Report Distribution

Create a **Databricks Job** to send reports daily:

```yaml
# Add to databricks.yml
jobs:
  send_daily_report:
    name: "[dev churn] Send Daily Report (Email + Discord)"
    queue:
      enabled: true
    tasks:
      - task_key: report
        python_script_task:
          python_file: src/scripts/send_report_task.py
        schedule:
          quartz_cron_expression: "0 8 * * *"  # 8 AM daily
          timezone_id: "America/New_York"
```

Then the notebook would call:
```python
import subprocess
subprocess.run([
    "python3", "scripts/send_report.py",
    "--email", "slysik@gmail.com",
    "--discord-webhook", "YOUR_WEBHOOK_URL"
])
```

---

## Step 5: Set Up Real-Time Alerts

Connect Databricks SQL Alerts → Discord Webhook

### Create a Discord Alert Bot

```python
# This would run in a Databricks job
import requests
from datetime import datetime

def send_alert_to_discord(webhook_url, title, message, severity="info"):
    """Send churn alert to Discord"""
    
    colors = {
        "critical": 15158332,  # Red
        "high": 15105570,      # Orange
        "medium": 15277667,    # Yellow
        "info": 1915639        # Blue
    }
    
    embed = {
        "title": title,
        "description": message,
        "color": colors.get(severity, 1915639),
        "timestamp": datetime.now().isoformat(),
        "footer": {"text": "Databricks Churn Detection Platform"}
    }
    
    response = requests.post(webhook_url, json={"embeds": [embed]})
    return response.status_code == 204

# Usage:
send_alert_to_discord(
    webhook_url="YOUR_WEBHOOK_URL",
    title="🚨 High-Risk VIP Detected",
    message="Customer USER-00042 (Tier: CRITICAL) showing 5+ risk signals this week",
    severity="critical"
)
```

---

## Step 6: Monitor Churn in Discord (Real-Time)

### Example: Daily 8 AM Report

Every morning at 8 AM, Discord receives:

```
🏦 Banking Churn Detection Platform — Daily Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 At-Risk Customers Today:
  • CRITICAL: 2 customers
  • HIGH: 8 customers
  • MEDIUM: 24 customers

🎯 Key Metrics:
  • App Crashes: 12 events
  • Failed Logins: 8 events
  • Support Calls: 5 events

📈 Interventions Logged (Last 24h):
  • Calls: 6
  • Offers Sent: 3
  • Success Rate: 67%

✅ Report Generated 2026-03-21 08:00 AM
```

### Example: Critical Alert

When high-risk VIP detected:

```
🚨 CRITICAL ALERT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

High-Risk VIP Customer Detected!

Customer ID: USER-00042
Risk Score: 87/100
Account Value: $150,000

Recent Signals:
  ❌ App crashed 3x in past hour
  ❌ Failed login attempt
  ❌ No transactions for 7 days

Recommended Action: VIP_SUPPORT
Call customer immediately!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated: 2026-03-21 14:23:45
```

---

## Step 7: Team Collaboration

### Set Up Channels:

| Channel | Purpose | Who | Frequency |
|---------|---------|-----|-----------|
| `#churn-alerts` | Critical alerts only | Support leads | Real-time |
| `#reports` | Daily/weekly summaries | Everyone | 8 AM daily |
| `#interventions` | Log intervention results | Support team | As needed |
| `#insights` | Data analysis deep-dives | Analytics | Weekly Friday |

### Permissions:

1. Go to `#churn-alerts` → **Edit Channel**
2. Go to **Roles/Members**
3. Give `@support-team` role **Send Messages** permission
4. Pin the alert format at the top (for consistency)

---

## Troubleshooting

### Webhook URL not working?

- Check the URL is complete (includes `/api/webhooks/...`)
- Make sure the webhook is for the correct channel
- Test with `curl`:
  ```bash
  curl -X POST "YOUR_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{"content":"Test message"}'
  ```

### Not receiving emails?

- Google Account: Use **App Passwords** (not your Gmail password)
  - Go to myaccount.google.com → Security → App Passwords
  - Generate one for "Databricks"
  - Use that in SENDER_PASSWORD
- Check spam folder
- Verify SENDER_EMAIL is correct

### Can't send to Discord?

- Make sure webhook is not expired
- Check if bot has permissions in the channel
- Try sending a test message manually in the webhook URL

---

## Next Steps

1. ✅ Create Discord server + channels
2. ✅ Get webhook URLs
3. ✅ Send first test report
4. ✅ Set up automated daily reports
5. ✅ Configure critical alerts
6. ✅ Train team on alert response
7. ✅ Monitor intervention effectiveness

---

## Questions?

Email: slysik@gmail.com  
Discord: Post in #churn-alerts  
GitHub: Open an issue in churn_detection_lakehouse
