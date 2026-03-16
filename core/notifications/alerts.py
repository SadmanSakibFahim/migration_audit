import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.audit.logger import get_logger

logger = get_logger(__name__)

class AlertManager:
    """Dispatches webhook alerts to external systems (e.g. Slack/Teams/Email)."""
    
    def __init__(self) -> None:
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.teams_webhook_url = os.getenv("TEAMS_WEBHOOK_URL")

    def _post_json(self, url: str, payload: Dict[str, Any]) -> None:
        """Utility to post JSON to a webhook URL without heavy third-party libs."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json", "User-Agent": "MigrationAudit/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status >= 400:
                    logger.warning(f"Webhook {url} returned {response.status}")
        except urllib.error.URLError as e:
            logger.error(f"Failed to deliver webhook to {url}: {e}")
            
    def dispatch_slack_alert(self, passes: int, fails: int, errors: int) -> None:
        if not self.slack_webhook_url:
            return
            
        color = "#36a64f" if fails == 0 and errors == 0 else "#ff0000"
        title = "✅ Albatross Audit Completed" if fails == 0 and errors == 0 else "🚨 Albatross Audit Failed Constraints"
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "fields": [
                        {"title": "PASSED", "value": str(passes), "short": True},
                        {"title": "FAILED", "value": str(fails), "short": True},
                        {"title": "ERRORS", "value": str(errors), "short": True}
                    ]
                }
            ]
        }
        self._post_json(self.slack_webhook_url, payload)

    def dispatch_teams_alert(self, passes: int, fails: int, errors: int) -> None:
        if not self.teams_webhook_url:
            return
            
        color = "00ff00" if fails == 0 and errors == 0 else "ff0000"
        title = "Albatross Audit Completed" if fails == 0 and errors == 0 else "Albatross Audit Failure"
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "facts": [
                    {"name": "PASSED", "value": str(passes)},
                    {"name": "FAILED", "value": str(fails)},
                    {"name": "ERRORS", "value": str(errors)}
                ],
                "markdown": True
            }]
        }
        self._post_json(self.teams_webhook_url, payload)

    def dispatch_all(self, passes: int, fails: int, errors: int) -> None:
        """Dispatches summaries out to all configured destinations."""
        self.dispatch_slack_alert(passes, fails, errors)
        self.dispatch_teams_alert(passes, fails, errors)
