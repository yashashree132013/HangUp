from mcp.server.fastmcp import FastMCP
import json
import uuid
from datetime import datetime
from pathlib import Path
mcp = FastMCP("HangUp", json_response=True)

RED_FLAGS = {
    "arrest threat": ["arrest", "warrant", "cbi", "customs"],
    "stay on call": ["stay on the call", "video call", "don't hang up"],
    "secrecy": ["don't tell", "do not tell", "keep this secret"],
    "move money": ["safe account", "verification account", "transfer"],
    "credentials": ["otp", "pin", "remote access", "anydesk"],
}

@mcp.tool()
def assess_scam_call(description: str) -> dict:
    """Check a caller's description for known scam red flags."""
    text = description.lower()
    hits = [name for name, words in RED_FLAGS.items()
            if any(w in text for w in words)]
    risk = "high" if len(hits) >= 2 else "medium" if hits else "low"
    if hits:
        advice = "Hang up. Do not send money. Call 1930."
    else:
        advice = ("No clear red flags found. If anyone pressures you "
                  "for money, hang up and call 1930.")
    return {"risk": risk, "red_flags": hits, "advice": advice}

INCIDENTS_FILE = Path("incidents.json")


def load_incidents() -> list:
    if INCIDENTS_FILE.exists():
        return json.loads(INCIDENTS_FILE.read_text(encoding="utf-8"))
    return []


@mcp.tool()
def log_incident(caller_claim: str, amount_lost: int = 0, notes: str = "") -> dict:
    """Save a record of a suspicious call so it can be reported later."""
    incidents = load_incidents()
    incident = {
        "id": str(uuid.uuid4())[:8],
        "time": datetime.now().isoformat(timespec="seconds"),
        "caller_claim": caller_claim,
        "amount_lost": amount_lost,
        "notes": notes,
    }
    incidents.append(incident)
    INCIDENTS_FILE.write_text(json.dumps(incidents, indent=2), encoding="utf-8")
    return incident

if __name__ == "__main__":
    mcp.run(transport="streamable-http")