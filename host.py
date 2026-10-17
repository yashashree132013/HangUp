import json
import re

import uvicorn
from mcp import ClientSession
from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

try:
    from mcp.client.streamable_http import streamable_http_client as http_client
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client as http_client

MCP_URL = "http://localhost:8000/mcp"
YES = {"yes", "yeah", "yep", "sure", "ok", "okay", "please", "haan"}
NO = {"no", "nope", "nahi"}
state = {"pending": False, "claim": ""}


async def call_tool(name: str, args: dict) -> dict:
    async with http_client(MCP_URL) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
    return json.loads(result.content[0].text)


async def chat(request):
    body = await request.json()
    text = str(body.get("text", "")).strip()
    words = set(re.findall(r"[a-z']+", text.lower().replace("\u2019", "'")))
    short = len(words) <= 4
    tools = []

    async def use(name, args):
        result = await call_tool(name, args)
        tools.append({"name": name, "args": args, "result": result})
        return result

    try:
        if not text:
            reply = "I did not catch that. Please tell me what the caller said."
        elif state["pending"] and short and words & YES:
            incident = await use("log_incident", {
                "caller_claim": state["claim"],
                "notes": "Logged by the HangUp voice assistant (demo).",
            })
            await use("alert_trusted_contact", {
                "contact_name": "Family contact",
                "message": "HangUp alert: I may be targeted by a scam call. "
                           "Please call me. Details: " + state["claim"],
            })
            summary = await use("draft_complaint_summary",
                                {"incident_id": incident["id"]})
            steps = " ".join(summary.get("next_steps", [])[:2])
            reply = ("Done. I saved incident " + incident["id"] +
                     ", sent a simulated alert to your family contact, and "
                     "prepared your report summary. Next: " + steps)
            state["pending"] = False
        elif state["pending"] and short and words & NO:
            reply = ("Okay, I will not save anything. Stay safe. If anyone "
                     "pressures you again, hang up and call 1930.")
            state["pending"] = False
        else:
            result = await use("assess_scam_call", {"description": text})
            reply = result["advice"]
            if result["risk"] != "low":
                reply += (" Would you like me to save a record, alert your "
                          "family contact, and prepare a report summary? "
                          "Say yes or no.")
                state["pending"] = True
                state["claim"] = text
            else:
                state["pending"] = False
    except Exception as exc:
        return JSONResponse({
            "reply": "I cannot reach my tools. Please check that the "
                     "MCP server is running.",
            "tools": [], "error": str(exc)}, status_code=500)

    return JSONResponse({"reply": reply, "tools": tools})


async def home(request):
    return FileResponse("index.html")


app = Starlette(routes=[
    Route("/", home),
    Route("/chat", chat, methods=["POST"]),
])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)