# AskChatGPT

AskChatGPT is a mention-only OpenAI assistant for Red-DiscordBot. It uses the
conversation already visible in the current Discord channel or thread, answers
briefly, and does not maintain a separate transcript database.

## Behavior

- The assistant responds only when its Discord account is explicitly
  mentioned. Mention-prefix commands are left to Red's command system.
- Each request can include up to 20 recent messages from the same channel or
  thread. The recent-history scan stops at a 30-minute idle gap and never
  crosses channels.
- A same-channel replied-to message is included when available, even if it is
  older than that recent-history window. A bare mention is useful only when it
  replies to a message; otherwise the bot asks for a question.
- OpenAI receives structured JSON message cards with explicit speaker kinds
  instead of a flat, spoofable transcript.
- Responses default to one to three sentences, low verbosity, and low reasoning
  effort. The cog also caps output length.
- Only the requester, reply target, recent participants, and explicitly
  mentioned members receive identity cards. A card can contain the Discord user
  ID, current names, bot status, relevant server roles, owner/moderator status,
  and that member's optional self-written profile.
- Generated replies suppress Discord mentions so model output cannot ping
  members or roles.

## Install and configure

Install the cog through Red's Downloader, then configure the API key through
Red's shared-token command (replace `[p]` with the bot's prefix):

This release requires Red-DiscordBot 3.5.24 or newer and Python 3.9 or newer.

```text
[p]set api openai api_key,YOUR_OPENAI_API_KEY
[p]load askchatgpt
```

Do not paste an API key into a normal server message. Model settings are owner
only.

The bot needs Discord's Message Content intent and these channel permissions:

- View Channel
- Read Message History
- Send Messages
- Attach Files (for image generation)

## Use

Mention the bot with a question:

```text
@MyBot summarize the decision above
```

You can also reply to a message and mention the bot without adding text. Chat
requests are intentionally not exposed as a prefix command.

Members may opt in to a short server profile, or clear it at any time:

```text
[p]askgpt profile
[p]askgpt profile @Member
[p]askgpt profile set Preferred name: Dee; pronouns: they/them; builds robots
[p]askgpt profile clear
```

Profiles are not private: other server members can view them with the profile
command. They should contain only information the member wants visible in the
server and shared with OpenAI when relevant to a request.

Bot owners can inspect or change the selected models:

```text
[p]askgpt status
[p]askgpt model gpt-5.6-luna
[p]askgpt imagemodel gpt-image-2
```

Supported text choices are `gpt-5.6-luna`, `gpt-5.6-terra`, and
`gpt-5.6-sol`. Image generation is restricted to `gpt-image-2` so its output
can be validated and uploaded safely.

Image generation remains a separate, rate-limited command:

```text
[p]generateimage a tiny watercolor robot tending a rooftop garden
```

## Privacy and retention

When someone tags the bot, the cog sends the question, bounded recent context,
and relevant identity cards to OpenAI. This can include message text, display
names, role names, Discord user IDs, and opted-in profile text. The cog does not
persist those conversation messages as its own history.

The `generateimage` command sends its image prompt to OpenAI. The cog does not
persist image prompts.

Optional profiles are stored in Red's configuration until the member clears
them or their Red data is deleted. OpenAI Responses requests set `store=False`
and use a one-way safety identifier rather than sending the raw Discord ID in
that field. OpenAI may still retain abuse-monitoring logs under its applicable
data-retention policy.

Server owners should disclose this processing to members and restrict the
bot's channel access to places where it is appropriate.

## Maintainer checks

The repository includes dependency-free contract tests. Run them from the
repository root:

```text
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q askchatgpt
```

Before release, manually verify:

1. An untagged message produces no reply.
2. A tag in one channel cannot import context from another channel.
3. A gap longer than 30 minutes stops context collection.
4. A reply plus a bare tag includes the replied-to message.
5. Only the requester, reply target, recent participants, or explicitly
   mentioned people appear in identity cards.
6. A profile can be set, shown, cleared, and removed through Red's user-data
   deletion hook.
7. Non-owners cannot change models or credentials.
8. Rapid text and image requests hit their respective limits cleanly.
9. Generated output containing `@everyone`, role text, or a user mention does
   not create a Discord ping.
10. Authentication, rate-limit, network, and model errors produce short public
    messages without exposing secrets or raw provider responses.
