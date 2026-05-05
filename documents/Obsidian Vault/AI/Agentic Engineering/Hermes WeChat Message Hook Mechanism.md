# Hermes WeChat Message Hook Mechanism

Updated: 2026-05-05

## One-sentence summary

Hermes connects to WeChat by acting as a message gateway: it continuously receives new WeChat events from an external WeChat/iLink service, converts them into Hermes' standard message format, runs the agent pipeline, then sends the answer back through the same service.

## The core idea

The "message hook" is not a low-level hook into the WeChat desktop app. It is a higher-level integration point between WeChat and Hermes.

Conceptually, it works like this:

```text
WeChat message
  → WeChat/iLink bridge
  → Hermes gateway
  → Hermes message event
  → authorization / session / agent logic
  → agent response
  → WeChat/iLink bridge
  → WeChat reply
```

So the hook is best understood as a bridge-plus-dispatch mechanism, not as app injection, screen scraping, or local database watching.

## Why a bridge is needed

Hermes itself does not live inside WeChat. It needs some way to observe incoming WeChat messages and send outgoing replies.

The WeChat/iLink side provides that transport layer:

- It exposes new messages to Hermes.
- It gives Hermes enough identity/context to know who sent the message.
- It accepts Hermes' outgoing response and delivers it back to the WeChat conversation.

Hermes then provides the intelligence layer:

- It decides whether the sender is allowed.
- It maps the conversation to a session.
- It prepares context for the agent.
- It runs the model and tools.
- It formats and returns the response.

## The main principle: normalize first, then dispatch

A key design principle is that WeChat-specific details are isolated near the gateway edge.

Incoming WeChat data may have its own structure, ids, media representation, and context fields. Hermes converts that into a common internal message abstraction. Once normalized, the rest of Hermes can treat WeChat similarly to Telegram, Discord, Slack, or other messaging platforms.

This keeps the system modular:

- WeChat transport concerns stay in the WeChat adapter.
- Shared message-processing concerns stay in the gateway pipeline.
- Agent reasoning stays platform-independent.
- Tools and memory do not need to know whether the user came from WeChat.

## The hook layers, conceptually

There are three useful levels of "hooking" in this architecture.

### 1. Transport hook

This is the WeChat/iLink connection. It is responsible for getting messages in and sending messages out.

Use this level only when changing the WeChat transport itself: login, polling, delivery, media handling, or connection reliability.

### 2. Gateway dispatch hook

This is the best place for custom behavior before a WeChat message reaches the agent.

At this level, custom logic can decide:

- Let the message continue normally.
- Rewrite the message before the agent sees it.
- Drop or handle the message without invoking the agent.

This is the practical place for message routing rules, custom commands, allowlists, handoff logic, and WeChat-specific preprocessing.

### 3. Lifecycle/event hooks

These hooks observe what Hermes is doing after dispatch begins: session starts, agent starts, agent finishes, commands run, etc.

They are useful for logging, analytics, monitoring, notifications, and side effects. They are less suitable for deciding whether an inbound WeChat message should reach the agent, because they happen later in the lifecycle.

## How responses return to WeChat

After the agent finishes, Hermes hands the response back to the WeChat adapter. The adapter translates the response into a WeChat-deliverable message and sends it through the same bridge.

The important principle is symmetry:

```text
Inbound:  WeChat-specific message → Hermes-standard event
Outbound: Hermes-standard response → WeChat-specific message
```

This symmetry lets Hermes keep the core agent loop independent from the messaging platform.

## Why this design is useful

This architecture has several advantages:

- It avoids fragile desktop automation.
- It avoids depending on local WeChat app internals.
- It lets Hermes support WeChat using the same gateway model as other platforms.
- It keeps custom behavior extensible through gateway/plugin hooks.
- It allows policy, session, model, and tool behavior to remain consistent across messaging channels.

## Mental model

Think of Hermes WeChat support as four layers:

```text
1. WeChat transport layer
   Receives and sends messages through the WeChat/iLink bridge.

2. Gateway normalization layer
   Converts WeChat messages into Hermes' common message event shape.

3. Dispatch and policy layer
   Applies authorization, sessions, command handling, custom hooks, and routing.

4. Agent layer
   Runs the LLM/tool loop and produces the final response.
```

A "message hook" can refer to any of these layers, but for most customization work the right layer is the dispatch/policy layer, not the low-level transport layer.

## Practical takeaway

For Hermes + WeChat, the principled approach is:

- Do not hook the desktop WeChat app directly.
- Use the WeChat/iLink bridge as the transport.
- Normalize all inbound messages into Hermes message events.
- Put custom routing/rewrite/drop behavior at the gateway dispatch hook.
- Keep the agent layer platform-agnostic.
- Use lifecycle hooks for observation and automation after dispatch.

This keeps the integration robust, understandable, and easier to extend.

## Implementation summary with code references

The Hermes WeChat implementation is easiest to understand as a small pipeline: receive from iLink, normalize into a Hermes event, run the common gateway/agent logic, then send the answer back through iLink.

### 1. WeChat transport adapter

The platform-specific code lives in `gateway/platforms/weixin.py` ([source](https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/weixin.py)). The main class is `WeixinAdapter`.

Human meaning: this file is the WeChat boundary. It knows about iLink API details, WeChat user IDs, context tokens, media upload, and WeChat-specific message formatting. The rest of Hermes should not need to care about those details.

### 2. Inbound receive path

On startup, `WeixinAdapter.connect()` restores local state, opens HTTP sessions, and starts `_poll_loop()`.

The receive loop is:

```text
WeixinAdapter.connect()
  → _poll_loop()
  → _get_updates()
  → _message_to_event()
```

What this does:

- `_get_updates()` calls iLink `ilink/bot/getupdates` to long-poll for new WeChat messages.
- `get_updates_buf` is the cursor that tells iLink where Hermes left off; Hermes persists it under `~/.hermes/weixin/accounts/` so restarts do not reread old messages.
- `_message_to_event()` converts a raw iLink message into Hermes' common `MessageEvent` shape.
- Helpers like `_extract_text()`, `_collect_media()`, `_message_type_from_media()`, and `_guess_chat_type()` hide WeChat-specific parsing details.
- `MessageDeduplicator` prevents repeated processing of the same iLink `message_id`.

Reference: `gateway/platforms/weixin.py` ([source](https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/weixin.py)).

### 3. Gateway and agent dispatch

After WeChat data has been normalized, it enters the shared Hermes gateway pipeline.

```text
MessageEvent
  → BasePlatformAdapter.handle_message()
  → GatewayRunner._handle_message()
  → Hermes agent session
```

Human meaning: after this point, the message is no longer "special WeChat data". It is a normal Hermes platform message, so common behavior like authorization, session lookup, commands, model calls, tools, and memory can work the same way as Telegram/Discord/Slack.

Important files:

- `gateway/platforms/base.py` contains `BasePlatformAdapter.handle_message()` ([source](https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/base.py)).
- `gateway/run.py` contains `GatewayRunner._handle_message()` and the gateway dispatch/session logic ([source](https://github.com/NousResearch/hermes-agent/blob/main/gateway/run.py)).

### 4. Outbound reply path

When the agent produces a final response, Hermes sends it back through the WeChat adapter.

```text
agent response
  → WeixinAdapter.send()
  → _split_text()
  → _send_text_chunk()
  → _send_message()
  → iLink ilink/bot/sendmessage
```

What this does:

- `WeixinAdapter.send()` is the high-level send method for text/media replies.
- `_split_text()` and `_send_text_chunk()` keep long replies within WeChat/iLink delivery limits.
- `_send_message()` performs the actual iLink `sendmessage` API call.
- `ContextTokenStore` stores per-peer `context_token` values in `~/.hermes/weixin/accounts/<account_id>.context-tokens.json`; outbound text reuses the latest token so iLink can associate replies with the correct conversation context.
- Text payloads are represented as iLink `item_list` entries with `ITEM_TEXT`, `MSG_TYPE_BOT`, and `MSG_STATE_FINISH`.

Reference: `gateway/platforms/weixin.py` ([source](https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/weixin.py)).

### 5. Media and typing support

The same adapter also handles non-text details:

- Typing indicators: `_get_config()` fetches a `typing_ticket`, then `_send_typing()` sends `TYPING_START` or `TYPING_STOP` through `ilink/bot/sendtyping`.
- Media files: `_send_file()` and `_get_upload_url()` handle encrypted upload. Hermes encrypts media with AES-128-ECB before upload, then sends an iLink media reference instead of raw bytes.

Reference: `gateway/platforms/weixin.py` ([source](https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/weixin.py)).

### 6. Where to customize behavior

For most human-facing automation, do not edit the low-level iLink transport first. Prefer higher-level hooks:

- Use the plugin hook `pre_gateway_dispatch` to skip, rewrite, route, or allow messages before they reach the agent. Reference: `hermes_cli/plugins.py` ([source](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/plugins.py)).
- Use lifecycle/event hooks for observation and side effects such as logging, monitoring, or notifications. Reference: `gateway/hooks.py` ([source](https://github.com/NousResearch/hermes-agent/blob/main/gateway/hooks.py)).
- Edit `gateway/platforms/weixin.py` only when changing WeChat transport behavior itself: login, polling, context tokens, sendmessage, typing, or media delivery.

### Compact mental model

```text
WeChat/iLink event
  → weixin.py turns it into MessageEvent
  → base.py handles shared platform processing
  → run.py handles auth/session/agent dispatch
  → agent produces a reply
  → weixin.py sends it back with sendmessage
```

In short: `weixin.py` is the WeChat adapter, `base.py` is the common platform pipeline, `run.py` is the gateway brain, and `plugins.py` / `hooks.py` are the safest extension points.

## Schema details

This section records the important data shapes used by the WeChat/iLink integration. The source of truth is `gateway/platforms/weixin.py` for iLink-specific payloads and `gateway/platforms/base.py` for Hermes' normalized message objects.

### 1. iLink `getupdates` request

Hermes polls iLink for inbound WeChat messages with `_get_updates()`.

```json
{
  "get_updates_buf": "<sync cursor string>",
  "base_info": {
    "channel_version": "2.2.0"
  }
}
```

Important fields:

- `get_updates_buf`: sync cursor telling iLink where Hermes last stopped reading.
- `base_info.channel_version`: common iLink client metadata added by the API wrapper.

Human meaning: Hermes asks iLink, "Give me new messages after this cursor."

### 2. iLink `getupdates` response

```json
{
  "ret": 0,
  "msgs": [
    {
      "from_user_id": "<sender weixin id>",
      "to_user_id": "<bot/account or chat id>",
      "message_id": "<iLink message id>",
      "context_token": "<conversation context token>",
      "item_list": []
    }
  ],
  "get_updates_buf": "<new sync cursor string>"
}
```

Important fields:

- `ret`: iLink status code; `0` means success.
- `msgs`: raw inbound WeChat/iLink messages.
- `get_updates_buf`: next cursor; Hermes persists this locally under `~/.hermes/weixin/accounts/`.

### 3. Raw inbound iLink message

Hermes reads these fields when normalizing an inbound message:

```json
{
  "from_user_id": "<sender weixin id>",
  "to_user_id": "<recipient/bot/chat id>",
  "room_id": "<optional group id>",
  "chat_room_id": "<optional group id>",
  "message_id": "<message id for deduplication>",
  "msg_type": 1,
  "context_token": "<reply context token>",
  "item_list": [
    {
      "type": 1,
      "text_item": {
        "text": "hello"
      }
    }
  ]
}
```

Important fields:

- `from_user_id`: sender identity.
- `to_user_id`: recipient, bot, or chat identity.
- `room_id` / `chat_room_id`: group chat identity when present.
- `message_id`: used by `MessageDeduplicator` to avoid duplicate processing.
- `context_token`: saved separately by `ContextTokenStore` so later replies can use the same conversation context.
- `item_list`: the message body. Text and media are represented as typed items.

### 4. iLink `item_list` body items

Text item:

```json
{
  "type": 1,
  "text_item": {
    "text": "message text"
  }
}
```

Media items follow the same pattern: a numeric `type` plus a media-specific object such as `image_item`, `voice_item`, `file_item`, or `video_item`. Hermes uses helper functions like `_extract_text()` and `_collect_media()` to convert these into normalized text and local media paths.

Common item constants:

- `ITEM_TEXT = 1`
- `ITEM_IMAGE = 2`
- `ITEM_VOICE = 3`
- `ITEM_FILE = 4`
- `ITEM_VIDEO = 5`

### 5. Hermes normalized `MessageEvent`

After parsing iLink data, Hermes converts it into the platform-independent `MessageEvent` dataclass from `gateway/platforms/base.py`.

```python
@dataclass
class MessageEvent:
    text: str
    message_type: MessageType = MessageType.TEXT
    source: SessionSource = None
    raw_message: Any = None
    message_id: Optional[str] = None
    platform_update_id: Optional[int] = None
    media_urls: List[str] = field(default_factory=list)
    media_types: List[str] = field(default_factory=list)
    reply_to_message_id: Optional[str] = None
    reply_to_text: Optional[str] = None
    auto_skill: Optional[str | list[str]] = None
    channel_prompt: Optional[str] = None
    internal: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
```

Important mappings:

| Raw iLink data | Hermes field | Meaning |
|---|---|---|
| `item_list[*].text_item.text` | `text` | User-visible text |
| `from_user_id` | `source.user_id` | Sender identity |
| group/DM detection | `source.chat_id` | Conversation identity |
| `message_id` | `message_id` | Dedup/reference ID |
| full raw message | `raw_message` | Original platform payload |
| downloaded media files | `media_urls` | Local paths for media processing |
| media type hints | `media_types` | Normalized media categories |
| `context_token` | stored outside `MessageEvent` | Reused for outbound replies |

### 6. `MessageType` enum

```python
class MessageType(Enum):
    TEXT = "text"
    LOCATION = "location"
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    DOCUMENT = "document"
    STICKER = "sticker"
    COMMAND = "command"
```

Human meaning: WeChat-specific message/media forms are reduced to shared Hermes message categories.

### 7. Outbound iLink `sendmessage` request

When Hermes sends a text reply, `_send_message()` posts a wrapper payload shaped like this:

```json
{
  "msg": {
    "from_user_id": "",
    "to_user_id": "<recipient weixin id>",
    "client_id": "<unique hermes client id>",
    "message_type": 2,
    "message_state": 2,
    "context_token": "<optional context token>",
    "item_list": [
      {
        "type": 1,
        "text_item": {
          "text": "reply text"
        }
      }
    ]
  },
  "base_info": {
    "channel_version": "2.2.0"
  }
}
```

Important fields:

- `msg.from_user_id`: empty for bot-originated sends.
- `msg.to_user_id`: target Weixin user or chat.
- `msg.client_id`: Hermes-generated unique client message ID.
- `msg.message_type`: `MSG_TYPE_BOT`.
- `msg.message_state`: `MSG_STATE_FINISH`.
- `msg.context_token`: optional, but important for conversation continuity.
- `msg.item_list`: text/media body.

### 8. Typing and config schemas

`_get_config()` asks iLink for per-conversation config, especially the typing ticket:

```json
{
  "ilink_user_id": "<target user id>",
  "context_token": "<optional context token>",
  "base_info": {
    "channel_version": "2.2.0"
  }
}
```

`_send_typing()` sends typing state:

```json
{
  "ilink_user_id": "<target user id>",
  "typing_ticket": "<ticket from getconfig>",
  "status": 1,
  "base_info": {
    "channel_version": "2.2.0"
  }
}
```

Typical statuses:

- `TYPING_START = 1`
- `TYPING_STOP = 2`

### 9. Upload URL schema for media

Before sending media, Hermes asks iLink/CDN for an upload URL:

```json
{
  "filekey": "<generated file key>",
  "media_type": 3,
  "to_user_id": "<target user id>",
  "rawsize": 12345,
  "rawfilemd5": "<md5 of original file>",
  "filesize": 12352,
  "no_need_thumb": true,
  "aeskey": "<hex AES key>",
  "base_info": {
    "channel_version": "2.2.0"
  }
}
```

Human meaning: media is not sent as raw bytes in `sendmessage`. Hermes prepares/encrypts the file, gets an upload URL, uploads the encrypted bytes, then sends an iLink media reference.

### 10. Hermes `SendResult`

Normalized send result from `gateway/platforms/base.py`:

```python
@dataclass
class SendResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Any = None
    retryable: bool = False
```

Human meaning: every platform adapter can report send success/failure in a common shape.

### 11. Local persisted state schemas

Account/session state:

```json
{
  "token": "<redacted token>",
  "base_url": "https://ilinkai.weixin.qq.com",
  "user_id": "<weixin user id>",
  "saved_at": "<timestamp>"
}
```

Sync cursor state:

```json
{
  "get_updates_buf": "<cursor string>"
}
```

Context-token state:

```json
{
  "<peer_user_id>": "<context token>"
}
```

Human meaning: Hermes persists login/session data, polling position, and conversation context so the gateway can recover after restart.

## References

- Official Hermes Agent repository: https://github.com/NousResearch/hermes-agent
- Official Weixin / WeChat messaging docs: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/weixin.md
- Weixin runtime adapter source (`gateway/platforms/weixin.py`): https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/weixin.py
- Weixin gateway tests (`tests/gateway/test_weixin.py`): https://github.com/NousResearch/hermes-agent/blob/main/tests/gateway/test_weixin.py
- Common gateway platform base adapter (`gateway/platforms/base.py`): https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/base.py
- Gateway runner and dispatch source (`gateway/run.py`): https://github.com/NousResearch/hermes-agent/blob/main/gateway/run.py
- Hermes plugin hook system (`hermes_cli/plugins.py`): https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/plugins.py
- Gateway hooks implementation (`gateway/hooks.py`): https://github.com/NousResearch/hermes-agent/blob/main/gateway/hooks.py
- HermesClaw community WeChat bridge: https://github.com/AaronWong1999/hermesclaw
