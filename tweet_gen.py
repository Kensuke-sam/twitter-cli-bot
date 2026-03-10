import os
import sys
import re
import subprocess
import random
import argparse
from pathlib import Path

# --- Configuration ---
POSTS_FILE = Path("koteihi-zero/src/lib/posts.ts")
TWITTER_CLI_DIR = Path("twitter-cli")
BASE_URL = "https://koteihi-zero.com"

# --- Prompt Template ---
PROMPT_TEMPLATE = """あなたはSNSマーケターです。
「固定費ゼロ研究所」のX投稿（140文字以内、フックあり、断定的、具体例あり、最後に記事リンク）を5つ作ってください。
出力はツイート内容のみを1行ずつ出力してください。

記事URL: {url}
記事タイトル: {title}
"""

def get_post_data(slug):
    if not POSTS_FILE.exists():
        # Fallback for when running from inside the bot directory
        alternative_path = Path("../koteihi-zero/src/lib/posts.ts")
        if alternative_path.exists():
            content = alternative_path.read_text(encoding="utf-8")
        else:
            print(f"Error: {POSTS_FILE} not found.")
            sys.exit(1)
    else:
        content = POSTS_FILE.read_text(encoding="utf-8")
        
    pattern = rf"slug:\s*\"{re.escape(slug)}\".*?title:\s*\"(.*?)\".*?excerpt:\s*\"(.*?)\""
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print(f"Error: Post with slug '{slug}' not found.")
        sys.exit(1)
        
    return {
        "title": match.group(1),
        "url": f"{BASE_URL}/posts/{slug}"
    }

def generate_tweets_with_cli(post_data, ai_cli="gemini"):
    prompt = PROMPT_TEMPLATE.format(url=post_data["url"], title=post_data["title"])
    
    print(f"Generating tweets using {ai_cli} CLI...")
    
    try:
        if ai_cli == "gemini":
            cmd = ["gemini", prompt]
        elif ai_cli == "codex":
            cmd = ["codex", prompt]
        elif ai_cli == "claude":
            # Claude Code CLI
            cmd = ["claude", prompt]
        else:
            cmd = ["gemini", prompt]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        content = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error calling {ai_cli} cli: {e}\nOutput: {e.output}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: '{ai_cli}' command not found. Please make sure the {ai_cli} CLI is installed and in your PATH.")
        sys.exit(1)
    
    # ツイートを分割（空行や番号を除去）
    lines = content.strip().split("\n")
    tweets = [re.sub(r'^\d+[\.、]\s*', '', line).strip() for line in lines if line.strip()]
    
    return tweets[:5]

def post_to_twitter(tweet_text):
    print(f"\nPosting to Twitter:\n{tweet_text}")
    # twitter-cli ディレクトリが存在するか確認
    cwd = TWITTER_CLI_DIR if TWITTER_CLI_DIR.exists() else Path("../twitter-cli")
    cmd = ["uv", "run", "twitter", "post", tweet_text]
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
        print("Successfully posted!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to post: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate and post tweets using AI CLIs.")
    parser.add_argument("input", nargs="?", help="URL or slug of the article")
    parser.add_argument("--auto", action="store_true", help="Automatically pick and post a tweet")
    parser.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="Choose AI CLI backend (gemini, codex, claude)")
    args = parser.parse_args()
    
    # 記事データの読み込み
    try:
        path = POSTS_FILE if POSTS_FILE.exists() else Path("../koteihi-zero/src/lib/posts.ts")
        content = path.read_text(encoding="utf-8")
        slugs = re.findall(r'slug:\s*"(.*?)"', content)
    except Exception as e:
        print(f"Error reading posts: {e}")
        sys.exit(1)

    if not args.input:
        slug = random.choice(slugs)
        print(f"Picked random article: {slug}")
    else:
        slug = args.input.split("/")[-1]
    
    post_data = get_post_data(slug)
    tweets = generate_tweets_with_cli(post_data, ai_cli=args.ai)
    
    if not tweets:
        print("Error: No tweets generated.")
        sys.exit(1)
        
    if args.auto:
        tweet = random.choice(tweets)
        post_to_twitter(tweet)
        return

    print(f"\n--- Generated Tweets for: {post_data['title']} ---")
    for i, t in enumerate(tweets, 1):
        print(f"\n[{i}]\n{t}")
        print("-" * 20)
        
    while True:
        try:
            choice = input("\nChoose a tweet to post (1-5, or 'q' to quit): ")
            if choice.lower() == 'q': break
            idx = int(choice) - 1
            if 0 <= idx < len(tweets):
                post_to_twitter(tweets[idx])
                break
        except ValueError: pass

if __name__ == "__main__":
    main()
