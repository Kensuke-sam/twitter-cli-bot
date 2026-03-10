import os
import sys
import re
import subprocess
import random
import argparse
import json
from pathlib import Path


def load_config():
    config_path = Path("config.json")
    if not config_path.exists():
        print("Error: config.json not found. Please create one from config.json.sample.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_twitter_env(config):
    env = os.environ.copy()
    if config.get("twitter_auth_token"):
        env["TWITTER_AUTH_TOKEN"] = config["twitter_auth_token"]
    if config.get("twitter_ct0"):
        env["TWITTER_CT0"] = config["twitter_ct0"]
    return env


def run_twitter(config, *args):
    """twitter-cli の任意のコマンドを実行する"""
    twitter_cli_dir = Path(config["twitter_cli_path"])
    cmd = ["uv", "run", "twitter"] + list(args)
    env = get_twitter_env(config)
    try:
        subprocess.run(cmd, cwd=twitter_cli_dir, env=env)
    except FileNotFoundError:
        print("Error: 'uv' コマンドが見つかりません。uv をインストールしてください。")
        sys.exit(1)


# --- AI Tweet Generation ---

def get_post_data(slug, config):
    posts_file = Path(config["posts_file_path"])
    if not posts_file.exists():
        print(f"Error: Posts file not found at {posts_file}")
        sys.exit(1)
    content = posts_file.read_text(encoding="utf-8")
    pattern = rf"slug:\s*\"{re.escape(slug)}\".*?title:\s*\"(.*?)\".*?excerpt:\s*\"(.*?)\""
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"Error: Post with slug '{slug}' not found.")
        sys.exit(1)
    return {
        "title": match.group(1),
        "url": f"{config['base_url']}/posts/{slug}"
    }


def generate_tweets_with_cli(post_data, config, ai_cli="gemini"):
    prompt = config["prompt_template"].format(
        url=post_data["url"],
        title=post_data["title"],
        site_name=config.get("site_name", "公式")
    )
    print(f"Generating tweets using {ai_cli} CLI...")
    try:
        cmd = [ai_cli, prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        content = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error calling {ai_cli} cli: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: '{ai_cli}' command not found.")
        sys.exit(1)
    lines = content.strip().split("\n")
    tweets = [re.sub(r'^\d+[\.、]\s*', '', line).strip() for line in lines if line.strip()]
    return tweets[:5]


def cmd_generate(args, config):
    posts_file = Path(config["posts_file_path"])
    content = posts_file.read_text(encoding="utf-8")
    slugs = re.findall(r'slug:\s*"(.*?)"', content)

    if not args.input:
        slug = random.choice(slugs)
        print(f"Picked random article: {slug}")
    else:
        slug = args.input.split("/")[-1]

    post_data = get_post_data(slug, config)
    tweets = generate_tweets_with_cli(post_data, config, ai_cli=args.ai)

    if args.auto:
        tweet = random.choice(tweets)
        print(f"\nPosting to Twitter:\n{tweet}")
        run_twitter(config, "post", tweet)
        return

    print(f"\n--- Generated Tweets for: {post_data['title']} ---")
    for i, t in enumerate(tweets, 1):
        print(f"\n[{i}]\n{t}")
        print("-" * 20)

    while True:
        try:
            choice = input("\nChoose a tweet to post (1-5, or 'q' to quit): ")
            if choice.lower() == 'q':
                break
            idx = int(choice) - 1
            if 0 <= idx < len(tweets):
                run_twitter(config, "post", tweets[idx])
                break
        except ValueError:
            pass


# --- Read Operations ---

def cmd_feed(args, config):
    extra = []
    if getattr(args, 'compact', False):
        extra = ["-c"]
    extra.append("feed")
    if getattr(args, 'type', None):
        extra += ["-t", args.type]
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'filter', False):
        extra += ["--filter"]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    if getattr(args, 'output', None):
        extra += ["-o", args.output]
    run_twitter(config, *extra)


def cmd_bookmarks(args, config):
    extra = []
    if getattr(args, 'compact', False):
        extra = ["-c"]
    extra.append("bookmarks")
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    if getattr(args, 'output', None):
        extra += ["-o", args.output]
    run_twitter(config, *extra)


def cmd_search(args, config):
    extra = []
    if getattr(args, 'compact', False):
        extra = ["-c"]
    extra.append("search")
    extra.append(args.query)
    if getattr(args, 'type', None):
        extra += ["-t", args.type]
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    if getattr(args, 'output', None):
        extra += ["-o", args.output]
    run_twitter(config, *extra)


def cmd_tweet(args, config):
    extra = ["tweet", args.id_or_url]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


def cmd_list(args, config):
    extra = ["list", args.list_id]
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


def cmd_user_posts(args, config):
    extra = []
    if getattr(args, 'compact', False):
        extra = ["-c"]
    extra += ["user-posts", args.username]
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


def cmd_likes(args, config):
    extra = ["likes", args.username]
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


def cmd_followers(args, config):
    extra = ["followers", args.username]
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


def cmd_following(args, config):
    extra = ["following", args.username]
    if getattr(args, 'max', None):
        extra += ["--max", str(args.max)]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


def cmd_whoami(args, config):
    extra = ["whoami"]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


def cmd_status(args, config):
    extra = ["status"]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    run_twitter(config, *extra)


def cmd_user(args, config):
    extra = ["user", args.username]
    if getattr(args, 'yaml', False):
        extra += ["--yaml"]
    if getattr(args, 'json', False):
        extra += ["--json"]
    run_twitter(config, *extra)


# --- Write Operations ---

def cmd_post(args, config):
    extra = ["post", args.text]
    if getattr(args, 'reply_to', None):
        extra += ["--reply-to", args.reply_to]
    run_twitter(config, *extra)


def cmd_reply(args, config):
    run_twitter(config, "reply", args.tweet_id, args.text)


def cmd_quote(args, config):
    run_twitter(config, "quote", args.tweet_id, args.text)


def cmd_delete(args, config):
    run_twitter(config, "delete", args.tweet_id)


def cmd_like(args, config):
    run_twitter(config, "like", args.tweet_id)


def cmd_unlike(args, config):
    run_twitter(config, "unlike", args.tweet_id)


def cmd_retweet(args, config):
    run_twitter(config, "retweet", args.tweet_id)


def cmd_unretweet(args, config):
    run_twitter(config, "unretweet", args.tweet_id)


def cmd_bookmark(args, config):
    run_twitter(config, "bookmark", args.tweet_id)


def cmd_unbookmark(args, config):
    run_twitter(config, "unbookmark", args.tweet_id)


def cmd_follow(args, config):
    run_twitter(config, "follow", args.username)


def cmd_unfollow(args, config):
    run_twitter(config, "unfollow", args.username)


# --- Parser Helpers ---

def add_output_flags(p):
    p.add_argument("--yaml", action="store_true", help="YAML形式で出力")
    p.add_argument("--json", action="store_true", help="JSON形式で出力")


def add_output_file_flag(p):
    p.add_argument("-o", "--output", metavar="FILE", help="ファイルに保存")


def add_compact_flag(p):
    p.add_argument("-c", "--compact", action="store_true", help="コンパクト出力（LLM向け）")


def add_max_flag(p):
    p.add_argument("--max", type=int, metavar="N", help="取得件数の上限")


def add_tweet_id_arg(p):
    p.add_argument("tweet_id", help="ツイートID")


def add_username_arg(p):
    p.add_argument("username", help="ユーザー名（@なし）")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="twitter-cli-bot: AI生成ツイート投稿 + twitter-cli 全機能ラッパー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
サブコマンド:
  [AI生成]
    generate    AIでツイートを生成して投稿（デフォルト）

  [読み取り]
    feed        タイムライン表示
    bookmarks   ブックマーク表示
    search      キーワード検索
    tweet       ツイート詳細表示
    list        リストタイムライン
    user-posts  ユーザーのツイート一覧
    likes       ユーザーのいいね一覧
    followers   フォロワー一覧
    following   フォロー中一覧
    whoami      認証中のユーザー情報
    status      認証状態確認
    user        ユーザープロフィール

  [書き込み]
    post        ツイート投稿
    reply       返信
    quote       引用ツイート
    delete      ツイート削除
    like        いいね
    unlike      いいね解除
    retweet     リツイート
    unretweet   リツイート解除
    bookmark    ブックマーク追加
    unbookmark  ブックマーク解除
    follow      フォロー
    unfollow    フォロー解除
"""
    )
    subparsers = parser.add_subparsers(dest="command")

    # generate
    p = subparsers.add_parser("generate", help="AIでツイートを生成して投稿")
    p.add_argument("input", nargs="?", help="記事URLまたはslug")
    p.add_argument("--auto", action="store_true", help="自動でランダム選択して投稿")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.set_defaults(func=cmd_generate)

    # feed
    p = subparsers.add_parser("feed", help="タイムライン表示")
    p.add_argument("-t", "--type", choices=["following"], help="following タイムライン")
    add_max_flag(p)
    p.add_argument("--filter", action="store_true", help="ランキングフィルター有効化")
    add_output_flags(p)
    add_compact_flag(p)
    add_output_file_flag(p)
    p.set_defaults(func=cmd_feed)

    # bookmarks
    p = subparsers.add_parser("bookmarks", help="ブックマーク表示")
    add_max_flag(p)
    add_output_flags(p)
    add_compact_flag(p)
    add_output_file_flag(p)
    p.set_defaults(func=cmd_bookmarks)

    # search
    p = subparsers.add_parser("search", help="キーワード検索")
    p.add_argument("query", help="検索キーワード")
    p.add_argument("-t", "--type", choices=["Top", "Latest", "Photos", "Videos"], help="検索タイプ")
    add_max_flag(p)
    add_output_flags(p)
    add_compact_flag(p)
    add_output_file_flag(p)
    p.set_defaults(func=cmd_search)

    # tweet
    p = subparsers.add_parser("tweet", help="ツイート詳細表示")
    p.add_argument("id_or_url", help="ツイートID またはURL")
    add_output_flags(p)
    p.set_defaults(func=cmd_tweet)

    # list
    p = subparsers.add_parser("list", help="リストタイムライン")
    p.add_argument("list_id", help="リストID")
    add_max_flag(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_list)

    # user-posts
    p = subparsers.add_parser("user-posts", help="ユーザーのツイート一覧")
    add_username_arg(p)
    add_max_flag(p)
    add_output_flags(p)
    add_compact_flag(p)
    p.set_defaults(func=cmd_user_posts)

    # likes
    p = subparsers.add_parser("likes", help="ユーザーのいいね一覧")
    add_username_arg(p)
    add_max_flag(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_likes)

    # followers
    p = subparsers.add_parser("followers", help="フォロワー一覧")
    add_username_arg(p)
    add_max_flag(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_followers)

    # following
    p = subparsers.add_parser("following", help="フォロー中一覧")
    add_username_arg(p)
    add_max_flag(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_following)

    # whoami
    p = subparsers.add_parser("whoami", help="認証中のユーザー情報")
    add_output_flags(p)
    p.set_defaults(func=cmd_whoami)

    # status
    p = subparsers.add_parser("status", help="認証状態確認")
    p.add_argument("--yaml", action="store_true", help="YAML形式で出力")
    p.set_defaults(func=cmd_status)

    # user
    p = subparsers.add_parser("user", help="ユーザープロフィール")
    add_username_arg(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_user)

    # post
    p = subparsers.add_parser("post", help="ツイート投稿")
    p.add_argument("text", help="投稿するテキスト")
    p.add_argument("--reply-to", metavar="TWEET_ID", help="返信先ツイートID")
    p.set_defaults(func=cmd_post)

    # reply
    p = subparsers.add_parser("reply", help="返信")
    add_tweet_id_arg(p)
    p.add_argument("text", help="返信テキスト")
    p.set_defaults(func=cmd_reply)

    # quote
    p = subparsers.add_parser("quote", help="引用ツイート")
    add_tweet_id_arg(p)
    p.add_argument("text", help="コメントテキスト")
    p.set_defaults(func=cmd_quote)

    # delete
    p = subparsers.add_parser("delete", help="ツイート削除")
    add_tweet_id_arg(p)
    p.set_defaults(func=cmd_delete)

    # like
    p = subparsers.add_parser("like", help="いいね")
    add_tweet_id_arg(p)
    p.set_defaults(func=cmd_like)

    # unlike
    p = subparsers.add_parser("unlike", help="いいね解除")
    add_tweet_id_arg(p)
    p.set_defaults(func=cmd_unlike)

    # retweet
    p = subparsers.add_parser("retweet", help="リツイート")
    add_tweet_id_arg(p)
    p.set_defaults(func=cmd_retweet)

    # unretweet
    p = subparsers.add_parser("unretweet", help="リツイート解除")
    add_tweet_id_arg(p)
    p.set_defaults(func=cmd_unretweet)

    # bookmark
    p = subparsers.add_parser("bookmark", help="ブックマーク追加")
    add_tweet_id_arg(p)
    p.set_defaults(func=cmd_bookmark)

    # unbookmark
    p = subparsers.add_parser("unbookmark", help="ブックマーク解除")
    add_tweet_id_arg(p)
    p.set_defaults(func=cmd_unbookmark)

    # follow
    p = subparsers.add_parser("follow", help="フォロー")
    add_username_arg(p)
    p.set_defaults(func=cmd_follow)

    # unfollow
    p = subparsers.add_parser("unfollow", help="フォロー解除")
    add_username_arg(p)
    p.set_defaults(func=cmd_unfollow)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    config = load_config()
    args.func(args, config)


if __name__ == "__main__":
    main()
