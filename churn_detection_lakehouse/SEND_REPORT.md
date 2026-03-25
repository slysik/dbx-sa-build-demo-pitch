# 📧 Send Your Report Now

The **3-page HTML report** is ready! Here's how to send it to slysik@gmail.com (and Discord if you want).

---

## Option 1: Email Only (2 minutes setup)

### Step 1: Get a Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Select **Mail** and **Windows Computer** (or your device)
3. Click **Generate**
4. Copy the 16-character password

### Step 2: Set Environment Variables

Add these lines to your `~/.zshrc` or `~/.bash_profile`:

```bash
export SENDER_EMAIL="your-gmail-address@gmail.com"
export SENDER_PASSWORD="xxxx xxxx xxxx xxxx"  # Your 16-char app password
```

Then reload:
```bash
source ~/.zshrc
```

### Step 3: Send the Report

```bash
cd /Users/slysik/databricks/churn_detection_lakehouse

python3 scripts/send_report.py --email slysik@gmail.com
```

**Output:**
```
🏦 Churn Detection Platform — Report Distribution
==================================================
📄 Report location: .../docs/CHURN_DETECTION_REPORT.html
📊 Report size: 47.3 KB
📤 Sending report to slysik@gmail.com...
✅ Email sent successfully to slysik@gmail.com
```

✅ Check your inbox (or spam folder)!

---

## Option 2: Email + Discord (5 minutes setup)

### Step 1: Set Up Discord Webhook

**See full instructions:** `docs/DISCORD_SETUP.md`

**Quick version:**
1. Create Discord server: `Banking Churn Detection`
2. Create channel: `#reports`
3. Right-click channel → **Edit Channel** → **Integrations** → **Webhooks** → **New Webhook**
4. Copy webhook URL

### Step 2: Send Report to Both

```bash
cd /Users/slysik/databricks/churn_detection_lakehouse

python3 scripts/send_report.py \
  --email slysik@gmail.com \
  --discord-webhook "https://discordapp.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
```

**Output:**
```
🏦 Churn Detection Platform — Report Distribution
==================================================
📤 Sending report to slysik@gmail.com...
✅ Email sent successfully to slysik@gmail.com
📤 Sending to Discord...
✅ Discord notification sent successfully
==================================================
✅ All deliveries successful!
```

✅ Check your email AND Discord!

---

## What You'll Receive

### 📧 Email

A beautiful **3-page HTML report** with:
- **Page 1:** Executive Summary + Architecture
- **Page 2:** Technical Deep Dive (medallion layers, risk scoring, ML model)
- **Page 3:** Deployment Guide + How to Use

### 💬 Discord

A formatted embed message with:
- 🏦 System overview
- 📋 Components included
- 📦 Deployment commands
- 📖 Documentation summary

---

## Next: Deploy the System

Once you've read the report:

```bash
# 1. Validate the bundle
databricks bundle validate

# 2. Deploy everything to workspace
databricks bundle deploy

# 3. Run the producer (generates 2K events)
databricks jobs run-now --job-id [produce_banking_events]

# 4. Start the SDP pipeline
databricks pipelines start-update --pipeline-id [churn_pipeline]

# 5. Open the dashboard
databricks workspace list /Users/lysiak043@gmail.com/dashboards/
```

---

## Troubleshooting

### "SENDER_EMAIL and SENDER_PASSWORD not set"

**Solution:** Make sure you added them to `~/.zshrc` AND ran `source ~/.zshrc`

```bash
# Check they're set:
echo $SENDER_EMAIL
echo $SENDER_PASSWORD
```

### Email went to spam folder

**Solution:** Gmail may filter it initially. Check spam and mark as "Not Spam" so future emails arrive in inbox.

### Discord webhook not working

**Solution:** 
- Make sure you copied the FULL webhook URL
- Make sure the bot has permissions in the #reports channel
- Try the test in `docs/DISCORD_SETUP.md`

### Report file not found

```bash
ls -la docs/CHURN_DETECTION_REPORT.html
```

Should show the file. If not, I may need to regenerate it.

---

## Automate Daily Delivery

Want to send the report automatically every morning?

Add this to `databricks.yml`:

```yaml
jobs:
  send_daily_report:
    name: "[dev churn] Send Daily Report"
    queue:
      enabled: true
    tasks:
      - task_key: report
        python_script_task:
          python_file: scripts/send_report.py
          parameters: ["--email", "slysik@gmail.com", "--discord-webhook", "YOUR_WEBHOOK_URL"]
        schedule:
          quartz_cron_expression: "0 8 * * *"  # 8 AM daily
          timezone_id: "America/New_York"
```

Then deploy:
```bash
databricks bundle deploy
```

---

## Questions?

📧 Email: slysik@gmail.com  
💬 Discord: We'll set up a channel next  
📖 Full docs: `docs/DISCORD_SETUP.md`

**Enjoy your churn detection platform!** 🚀
