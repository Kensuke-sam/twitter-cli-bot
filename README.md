# koteihi-twitter-bot 🐦

「固定費ゼロ研究所」の記事から X (Twitter) 投稿を自動生成・投稿する AI 自動運用スクリプトです。
API キーを直接管理せず、ローカルにインストールされた AI CLI (Gemini, Codex, Claude Code) を使用します。

## 🚀 使い方

### 1. 手動モード（ツイートを選んで投稿）
記事の URL またはスラッグを指定して実行します。5つの案が生成されるので、番号で選んで投稿します。

```bash
# Gemini CLI を使用（デフォルト）
./tweet.sh daigakusei-credit-card-3sen

# Codex CLI を使用
./tweet.sh daigakusei-credit-card-3sen --ai codex

# Claude Code CLI を使用
./tweet.sh daigakusei-credit-card-3sen --ai claude
```

### 2. 自動モード（ランダムに1つ選んで投稿）
`--auto` フラグを付けると、生成された案からランダムに1つ選んで即座に投稿します。

```bash
./tweet.sh --auto
```

※ 記事を指定しない場合は、`posts.ts` からランダムに記事が選ばれます。

## 📅 定期実行 (cron) の設定

1日3回（9時, 12時, 18時）、ランダムな記事を自動投稿する設定例です。

```cron
0 9,12,18 * * * cd ~/koteihi-twitter-bot && ./tweet.sh --auto >> tweet.log 2>&1
```

## 🛠 準備・要件

1. **AI CLI のインストール**:
   - `gemini`, `codex`, `claude` いずれかのコマンドがターミナルで叩ける状態であること。
2. **Twitter CLI のセットアップ**:
   - `twitter-cli` がインストールされており、ブラウザ等で `x.com` にログイン済みであること。
3. **uv のインストール**:
   - Python 依存関係の解決に `uv` を使用します。

## 📂 ディレクトリ構造
- `tweet_gen.py`: ツイート生成・投稿のメインロジック。
- `tweet.sh`: 実行用ラッパースクリプト。
- `../koteihi-zero/src/lib/posts.ts`: 記事データの参照先。
