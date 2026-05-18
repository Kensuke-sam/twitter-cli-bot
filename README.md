# twitter-cli-bot

[日本語版 README はこちら](./README.ja.md)

**AI-powered tweet generation from article URLs — no Twitter API key required.**

Generate tweet drafts using Gemini, Claude, or Codex CLI, then post them interactively or automatically via [twitter-cli](https://github.com/jackwener/twitter-cli).

> Built for developers who write blogs and want a CLI-first workflow for sharing content on X (Twitter).

> **Warning — read this first.** This tool reads from and posts to X (Twitter) through **unofficial, browser-cookie-based automation** ([twitter-cli](https://github.com/jackwener/twitter-cli)) — **not** the official X API. This may violate X's Terms of Service and can get your account **rate-limited, suspended, or permanently banned**. It is provided as-is for educational and personal use, with no warranty. Read the [Disclaimer](#disclaimer) before using it.

---

## Disclaimer

This project does **not** use the official X API. It wraps [twitter-cli](https://github.com/jackwener/twitter-cli), which authenticates with **browser session cookies** (`auth_token`, `ct0`) and accesses X (Twitter) the way a logged-in browser would.

**Terms of Service.** Accessing X by automated means outside the official API — automated reading, scraping, and automated posting — may breach the [X Terms of Service](https://x.com/en/tos), the [X Developer Agreement and Policy](https://developer.x.com/en/developer-terms/agreement-and-policy), and the [X Automation Rules](https://help.x.com/en/rules-and-policies/x-automation).

**Account risk.** Automated and bulk activity — `--auto`, `generate-batch`, `engage` (auto-like), `recycle`, and cron-scheduled posting — is exactly the behavior X's anti-spam and automation rules restrict. Using these features can get your account **rate-limited, suspended, or permanently banned**, and X may act without warning. The unofficial cookie-based mechanism can also stop working at any time if X changes its internals.

**Your responsibility.**

- Use this tool **only on an account you personally own**. Never use it on accounts you do not control.
- **You are responsible for everything posted**, including AI-generated text. Review drafts before posting, and be especially careful with fully automatic modes (`--auto`, `chain`, cron).
- Do not use it for spam, mass following, mass engagement, or anything else prohibited by X.
- When generating tweets from an article, respect the source's copyright — summarize and credit the source rather than copying text verbatim.

**No warranty.** This software is provided "as is", without warranty of any kind. The author accepts **no liability** for account suspension, data loss, or any other damage arising from its use. **Use it at your own risk.** If you need a fully compliant solution, use the [official X API](https://developer.x.com/en/docs/x-api) instead.

---

## Why this project exists

Managing social media as a developer is tedious. This tool fits into an existing CLI workflow:

1. You write an article
2. Pass the URL to this tool
3. Your AI CLI generates 5 tweet drafts
4. You pick one (or let it auto-post)

No browser, no dashboard, no Twitter API billing.

---

## What this tool does

- Accepts an article URL or slug as input
- Calls Gemini / Claude / Codex CLI to generate 5 tweet drafts
- Lets you select a draft interactively, or auto-posts one (for cron jobs)
- Wraps the full feature set of twitter-cli: timeline, bookmarks, search, like, follow, and more

---

## Demo

```
$ ./tweet.sh generate https://example.com/my-article --ai gemini --tone provocative

Generating tweets using gemini CLI...
Tone: provocative

--- Generated Tweets for: https://example.com/my-article ---

[1]
Most developers ship without thinking about X distribution.
Here's how to fix that automatically from your CLI.
https://example.com/my-article
--------------------
[2]
You wrote the article. Now automate the tweet.
A CLI-first approach to content distribution.
https://example.com/my-article
--------------------
[3]
Stop copy-pasting blog URLs into Twitter manually.
This shell script does it for you.
https://example.com/my-article
--------------------

番号で選択 (1-3), 'e数字' で編集 (例: e1), 'q' で中止: e2

新しいテキスト:
Automate your content distribution from the terminal.
https://example.com/my-article

[2] (編集済み)
Automate your content distribution from the terminal.
https://example.com/my-article
--------------------

番号で選択 (1-3), 'e数字' で編集 (例: e1), 'q' で中止: 2

Successfully posted!
```

---

## Features

- Generate tweet drafts from any article URL
- **Free-form generation** (`--topic`) — generate tweets about any theme without a URL
- Supports Gemini, Claude Code, and Codex CLI as AI backends
- Interactive draft selection or fully automatic posting
- **Thread generation** — generate and post multi-tweet threads from articles or any topic
- **Tone presets** (`--tone`) — professional, casual, provocative, technical, humorous
- **Post history** (SQLite) — duplicate detection, `history` and `stats` subcommands
- **Smart auto mode** — `--auto` skips already-posted articles automatically
- **Batch generation** (`generate-batch`) — process all unposted articles at once
- **AI improve** (`improve`) — polish a draft text into tweet-ready form
- **AI reply suggestions** (`reply-suggest`) — generate reply drafts for any tweet
- **Timeline digest** (`digest`) — AI-powered summary of your timeline
- **Auto-engage** (`engage`) — auto-like tweets matching keywords
- **Recycle** (`recycle`) — rephrase past posts for re-posting
- **User analysis** (`analyze`) — AI-powered analysis of any user's posting patterns
- **Translate** (`translate`) — translate tweets for cross-posting (en, ja, zh, ko, es, fr, de, pt)
- **Trend analysis** (`trending`) — AI analysis of keyword trends from latest tweets
- **Chain workflow** (`chain`) — generate → improve → post/schedule in one command
- **Draft management** (`draft-save/list/edit/post/delete`) — local draft storage with SQLite
- **Schedule queue** (`schedule-add/list/run/remove`) — queue tweets for timed posting via cron
- **Character count** — displays character count per tweet, warns if >280
- **Dry-run mode** (`--dry-run`) — preview without posting
- **Clipboard mode** (`--clipboard`) — copy to clipboard instead of posting
- **Edit before posting** — modify generated tweets inline or via `$EDITOR`
- **Config validation** — clear error messages for misconfigured settings
- Cron-compatible for scheduled posting
- Full twitter-cli wrapper: `feed`, `search`, `bookmarks`, `like`, `follow`, and more
- No Twitter API key needed — uses browser cookies via twitter-cli
- Minimal config — only `twitter_cli_path` is required to get started

---

## Use Cases

- Developers sharing blog posts on X
- CLI-first content automation workflows
- AI-assisted social media posting
- Scheduled content distribution via cron

---

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv)
- [twitter-cli](https://github.com/jackwener/twitter-cli) (cloned locally)
- At least one AI CLI: `gemini`, `codex`, or `claude`

---

## Installation

```bash
git clone https://github.com/Kensuke-sam/twitter-cli-bot
cd twitter-cli-bot
cp config.json.sample config.json
```

Edit `config.json` with your settings (see Configuration below), then authenticate twitter-cli:

```bash
cd /path/to/twitter-cli
uv run twitter whoami
```

See [twitter-cli authentication docs](https://github.com/jackwener/twitter-cli) for details.

---

## Configuration

Minimum required config:

```json
{
  "twitter_cli_path": "/path/to/twitter-cli"
}
```

Full config with all options:

```json
{
  "twitter_cli_path": "/path/to/twitter-cli",

  "site_name": "My Blog",
  "base_url": "https://your-domain.com",
  "posts_file_path": "/path/to/posts.ts",
  "prompt_template": "Write 5 tweets about this article...\n\nURL: {url}\nTitle: {title}",

  "twitter_auth_token": "",
  "twitter_ct0": ""
}
```

| Key | Required | Description |
|-----|----------|-------------|
| `twitter_cli_path` | Yes | Path to a local clone of twitter-cli |
| `site_name` | `generate` (posts file mode) only | Site name used in the AI prompt |
| `base_url` | `generate` (posts file mode) only | Your site's root URL |
| `posts_file_path` | `generate` (posts file mode) only | Path to your articles data file (`.ts`, `.js`, `.json`) |
| `prompt_template` | No | Custom AI prompt template. Falls back to a built-in default |
| `twitter_auth_token` / `twitter_ct0` | No | Optional. twitter-cli auto-extracts from browser cookies |

> **Note:** `generate` accepts a URL directly (`./tweet.sh generate https://...`), so the site-related keys are only needed if you want to pull articles from a local posts file.

---

## Usage

### Generate and post tweets

```bash
# Pass a URL directly
./tweet.sh generate https://example.com/my-article --ai gemini

# Use a slug from your posts file
./tweet.sh generate my-article-slug --ai claude

# Auto-post a random draft (for cron)
./tweet.sh generate https://example.com/my-article --auto --ai codex

# Auto-pick a random article from your posts file and post
./tweet.sh generate --auto

# Preview without posting
./tweet.sh generate https://example.com/my-article --dry-run

# Use a specific tone
./tweet.sh generate https://example.com/my-article --tone provocative

# Force post even if the URL was posted before
./tweet.sh generate https://example.com/my-article --force

# Free-form: generate tweets about any topic (no URL needed)
./tweet.sh generate --topic "Rust vs Go for CLI tools"
./tweet.sh generate "Today I learned about WebAssembly" --tone casual

# Copy to clipboard instead of posting
./tweet.sh generate https://example.com/my-article --clipboard
```

### Generate and post threads

```bash
# Generate a 4-tweet thread (default)
./tweet.sh generate-thread https://example.com/my-article --ai gemini

# Generate a 6-tweet thread with a casual tone
./tweet.sh generate-thread https://example.com/my-article --count 6 --tone casual

# Free-form thread about any topic (no URL needed)
./tweet.sh generate-thread --topic "The evolution of CLI tools"

# Preview a thread without posting
./tweet.sh generate-thread https://example.com/my-article --dry-run
```

### Post history

```bash
# View recent post history
./tweet.sh history

# View last 50 posts
./tweet.sh history --max 50

# Clear all history
./tweet.sh history-clear

# View posting statistics
./tweet.sh stats

# Export history to JSON
./tweet.sh history --json
./tweet.sh history --json -o history.json
```

### Batch generation

```bash
# Preview all unposted articles (dry-run)
./tweet.sh generate-batch --dry-run --ai gemini

# Post all unposted articles
./tweet.sh generate-batch --ai gemini --tone professional

# Post up to 5 unposted articles
./tweet.sh generate-batch --max 5 --ai gemini
```

### AI-assisted operations

```bash
# Improve a draft text into tweet-ready form
./tweet.sh improve "I built a CLI tool for Twitter" --ai gemini --tone professional

# Preview improvements without posting
./tweet.sh improve "I built a CLI tool for Twitter" --dry-run

# Generate reply suggestions for a tweet
./tweet.sh reply-suggest 1234567890 --ai gemini --tone casual

# Preview reply suggestions without posting
./tweet.sh reply-suggest 1234567890 --dry-run

# Get an AI summary of your timeline
./tweet.sh digest --ai gemini --max 30

# Auto-like tweets matching keywords
./tweet.sh engage "Rust CLI" "developer tools" --max 5
./tweet.sh engage "AI agent" --dry-run

# Rephrase and re-post a past tweet
./tweet.sh recycle --ai gemini --tone humorous
./tweet.sh recycle --dry-run
```

### User analysis and trends

```bash
# Analyze a user's posting patterns
./tweet.sh analyze username --ai gemini --max 30

# Analyze trends for a keyword
./tweet.sh trending "AI agent" --ai gemini --max 30
```

### Translate and cross-post

```bash
# Translate a tweet to English
./tweet.sh translate "CLIからTwitterを自動化する話" --lang en --ai gemini

# Translate to Korean
./tweet.sh translate "Built a CLI tool for Twitter" --lang ko

# Preview translation without posting
./tweet.sh translate "テスト" --lang en --dry-run
```

### Draft management

```bash
# Save a draft locally
./tweet.sh draft-save "Work in progress tweet" --tone casual

# List all drafts
./tweet.sh draft-list

# Edit a draft
./tweet.sh draft-edit 1

# Post a draft
./tweet.sh draft-post 1

# Delete a draft
./tweet.sh draft-delete 1
```

### Chain workflow (generate → improve → post)

```bash
# Full workflow: generate, improve, then post
./tweet.sh chain https://example.com/my-article --ai gemini --tone professional

# Chain with scheduled posting
./tweet.sh chain --topic "Rust vs Go" --ai gemini --at "2026-04-06T18:00"

# Chain with dry-run
./tweet.sh chain https://example.com/my-article --dry-run
```

### Schedule queue

```bash
# Add a tweet to the schedule queue
./tweet.sh schedule-add "Scheduled tweet text" --at "2026-04-06T18:00"

# View the schedule queue
./tweet.sh schedule-list

# Post all tweets whose scheduled time has passed
./tweet.sh schedule-run

# Preview without posting
./tweet.sh schedule-run --dry-run

# Remove a tweet from the queue
./tweet.sh schedule-remove 3
```

To auto-post scheduled tweets via cron:

```cron
*/5 * * * * cd ~/twitter-cli-bot && ./tweet.sh schedule-run >> bot.log 2>&1
```

### Read operations

```bash
./tweet.sh feed                            # Home timeline
./tweet.sh feed -t following --max 30      # Following timeline
./tweet.sh bookmarks --max 20              # Bookmarks
./tweet.sh search "AI agent" -t Latest     # Search tweets
./tweet.sh tweet 1234567890                # Tweet detail
./tweet.sh user-posts username --max 20    # User's tweets
./tweet.sh likes username                  # User's likes
./tweet.sh followers username --max 50     # Followers
./tweet.sh following username              # Following
./tweet.sh user username                   # User profile
./tweet.sh whoami                          # Current authenticated user
./tweet.sh status                          # Auth status check
```

### Write operations

```bash
./tweet.sh post "Hello from twitter-cli-bot!"
./tweet.sh reply 1234567890 "Great post!"
./tweet.sh quote 1234567890 "Interesting take"
./tweet.sh like 1234567890
./tweet.sh retweet 1234567890
./tweet.sh bookmark 1234567890
./tweet.sh follow username
./tweet.sh delete 1234567890
```

### Output formats

Most read commands support `--yaml`, `--json`, `-c` (compact), and `-o FILE`:

```bash
./tweet.sh feed --json | jq '.[0].text'
./tweet.sh search "rust" --max 10 -c
./tweet.sh bookmarks --yaml -o bookmarks.yaml
```

---

## Automation (Cron)

Post automatically 3 times a day using a random article:

```cron
0 9,12,18 * * * cd ~/twitter-cli-bot && ./tweet.sh generate --auto >> bot.log 2>&1
```

---

## Security Notes

- **Never commit `config.json`** — it is gitignored by default, keep it that way
- **Do not share browser cookies** — `twitter_auth_token` and `twitter_ct0` are session credentials
- **Use only on accounts you own** — do not use this tool on accounts you do not control
- **Twitter/X may change behavior** — unofficial cookie-based auth can break without notice

---

## Project Structure

```
twitter-cli-bot/
├── tweet.sh            # Entry point
├── tweet_gen.py        # All subcommand logic
├── config.json.sample  # Configuration template
├── config.json         # Your local config (gitignored)
└── history.db          # Post history (gitignored, auto-created)
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes
4. Open a pull request

Bug reports and feature requests are welcome via [Issues](https://github.com/Kensuke-sam/twitter-cli-bot/issues).

---

## Next project

This CLI wrapper is the execution-layer foundation.

The next-generation project built on top of this idea is:
- [twitter-ai-agent](https://github.com/Kensuke-sam/twitter-ai-agent): lightweight CLI-first AI posting engine with history, scoring, and autopilot workflow

---

## Related

- [twitter-cli](https://github.com/jackwener/twitter-cli) — The underlying Twitter/X CLI this bot wraps
