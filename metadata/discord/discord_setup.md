# Discord Bot Setup — aiNOC Remote Approval

This guide walks through creating and configuring the Discord bot that aiNOC uses to notify operators of proposed fixes and collect ✅/❌ approval reactions remotely.

**Time required**: ~5 minutes

---

## Prerequisites

- A Discord account
- A Discord server where the NOC team operates (or a dedicated one for aiNOC)
- Access to the aiNOC `.env` file on the server

---

## Step 1: Create the Application

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it `aiNOC` → click **Create**

---

## Step 2: Disable Default Install Link

> This must be done **before** setting the bot to private — otherwise the save will fail with "Private application cannot have a default authorization link."

1. Click **Installation** in the left sidebar
2. Find the **Install Link** setting → set it to **None**
3. Click **Save Changes**

---

## Step 3: Get the Bot Token

1. Click **Bot** in the left sidebar
2. Click **Reset Token** → confirm → copy the token
3. Add it to your `.env` file:
   ```
   DISCORD_BOT_TOKEN=your-token-here
   ```

> Keep this token secret. Anyone with the token can control the bot.

---

## Step 4: Set Bot to Private

1. Still on the **Bot** tab
2. **Uncheck "Public Bot"** — this ensures only you can invite the bot to servers
3. Click **Save Changes**

---

## Step 5: Enable Message Content Intent

1. Still on the **Bot** tab
2. Scroll to **Privileged Gateway Intents**
3. Enable **Message Content Intent** (required to read reactions)
4. Leave **Presence Intent** and **Server Members Intent** off
5. Click **Save Changes**

---

## Step 6: Set Bot Permissions

Still on the **Bot** tab, scroll to **Bot Permissions**. Check **only** these 5 permissions under **Text Permissions**:

- ✅ Send Messages
- ✅ Embed Links
- ✅ Read Message History
- ✅ Add Reactions
- ✅ Manage Messages *(for editing the outcome reply)*

Leave all General, Voice, and other Text permissions **unchecked**.

---

## Step 7: Generate the Invite URL

1. Click **OAuth2** → **URL Generator** in the left sidebar
2. Under **Scopes**, check `bot`
3. Under **Bot Permissions** (appears below), check the same 5 permissions from Step 6
4. Scroll to the bottom — copy the **Generated URL**

---

## Step 8: Add the Bot to Your Server

1. Open the generated URL in your browser
2. Select your Discord server from the dropdown
3. Click **Authorize** → complete the CAPTCHA if prompted
4. The bot now appears in your server's member list (shows as offline until aiNOC runs)

---

## Step 9: Create the Approval Channel and Get Channel ID

1. In your Discord server, create a channel named `#noc-approvals`
2. Right-click the channel → **Copy Channel ID**

   > If "Copy Channel ID" doesn't appear: go to Discord Settings → **Advanced** → enable **Developer Mode**, then right-click the channel again.

3. Add the Channel ID to your `.env` file:
   ```
   DISCORD_CHANNEL_ID=your-channel-id-here
   ```

---

## Step 10: Configure Approval Timeout

In `.env`, set how long the agent waits for a response before expiring:
```
APPROVAL_TIMEOUT_MINUTES=10
```

Default is 10 minutes (matches `.env` default). Adjust based on your SLA requirements.

---

## Step 11: Set Up Mobile Push Notifications

For the `#noc-approvals` channel to page you at 2AM:

1. Open the Discord mobile app
2. Open the `#noc-approvals` channel
3. Tap the channel name at the top → **Notification Settings**
4. Set to **All Messages**

This ensures every bot post triggers a push notification on your phone.

---

## Verification

After completing setup, test the integration:

```bash
cd /home/mcp/aiNOC
PYTHONPATH=/home/mcp/aiNOC /home/mcp/aiNOC/mcp/bin/python - <<'EOF'
import asyncio
from core.discord_approval import post_approval_request, poll_for_reaction, post_outcome, is_configured
from dotenv import load_dotenv
load_dotenv()

if not is_configured():
    print("ERROR: DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID not set in .env")
else:
    async def test():
        msg_id = await post_approval_request(
            summary="Test: OSPF dead timer mismatch on C1C",
            findings="| Finding | Detail | Status |\n|---------|--------|--------|\n| Test | This is a test approval request | ⚠️ |",
            commands=["! This is a test — no real commands"],
            devices=["C1C"],
            risk_level="low",
            issue_key=None,
            timeout_minutes=2,
        )
        print(f"Message posted: {msg_id}")
        print("React ✅ or ❌ on the Discord message within 2 minutes...")
        result = await poll_for_reaction(msg_id, timeout_minutes=2)
        print(f"Result: {result}")
        await post_outcome(msg_id, result["decision"], decided_by=result.get("approved_by") or result.get("rejected_by"))

    asyncio.run(test())
EOF
```

Expected: a Discord embed appears in `#noc-approvals` with ✅ and ❌ reactions. React to one, and the script prints the decision and posts an outcome reply.

---

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes (if using Discord) | Bot token from developer portal |
| `DISCORD_CHANNEL_ID` | Yes (if using Discord) | Channel ID of `#noc-approvals` |
| `APPROVAL_TIMEOUT_MINUTES` | No (default: 10) | Minutes to wait before expiring |

If `DISCORD_BOT_TOKEN` or `DISCORD_CHANNEL_ID` is missing, `request_approval` returns `{"decision": "skipped"}` and the agent logs to Jira that no approval channel is configured, then exits without pushing config. Configure Discord to enable remote approval.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Private application cannot have a default authorization link" | Install Link is set | Step 2: Set Install Link to None first |
| Bot appears in server but messages fail | Wrong permissions or channel ID | Verify Channel ID and re-check Step 6 permissions |
| Reactions added but poll returns expired | Bot's own reactions counted | Verify Message Content Intent is enabled (Step 5) |
| No mobile notification | Notification settings on default | Step 11: Set channel to All Messages |
| `is_configured()` returns False | Missing env vars | Check `.env` has both `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` with non-empty values |
