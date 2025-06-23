import os
import requests
import datetime
import csv
import json

# --- CONFIG ---
ZENDESK_DOMAIN = "gmtour.zendesk.com"
EMAIL = "yannawut@gmtour.com"
TOKEN = "5IKzpPptiDAOmcBztHTOKkUWeYJhp6tTyoh0KO5n"
AUTH = (f"{EMAIL}/token", TOKEN)
ARCHIVE_DIR = "./zendesk_archive_cursor"
CUTOFF_DATE = datetime.datetime(2019, 8, 31, tzinfo=datetime.timezone.utc)
START_TIME = 0  # From Unix epoch

os.makedirs(ARCHIVE_DIR, exist_ok=True)

def search_tickets_cursor():
    url = f"https://{ZENDESK_DOMAIN}/api/v2/incremental/tickets/cursor.json?start_time={START_TIME}"
    while url:
        print(f" Fetching: {url}")
        resp = requests.get(url, auth=AUTH)
        data = resp.json()

        stop_fetching = False
        for ticket in data.get("tickets", []):
            created_at = datetime.datetime.fromisoformat(ticket["created_at"].replace("Z", "+00:00"))
            if created_at > CUTOFF_DATE:
                stop_fetching = True
                break
            if ticket.get("status") == "closed":
                print(f"𒌛 Ticket ID: {ticket['id']}, Created: {ticket['created_at']}, Status: {ticket['status']}")
                yield ticket

        if stop_fetching or not data.get("after_url"):
            break
        url = data.get("after_url")

def get_ticket_comments(ticket_id):
    url = f"https://{ZENDESK_DOMAIN}/api/v2/tickets/{ticket_id}/comments.json"
    resp = requests.get(url, auth=AUTH)
    return resp.json()

def download_attachment(att, save_path):
    file_url = att["content_url"]
    print(f"📅 Downloading {att['file_name']}")
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
all_tickets = list(search_tickets_cursor())
for ticket in all_tickets:
    archive_ticket(ticket)

export_summary_csv(all_tickets)
print(f"✅ Archived {len(all_tickets)} tickets and attachments to '{ARCHIVE_DIR}'")
