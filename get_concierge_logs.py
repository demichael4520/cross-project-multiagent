import google.cloud.logging
from datetime import datetime, timedelta, timezone

def main():
    project_id = "deepakmichael-svc3"
    client = google.cloud.logging.Client(project=project_id)
    
    time_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    filter_str = (
        f'timestamp >= "{time_ago}" AND '
        'resource.type="aiplatform.googleapis.com/ReasoningEngine"'
    )
    
    print(f"Fetching recent Reasoning Engine logs for project {project_id}...")
    try:
        entries = list(client.list_entries(filter_=filter_str, max_results=200))
        print(f"Retrieved {len(entries)} log entries.")
        
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        for e in entries:
            payload = getattr(e, 'payload', None) or getattr(e, 'text_payload', None) or getattr(e, 'json_payload', None) or ""
            print(f"[{e.timestamp}] [{e.severity}] {str(payload).strip()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
