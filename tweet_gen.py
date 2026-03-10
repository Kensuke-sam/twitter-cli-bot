import os
import sys
import re
import subprocess
import json
import random
import argparse
from pathlib import Path

# --- Configuration ---
POSTS_FILE = Path("koteihi-zero/src/lib/posts.ts")
TWITTER_CLI_DIR = Path("twitter-cli")
BASE_URL = "https://koteihi-zero.com"

# --- Prompt Template ---
PROMPT_TEMPLATE = """あなたはSNSマーケターです。

目的
「固定費ゼロ研究所」のX投稿を作る

テーマ
固定費削減 / クレカ / 通信費 / サブスク / 投資

ターゲット
大学生〜20代

ルール
・140文字以内
・最初にフック
・断定的
・具体例あり
・最後に記事リンク

投稿構造
①問題提起
②具体例
③解決
④リンク

記事URL
{url}

記事タイトル
{title}

5ツイート作る。
出力はツイートのみを並べてください。余計な解説は不要です。
"""

def get_post_data(slug):
    if not POSTS_FILE.exists():
        print(f"Error: {POSTS_FILE} not found.")
        sys.exit(1)
        
    content = POSTS_FILE.read_text(encoding="utf-8")
    pattern = rf"slug:\s*\"{re.escape(slug)}\".*?title:\s*\"(.*?)\".*?excerpt:\s*\"(.*?)\""
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print(f"Error: Post with slug '{slug}' not found in {POSTS_FILE}.")
        sys.exit(1)
        
    return {
        "title": match.group(1),
        "excerpt": match.group(2),
        "url": f"{BASE_URL}/posts/{slug}"
    }

def generate_tweets(post_data):
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash') # 最新の高速モデルを使用
    
    prompt = PROMPT_TEMPLATE.format(url=post_data["url"], title=post_data["title"])
    
    print("Generating tweets with Gemini...")
    response = model.generate_content(prompt)
    content = response.text
    
    # AIの出力を分割（1. 2. などの番号付き、または改行区切りを想定）
    lines = content.strip().split("\n")
    tweets = []
    current_tweet = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_tweet:
                tweets.append("\n".join(current_tweet))
                current_tweet = []
            continue
            
        # 番号付きリスト（1. 2. など）の開始を検知
        if re.match(r'^\d+[\.、]\s*', line):
            if current_tweet:
                tweets.append("\n".join(current_tweet))
            current_tweet = [re.sub(r'^\d+[\.、]\s*', '', line)]
        else:
            current_tweet.append(line)
            
    if current_tweet:
        tweets.append("\n".join(current_tweet))
        
    # クリーンアップ
    tweets = [t.strip() for t in tweets if t.strip()]
    return tweets[:5]

def post_to_twitter(tweet_text):
    print(f"\nPosting to Twitter:\n{tweet_text}")
    cmd = ["uv", "run", "twitter", "post", tweet_text]
    try:
        subprocess.run(cmd, cwd=TWITTER_CLI_DIR, check=True)
        print("Successfully posted!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to post: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate and post tweets from articles using Gemini.")
    parser.add_argument("input", nargs="?", help="URL or slug of the article (optional, random if omitted)")
    parser.add_argument("--auto", action="store_true", help="Automatically pick and post a tweet (non-interactive)")
    args = parser.parse_args()
    
    input_val = args.input
    
    if not input_val:
        content = POSTS_FILE.read_text(encoding="utf-8")
        slugs = re.findall(r'slug:\s*"(.*?)"', content)
        if not slugs:
            print("Error: No slugs found in posts.ts")
            sys.exit(1)
        slug = random.choice(slugs)
        print(f"No input provided. Picked random article: {slug}")
    else:
        slug = input_val.split("/")[-1]
    
    post_data = get_post_data(slug)
    tweets = generate_tweets(post_data)
    
    if not tweets:
        print("Error: Failed to generate tweets.")
        sys.exit(1)
        
    if args.auto:
        tweet = random.choice(tweets)
        print(f"Auto-mode: Picked a random tweet.")
        post_to_twitter(tweet)
        return

    print(f"\n--- Generated Tweets for: {post_data['title']} ---")
    for i, tweet in enumerate(tweets, 1):
        print(f"\n[{i}]\n{tweet}")
        print("-" * 20)
        
    while True:
        try:
            choice = input("\nChoose a tweet to post (1-5, or 'q' to quit): ")
            if choice.lower() == 'q':
                break
            idx = int(choice) - 1
            if 0 <= idx < len(tweets):
                post_to_twitter(tweets[idx])
                break
            else:
                print("Invalid choice. Please select 1-5.")
        except ValueError:
            print("Please enter a number.")

if __name__ == "__main__":
    main()
