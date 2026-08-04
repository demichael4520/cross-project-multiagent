import google.cloud.logging
from datetime import datetime, timedelta, timezone

def main():
    project_id = "deepakmichael-svc3"
    client = google.cloud.logging.Client(project=project_id)
    
    time_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    filter_str = (
        f'timestamp >= "{time_ago}" AND '
        'resource.type="aiplatform.googleapis.com/ReasoningEngine"'
    )
    
    entries = list(client.list_entries(filter_=filter_str, max_results=200))
    entries.sort(key=lambda e: e.timestamp)
    for e in entries:
        payload = getattr(e, 'payload', None) or getattr(e, 'text_payload', None) or getattr(e, 'json_payload', None) or ""
        text = str(payload)
        if "Error" in text or "Traceback" in text or "failed" in text.lower() or e.severity in ("ERROR", "CRITICAL"):
            print(f"[{e.timestamp}] [{e.severity}] {text}")

if __name__ == "__main__":
    main()
