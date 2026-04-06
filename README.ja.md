# twitter-cli-bot

**記事URLからAIがツイートを自動生成 — Twitter APIキー不要。**

Gemini・Claude・Codex CLIを使ってツイート案を生成し、[twitter-cli](https://github.com/jackwener/twitter-cli)経由で対話的または自動的に投稿できます。

> ブログを書く開発者が、CLIだけでX（Twitter）への発信を完結させるために作りました。

---

## なぜ作ったか

開発者がSNSを管理するのは手間がかかります。このツールは既存のCLIワークフローに組み込めます：

1. 記事を書く
2. URLをこのツールに渡す
3. AIがツイート案を5つ生成する
4. 1つ選ぶ（または自動投稿）

ブラウザも、ダッシュボードも、Twitter APIの課金も不要。

---

## このツールでできること

- 記事URLまたはslugを入力として受け取る
- Gemini / Claude / Codex CLIを呼び出してツイート案を5つ生成
- 対話的に選んで投稿、またはcron用に自動投稿
- twitter-cliの全機能をラップ：タイムライン・ブックマーク・検索・いいね・フォローなど

---

## デモ

```
$ ./tweet.sh generate https://example.com/my-article --ai gemini --tone technical

Generating tweets using gemini CLI...
Tone: technical

--- Generated Tweets for: https://example.com/my-article ---

[1]
多くの開発者はX（Twitter）での発信を後回しにしている。
CLIから自動化する方法がある。
https://example.com/my-article
--------------------
[2]
記事を書いた。あとはツイートを自動化するだけ。
CLIファーストなコンテンツ配信の話。
https://example.com/my-article
--------------------
[3]
ブログのURLを手でTwitterに貼り付けるのをやめた。
シェルスクリプトがやってくれる。
https://example.com/my-article
--------------------

番号で選択 (1-3), 'e数字' で編集 (例: e1), 'q' で中止: 2

Successfully posted!
```

---

## 特徴

- 任意の記事URLからツイート案を生成
- **フリーフォーム生成** (`--topic`) — URL不要で自由なテーマからツイート生成
- Gemini・Claude Code・Codex CLIに対応
- 対話的な選択または完全自動投稿
- **スレッド生成** — 記事から複数ツイートのスレッドを生成・投稿
- **トーンプリセット** (`--tone`) — professional / casual / provocative / technical / humorous
- **投稿履歴** (SQLite) — 重複検出、`history`・`stats` サブコマンド
- **スマート auto** — `--auto` で投稿済み記事を自動スキップ
- **バッチ生成** (`generate-batch`) — 未投稿記事を一括処理
- **AI改善** (`improve`) — 下書きテキストをAIでツイート向けにブラッシュアップ
- **AIリプライ提案** (`reply-suggest`) — 特定ツイートへのリプライ案をAI生成
- **タイムライン要約** (`digest`) — タイムラインをAIで要約
- **自動エンゲージ** (`engage`) — キーワードにマッチするツイートに自動いいね
- **リサイクル** (`recycle`) — 過去の投稿をAIでリフレーズして再投稿
- **ユーザー分析** (`analyze`) — 特定ユーザーの投稿傾向をAI分析
- **翻訳** (`translate`) — ツイートを多言語翻訳してクロスポスト（en, ja, zh, ko, es, fr, de, pt）
- **トレンド分析** (`trending`) — キーワードのトレンドをAIで分析
- **チェーンワークフロー** (`chain`) — 生成→改善→投稿/スケジュールを一気通貫で実行
- **下書き管理** (`draft-save/list/edit/post/delete`) — ローカルに下書きをSQLite管理
- **スケジュール投稿** (`schedule-add/list/run/remove`) — 予約キューでcron投稿
- **文字数カウント** — ツイートごとに文字数表示、280文字超え警告
- **ドライラン** (`--dry-run`) — 投稿せずプレビュー
- **クリップボード** (`--clipboard`) — 投稿せずクリップボードにコピー
- **投稿前編集** — 生成結果をインラインまたは `$EDITOR` で修正可能
- **config バリデーション** — 設定ミスを分かりやすく報告
- cronによるスケジュール投稿に対応
- twitter-cliの全機能をラップ：`feed`・`search`・`bookmarks`・`like`・`follow`など
- Twitter APIキー不要 — twitter-cli経由でブラウザCookieを使用
- 最小構成は`twitter_cli_path`だけ

---

## ユースケース

- ブログ記事をXでシェアしたい開発者
- CLIファーストなコンテンツ自動化ワークフロー
- AIを活用したSNS投稿
- cronによる定期的なコンテンツ配信

---

## 必要なもの

- Python 3.8+
- [uv](https://github.com/astral-sh/uv)
- [twitter-cli](https://github.com/jackwener/twitter-cli)（ローカルにクローン済み）
- いずれか1つのAI CLI：`gemini` / `codex` / `claude`

---

## インストール

```bash
git clone https://github.com/Kensuke-sam/twitter-cli-bot
cd twitter-cli-bot
cp config.json.sample config.json
```

`config.json`を編集したあと、twitter-cliで認証します：

```bash
cd /path/to/twitter-cli
uv run twitter whoami
```

詳細は[twitter-cliのドキュメント](https://github.com/jackwener/twitter-cli)を参照してください。

---

## 設定

最小構成：

```json
{
  "twitter_cli_path": "/path/to/twitter-cli"
}
```

全項目の設定例：

```json
{
  "twitter_cli_path": "/path/to/twitter-cli",

  "site_name": "自分のブログ",
  "base_url": "https://your-domain.com",
  "posts_file_path": "/path/to/posts.ts",
  "prompt_template": "以下の記事についてツイートを5つ作ってください...\n\nURL: {url}\nタイトル: {title}",

  "twitter_auth_token": "",
  "twitter_ct0": ""
}
```

| キー | 必須 | 説明 |
|------|------|------|
| `twitter_cli_path` | 必須 | ローカルにクローンしたtwitter-cliのパス |
| `site_name` | `generate`（postsファイルモード）のみ | AIプロンプト内で使用するサイト名 |
| `base_url` | `generate`（postsファイルモード）のみ | サイトのルートURL |
| `posts_file_path` | `generate`（postsファイルモード）のみ | 記事データファイルのパス（`.ts`/`.js`/`.json`） |
| `prompt_template` | 任意 | カスタムプロンプト。省略時はデフォルトを使用 |
| `twitter_auth_token` / `twitter_ct0` | 任意 | 省略時はtwitter-cliがブラウザCookieを自動取得 |

> **補足：** `generate`はURLを直接渡せる（`./tweet.sh generate https://...`）ので、ローカルのpostsファイルから記事を引きたい場合以外はサイト関連の設定は不要です。

---

## 使い方

### ツイート生成・投稿

```bash
# URLを直接渡す
./tweet.sh generate https://example.com/my-article --ai gemini

# postsファイルのslugを指定
./tweet.sh generate my-article-slug --ai claude

# 自動投稿（cron向け）
./tweet.sh generate https://example.com/my-article --auto --ai codex

# postsファイルからランダムに記事を選んで自動投稿
./tweet.sh generate --auto

# プレビューのみ（投稿しない）
./tweet.sh generate https://example.com/my-article --dry-run

# トーン指定
./tweet.sh generate https://example.com/my-article --tone provocative

# 重複無視して強制投稿
./tweet.sh generate https://example.com/my-article --force

# フリーフォーム: URLなしで自由なテーマから生成
./tweet.sh generate --topic "RustとGoのCLI開発比較"
./tweet.sh generate "今日学んだWebAssemblyの話" --tone casual

# クリップボードにコピー（投稿しない）
./tweet.sh generate https://example.com/my-article --clipboard
```

### スレッド生成・投稿

```bash
# 4ツイートのスレッド生成（デフォルト）
./tweet.sh generate-thread https://example.com/my-article --ai gemini

# 6ツイート、カジュアルなトーンで
./tweet.sh generate-thread https://example.com/my-article --count 6 --tone casual

# プレビューのみ
./tweet.sh generate-thread https://example.com/my-article --dry-run
```

### 投稿履歴

```bash
# 最近の投稿履歴
./tweet.sh history

# 直近50件
./tweet.sh history --max 50

# 履歴をクリア
./tweet.sh history-clear

# 投稿統計を表示
./tweet.sh stats

# 履歴をJSONでエクスポート
./tweet.sh history --json
./tweet.sh history --json -o history.json
```

### バッチ生成

```bash
# 未投稿記事をすべてプレビュー
./tweet.sh generate-batch --dry-run --ai gemini

# 未投稿記事をすべて投稿
./tweet.sh generate-batch --ai gemini --tone professional

# 未投稿記事を最大5件まで投稿
./tweet.sh generate-batch --max 5 --ai gemini
```

### AI支援操作

```bash
# 下書きテキストをAIで改善
./tweet.sh improve "CLIツールを作った話" --ai gemini --tone professional

# ツイートへのリプライ案をAI生成
./tweet.sh reply-suggest 1234567890 --ai gemini --tone casual

# タイムラインをAIで要約
./tweet.sh digest --ai gemini --max 30

# キーワードにマッチするツイートに自動いいね
./tweet.sh engage "Rust CLI" "開発者ツール" --max 5
./tweet.sh engage "AIエージェント" --dry-run

# 過去の投稿をAIでリフレーズして再投稿
./tweet.sh recycle --ai gemini --tone humorous
./tweet.sh recycle --dry-run
```

### ユーザー分析・トレンド

```bash
# ユーザーの投稿傾向を分析
./tweet.sh analyze username --ai gemini --max 30

# キーワードのトレンドをAI分析
./tweet.sh trending "AIエージェント" --ai gemini --max 30
```

### 翻訳・クロスポスト

```bash
# 英語に翻訳
./tweet.sh translate "CLIからTwitterを自動化する話" --lang en --ai gemini

# 韓国語に翻訳
./tweet.sh translate "Built a CLI tool for Twitter" --lang ko

# プレビューのみ
./tweet.sh translate "テスト" --lang en --dry-run
```

### 下書き管理

```bash
# 下書きを保存
./tweet.sh draft-save "書きかけのツイート" --tone casual

# 下書き一覧
./tweet.sh draft-list

# 下書きを編集
./tweet.sh draft-edit 1

# 下書きを投稿
./tweet.sh draft-post 1

# 下書きを削除
./tweet.sh draft-delete 1
```

### チェーンワークフロー（生成→改善→投稿）

```bash
# フルワークフロー: 生成、改善、投稿
./tweet.sh chain https://example.com/my-article --ai gemini --tone professional

# スケジュール付きチェーン
./tweet.sh chain --topic "RustとGo比較" --ai gemini --at "2026-04-06T18:00"

# ドライラン
./tweet.sh chain https://example.com/my-article --dry-run
```

### スケジュール投稿

```bash
# ツイートを予約キューに追加
./tweet.sh schedule-add "予約ツイートのテキスト" --at "2026-04-06T18:00"

# 予約キューを一覧表示
./tweet.sh schedule-list

# 予約時刻を過ぎたツイートを投稿
./tweet.sh schedule-run

# プレビューのみ
./tweet.sh schedule-run --dry-run

# 予約キューから削除
./tweet.sh schedule-remove 3
```

cronで自動投稿する場合：

```cron
*/5 * * * * cd ~/twitter-cli-bot && ./tweet.sh schedule-run >> bot.log 2>&1
```

### 読み取り操作

```bash
./tweet.sh feed                            # ホームタイムライン
./tweet.sh feed -t following --max 30      # フォロー中タイムライン
./tweet.sh bookmarks --max 20              # ブックマーク
./tweet.sh search "AIエージェント" -t Latest  # ツイート検索
./tweet.sh tweet 1234567890                # ツイート詳細
./tweet.sh user-posts username --max 20    # ユーザーのツイート一覧
./tweet.sh likes username                  # ユーザーのいいね
./tweet.sh followers username --max 50     # フォロワー一覧
./tweet.sh following username              # フォロー中一覧
./tweet.sh user username                   # ユーザープロフィール
./tweet.sh whoami                          # 認証中のユーザー確認
./tweet.sh status                          # 認証状態確認
```

### 書き込み操作

```bash
./tweet.sh post "投稿テキスト"
./tweet.sh reply 1234567890 "返信テキスト"
./tweet.sh quote 1234567890 "コメント"
./tweet.sh like 1234567890
./tweet.sh retweet 1234567890
./tweet.sh bookmark 1234567890
./tweet.sh follow username
./tweet.sh delete 1234567890
```

### 出力形式

ほとんどの読み取りコマンドで`--yaml`・`--json`・`-c`（コンパクト）・`-o FILE`が使えます：

```bash
./tweet.sh feed --json | jq '.[0].text'
./tweet.sh search "rust" --max 10 -c
./tweet.sh bookmarks --yaml -o bookmarks.yaml
```

---

## 自動化（cron）

1日3回、ランダムな記事から自動投稿する例：

```cron
0 9,12,18 * * * cd ~/twitter-cli-bot && ./tweet.sh generate --auto >> bot.log 2>&1
```

---

## セキュリティについて

- **`config.json`は絶対にコミットしない** — デフォルトでgitignore済みですが、変更しないでください
- **ブラウザCookieを共有しない** — `twitter_auth_token`と`twitter_ct0`はセッション認証情報です
- **自分のアカウントのみで使用する** — 他人のアカウントへの使用は禁止です
- **Twitter/Xの仕様変更に注意** — 非公式のCookieベース認証は予告なく動作しなくなる可能性があります

---

## ファイル構成

```
twitter-cli-bot/
├── tweet.sh            # エントリポイント
├── tweet_gen.py        # サブコマンドのロジック
├── config.json.sample  # 設定テンプレート
├── config.json         # ローカル設定（gitignore済み）
└── history.db          # 投稿履歴（gitignore済み、自動生成）
```

---

## コントリビューション

1. リポジトリをフォーク
2. ブランチを作成：`git checkout -b feature/your-feature`
3. 変更をコミット
4. プルリクエストを作成

バグ報告や機能要望は[Issues](https://github.com/Kensuke-sam/twitter-cli-bot/issues)からどうぞ。

---

## 次のプロジェクト

このCLIラッパーは実行レイヤーの土台です。

この発想を発展させた次世代プロジェクトは次です。
- [twitter-ai-agent](https://github.com/Kensuke-sam/twitter-ai-agent): history・score・autopilotを備えた軽量CLI-first AI投稿エンジン

---

## 関連

- [twitter-cli](https://github.com/jackwener/twitter-cli) — このbotがラップしているTwitter/X CLIツール
