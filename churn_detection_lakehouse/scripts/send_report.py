#!/usr/bin/env python3
"""
Send CHURN_DETECTION_REPORT.html via Email

Usage:
    python3 send_report.py --email slysik@gmail.com
    python3 send_report.py --email slysik@gmail.com --discord-webhook [URL]
"""

import smtplib
import os
import requests
import argparse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration
REPORT_PATH = Path(__file__).parent.parent / "docs" / "CHURN_DETECTION_REPORT.html"
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

def send_email(recipient_email: str, html_report_path: Path):
    """Send report via Gmail"""
    
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        print("❌ ERROR: Set SENDER_EMAIL and SENDER_PASSWORD environment variables")
        print("   Example (in ~/.zshrc):")
        print("   export SENDER_EMAIL='your-email@gmail.com'")
        print("   export SENDER_PASSWORD='your-app-password'")
        return False
    
    try:
        # Read HTML report
        with open(html_report_path, "r") as f:
            html_content = f.read()
        
        # Create email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🏦 Banking Churn Detection Platform — 3-Page Report ({datetime.now().strftime('%Y-%m-%d')})"
        msg["From"] = sender_email
        msg["To"] = recipient_email
        
        # Attach HTML
        msg.attach(MIMEText(html_content, "html"))
        
        # Send via SMTP
        print(f"📤 Sending report to {recipient_email}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {recipient_email}")
        return True
    
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False

def send_discord(webhook_url: str, html_report_path: Path):
    """Send report summary to Discord"""
    
    try:
        # Read report to extract key info
        with open(html_report_path, "r") as f:
            html = f.read()
        
        # Create Discord embed
        embed = {
            "title": "🏦 Banking Churn Detection Platform",
            "description": "Real-Time Customer Retention Intelligence System",
            "color": 1915639,  # Blue
            "fields": [
                {
                    "name": "📊 System Overview",
                    "value": "✅ Real-time Zerobus ingestion (2K events/5min)\n✅ SDP pipeline (Bronze → Silver → Gold)\n✅ ML churn predictions (LogisticRegression)\n✅ 4 delivery channels (Dashboard, Genie, App, Alerts)",
                    "inline": False
                },
                {
                    "name": "📋 What's Included",
                    "value": "✅ Producer (events generator)\n✅ SDP Pipeline (3-layer medallion)\n✅ ML Training (weekly)\n✅ Streamlit intervention app\n✅ AI/BI Dashboard\n✅ Genie Space\n✅ SQL Alerts",
                    "inline": False
                },
                {
                    "name": "📦 Deployment",
                    "value": "```\ndatabricks bundle validate\ndatabricks bundle deploy\n```",
                    "inline": False
                },
                {
                    "name": "📖 Documentation",
                    "value": "📄 Full 3-page HTML report sent via email\n📊 Complete architecture guide\n🚀 Deployment & usage instructions\n💡 Customization tips",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Report Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Databricks Platform"
            }
        }
        
        payload = {"embeds": [embed]}
        
        print(f"📤 Sending to Discord...")
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 204:
            print(f"✅ Discord notification sent successfully")
            return True
        else:
            print(f"❌ Discord send failed: {response.status_code} {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Discord send failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Send churn detection report")
    parser.add_argument("--email", required=True, help="Recipient email address (e.g., slysik@gmail.com)")
    parser.add_argument("--discord-webhook", help="Discord webhook URL (optional)")
    
    args = parser.parse_args()
    
    print(f"\n🏦 Churn Detection Platform — Report Distribution")
    print(f"{'='*50}")
    
    if not REPORT_PATH.exists():
        print(f"❌ Report not found: {REPORT_PATH}")
        return
    
    print(f"📄 Report location: {REPORT_PATH}")
    print(f"📊 Report size: {REPORT_PATH.stat().st_size / 1024:.1f} KB")
    
    # Send email
    email_ok = send_email(args.email, REPORT_PATH)
    
    # Send Discord if webhook provided
    discord_ok = True
    if args.discord_webhook:
        discord_ok = send_discord(args.discord_webhook, REPORT_PATH)
    
    # Summary
    print(f"\n{'='*50}")
    if email_ok and discord_ok:
        print("✅ All deliveries successful!")
    elif email_ok:
        print("✅ Email sent successfully")
        if args.discord_webhook:
            print("⚠️  Discord delivery had issues")
    else:
        print("❌ Delivery failed. Check SENDER_EMAIL and SENDER_PASSWORD.")

if __name__ == "__main__":
    main()
