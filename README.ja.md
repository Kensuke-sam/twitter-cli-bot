# twitter-cli-bot

[twitter-cli](https://github.com/jackwener/twitter-cli) とローカルAI CLI（Gemini・Codex・Claude）を組み合わせ、記事からツイートを自動生成・投稿するCLIツールです。twitter-cliの全機能を単一のエントリポイントからそのまま利用できます。

> **Twitter APIキー不要。** 認証はtwitter-cliがブラウザのCookieを自動抽出して処理します。

## 特徴

- **AI によるツイート自動生成** — 記事URLをもとにGemini・Codex・ClaudeでツイートをX件生成
- **対話モード / 自動モード** — 手動で選ぶか、ランダム自動投稿（cron連携向け）
- **twitter-cli の全機能をラップ** — 読み取り・書き込み操作すべてをサブコマンドとして提供
- **設定ファイル方式** — どんなブログ・サイトでも `config.json` を書くだけで対応

## 必要なもの

- Python 3.8+
- [uv](https://github.com/astral-sh/uv)
- [twitter-cli](https://github.com/jackwener/twitter-cli)
- いずれか1つのAI CLI: `gemini` / `codex` / `claude`

## セットアップ

### 1. クローンと設定

```bash
git clone https://github.com/Kensuke-sam/twitter-cli-bot
cd twitter-cli-bot
cp config.json.sample config.json
```

`config.json` を編集：

```json
{
  "site_name": "自分のサイト名",
  "base_url": "https://your-domain.com",
  "posts_file_path": "/path/to/posts.ts",
  "twitter_cli_path": "/path/to/twitter-cli",
  "prompt_template": "...",
  "twitter_auth_token": "",
  "twitter_ct0": ""
}
```

| キー | 説明 |
|------|------|
| `posts_file_path` | 記事データファイルのパス（`.ts` / `.js` / `.json`） |
| `twitter_cli_path` | ローカルにクローンした twitter-cli のパス |
| `twitter_auth_token` / `twitter_ct0` | 任意。省略するとtwitter-cliがブラウザCookieを自動取得 |

### 2. twitter-cli の認証

```bash
cd /path/to/twitter-cli
uv run twitter whoami
```

詳細は [twitter-cli のドキュメント](https://github.com/jackwener/twitter-cli) を参照してください。

## 使い方

### AI ツイート生成

指定した記事slugからツイート案を5つ生成して対話的に選択：

```bash
./tweet.sh generate your-article-slug --ai gemini
```

自動でランダム選択して即投稿（cron向け）：

```bash
./tweet.sh generate --auto --ai claude
```

slugを省略するとランダムに記事を選択：

```bash
./tweet.sh generate --auto
```

### 読み取り操作

```bash
./tweet.sh feed                          # ホームタイムライン
./tweet.sh feed -t following --max 30    # フォロー中タイムライン
./tweet.sh feed --yaml > tweets.yaml     # YAMLで保存
./tweet.sh bookmarks --max 20            # ブックマーク
./tweet.sh search "AIエージェント" -t Latest  # ツイート検索
./tweet.sh tweet 1234567890              # ツイート詳細
./tweet.sh list 1539453138322673664      # リストタイムライン
./tweet.sh user-posts elonmusk --max 20  # ユーザーのツイート一覧
./tweet.sh likes elonmusk                # ユーザーのいいね一覧
./tweet.sh followers elonmusk --max 50   # フォロワー一覧
./tweet.sh following elonmusk            # フォロー中一覧
./tweet.sh user elonmusk                 # ユーザープロフィール
./tweet.sh whoami                        # 認証中ユーザーの確認
./tweet.sh status                        # 認証状態確認
```

### 書き込み操作

```bash
./tweet.sh post "投稿するテキスト"
./tweet.sh post "返信テキスト" --reply-to 1234567890
./tweet.sh reply 1234567890 "返信テキスト"
./tweet.sh quote 1234567890 "コメント"
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

### 出力形式

ほとんどの読み取りコマンドで `--yaml` / `--json` / `-c`（コンパクト）/ `-o FILE` が使えます：

```bash
./tweet.sh feed --json | jq '.[0].text'
./tweet.sh search "rust" --max 10 -c     # LLM向けコンパクト出力
./tweet.sh bookmarks --yaml -o bm.yaml
```

## 定期投稿（cron）

1日3回、ランダムな記事から自動投稿する例：

```cron
0 9,12,18 * * * cd ~/twitter-cli-bot && ./tweet.sh generate --auto >> bot.log 2>&1
```

## ファイル構成

```
twitter-cli-bot/
├── tweet.sh            # エントリポイント
├── tweet_gen.py        # サブコマンドのロジック
├── config.json.sample  # 設定テンプレート
└── config.json         # ローカル設定（gitignore済み）
```

## 関連

- [twitter-cli](https://github.com/jackwener/twitter-cli) — このbotがラップしているTwitter/X CLIツール
