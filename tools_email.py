# tools_email.py
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from langchain_core.tools import tool
import config 

@tool
def check_inbox(query: str = "UNSEEN"):
    """Checks the inbox. Automatically fixes invalid queries."""
    try:
        valid_commands = ["UNSEEN", "SEEN", "ALL", "FLAGGED", "ANSWERED"]
        clean_query = str(query).upper().strip()
        
        # Safety Guard
        if clean_query not in valid_commands:
            print(f"   (🛠️ Safety Guard: AI asked for '{query}', switching to 'UNSEEN')")
            clean_query = "UNSEEN"
            
        print(f"   (Tool: Checking Inbox for '{clean_query}'...)")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(config.EMAIL_USER, config.EMAIL_PASS)
        mail.select("inbox")
        status, messages = mail.search(None, clean_query)
        
        # --- FIX: BETTER ERROR MESSAGE ---
        if not messages or not messages[0]: 
            return "✅ STATUS: Inbox is empty. No emails found for this query."
        
        results = []
        for e_id in messages[0].split()[-3:]:
            _, msg_data = mail.fetch(e_id, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            body = msg.get_payload(decode=True).decode() if not msg.is_multipart() else "Multipart"
            results.append(f"From: {msg['From']} | Subject: {msg['Subject']} | Body: {body[:150]}...")
        return "\n".join(results)
    except Exception as e: return f"Error: {e}"

@tool
def draft_reply(to_address: str, subject: str, body: str):
    """Drafts a reply in Gmail."""
    try:
        print(f"   (Tool: Saving draft to {to_address}...)")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(config.EMAIL_USER, config.EMAIL_PASS)
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_USER
        msg["To"] = to_address
        msg.attach(MIMEText(body, "plain"))
        mail.select('"[Gmail]/Drafts"')
        mail.append('"[Gmail]/Drafts"', None, imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        return f"Draft Saved! Content:\nSubject: {subject}\nBody: {body}"
    except Exception as e: return f"Error: {e}"