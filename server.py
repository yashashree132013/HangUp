import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HangUp", json_response=True)

RED_FLAGS = {
    "arrest threat": ["arrest", "arrested", "warrant", "cbi", "customs",
                      "digital arrest", "police"],
    "stay on call": ["stay on the call", "stay on the video call",
                     "video call", "don't hang up"],
    "secrecy": ["don't tell", "do not tell", "keep this secret",
                "tell no one"],
    "move money": ["safe account", "verification account", "transfer"],
    "credentials": ["otp", "pin", "remote access", "anydesk"],
    "parcel or kyc pretext": ["parcel", "courier", "kyc", "narcotics",
                              "drugs", "aadhaar", "trai"],
}

PAID_PHRASES = ["already paid", "i paid", "sent money", "i sent",
                "i transferred", "already transferred"]


def has_phrase(text: str, phrase: str) -> bool:
    return re.search(r"\b" + re.escape(phrase) + r"\b", text) is not None


@mcp.tool()
def assess_scam_call(description: str) -> dict:
    """Check a caller's description for known scam red flags."""
    text = description.lower().replace("\u2019", "'")
    hits = [name for name, phrases in RED_FLAGS.items()
            if any(has_phrase(text, p) for p in phrases)]
    already_paid = any(has_phrase(text, p) for p in PAID_PHRASES)

    if len(hits) >= 2 or (hits and already_paid):
        risk = "high"
    elif hits:
        risk = "medium"
    else:
        risk = "low"

    if already_paid:
        advice = ("Do not send any more money. Call 1930 and your bank "
                  "right now, and keep your payment receipts.")
    elif hits:
        advice = ("Hang up. Do not send money or share any OTP or PIN. "
                  "Real police do not arrest people over a video call. "
                  "If you are unsure, call 1930.")
    else:
        advice = ("I found no clear red flags. If anyone pressures you "
                  "for money, hang up and call 1930.")
    return {"risk": risk, "red_flags": hits,
            "already_paid": already_paid, "advice": advice}


INCIDENTS_FILE = Path("incidents.json")
ALERTS_FILE = Path("alerts.json")


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


@mcp.tool()
def draft_complaint_summary(incident_id: str) -> dict:
    """Write a short summary of a logged incident, ready for reporting."""
    for item in load_incidents():
        if item["id"] == incident_id:
            lines = [
                f"Incident ID: {item['id']}",
                f"Date and time: {item['time']}",
                f"What the caller claimed: {item['caller_claim']}",
                f"Amount lost (INR): {item['amount_lost']}",
                f"Notes: {item['notes'] or 'None'}",
            ]
            return {
                "summary": "\n".join(lines),
                "next_steps": [
                    "Call 1930 as soon as possible, especially if money was sent.",
                    "Tell your bank immediately.",
                    "Report online at cybercrime.gov.in.",
                    "Keep screenshots, phone numbers and payment receipts.",
                ],
            }
    return {"error": "No incident found with that id."}


@mcp.tool()
def alert_trusted_contact(contact_name: str, message: str) -> dict:
    """Simulated alert to a trusted family member. Demo only, nothing is sent."""
    alerts = []
    if ALERTS_FILE.exists():
        alerts = json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
    alert = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "to": contact_name,
        "message": message,
    }
    alerts.append(alert)
    ALERTS_FILE.write_text(json.dumps(alerts, indent=2), encoding="utf-8")
    return {
        "status": "simulated",
        "note": "Demo only: no real message was sent.",
        "alert": alert,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")