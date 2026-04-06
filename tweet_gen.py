import os
import sys
import re
import subprocess
import random
import argparse
import json
import sqlite3
import tempfile
import platform
from datetime import datetime
from pathlib import Path


def load_config():
    config_path = Path(__file__).resolve().parent / "config.json"
    if not config_path.exists():
        print("Error: config.json not found. Please create one from config.json.sample.")
        sys.exit(1)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: config.json is not valid JSON: {e}")
                sys.exit(1)
    except OSError as e:
        print(f"Error: config.json を読み込めません: {e}")
        sys.exit(1)


def validate_config(config, command):
    """コマンドに応じた設定バリデーション"""
    errors = []
    warnings = []

    # twitter_cli_path は全コマンドで必要（history 系除く）
    config_free_cmds = (
        "history", "history-clear", "stats",
        "schedule-add", "schedule-list", "schedule-remove",
        "draft-save", "draft-list", "draft-edit", "draft-delete",
    )
    if command not in config_free_cmds:
        tcp = config.get("twitter_cli_path", "").strip()
        if not tcp:
            errors.append("twitter_cli_path が設定されていません。")
        elif not Path(tcp).exists():
            errors.append(f"twitter_cli_path のパスが存在しません: {tcp}")
        elif not Path(tcp).is_dir():
            errors.append(f"twitter_cli_path はディレクトリではありません: {tcp}")

    # generate 系で posts_file_path が設定されている場合のチェック
    if command in ("generate", "generate-thread"):
        pfp = config.get("posts_file_path", "").strip()
        if pfp and not Path(pfp).exists():
            warnings.append(f"posts_file_path が存在しません: {pfp}")
        bu = config.get("base_url", "").strip()
        if pfp and not bu:
            warnings.append("posts_file_path が設定されていますが base_url が空です。slug モードでは base_url が必要です。")

    for w in warnings:
        print(f"Warning: {w}")
    if errors:
        for e in errors:
            print(f"Error: {e}")
        sys.exit(1)


# --- Post History (SQLite) ---

def get_db_path():
    return Path(__file__).resolve().parent / "history.db"


def init_db():
    db = sqlite3.connect(get_db_path())
    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_text TEXT NOT NULL,
            article_url TEXT,
            tone TEXT,
            posted_at TEXT NOT NULL,
            is_thread INTEGER DEFAULT 0
        )
    """)
    db.commit()
    return db


def save_post(text, article_url=None, tone=None, is_thread=False):
    db = init_db()
    db.execute(
        "INSERT INTO posts (tweet_text, article_url, tone, posted_at, is_thread) VALUES (?, ?, ?, ?, ?)",
        (text, article_url, tone, datetime.now().isoformat(), int(is_thread))
    )
    db.commit()
    db.close()


def find_duplicate(article_url):
    """同じURLの過去投稿を検索。見つかれば (id, text, posted_at) を返す"""
    if not article_url:
        return None
    db = init_db()
    row = db.execute(
        "SELECT id, tweet_text, posted_at FROM posts WHERE article_url = ? ORDER BY posted_at DESC LIMIT 1",
        (article_url,)
    ).fetchone()
    db.close()
    return row


# --- Tone Presets ---

TONE_PRESETS = {
    "professional": "プロフェッショナルで信頼感のあるトーンで。データや実績に基づく表現を使い、読者に価値を感じさせる。",
    "casual": "カジュアルで親しみやすいトーンで。口語的な表現や語りかけるような文体を使う。",
    "provocative": "挑発的で注目を引くトーンで。常識を疑う切り口や、議論を呼ぶ主張を含める。",
    "technical": "技術者向けの具体的なトーンで。技術用語を適切に使い、実装の詳細やメリットを明確に伝える。",
    "humorous": "ユーモアのあるトーンで。クスッと笑える表現やウィットに富んだ比喩を使う。",
}


# --- Tweet Editing ---

def edit_tweet(tweet):
    """$EDITOR でツイートを編集する。EDITOR未設定ならインライン入力にフォールバック"""
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", ""))
    if editor:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(tweet)
            tmppath = f.name
        try:
            subprocess.run([editor, tmppath])
            with open(tmppath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        finally:
            os.unlink(tmppath)
    else:
        print(f"\n現在のテキスト:\n  {tweet}\n")
        new_text = input("新しいテキストを入力（空欄で変更なし）: ").strip()
        return new_text if new_text else tweet


def get_twitter_env(config):
    env = os.environ.copy()
    auth_token = config.get("twitter_auth_token", "").strip()
    ct0 = config.get("twitter_ct0", "").strip()
    if auth_token:
        env["TWITTER_AUTH_TOKEN"] = auth_token
    if ct0:
        env["TWITTER_CT0"] = ct0
    return env


def _resolve_twitter_cli_dir(config):
    """twitter_cli_path を検証して Path を返す"""
    twitter_cli_path = config.get("twitter_cli_path")
    if not twitter_cli_path:
        print("Error: config.json に twitter_cli_path が設定されていません。")
        sys.exit(1)
    twitter_cli_dir = Path(twitter_cli_path)
    if not twitter_cli_dir.exists():
        print(f"Error: twitter_cli_path が存在しません: {twitter_cli_dir}")
        sys.exit(1)
    if not twitter_cli_dir.is_dir():
        print(f"Error: twitter_cli_path はディレクトリではありません: {twitter_cli_dir}")
        sys.exit(1)
    return twitter_cli_dir


def run_twitter(config, *args):
    """twitter-cli の任意のコマンドを実行する"""
    twitter_cli_dir = _resolve_twitter_cli_dir(config)
    cmd = ["uv", "run", "twitter"] + list(args)
    env = get_twitter_env(config)
    try:
        subprocess.run(cmd, cwd=twitter_cli_dir, env=env)
    except FileNotFoundError:
        print("Error: 'uv' コマンドが見つかりません。uv をインストールしてください。")
        sys.exit(1)


def run_twitter_capture(config, *args):
    """twitter-cli を実行し、stdout をキャプチャして返す（スレッド投稿用）"""
    twitter_cli_dir = _resolve_twitter_cli_dir(config)
    cmd = ["uv", "run", "twitter"] + list(args)
    env = get_twitter_env(config)
    try:
        result = subprocess.run(
            cmd, cwd=twitter_cli_dir, env=env,
            capture_output=True, text=True, encoding="utf-8"
        )
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.stdout
    except FileNotFoundError:
        print("Error: 'uv' コマンドが見つかりません。uv をインストールしてください。")
        sys.exit(1)


def extract_tweet_id(output):
    """twitter-cli の出力からツイートIDを抽出する"""
    # 一般的なパターン: URL中のstatus ID、または数字のみの行
    match = re.search(r'status/(\d+)', output)
    if match:
        return match.group(1)
    match = re.search(r'\b(\d{15,25})\b', output)
    if match:
        return match.group(1)
    return None


# --- AI Tweet Generation ---

def get_post_data(slug, content, config):
    pattern = rf"slug:\s*\"{re.escape(slug)}\".*?title:\s*\"(.*?)\""
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"Error: Post with slug '{slug}' not found.")
        sys.exit(1)
    base_url = config.get("base_url", "")
    if not base_url:
        print("Error: config.json に base_url が設定されていません。")
        sys.exit(1)
    return {
        "title": match.group(1),
        "url": f"{base_url}/posts/{slug}"
    }


def get_posted_urls():
    """履歴にある全URLのセットを返す"""
    db = init_db()
    rows = db.execute("SELECT DISTINCT article_url FROM posts WHERE article_url IS NOT NULL").fetchall()
    db.close()
    return {row[0] for row in rows}


def resolve_post_data(args, config):
    """URL・slug・トピック・ランダムのいずれかでpost_dataを解決する"""
    inp = args.input
    topic = getattr(args, 'topic', None)
    smart = getattr(args, 'auto', False) and not getattr(args, 'force', False)

    # --topic モード: 自由なテーマからツイート生成（URL不要）
    if topic:
        return {"url": "", "title": "", "topic": topic}

    # URLを直接渡した場合（postsファイル不要）
    if inp and inp.startswith(("http://", "https://")):
        return {"url": inp, "title": ""}

    # slug or ランダム（postsファイルが必要）
    if not config.get("posts_file_path"):
        if inp:
            # URL でも slug でもないテキスト → トピックとして扱う
            return {"url": "", "title": "", "topic": inp}
        print("Error: URL、トピック、または config.json の posts_file_path を指定してください。")
        sys.exit(1)

    posts_file = Path(config["posts_file_path"])
    if not posts_file.exists():
        print(f"Error: Posts file not found at {posts_file}")
        sys.exit(1)
    try:
        content = posts_file.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error: Posts file を読み込めません: {e}")
        sys.exit(1)
    slugs = re.findall(r'slug:\s*"(.*?)"', content)

    if not inp:
        if not slugs:
            print(f"Error: No slugs found in {posts_file}")
            sys.exit(1)

        # スマート auto: 投稿済みURLをスキップ
        if smart:
            posted_urls = get_posted_urls()
            base_url = config.get("base_url", "")
            unposted = [s for s in slugs if f"{base_url}/posts/{s}" not in posted_urls]
            if not unposted:
                print("すべての記事が投稿済みです。新しい記事を追加するか --force を使用してください。")
                return None
            slug = random.choice(unposted)
            print(f"Picked unposted article: {slug} ({len(unposted)}/{len(slugs)} remaining)")
        else:
            slug = random.choice(slugs)
            print(f"Picked random article: {slug}")
    else:
        slug = inp.rstrip("/").split("/")[-1]
        if not slug:
            print(f"Error: '{inp}' から slug を取得できませんでした。")
            sys.exit(1)

    return get_post_data(slug, content, config)


def generate_tweets_with_cli(post_data, config, ai_cli="gemini", tone=None):
    topic = post_data.get("topic")
    if topic:
        # フリーフォームモード: トピックからツイート生成
        prompt = (
            f"以下のテーマについて、X（Twitter）投稿（140文字以内）を5つ作ってください。"
            f"出力はツイート内容のみを1行ずつ出力してください。\n\nテーマ: {topic}"
        )
    else:
        template = config.get(
            "prompt_template",
            "以下のURLについて、X（Twitter）投稿（140文字以内）を5つ作ってください。出力はツイート内容のみを1行ずつ出力してください。\n\nURL: {url}"
        )
        try:
            prompt = template.format(
                url=post_data["url"],
                title=post_data.get("title", ""),
                site_name=config.get("site_name", "")
            )
        except KeyError as e:
            print(f"Error: prompt_template に未知のプレースホルダーがあります: {e}")
            sys.exit(1)
    if tone and tone in TONE_PRESETS:
        prompt = f"【トーン指定】{TONE_PRESETS[tone]}\n\n{prompt}"
    print(f"Generating tweets using {ai_cli} CLI...")
    content = run_ai_cli(ai_cli, prompt)
    return parse_ai_tweets(content, max_count=5)


AI_TIMEOUT_SECONDS = 120


def run_ai_cli(ai_cli, prompt):
    """AI CLI を実行して stdout を返す（タイムアウト付き）"""
    try:
        result = subprocess.run(
            [ai_cli, prompt],
            capture_output=True, text=True, encoding="utf-8", check=True,
            timeout=AI_TIMEOUT_SECONDS
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"Error: {ai_cli} が {AI_TIMEOUT_SECONDS} 秒以内に応答しませんでした。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error calling {ai_cli} cli: {e}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: '{ai_cli}' command not found.")
        sys.exit(1)


def parse_ai_tweets(content, max_count=5):
    """AI 出力からツイートを抽出する（Gemini/Claude/Codex の形式差を吸収）"""
    lines = content.strip().split("\n")
    tweets = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # マークダウン装飾を除去
        if line.startswith(('#', '---', '```', '**Tweet', '- **')):
            continue
        # 番号プレフィックスを除去 (1. / 1) / 1] / 1、/ ①)
        line = re.sub(r'^\d+[\.、\)\]\:]\s*', '', line)
        line = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', line)
        # マークダウンのボールド/イタリックを除去
        line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
        line = re.sub(r'^\s*[-\*]\s+', '', line)
        # 引用符を除去（行頭は開き引用符、行末は閉じ引用符のみ）
        line = re.sub(r'^[「『"\u201c\']', '', line)
        line = re.sub(r'[」』"\u201d\']$', '', line)
        line = line.strip()
        if line and len(line) >= 10:  # 短すぎるゴミ行を除外
            tweets.append(line)
    return tweets[:max_count]


TWEET_CHAR_LIMIT = 280


def format_tweet_display(tweet, index, total=None):
    """ツイートを文字数付きで表示用にフォーマットする"""
    char_count = len(tweet)
    warn = " [!280文字超]" if char_count > TWEET_CHAR_LIMIT else ""
    if total:
        header = f"[{index}/{total}]"
    else:
        header = f"[{index}]"
    return f"\n{header} ({char_count}文字{warn})\n{tweet}\n" + "-" * 20


def copy_to_clipboard(text):
    """テキストをクリップボードにコピーする"""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
        elif system == "Linux":
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
        else:
            print("Warning: クリップボードコピーは macOS/Linux のみ対応しています。")
            return False
        return True
    except FileNotFoundError:
        print("Warning: クリップボードコマンドが見つかりません。")
        return False


def cmd_generate(args, config):
    post_data = resolve_post_data(args, config)
    if post_data is None:
        return
    article_url = post_data.get("url") or None  # "" → None に統一
    topic = post_data.get("topic")
    tone = getattr(args, 'tone', None)
    dry_run = getattr(args, 'dry_run', False)
    force = getattr(args, 'force', False)
    clipboard = getattr(args, 'clipboard', False)

    # 重複チェック（トピックモードではスキップ）
    if not force and not topic and article_url:
        dup = find_duplicate(article_url)
        if dup:
            dup_id, dup_text, dup_date = dup
            print(f"Warning: この URL は投稿済みです ({dup_date})")
            print(f"  前回: {dup_text[:80]}...")
            if args.auto:
                print("スキップしました。強制投稿するには --force を使用してください。")
                return
            try:
                ans = input("続行しますか？ (y/N): ").strip().lower()
            except EOFError:
                return
            if ans != 'y':
                print("キャンセルしました。")
                return

    tweets = generate_tweets_with_cli(post_data, config, ai_cli=args.ai, tone=tone)

    if not tweets:
        print("Error: AI がツイートを生成できませんでした。")
        sys.exit(1)

    if tone:
        print(f"Tone: {tone}")

    if args.auto:
        tweet = random.choice(tweets)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if dry_run:
            print(f"[{timestamp}] [dry-run] 投稿されるツイート ({len(tweet)}文字):\n{tweet}")
            return
        if clipboard:
            if copy_to_clipboard(tweet):
                print(f"[{timestamp}] クリップボードにコピーしました ({len(tweet)}文字):\n{tweet}")
            return
        print(f"[{timestamp}] Posting to Twitter ({len(tweet)}文字):\n{tweet}")
        run_twitter(config, "post", tweet)
        save_post(tweet, article_url=article_url, tone=tone)
        return

    label = topic or post_data.get('title') or post_data.get('url') or "Free-form"
    print(f"\n--- Generated Tweets for: {label} ---")
    for i, t in enumerate(tweets, 1):
        print(format_tweet_display(t, i))

    if dry_run:
        print("\n[dry-run] プレビューのみ。投稿は行われません。")
        return

    actions = f"番号で選択 (1-{len(tweets)}), 'e数字' で編集 (例: e1)"
    if clipboard:
        actions += ", 'c数字' でコピー (例: c1)"
    actions += ", 'q' で中止"

    while True:
        try:
            choice = input(f"\n{actions}: ")
        except EOFError:
            break
        choice = choice.strip()
        if choice.lower() == 'q':
            break

        # 編集モード: e1, e2, ...
        edit_match = re.match(r'^e(\d+)$', choice.lower())
        if edit_match:
            idx = int(edit_match.group(1)) - 1
            if 0 <= idx < len(tweets):
                tweets[idx] = edit_tweet(tweets[idx])
                print(format_tweet_display(tweets[idx], idx + 1) + " (編集済み)")
            else:
                print(f"  範囲外です。1〜{len(tweets)} の番号を指定してください。")
            continue

        # クリップボードコピー: c1, c2, ...
        if clipboard:
            clip_match = re.match(r'^c(\d+)$', choice.lower())
            if clip_match:
                idx = int(clip_match.group(1)) - 1
                if 0 <= idx < len(tweets):
                    if copy_to_clipboard(tweets[idx]):
                        print(f"  クリップボードにコピーしました。")
                else:
                    print(f"  範囲外です。1〜{len(tweets)} の番号を指定してください。")
                continue

        try:
            idx = int(choice) - 1
        except ValueError:
            print(f"  無効な入力です。")
            continue
        if 0 <= idx < len(tweets):
            run_twitter(config, "post", tweets[idx])
            save_post(tweets[idx], article_url=article_url, tone=tone)
            break
        else:
            print(f"  範囲外です。1〜{len(tweets)} の番号を指定してください。")


# --- Thread Generation ---

def generate_thread_with_cli(post_data, config, ai_cli="gemini", tone=None, count=4):
    """記事またはトピックからスレッド用の連続ツイートを生成する"""
    output_instructions = (
        "各ツイートは140文字以内。出力はツイート内容のみを空行で区切って出力してください。\n"
        "番号は付けないでください。\n"
    )
    topic = post_data.get("topic")
    if topic:
        thread_prompt = (
            f"以下のテーマについて、X（Twitter）のスレッド（連続ツイート）を{count}件作ってください。\n"
            "1件目はフックとなる導入ツイート、中間はテーマの要点、最後はまとめにしてください。\n"
            f"{output_instructions}"
            f"\nテーマ: {topic}"
        )
    else:
        thread_prompt = (
            f"以下のURLについて、X（Twitter）のスレッド（連続ツイート）を{count}件作ってください。\n"
            "1件目はフックとなる導入ツイート、中間は記事の要点、最後はまとめとURL紹介にしてください。\n"
            f"{output_instructions}"
        )
        url = post_data["url"]
        title = post_data.get("title", "")
        thread_prompt += f"\nURL: {url}"
        if title:
            thread_prompt += f"\nタイトル: {title}"
    site_name = config.get("site_name", "")
    if site_name:
        thread_prompt += f"\nサイト名: {site_name}"

    if tone and tone in TONE_PRESETS:
        thread_prompt = f"【トーン指定】{TONE_PRESETS[tone]}\n\n{thread_prompt}"

    print(f"Generating thread ({count} tweets) using {ai_cli} CLI...")
    content = run_ai_cli(ai_cli, thread_prompt)

    # 空行で区切られたブロックを各ツイートとして扱う
    blocks = re.split(r'\n\s*\n', content.strip())
    tweets = []
    for block in blocks:
        text = block.strip()
        if text.startswith(('#', '---', '```')):
            continue
        text = re.sub(r'^\d+[\.、\)\]\:]\s*', '', text)
        text = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = text.strip()
        if text and len(text) >= 10:
            tweets.append(text)
    return tweets[:count]


def cmd_generate_thread(args, config):
    post_data = resolve_post_data(args, config)
    if post_data is None:
        return
    article_url = post_data.get("url") or None  # "" → None に統一
    tone = getattr(args, 'tone', None)
    dry_run = getattr(args, 'dry_run', False)
    clipboard = getattr(args, 'clipboard', False)
    count = getattr(args, 'count', 4) or 4

    tweets = generate_thread_with_cli(
        post_data, config, ai_cli=args.ai, tone=tone, count=count
    )

    if not tweets:
        print("Error: AI がスレッドを生成できませんでした。")
        sys.exit(1)

    label = post_data.get('title') or post_data.get('url') or "Free-form"
    print(f"\n--- Generated Thread for: {label} ({len(tweets)} tweets) ---")
    for i, t in enumerate(tweets, 1):
        print(format_tweet_display(t, i, total=len(tweets)))

    if dry_run:
        print("\n[dry-run] プレビューのみ。投稿は行われません。")
        return

    if clipboard:
        full_thread = "\n\n---\n\n".join(tweets)
        if copy_to_clipboard(full_thread):
            print(f"\nスレッド全体をクリップボードにコピーしました ({len(tweets)} tweets)")
        return

    try:
        confirm = input("\nこのスレッドを投稿しますか？ (y/N): ").strip().lower()
    except EOFError:
        return
    if confirm != 'y':
        print("キャンセルしました。")
        return

    # スレッド投稿: 最初のツイートを投稿し、以降はリプライチェーン
    print(f"\n[1/{len(tweets)}] 投稿中...")
    output = run_twitter_capture(config, "post", tweets[0])
    save_post(tweets[0], article_url=article_url, tone=tone, is_thread=True)
    prev_id = extract_tweet_id(output) if output else None

    for i, tweet in enumerate(tweets[1:], 2):
        print(f"[{i}/{len(tweets)}] 投稿中...")
        if prev_id:
            output = run_twitter_capture(config, "reply", prev_id, tweet)
            new_id = extract_tweet_id(output) if output else None
            if new_id:
                prev_id = new_id
        else:
            print("  Warning: 前のツイートIDが取得できなかったため、通常投稿します。")
            run_twitter(config, "post", tweet)
        save_post(tweet, article_url=article_url, tone=tone, is_thread=True)

    print(f"\nスレッド投稿完了 ({len(tweets)} tweets)")


# --- Batch Generation ---

def cmd_generate_batch(args, config):
    """未投稿の記事をまとめて生成・投稿する"""
    if not config.get("posts_file_path"):
        print("Error: バッチモードには config.json に posts_file_path が必要です。")
        sys.exit(1)

    posts_file = Path(config["posts_file_path"])
    if not posts_file.exists():
        print(f"Error: Posts file not found at {posts_file}")
        sys.exit(1)
    content = posts_file.read_text(encoding="utf-8")
    slugs = re.findall(r'slug:\s*"(.*?)"', content)
    if not slugs:
        print("Error: postsファイルにslugが見つかりません。")
        sys.exit(1)

    base_url = config.get("base_url", "")
    posted_urls = get_posted_urls()
    unposted = [s for s in slugs if f"{base_url}/posts/{s}" not in posted_urls]

    if not unposted:
        print("すべての記事が投稿済みです。")
        return

    limit = getattr(args, 'max', None) or len(unposted)
    targets = unposted[:limit]
    tone = getattr(args, 'tone', None)
    dry_run = getattr(args, 'dry_run', False)
    ai_cli = args.ai

    print(f"未投稿記事: {len(unposted)} 件 (処理対象: {len(targets)} 件)")
    if not dry_run:
        try:
            confirm = input("投稿を開始しますか？ (y/N): ").strip().lower()
        except EOFError:
            return
        if confirm != 'y':
            print("キャンセルしました。")
            return

    for idx, slug in enumerate(targets, 1):
        post_data = get_post_data(slug, content, config)
        article_url = post_data["url"]
        label = post_data['title'] or slug
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{idx}/{len(targets)}] {label}")
        tweets = generate_tweets_with_cli(post_data, config, ai_cli=ai_cli, tone=tone)
        if not tweets:
            print(f"  Warning: ツイート生成失敗、スキップします。")
            continue

        tweet = random.choice(tweets)
        if dry_run:
            print(f"  [{timestamp}] [dry-run] ({len(tweet)}文字): {tweet[:80]}...")
        else:
            print(f"  [{timestamp}] Posting ({len(tweet)}文字): {tweet[:80]}...")
            run_twitter(config, "post", tweet)
            save_post(tweet, article_url=article_url, tone=tone)

    status = "プレビュー" if dry_run else "投稿"
    print(f"\nバッチ{status}完了: {len(targets)} 件")


# --- History ---

def cmd_history(args, config):
    db = init_db()
    limit = getattr(args, 'max', 20) or 20
    rows = db.execute(
        "SELECT posted_at, tweet_text, article_url, tone, is_thread "
        "FROM posts ORDER BY posted_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    db.close()

    if not rows:
        print("投稿履歴はありません。")
        return

    # JSON エクスポート
    if getattr(args, 'json', False):
        data = [
            {
                "posted_at": r[0], "text": r[1], "url": r[2],
                "tone": r[3], "is_thread": bool(r[4])
            }
            for r in rows
        ]
        output = json.dumps(data, ensure_ascii=False, indent=2)
        out_file = getattr(args, 'output', None)
        if out_file:
            Path(out_file).write_text(output, encoding="utf-8")
            print(f"{len(data)} 件を {out_file} にエクスポートしました。")
        else:
            print(output)
        return

    for posted_at, text, url, tone, is_thread in rows:
        tags = []
        if tone:
            tags.append(f"tone:{tone}")
        if is_thread:
            tags.append("thread")
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        print(f"\n{posted_at}{tag_str}")
        print(f"  {text[:120]}{'...' if len(text) > 120 else ''}")
        if url:
            print(f"  URL: {url}")

    print(f"\n表示: {len(rows)} / 全 {total} 件")


def cmd_history_clear(args, config):
    db = init_db()
    count = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    db.close()
    if count == 0:
        print("投稿履歴はありません。")
        return
    try:
        confirm = input(f"投稿履歴 {count} 件をすべて削除しますか？ (y/N): ").strip().lower()
    except EOFError:
        return
    if confirm != 'y':
        print("キャンセルしました。")
        return
    db = init_db()
    db.execute("DELETE FROM posts")
    db.commit()
    db.close()
    print(f"{count} 件の履歴を削除しました。")


# --- Stats ---

def cmd_stats(args, config):
    """投稿履歴の統計情報を表示する"""
    db = init_db()
    total = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    if total == 0:
        print("投稿履歴はありません。")
        db.close()
        return

    threads = db.execute("SELECT COUNT(*) FROM posts WHERE is_thread = 1").fetchone()[0]
    singles = total - threads
    unique_urls = db.execute(
        "SELECT COUNT(DISTINCT article_url) FROM posts WHERE article_url IS NOT NULL AND article_url != ''"
    ).fetchone()[0]
    topics = db.execute(
        "SELECT COUNT(*) FROM posts WHERE (article_url IS NULL OR article_url = '')"
    ).fetchone()[0]

    # トーン別集計
    tone_rows = db.execute(
        "SELECT tone, COUNT(*) FROM posts WHERE tone IS NOT NULL GROUP BY tone ORDER BY COUNT(*) DESC"
    ).fetchall()

    # 日別投稿数（直近7日）
    daily_rows = db.execute(
        "SELECT DATE(posted_at) as d, COUNT(*) FROM posts "
        "GROUP BY d ORDER BY d DESC LIMIT 7"
    ).fetchall()

    # 最新・最古
    oldest = db.execute("SELECT MIN(posted_at) FROM posts").fetchone()[0]
    newest = db.execute("SELECT MAX(posted_at) FROM posts").fetchone()[0]
    db.close()

    print(f"\n--- 投稿統計 ---")
    print(f"総投稿数: {total} (単発: {singles}, スレッド: {threads})")
    print(f"ユニーク記事数: {unique_urls}")
    print(f"フリーフォーム投稿: {topics}")
    print(f"期間: {oldest[:10]} 〜 {newest[:10]}")

    if tone_rows:
        print(f"\nトーン別:")
        for tone_name, cnt in tone_rows:
            print(f"  {tone_name}: {cnt}")

    if daily_rows:
        print(f"\n日別投稿数（直近7日）:")
        for day, cnt in daily_rows:
            bar = "#" * cnt
            print(f"  {day}: {bar} ({cnt})")


# --- AI-Powered Twitter Operations ---

def cmd_improve(args, config):
    """下書きテキストをAIでTwitter向けに改善する"""
    text = args.text
    tone = getattr(args, 'tone', None)
    clipboard = getattr(args, 'clipboard', False)
    ai_cli = args.ai

    prompt = (
        "以下の文章をX（Twitter）投稿として改善してください。\n"
        "改善版を3つ作ってください。それぞれ異なるアプローチで。\n"
        "出力はツイート内容のみを1行ずつ出力してください。番号は付けないでください。\n"
        f"280文字以内に収めてください。\n\n元の文章: {text}"
    )
    if tone and tone in TONE_PRESETS:
        prompt = f"【トーン指定】{TONE_PRESETS[tone]}\n\n{prompt}"

    print(f"Improving tweet using {ai_cli} CLI...")
    content = run_ai_cli(ai_cli, prompt)
    tweets = parse_ai_tweets(content, max_count=3)

    if not tweets:
        print("Error: AI が改善案を生成できませんでした。")
        sys.exit(1)

    print(f"\n--- Original ---\n{text} ({len(text)}文字)")
    print(f"\n--- Improved Versions ---")
    for i, t in enumerate(tweets, 1):
        print(format_tweet_display(t, i))

    if getattr(args, 'dry_run', False):
        return

    while True:
        try:
            actions = f"番号で投稿 (1-{len(tweets)}), 'e数字' で編集, 'c数字' でコピー, 'o' で元のまま投稿, 'q' で中止"
            choice = input(f"\n{actions}: ").strip()
        except EOFError:
            break
        if choice.lower() == 'q':
            break
        if choice.lower() == 'o':
            if clipboard:
                copy_to_clipboard(text)
                print("元のテキストをクリップボードにコピーしました。")
            else:
                run_twitter(config, "post", text)
                save_post(text)
            break

        edit_match = re.match(r'^e(\d+)$', choice.lower())
        if edit_match:
            idx = int(edit_match.group(1)) - 1
            if 0 <= idx < len(tweets):
                tweets[idx] = edit_tweet(tweets[idx])
                print(format_tweet_display(tweets[idx], idx + 1) + " (編集済み)")
            continue

        clip_match = re.match(r'^c(\d+)$', choice.lower())
        if clip_match:
            idx = int(clip_match.group(1)) - 1
            if 0 <= idx < len(tweets):
                if copy_to_clipboard(tweets[idx]):
                    print("  クリップボードにコピーしました。")
            continue

        try:
            idx = int(choice) - 1
        except ValueError:
            continue
        if 0 <= idx < len(tweets):
            if clipboard:
                copy_to_clipboard(tweets[idx])
                print("クリップボードにコピーしました。")
            else:
                run_twitter(config, "post", tweets[idx])
                save_post(tweets[idx], tone=tone)
            break


def cmd_reply_suggest(args, config):
    """特定ツイートへのリプライ案をAI生成する"""
    tweet_id = args.tweet_id
    ai_cli = args.ai
    tone = getattr(args, 'tone', None)

    # ツイート内容を取得
    print(f"ツイート {tweet_id} を取得中...")
    tweet_content = run_twitter_capture(config, "tweet", tweet_id, "--json")
    if not tweet_content:
        print("Error: ツイートの取得に失敗しました。")
        sys.exit(1)

    # JSON パースを試みる。失敗したら生テキストを使う
    try:
        tweet_data = json.loads(tweet_content)
        if isinstance(tweet_data, list) and tweet_data:
            tweet_text = tweet_data[0].get("text", tweet_content)
            tweet_author = tweet_data[0].get("user", {}).get("screen_name", "")
        elif isinstance(tweet_data, dict):
            tweet_text = tweet_data.get("text", tweet_content)
            tweet_author = tweet_data.get("user", {}).get("screen_name", "")
        else:
            tweet_text = tweet_content
            tweet_author = ""
    except (json.JSONDecodeError, TypeError):
        tweet_text = tweet_content.strip()
        tweet_author = ""

    author_info = f" (@{tweet_author})" if tweet_author else ""
    print(f"\n--- 元のツイート{author_info} ---\n{tweet_text[:280]}")

    prompt = (
        "以下のツイートに対する自然なリプライを5つ作ってください。\n"
        "AIっぽくない、人間が書いたような自然な口調で。\n"
        "共感、質問、補足情報、ユーモアなど多様なアプローチで。\n"
        "出力はリプライ内容のみを1行ずつ出力してください。\n"
        f"\n元のツイート: {tweet_text}"
    )
    if tone and tone in TONE_PRESETS:
        prompt = f"【トーン指定】{TONE_PRESETS[tone]}\n\n{prompt}"

    print(f"\nリプライ案を生成中 ({ai_cli})...")
    content = run_ai_cli(ai_cli, prompt)
    replies = parse_ai_tweets(content, max_count=5)

    if not replies:
        print("Error: リプライ案を生成できませんでした。")
        sys.exit(1)

    print(f"\n--- Reply Suggestions ---")
    for i, r in enumerate(replies, 1):
        print(format_tweet_display(r, i))

    if getattr(args, 'dry_run', False):
        return

    while True:
        try:
            choice = input(f"\n番号でリプライ (1-{len(replies)}), 'e数字' で編集, 'q' で中止: ").strip()
        except EOFError:
            break
        if choice.lower() == 'q':
            break

        edit_match = re.match(r'^e(\d+)$', choice.lower())
        if edit_match:
            idx = int(edit_match.group(1)) - 1
            if 0 <= idx < len(replies):
                replies[idx] = edit_tweet(replies[idx])
                print(format_tweet_display(replies[idx], idx + 1) + " (編集済み)")
            continue

        try:
            idx = int(choice) - 1
        except ValueError:
            continue
        if 0 <= idx < len(replies):
            run_twitter(config, "reply", tweet_id, replies[idx])
            save_post(replies[idx])
            break


def cmd_digest(args, config):
    """タイムラインをAIで要約する"""
    ai_cli = args.ai
    max_tweets = getattr(args, 'max', 20) or 20
    feed_type = getattr(args, 'type', None)

    # タイムラインを取得
    extra = ["feed", "--json", "--max", str(max_tweets)]
    if feed_type:
        extra += ["-t", feed_type]

    print(f"タイムライン取得中 (最大 {max_tweets} 件)...")
    feed_output = run_twitter_capture(config, *extra)

    if not feed_output:
        print("Error: タイムラインの取得に失敗しました。")
        sys.exit(1)

    # ツイートテキストを抽出
    try:
        feed_data = json.loads(feed_output)
    except json.JSONDecodeError:
        # JSON パース失敗 → 生テキストを使う
        feed_data = None

    if feed_data and isinstance(feed_data, list):
        tweet_texts = []
        for item in feed_data[:max_tweets]:
            user = item.get("user", {}).get("screen_name", "?")
            text = item.get("text", "")
            if text:
                tweet_texts.append(f"@{user}: {text}")
        timeline_text = "\n".join(tweet_texts)
    else:
        timeline_text = feed_output[:5000]

    if not timeline_text.strip():
        print("タイムラインが空です。")
        return

    prompt = (
        "以下はX（Twitter）のタイムラインです。\n"
        "これを以下の形式で要約してください：\n\n"
        "1. **今日の主要トピック**（3-5個、箇条書き）\n"
        "2. **注目のツイート**（特に反応が多そうなもの1-2個を引用）\n"
        "3. **全体の雰囲気**（1文で）\n\n"
        f"タイムライン:\n{timeline_text[:4000]}"
    )

    print(f"AI で要約中 ({ai_cli})...")
    content = run_ai_cli(ai_cli, prompt)
    print(f"\n--- Timeline Digest ---\n{content.strip()}")


def cmd_engage(args, config):
    """キーワードにマッチするツイートに自動いいねする"""
    keywords = args.keywords
    max_count = getattr(args, 'max', 10) or 10
    dry_run = getattr(args, 'dry_run', False)

    for keyword in keywords:
        print(f"\n検索中: \"{keyword}\" ...")
        search_output = run_twitter_capture(config, "search", keyword, "-t", "Latest", "--max", str(max_count), "--json")

        if not search_output:
            print(f"  検索結果なし。")
            continue

        try:
            results = json.loads(search_output)
        except json.JSONDecodeError:
            print(f"  検索結果のパースに失敗しました。")
            continue

        if not isinstance(results, list):
            continue

        liked = 0
        for tweet in results:
            tweet_id = tweet.get("id_str") or tweet.get("id")
            text = tweet.get("text", "")[:80]
            user = tweet.get("user", {}).get("screen_name", "?")
            if not tweet_id:
                continue

            if dry_run:
                print(f"  [dry-run] Like: @{user}: {text}...")
            else:
                print(f"  Like: @{user}: {text}...")
                run_twitter(config, "like", str(tweet_id))
            liked += 1

        status = "プレビュー" if dry_run else "いいね"
        print(f"  → {liked} 件 {status}")


def cmd_recycle(args, config):
    """過去の投稿をAIでリフレーズして再投稿する"""
    ai_cli = args.ai
    tone = getattr(args, 'tone', None)
    dry_run = getattr(args, 'dry_run', False)

    db = init_db()
    rows = db.execute(
        "SELECT id, tweet_text, posted_at FROM posts WHERE is_thread = 0 ORDER BY posted_at DESC LIMIT 20"
    ).fetchall()
    db.close()

    if not rows:
        print("リサイクル可能な過去の投稿がありません。")
        return

    print("--- 過去の投稿 ---")
    for i, (pid, text, posted_at) in enumerate(rows, 1):
        print(f"\n[{i}] ({posted_at[:10]})")
        print(f"  {text[:100]}{'...' if len(text) > 100 else ''}")

    try:
        choice = input(f"\nリフレーズする投稿を選択 (1-{len(rows)}, 'q' で中止): ").strip()
    except EOFError:
        return
    if choice.lower() == 'q':
        return
    try:
        idx = int(choice) - 1
    except ValueError:
        print("無効な入力です。")
        return
    if not (0 <= idx < len(rows)):
        print("範囲外です。")
        return

    original = rows[idx][1]
    prompt = (
        "以下の過去のツイートを、同じ内容を伝えつつ全く違う言い回しでリフレーズしてください。\n"
        "コピーではなく、新鮮に聞こえるように。3つのバリエーションを作ってください。\n"
        "出力はツイート内容のみを1行ずつ出力してください。\n"
        f"\n元のツイート: {original}"
    )
    if tone and tone in TONE_PRESETS:
        prompt = f"【トーン指定】{TONE_PRESETS[tone]}\n\n{prompt}"

    print(f"\nリフレーズ中 ({ai_cli})...")
    content = run_ai_cli(ai_cli, prompt)
    tweets = parse_ai_tweets(content, max_count=3)

    if not tweets:
        print("Error: リフレーズを生成できませんでした。")
        return

    print(f"\n--- Original ---\n{original}")
    print(f"\n--- Recycled Versions ---")
    for i, t in enumerate(tweets, 1):
        print(format_tweet_display(t, i))

    if dry_run:
        return

    while True:
        try:
            choice = input(f"\n番号で投稿 (1-{len(tweets)}), 'e数字' で編集, 'q' で中止: ").strip()
        except EOFError:
            break
        if choice.lower() == 'q':
            break

        edit_match = re.match(r'^e(\d+)$', choice.lower())
        if edit_match:
            idx = int(edit_match.group(1)) - 1
            if 0 <= idx < len(tweets):
                tweets[idx] = edit_tweet(tweets[idx])
                print(format_tweet_display(tweets[idx], idx + 1) + " (編集済み)")
            continue

        try:
            idx = int(choice) - 1
        except ValueError:
            continue
        if 0 <= idx < len(tweets):
            run_twitter(config, "post", tweets[idx])
            save_post(tweets[idx], tone=tone)
            break


# --- Schedule Queue ---

QUEUE_TABLE = "schedule_queue"


def init_queue_db():
    db = init_db()
    db.execute(f"""
        CREATE TABLE IF NOT EXISTS {QUEUE_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_text TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    db.commit()
    return db


def cmd_schedule_add(args, config):
    """ツイートをキューに追加する"""
    text = args.text
    scheduled_at = args.at

    # 日時パース検証
    try:
        dt = datetime.fromisoformat(scheduled_at)
    except ValueError:
        print(f"Error: 日時フォーマットが不正です: {scheduled_at}")
        print("  例: 2026-04-06T18:00 or 2026-04-06 18:00")
        sys.exit(1)

    db = init_queue_db()
    db.execute(
        f"INSERT INTO {QUEUE_TABLE} (tweet_text, scheduled_at, created_at) VALUES (?, ?, ?)",
        (text, dt.isoformat(), datetime.now().isoformat())
    )
    db.commit()
    db.close()
    print(f"キューに追加しました: {dt.strftime('%Y-%m-%d %H:%M')} → {text[:60]}...")


def cmd_schedule_list(args, config):
    """キュー内のツイートを一覧表示する"""
    db = init_queue_db()
    rows = db.execute(
        f"SELECT id, tweet_text, scheduled_at, status FROM {QUEUE_TABLE} ORDER BY scheduled_at"
    ).fetchall()
    db.close()

    if not rows:
        print("キューは空です。")
        return

    pending = [r for r in rows if r[3] == 'pending']
    posted = [r for r in rows if r[3] == 'posted']

    if pending:
        print(f"\n--- 予約中 ({len(pending)} 件) ---")
        for qid, text, sched, status in pending:
            print(f"  [{qid}] {sched[:16]} → {text[:60]}{'...' if len(text) > 60 else ''}")

    if posted:
        print(f"\n--- 投稿済み ({len(posted)} 件) ---")
        for qid, text, sched, status in posted:
            print(f"  [{qid}] {sched[:16]} → {text[:60]}{'...' if len(text) > 60 else ''}")


def cmd_schedule_run(args, config):
    """予約時刻を過ぎたキュー内のツイートを投稿する"""
    now = datetime.now().isoformat()
    db = init_queue_db()
    rows = db.execute(
        f"SELECT id, tweet_text, scheduled_at FROM {QUEUE_TABLE} WHERE status = 'pending' AND scheduled_at <= ? ORDER BY scheduled_at",
        (now,)
    ).fetchall()

    if not rows:
        print("投稿すべきツイートはありません。")
        db.close()
        return

    dry_run = getattr(args, 'dry_run', False)

    for qid, text, sched in rows:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if dry_run:
            print(f"[{timestamp}] [dry-run] [{qid}] {text[:80]}...")
        else:
            print(f"[{timestamp}] Posting [{qid}]: {text[:80]}...")
            run_twitter(config, "post", text)
            db.execute(f"UPDATE {QUEUE_TABLE} SET status = 'posted' WHERE id = ?", (qid,))
            db.commit()
            save_post(text)

    status = "プレビュー" if dry_run else "投稿"
    print(f"\n{len(rows)} 件 {status}完了")
    db.close()


def cmd_schedule_remove(args, config):
    """キューからツイートを削除する"""
    qid = args.id
    db = init_queue_db()
    row = db.execute(f"SELECT tweet_text FROM {QUEUE_TABLE} WHERE id = ? AND status = 'pending'", (qid,)).fetchone()
    if not row:
        print(f"Error: ID {qid} の予約が見つかりません（投稿済みまたは存在しない）。")
        db.close()
        return
    db.execute(f"DELETE FROM {QUEUE_TABLE} WHERE id = ?", (qid,))
    db.commit()
    db.close()
    print(f"削除しました: {row[0][:60]}...")


# --- Drafts (Local) ---

DRAFTS_TABLE = "drafts"


def init_drafts_db():
    db = init_db()
    db.execute(f"""
        CREATE TABLE IF NOT EXISTS {DRAFTS_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            tone TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    db.commit()
    return db


def cmd_draft_save(args, config):
    """下書きをローカルに保存する"""
    text = args.text
    tone = getattr(args, 'tone', None)
    now = datetime.now().isoformat()
    db = init_drafts_db()
    db.execute(
        f"INSERT INTO {DRAFTS_TABLE} (text, tone, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (text, tone, now, now)
    )
    db.commit()
    db.close()
    print(f"下書きを保存しました: {text[:60]}{'...' if len(text) > 60 else ''}")


def cmd_draft_list(args, config):
    """下書き一覧を表示する"""
    db = init_drafts_db()
    rows = db.execute(
        f"SELECT id, text, tone, created_at FROM {DRAFTS_TABLE} ORDER BY updated_at DESC"
    ).fetchall()
    db.close()

    if not rows:
        print("下書きはありません。")
        return

    print(f"\n--- 下書き ({len(rows)} 件) ---")
    for did, text, tone, created_at in rows:
        tone_tag = f" [{tone}]" if tone else ""
        print(f"\n  [{did}]{tone_tag} ({created_at[:10]})")
        print(f"  {text[:100]}{'...' if len(text) > 100 else ''}")
        print(f"  ({len(text)}文字)")


def cmd_draft_edit(args, config):
    """下書きを編集する"""
    did = args.id
    db = init_drafts_db()
    row = db.execute(f"SELECT text FROM {DRAFTS_TABLE} WHERE id = ?", (did,)).fetchone()
    if not row:
        print(f"Error: ID {did} の下書きが見つかりません。")
        db.close()
        return
    new_text = edit_tweet(row[0])
    db.execute(
        f"UPDATE {DRAFTS_TABLE} SET text = ?, updated_at = ? WHERE id = ?",
        (new_text, datetime.now().isoformat(), did)
    )
    db.commit()
    db.close()
    print(f"下書きを更新しました ({len(new_text)}文字): {new_text[:60]}...")


def cmd_draft_post(args, config):
    """下書きを投稿する"""
    did = args.id
    dry_run = getattr(args, 'dry_run', False)
    db = init_drafts_db()
    row = db.execute(f"SELECT text, tone FROM {DRAFTS_TABLE} WHERE id = ?", (did,)).fetchone()
    if not row:
        print(f"Error: ID {did} の下書きが見つかりません。")
        db.close()
        return
    text, tone = row

    print(f"\n投稿する下書き ({len(text)}文字):\n  {text}")

    if dry_run:
        print("\n[dry-run] プレビューのみ。")
        db.close()
        return

    try:
        confirm = input("\n投稿しますか？ (y/N): ").strip().lower()
    except EOFError:
        db.close()
        return
    if confirm != 'y':
        print("キャンセルしました。")
        db.close()
        return

    run_twitter(config, "post", text)
    save_post(text, tone=tone)
    db.execute(f"DELETE FROM {DRAFTS_TABLE} WHERE id = ?", (did,))
    db.commit()
    db.close()
    print("投稿完了。下書きを削除しました。")


def cmd_draft_delete(args, config):
    """下書きを削除する"""
    did = args.id
    db = init_drafts_db()
    row = db.execute(f"SELECT text FROM {DRAFTS_TABLE} WHERE id = ?", (did,)).fetchone()
    if not row:
        print(f"Error: ID {did} の下書きが見つかりません。")
        db.close()
        return
    db.execute(f"DELETE FROM {DRAFTS_TABLE} WHERE id = ?", (did,))
    db.commit()
    db.close()
    print(f"下書きを削除しました: {row[0][:60]}...")


# --- Advanced AI Operations ---

def cmd_analyze(args, config):
    """特定ユーザーの投稿傾向をAI分析する"""
    username = args.username
    ai_cli = args.ai
    max_tweets = getattr(args, 'max', 20) or 20

    print(f"@{username} のツイートを取得中 (最大 {max_tweets} 件)...")
    output = run_twitter_capture(config, "user-posts", username, "--max", str(max_tweets), "--json")

    if not output:
        print("Error: ツイートの取得に失敗しました。")
        sys.exit(1)

    try:
        tweets_data = json.loads(output)
    except json.JSONDecodeError:
        tweets_data = None

    if tweets_data and isinstance(tweets_data, list):
        tweet_texts = [t.get("text", "") for t in tweets_data if t.get("text")]
        timeline_text = "\n---\n".join(tweet_texts)
    else:
        timeline_text = output[:5000]

    prompt = (
        f"以下は @{username} の最近のツイートです。\n"
        "このユーザーの投稿傾向を分析してください：\n\n"
        "1. **主なトピック・関心領域**（3-5個）\n"
        "2. **投稿スタイルの特徴**（口調、長さ、絵文字使用、ハッシュタグなど）\n"
        "3. **エンゲージメント戦略**（どんな投稿がウケそうか）\n"
        "4. **投稿頻度・時間帯の傾向**\n"
        "5. **このアカウントとの効果的な交流方法**\n\n"
        f"ツイート:\n{timeline_text[:4000]}"
    )

    print(f"AI で分析中 ({ai_cli})...")
    content = run_ai_cli(ai_cli, prompt)
    print(f"\n--- @{username} の投稿分析 ---\n{content.strip()}")


def cmd_translate(args, config):
    """ツイートを翻訳してクロスポストする"""
    text = args.text
    target = getattr(args, 'lang', 'en')
    ai_cli = args.ai
    dry_run = getattr(args, 'dry_run', False)
    clipboard = getattr(args, 'clipboard', False)

    lang_names = {"en": "English", "ja": "Japanese", "zh": "Chinese", "ko": "Korean",
                  "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese"}
    lang_name = lang_names.get(target, target)

    prompt = (
        f"以下のツイートを{lang_name}に翻訳してください。\n"
        "X（Twitter）投稿として自然に読めるように意訳してOK。\n"
        "直訳ではなく、その言語のネイティブが書いたような文章にしてください。\n"
        "3つのバリエーションを作ってください。\n"
        "出力は翻訳内容のみを1行ずつ出力してください。\n"
        f"\n元のツイート: {text}"
    )

    print(f"Translating to {lang_name} using {ai_cli}...")
    content = run_ai_cli(ai_cli, prompt)
    tweets = parse_ai_tweets(content, max_count=3)

    if not tweets:
        print("Error: 翻訳を生成できませんでした。")
        sys.exit(1)

    print(f"\n--- Original ---\n{text} ({len(text)}文字)")
    print(f"\n--- {lang_name} Translations ---")
    for i, t in enumerate(tweets, 1):
        print(format_tweet_display(t, i))

    if dry_run:
        return

    while True:
        try:
            actions = f"番号で投稿 (1-{len(tweets)}), 'e数字' で編集, 'q' で中止"
            choice = input(f"\n{actions}: ").strip()
        except EOFError:
            break
        if choice.lower() == 'q':
            break

        edit_match = re.match(r'^e(\d+)$', choice.lower())
        if edit_match:
            idx = int(edit_match.group(1)) - 1
            if 0 <= idx < len(tweets):
                tweets[idx] = edit_tweet(tweets[idx])
                print(format_tweet_display(tweets[idx], idx + 1) + " (編集済み)")
            continue

        try:
            idx = int(choice) - 1
        except ValueError:
            continue
        if 0 <= idx < len(tweets):
            if clipboard:
                if copy_to_clipboard(tweets[idx]):
                    print("クリップボードにコピーしました。")
            else:
                run_twitter(config, "post", tweets[idx])
                save_post(tweets[idx])
            break


def cmd_trending(args, config):
    """検索キーワードの最新ツイートからトレンドをAI分析する"""
    query = args.query
    ai_cli = args.ai
    max_tweets = getattr(args, 'max', 30) or 30

    print(f"\"{query}\" の最新ツイートを取得中 (最大 {max_tweets} 件)...")
    output = run_twitter_capture(
        config, "search", query, "-t", "Latest", "--max", str(max_tweets), "--json"
    )

    if not output:
        print("Error: 検索結果の取得に失敗しました。")
        sys.exit(1)

    try:
        results = json.loads(output)
    except json.JSONDecodeError:
        results = None

    if results and isinstance(results, list):
        tweet_texts = []
        for item in results:
            user = item.get("user", {}).get("screen_name", "?")
            text = item.get("text", "")
            if text:
                tweet_texts.append(f"@{user}: {text}")
        search_text = "\n---\n".join(tweet_texts)
    else:
        search_text = output[:5000]

    prompt = (
        f"以下は「{query}」で検索した最新のツイートです。\n"
        "このトピックのトレンドを分析してください：\n\n"
        "1. **現在の主要な話題**（3-5個、箇条書き）\n"
        "2. **意見の分布**（賛成/反対/中立の傾向）\n"
        "3. **注目すべき視点やユニークな意見**\n"
        "4. **今このトピックでツイートするなら**（3つの角度を提案）\n\n"
        f"ツイート:\n{search_text[:4000]}"
    )

    print(f"AI でトレンド分析中 ({ai_cli})...")
    content = run_ai_cli(ai_cli, prompt)
    print(f"\n--- Trend Analysis: \"{query}\" ---\n{content.strip()}")


def cmd_chain(args, config):
    """generate → improve → schedule/post を一気通貫で実行するワークフロー"""
    ai_cli = args.ai
    tone = getattr(args, 'tone', None)
    schedule_at = getattr(args, 'at', None)
    dry_run = getattr(args, 'dry_run', False)

    # Step 1: テーマまたはURLからツイート生成
    post_data = resolve_post_data(args, config)
    if post_data is None:
        return

    label = post_data.get("topic") or post_data.get("title") or post_data.get("url") or "Free-form"
    print(f"\n=== Step 1: 生成 ({label}) ===")
    tweets = generate_tweets_with_cli(post_data, config, ai_cli=ai_cli, tone=tone)

    if not tweets:
        print("Error: AI がツイートを生成できませんでした。")
        sys.exit(1)

    for i, t in enumerate(tweets, 1):
        print(format_tweet_display(t, i))

    # Step 2: ベスト案を選択
    try:
        choice = input(f"\nベスト案を選択 (1-{len(tweets)}), 'q' で中止: ").strip()
    except EOFError:
        return
    if choice.lower() == 'q':
        return
    try:
        idx = int(choice) - 1
    except ValueError:
        print("無効な入力です。")
        return
    if not (0 <= idx < len(tweets)):
        print("範囲外です。")
        return

    selected = tweets[idx]

    # Step 3: AI で改善
    print(f"\n=== Step 2: AI で改善中 ===")
    improve_prompt = (
        "以下の文章をX（Twitter）投稿としてさらに改善してください。\n"
        "改善版を3つ作ってください。よりキャッチーに、自然に。\n"
        "出力はツイート内容のみを1行ずつ出力してください。\n"
        f"280文字以内に収めてください。\n\n元の文章: {selected}"
    )
    if tone and tone in TONE_PRESETS:
        improve_prompt = f"【トーン指定】{TONE_PRESETS[tone]}\n\n{improve_prompt}"

    content = run_ai_cli(ai_cli, improve_prompt)
    improved = parse_ai_tweets(content, max_count=3)

    if not improved:
        print("改善案を生成できませんでした。元のツイートを使用します。")
        final = selected
    else:
        print(f"\n--- Original ---\n{selected}")
        print(f"\n--- Improved ---")
        for i, t in enumerate(improved, 1):
            print(format_tweet_display(t, i))

        try:
            choice2 = input(f"\n改善版を選択 (1-{len(improved)}), '0' で元のまま, 'q' で中止: ").strip()
        except EOFError:
            return
        if choice2.lower() == 'q':
            return
        if choice2 == '0':
            final = selected
        else:
            try:
                idx2 = int(choice2) - 1
            except ValueError:
                final = selected
            else:
                final = improved[idx2] if 0 <= idx2 < len(improved) else selected

    # Step 4: スケジュールまたは投稿
    if schedule_at:
        print(f"\n=== Step 3: スケジュール ===")
        try:
            dt = datetime.fromisoformat(schedule_at)
        except ValueError:
            print(f"Error: 日時フォーマットが不正です: {schedule_at}")
            return
        if dry_run:
            print(f"[dry-run] {dt.strftime('%Y-%m-%d %H:%M')} に予約: {final[:80]}...")
            return
        db = init_queue_db()
        db.execute(
            f"INSERT INTO {QUEUE_TABLE} (tweet_text, scheduled_at, created_at) VALUES (?, ?, ?)",
            (final, dt.isoformat(), datetime.now().isoformat())
        )
        db.commit()
        db.close()
        print(f"予約しました: {dt.strftime('%Y-%m-%d %H:%M')} → {final[:60]}...")
    else:
        print(f"\n=== Step 3: 投稿 ===")
        print(f"最終テキスト ({len(final)}文字):\n  {final}")
        if dry_run:
            print("\n[dry-run] プレビューのみ。")
            return
        try:
            confirm = input("\n投稿しますか？ (y/N): ").strip().lower()
        except EOFError:
            return
        if confirm != 'y':
            print("キャンセルしました。")
            return
        article_url = post_data.get("url") or None
        run_twitter(config, "post", final)
        save_post(final, article_url=article_url, tone=tone)
        print("投稿完了！")


# --- Read Operations ---

def _build_twitter_args(args, command, positional=None):
    """Read系コマンドの共通引数を組み立てるヘルパー"""
    extra = []
    if getattr(args, 'compact', False):
        extra.append("-c")
    extra.append(command)
    if positional:
        extra += positional
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
    return extra


def cmd_feed(args, config):
    run_twitter(config, *_build_twitter_args(args, "feed"))


def cmd_bookmarks(args, config):
    run_twitter(config, *_build_twitter_args(args, "bookmarks"))


def cmd_search(args, config):
    run_twitter(config, *_build_twitter_args(args, "search", [args.query]))


def cmd_tweet(args, config):
    run_twitter(config, *_build_twitter_args(args, "tweet", [args.id_or_url]))


def cmd_list(args, config):
    run_twitter(config, *_build_twitter_args(args, "list", [args.list_id]))


def cmd_user_posts(args, config):
    run_twitter(config, *_build_twitter_args(args, "user-posts", [args.username]))


def cmd_likes(args, config):
    run_twitter(config, *_build_twitter_args(args, "likes", [args.username]))


def cmd_followers(args, config):
    run_twitter(config, *_build_twitter_args(args, "followers", [args.username]))


def cmd_following(args, config):
    run_twitter(config, *_build_twitter_args(args, "following", [args.username]))


def cmd_whoami(args, config):
    run_twitter(config, *_build_twitter_args(args, "whoami"))


def cmd_status(args, config):
    run_twitter(config, *_build_twitter_args(args, "status"))


def cmd_user(args, config):
    run_twitter(config, *_build_twitter_args(args, "user", [args.username]))


# --- Write Operations ---

def cmd_post(args, config):
    extra = ["post", args.text]
    if getattr(args, 'reply_to', None):
        extra += ["--reply-to", args.reply_to]
    run_twitter(config, *extra)
    save_post(args.text)


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
    generate         AIでツイートを生成して投稿
    generate-thread  AIでスレッド（連続ツイート）を生成して投稿
    generate-batch   未投稿記事をまとめて生成・投稿

  [AI支援]
    improve          下書きテキストをAIで改善
    reply-suggest    ツイートへのリプライ案をAI生成
    digest           タイムラインをAIで要約
    engage           キーワードにマッチするツイートに自動いいね
    recycle          過去の投稿をAIでリフレーズして再投稿
    analyze          ユーザーの投稿傾向をAI分析
    translate        ツイートを翻訳してクロスポスト
    trending         キーワードのトレンドをAI分析
    chain            生成→改善→投稿の一気通貫ワークフロー

  [下書き]
    draft-save       下書きをローカルに保存
    draft-list       下書き一覧を表示
    draft-edit       下書きを編集
    draft-post       下書きを投稿
    draft-delete     下書きを削除

  [スケジュール]
    schedule-add     ツイートを予約キューに追加
    schedule-list    予約キューを一覧表示
    schedule-run     予約時刻を過ぎたツイートを投稿
    schedule-remove  予約キューからツイートを削除

  [履歴・統計]
    history          投稿履歴を表示
    history-clear    投稿履歴をすべて削除
    stats            投稿統計を表示

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
    p.add_argument("input", nargs="?", help="記事URL、slug、またはフリーテーマ")
    p.add_argument("--topic", metavar="THEME", help="自由なテーマからツイート生成（URL不要）")
    p.add_argument("--auto", action="store_true", help="自動でランダム選択して投稿")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="ツイートのトーン")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.add_argument("--force", action="store_true", help="重複チェックをスキップ")
    p.add_argument("--clipboard", action="store_true", help="投稿せずクリップボードにコピー")
    p.set_defaults(func=cmd_generate)

    # generate-thread
    p = subparsers.add_parser("generate-thread", help="AIでスレッドを生成して投稿")
    p.add_argument("input", nargs="?", help="記事URL、slug、またはフリーテーマ")
    p.add_argument("--topic", metavar="THEME", help="自由なテーマからスレッド生成（URL不要）")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="ツイートのトーン")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.add_argument("--clipboard", action="store_true", help="投稿せずクリップボードにコピー")
    p.add_argument("--count", type=int, default=4, metavar="N", help="スレッドのツイート数 (デフォルト: 4)")
    p.set_defaults(func=cmd_generate_thread)

    # generate-batch
    p = subparsers.add_parser("generate-batch", help="未投稿記事をまとめて生成・投稿")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="ツイートのトーン")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    add_max_flag(p)
    p.set_defaults(func=cmd_generate_batch)

    # history
    p = subparsers.add_parser("history", help="投稿履歴を表示")
    add_max_flag(p)
    p.add_argument("--json", action="store_true", help="JSON形式で出力")
    p.add_argument("-o", "--output", metavar="FILE", help="ファイルにエクスポート")
    p.set_defaults(func=cmd_history)

    # history-clear
    p = subparsers.add_parser("history-clear", help="投稿履歴をすべて削除")
    p.set_defaults(func=cmd_history_clear)

    # stats
    p = subparsers.add_parser("stats", help="投稿統計を表示")
    p.set_defaults(func=cmd_stats)

    # improve
    p = subparsers.add_parser("improve", help="下書きテキストをAIで改善")
    p.add_argument("text", help="改善したいテキスト")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="ツイートのトーン")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.add_argument("--clipboard", action="store_true", help="投稿せずクリップボードにコピー")
    p.set_defaults(func=cmd_improve)

    # reply-suggest
    p = subparsers.add_parser("reply-suggest", help="ツイートへのリプライ案をAI生成")
    add_tweet_id_arg(p)
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="リプライのトーン")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.set_defaults(func=cmd_reply_suggest)

    # digest
    p = subparsers.add_parser("digest", help="タイムラインをAIで要約")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("-t", "--type", choices=["following"], help="following タイムライン")
    add_max_flag(p)
    p.set_defaults(func=cmd_digest)

    # engage
    p = subparsers.add_parser("engage", help="キーワードにマッチするツイートに自動いいね")
    p.add_argument("keywords", nargs="+", help="検索キーワード（複数指定可）")
    add_max_flag(p)
    p.add_argument("--dry-run", action="store_true", help="いいねせずプレビューのみ")
    p.set_defaults(func=cmd_engage)

    # recycle
    p = subparsers.add_parser("recycle", help="過去の投稿をAIでリフレーズして再投稿")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="ツイートのトーン")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.set_defaults(func=cmd_recycle)

    # schedule-add
    p = subparsers.add_parser("schedule-add", help="ツイートを予約キューに追加")
    p.add_argument("text", help="投稿するテキスト")
    p.add_argument("--at", required=True, metavar="DATETIME", help="予約日時 (例: 2026-04-06T18:00)")
    p.set_defaults(func=cmd_schedule_add)

    # schedule-list
    p = subparsers.add_parser("schedule-list", help="予約キューを一覧表示")
    p.set_defaults(func=cmd_schedule_list)

    # schedule-run
    p = subparsers.add_parser("schedule-run", help="予約時刻を過ぎたツイートを投稿")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.set_defaults(func=cmd_schedule_run)

    # schedule-remove
    p = subparsers.add_parser("schedule-remove", help="予約キューからツイートを削除")
    p.add_argument("id", type=int, help="削除するキューID")
    p.set_defaults(func=cmd_schedule_remove)

    # draft-save
    p = subparsers.add_parser("draft-save", help="下書きをローカルに保存")
    p.add_argument("text", help="下書きテキスト")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="トーンタグ")
    p.set_defaults(func=cmd_draft_save)

    # draft-list
    p = subparsers.add_parser("draft-list", help="下書き一覧を表示")
    p.set_defaults(func=cmd_draft_list)

    # draft-edit
    p = subparsers.add_parser("draft-edit", help="下書きを編集")
    p.add_argument("id", type=int, help="下書きID")
    p.set_defaults(func=cmd_draft_edit)

    # draft-post
    p = subparsers.add_parser("draft-post", help="下書きを投稿")
    p.add_argument("id", type=int, help="下書きID")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.set_defaults(func=cmd_draft_post)

    # draft-delete
    p = subparsers.add_parser("draft-delete", help="下書きを削除")
    p.add_argument("id", type=int, help="下書きID")
    p.set_defaults(func=cmd_draft_delete)

    # analyze
    p = subparsers.add_parser("analyze", help="ユーザーの投稿傾向をAI分析")
    add_username_arg(p)
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    add_max_flag(p)
    p.set_defaults(func=cmd_analyze)

    # translate
    p = subparsers.add_parser("translate", help="ツイートを翻訳してクロスポスト")
    p.add_argument("text", help="翻訳するテキスト")
    p.add_argument("--lang", default="en", help="翻訳先言語コード (デフォルト: en)")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.add_argument("--clipboard", action="store_true", help="投稿せずクリップボードにコピー")
    p.set_defaults(func=cmd_translate)

    # trending
    p = subparsers.add_parser("trending", help="キーワードのトレンドをAI分析")
    p.add_argument("query", help="検索キーワード")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    add_max_flag(p)
    p.set_defaults(func=cmd_trending)

    # chain
    p = subparsers.add_parser("chain", help="生成→改善→投稿/スケジュールの一気通貫ワークフロー")
    p.add_argument("input", nargs="?", help="記事URL、slug、またはフリーテーマ")
    p.add_argument("--topic", metavar="THEME", help="自由なテーマからツイート生成")
    p.add_argument("--ai", choices=["gemini", "codex", "claude"], default="gemini", help="使用するAI CLI")
    p.add_argument("--tone", choices=list(TONE_PRESETS.keys()), help="ツイートのトーン")
    p.add_argument("--at", metavar="DATETIME", help="スケジュール日時 (例: 2026-04-06T18:00)")
    p.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    p.add_argument("--auto", action="store_true", help="自動選択")
    p.add_argument("--force", action="store_true", help="重複チェックスキップ")
    p.set_defaults(func=cmd_chain)

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

    # config 不要なコマンド（SQLiteのみで完結）
    config_free = (
        "history", "history-clear", "stats",
        "schedule-add", "schedule-list", "schedule-remove",
        "draft-save", "draft-list", "draft-edit", "draft-delete",
    )
    if args.command in config_free:
        if not hasattr(args, 'func'):
            parser.print_help()
            return
        args.func(args, {})
        return

    config = load_config()
    validate_config(config, args.command)
    if not hasattr(args, 'func'):
        parser.print_help()
        return
    args.func(args, config)


if __name__ == "__main__":
    main()
