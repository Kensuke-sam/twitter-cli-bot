# twitter-cli-bot

[日本語版 README はこちら](./README.ja.md)

A CLI wrapper that combines [twitter-cli](https://github.com/jackwener/twitter-cli) with local AI CLIs (Gemini, Codex, Claude) to generate and post tweets from your articles — and exposes the full feature set of twitter-cli through a single entry point.

> **No Twitter API key required.** Authentication is handled by twitter-cli via browser cookies.

## Features

- **AI-powered tweet generation** — Generate 5 tweet drafts from an article using Gemini, Codex, or Claude CLI
- **Interactive or auto mode** — Pick a draft manually, or let it post randomly (great for cron)
- **Full twitter-cli wrapper** — All read/write operations available as subcommands
- **Config-driven** — Works with any site/blog that stores posts as structured files

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv)
- [twitter-cli](https://github.com/jackwener/twitter-cli)
- At least one AI CLI: `gemini`, `codex`, or `claude`

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/Kensuke-sam/twitter-cli-bot
cd twitter-cli-bot
cp config.json.sample config.json
```

Edit `config.json`:

```json
{
  "site_name": "My Blog",
  "base_url": "https://your-domain.com",
  "posts_file_path": "/path/to/posts.ts",
  "twitter_cli_path": "/path/to/twitter-cli",
  "prompt_template": "...",
  "twitter_auth_token": "",
  "twitter_ct0": ""
}
```

| Key | Required for | Description |
|-----|-------------|-------------|
| `twitter_cli_path` | All commands | Path to a local clone of twitter-cli |
| `site_name` | `generate` (posts file mode) | Your site name, used in the prompt |
| `base_url` | `generate` (posts file mode) | Your site's root URL (e.g. `https://your-domain.com`) |
| `posts_file_path` | `generate` (posts file mode) | Path to your articles data file (`.ts`, `.js`, `.json`) |
| `prompt_template` | Optional | Custom AI prompt. Defaults to a generic URL-based prompt |
| `twitter_auth_token` / `twitter_ct0` | Optional | twitter-cli can auto-extract from browser cookies |

> **Minimum config:** only `twitter_cli_path` is required. The `generate` command accepts a URL directly, so site-related keys are only needed if you want to pull articles from a local posts file.

### 2. Authenticate twitter-cli

```bash
cd /path/to/twitter-cli
uv run twitter whoami
```

See [twitter-cli docs](https://github.com/jackwener/twitter-cli) for authentication details.

## Usage

### AI Tweet Generation

Pass a URL directly — no site configuration needed:

```bash
./tweet.sh generate https://example.com/some-article --ai gemini
```

Or use an article slug (requires `posts_file_path` in config):

```bash
./tweet.sh generate your-article-slug --ai gemini
```

Auto-pick and post immediately (for cron):

```bash
./tweet.sh generate https://example.com/some-article --auto --ai claude
```

Pick a random article from your posts file if no input is given:

```bash
./tweet.sh generate --auto
```

### Read Operations

```bash
./tweet.sh feed                          # Home timeline (For You)
./tweet.sh feed -t following --max 30    # Following timeline
./tweet.sh feed --yaml > tweets.yaml     # Export as YAML
./tweet.sh bookmarks --max 20            # Bookmarks
./tweet.sh search "AI agent" -t Latest   # Search tweets
./tweet.sh search "topic" --json -o results.json
./tweet.sh tweet 1234567890              # Tweet detail
./tweet.sh tweet https://x.com/user/status/123
./tweet.sh list 1539453138322673664      # List timeline
./tweet.sh user-posts elonmusk --max 20  # User's tweets
./tweet.sh likes elonmusk                # User's likes
./tweet.sh followers elonmusk --max 50   # Followers
./tweet.sh following elonmusk            # Following
./tweet.sh user elonmusk                 # User profile
./tweet.sh whoami                        # Current authenticated user
./tweet.sh status                        # Auth status check
```

### Write Operations

```bash
./tweet.sh post "Hello from twitter-cli-bot!"
./tweet.sh post "Reply text" --reply-to 1234567890
./tweet.sh reply 1234567890 "Great tweet!"
./tweet.sh quote 1234567890 "Interesting take"
./tweet.sh delete 1234567890
./tweet.sh like 1234567890
./tweet.sh unlike 1234567890
./tweet.sh retweet 1234567890
./tweet.sh unretweet 1234567890
./tweet.sh bookmark 1234567890
./tweet.sh unbookmark 1234567890
./tweet.sh follow elonmusk
./tweet.sh unfollow elonmusk
```

### Output Formats

Most read commands support `--yaml`, `--json`, `-c` (compact), and `-o FILE`:

```bash
./tweet.sh feed --json | jq '.[0].text'
./tweet.sh search "rust" --max 10 -c     # Compact, token-efficient for LLMs
./tweet.sh bookmarks --yaml -o bm.yaml
```

## Scheduled Posting (Cron)

Post 3 times a day with a randomly selected article and draft:

```cron
0 9,12,18 * * * cd ~/twitter-cli-bot && ./tweet.sh generate --auto >> bot.log 2>&1
```

## Project Structure

```
twitter-cli-bot/
├── tweet.sh            # Entry point
├── tweet_gen.py        # All subcommand logic
├── config.json.sample  # Configuration template
└── config.json         # Your local config (gitignored)
```

## Related

- [twitter-cli](https://github.com/jackwener/twitter-cli) — The underlying Twitter/X CLI this bot wraps
