import os
import requests
import datetime
import csv
import json
from time import sleep

# --- CONFIG ---
ZENDESK_DOMAIN = "gmtour.zendesk.com"
EMAIL = "yannawut@gmtour.com"
TOKEN = "5IKzpPptiDAOmcBztHTOKkUWeYJhp6tTyoh0KO5n"
AUTH = (f"{EMAIL}/token", TOKEN)
ARCHIVE_DIR = "./zendesk_archive"
CREATED_BEFORE = "2019-08-31"

# Filter: Closed tickets created on or before 2019-08-31
SEARCH_URL = (
    f"https://{ZENDESK_DOMAIN}/api/v2/search.json?"
    f"query=type:ticket status:closed created<={CREATED_BEFORE}"
)

os.makedirs(ARCHIVE_DIR, exist_ok=True)

def search_old_closed_tickets():
    url = SEARCH_URL
    while url:
        print(f"Searching: {url}")
        resp = requests.get(url, auth=AUTH)
        data = resp.json()
        for ticket in data.get("results", []):
            print(f"🧾 Ticket ID: {ticket['id']}, Created: {ticket['created_at']}, Updated: {ticket['updated_at']}")
            yield ticket
        url = data.get("next_page")
        sleep(1)

def get_ticket_comments(ticket_id):
    url = f"https://{ZENDESK_DOMAIN}/api/v2/tickets/{ticket_id}/comments.json"
    resp = requests.get(url, auth=AUTH)
    return resp.json()

def download_attachment(att, save_path):
    file_url = att["content_url"]
    print(f"📥 Downloading {att['file_name']}")
    r = requests.get(file_url, auth=AUTH)
    with open(save_path, "wb") as f:
        f.write(r.content)

def archive_ticket(ticket):
    ticket_id = ticket["id"]
    folder = os.path.join(ARCHIVE_DIR, f"ticket_{ticket_id}")
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(ticket, f, indent=2)

    comments = get_ticket_comments(ticket_id)
    with open(os.path.join(folder, "comments.json"), "w", encoding="utf-8") as f:
        json.dump(comments, f, indent=2)

    for comment in comments.get("comments", []):
        for att in comment.get("attachments", []):
            filepath = os.path.join(folder, att["file_name"])
            download_attachment(att, filepath)

def export_summary_csv(tickets):
    path = os.path.join(ARCHIVE_DIR, "summary.csv")
    keys = ["id", "subject", "status", "priority", "updated_at"]
    with open(path, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for t in tickets:
            row = {k: t.get(k, "") for k in keys}
            writer.writerow(row)

# --- MAIN FLOW ---
all_tickets = list(search_old_closed_tickets())
for ticket in all_tickets:
    archive_ticket(ticket)

export_summary_csv(all_tickets)
print(f"✅ Archived {len(all_tickets)} tickets and attachments to '{ARCHIVE_DIR}'")
