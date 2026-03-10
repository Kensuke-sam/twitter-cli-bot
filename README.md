# AI Twitter Bot (CLI-based) 🤖🐦

A highly efficient tool to generate and post tweets from your articles using local AI CLIs (Gemini, Codex, or Claude Code). No API keys needed for generation if you already have the CLIs configured.

## ✨ Features
- **Multi-AI Support**: Use `gemini`, `codex`, or `claude` CLI as your backend.
- **Article Integration**: Automatically extracts titles and slugs from your project files (e.g., Next.js posts list).
- **Interactive & Auto Modes**: Choose from 5 generated drafts or let the bot pick one randomly.
- **Zero-Config Generation**: Leverages your existing CLI authentication.

## 🚀 Getting Started

### 1. Installation
Ensure you have the following installed:
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [twitter-cli](https://github.com/jackwener/twitter-cli)
- One of the AI CLIs: `gemini`, `codex`, or `claude`

### 2. Configuration
Copy the sample config and fill in your details:
```bash
cp config.json.sample config.json
```

Edit `config.json`:
- `posts_file_path`: Path to your articles file (supports `.ts`, `.js`, `.json`).
- `base_url`: Your website's root URL.
- `twitter_cli_path`: Path to where `twitter-cli` is located.
- `twitter_auth_token` / `twitter_ct0`: (Optional) Your X session tokens.

### 3. Usage

#### Interactive Mode
Select an article and pick a tweet from 5 drafts.
```bash
./tweet.sh your-article-slug --ai gemini
```

#### Automatic Mode (Perfect for Cron)
Pick a random article and a random tweet draft, then post immediately.
```bash
./tweet.sh --auto --ai claude
```

## 📅 Scheduled Posting (Cron)
Example: Post 3 times a day (9 AM, 12 PM, 6 PM) with a random article.
```cron
0 9,12,18 * * * cd ~/twitter-cli-bot && ./tweet.sh --auto >> bot.log 2>&1
```

## 📂 Project Structure
- `tweet_gen.py`: Core logic for extraction and generation.
- `tweet.sh`: Runner script.
- `config.json`: Your private configuration (ignored by git).
