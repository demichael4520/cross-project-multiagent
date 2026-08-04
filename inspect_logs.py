import google.cloud.logging
from datetime import datetime, timedelta, timezone

def inspect_project(project_id):
    print(f"\n=== Inspecting Cloud Logging for project {project_id} (last 10 minutes) ===")
    try:
        client = google.cloud.logging.Client(project=project_id)
        time_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        filter_str = f'timestamp >= "{time_ago}"'
        
        entries = list(client.list_entries(filter_=filter_str, max_results=100))
        print(f"Retrieved {len(entries)} log entries.")
        
        entries.sort(key=lambda e: e.timestamp)
        for entry in entries:
            payload = ""
            if entry.payload:
                payload = str(entry.payload)
            elif entry.text_payload:
                payload = str(entry.text_payload)
            elif entry.json_payload:
                payload = str(entry.json_payload)
            
            res_type = entry.resource.type if entry.resource else "unknown"
            log_name = entry.log_name.split("/")[-1] if entry.log_name else "unknown"
            
            if entry.severity and entry.severity in ["ERROR", "CRITICAL", "WARNING"] or "error" in payload.lower() or "exception" in payload.lower() or "fail" in payload.lower():
                print(f"[{entry.timestamp}] [{res_type}] [{log_name}] [{entry.severity}] {payload}")
    except Exception as e:
        print(f"Error inspecting project {project_id}: {e}")

if __name__ == "__main__":
    inspect_project("deepakmichael-svc3")
    inspect_project("deepakmichael-host")
