import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# Notification Credentials Setup
# ==========================================
# To make this live, put your actual Gmail and an "App Password" here.
# E.g. SMTP_USER = "myfarm@gmail.com", SMTP_PASS = "abcd efgh ijkl mnop"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your_email@gmail.com"
SMTP_PASS = "your_app_password"

# Destination phone/email (E.g. SMS Gateway: 5551234567@vtext.com for Verizon)
FARMER_CONTACT = "farmer@example.com" 

def send_alert(disease_name, alert_message, context_info):
    """
    Dispatches an email or SMS notification to the farmer.
    """
    print(f"[Notifier] Attempting to send alert for {disease_name}...")
    
    # If credentials haven't been configured, just simulate it locally.
    if SMTP_USER == "your_email@gmail.com":
        print("[Notifier] Credentials not configured. Simulating alert locally.")
        print(f"|---------------- ALERT DISPATCH ----------------|")
        print(f"| TO: {FARMER_CONTACT}")
        print(f"| SUBJECT: CROP ALERT: {disease_name}")
        print(f"| BODY: {alert_message}\n| CONTEXT: {context_info}")
        print(f"|------------------------------------------------|")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = FARMER_CONTACT
        msg['Subject'] = f"CROP DISEASE ALERT: {disease_name}"
        
        body = f"Automated Farm Alert System\n\n"
        body += f"Disease Detected: {disease_name}\n"
        body += f"Sensor Insight: {alert_message}\n"
        body += f"Environment Data: {context_info}\n\n"
        body += "Please inspect the crop perimeter immediately."

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        text = msg.as_string()
        server.sendmail(SMTP_USER, FARMER_CONTACT, text)
        server.quit()
        print("[Notifier] Alert dispatched successfully.")
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send email alert: {e}")
        return False
