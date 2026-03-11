# twitter-cli-bot

[日本語版 README はこちら](./README.ja.md)

**AI-powered tweet generation from article URLs — no Twitter API key required.**

Generate tweet drafts using Gemini, Claude, or Codex CLI, then post them interactively or automatically via [twitter-cli](https://github.com/jackwener/twitter-cli).

> Built for developers who write blogs and want a CLI-first workflow for sharing content on X (Twitter).

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
$ ./tweet.sh generate https://example.com/my-article --ai gemini

Generating tweets using gemini CLI...

--- Generated Tweets ---

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

Choose a tweet to post (1-5, or 'q' to quit): 2

Posting to Twitter:
You wrote the article. Now automate the tweet. ...
Successfully posted!
```

---

## Features

- Generate tweet drafts from any article URL
- Supports Gemini, Claude Code, and Codex CLI as AI backends
- Interactive draft selection or fully automatic posting
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
└── config.json         # Your local config (gitignored)
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes
4. Open a pull request

Bug reports and feature requests are welcome via [Issues](https://github.com/Kensuke-sam/twitter-cli-bot/issues).

---

## Related

- [twitter-cli](https://github.com/jackwener/twitter-cli) — The underlying Twitter/X CLI this bot wraps
