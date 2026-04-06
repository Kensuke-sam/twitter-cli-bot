"""tweet_gen.py のユニットテスト"""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# テスト対象のモジュールをインポート
import tweet_gen


class TestParseAiTweets(unittest.TestCase):
    """parse_ai_tweets のテスト"""

    def test_simple_numbered_list(self):
        content = "1. First tweet here\n2. Second tweet here\n3. Third tweet here"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "First tweet here")

    def test_japanese_numbered_list(self):
        content = "1、最初のツイートです。これは十分な長さのテスト\n2、次のツイートです。これも十分な長さのテスト\n3、最後のツイートです。これも十分な長さのテスト"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "最初のツイートです。これは十分な長さのテスト")

    def test_circled_numbers(self):
        content = "① これは最初のツイートです十分な長さ\n② これは二番目のツイートです十分な長さ"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "これは最初のツイートです十分な長さ")

    def test_markdown_headers_filtered(self):
        content = "# Header\n---\nActual tweet content here\n```code```"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "Actual tweet content here")

    def test_bold_markdown_stripped(self):
        content = "1. **This is bold** tweet content"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(result[0], "This is bold tweet content")

    def test_short_lines_filtered(self):
        content = "OK\nShort\nThis is a real tweet with enough content"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "This is a real tweet with enough content")

    def test_max_count_respected(self):
        content = "\n".join([f"Tweet number {i} with enough chars" for i in range(10)])
        result = tweet_gen.parse_ai_tweets(content, max_count=3)
        self.assertEqual(len(result), 3)

    def test_empty_lines_skipped(self):
        content = "\n\nFirst real tweet here\n\n\nSecond real tweet here\n\n"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(len(result), 2)

    def test_bracket_numbered(self):
        content = "1) First tweet bracket\n2] Second tweet bracket"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(result[0], "First tweet bracket")
        self.assertEqual(result[1], "Second tweet bracket")

    def test_quotes_stripped(self):
        content = "「日本語のツイートです」"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(result[0], "日本語のツイートです")

    def test_curly_quotes_stripped(self):
        content = "\u201cThis is a curly quoted tweet\u201d"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(result[0], "This is a curly quoted tweet")

    def test_double_corner_quotes_stripped(self):
        content = "『二重鉤括弧で囲まれたツイート』"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(result[0], "二重鉤括弧で囲まれたツイート")

    def test_closing_quote_at_start_not_stripped(self):
        """行頭の閉じ括弧は除去しない"""
        content = "」で始まるツイートは珍しいが残すべき"
        result = tweet_gen.parse_ai_tweets(content, max_count=5)
        self.assertEqual(result[0], "」で始まるツイートは珍しいが残すべき")


class TestExtractTweetId(unittest.TestCase):
    """extract_tweet_id のテスト"""

    def test_status_url(self):
        output = "Posted: https://twitter.com/user/status/1234567890123456789"
        self.assertEqual(tweet_gen.extract_tweet_id(output), "1234567890123456789")

    def test_bare_id(self):
        output = "Tweet ID: 1234567890123456789"
        self.assertEqual(tweet_gen.extract_tweet_id(output), "1234567890123456789")

    def test_no_id(self):
        output = "Success!"
        self.assertIsNone(tweet_gen.extract_tweet_id(output))

    def test_empty_output(self):
        self.assertIsNone(tweet_gen.extract_tweet_id(""))


class TestFormatTweetDisplay(unittest.TestCase):
    """format_tweet_display のテスト"""

    def test_basic_display(self):
        result = tweet_gen.format_tweet_display("Short tweet", 1)
        self.assertIn("[1]", result)
        self.assertIn("11文字", result)
        self.assertNotIn("!280文字超", result)

    def test_over_limit_warning(self):
        long_tweet = "x" * 281
        result = tweet_gen.format_tweet_display(long_tweet, 1)
        self.assertIn("!280文字超", result)

    def test_with_total(self):
        result = tweet_gen.format_tweet_display("Thread tweet", 2, total=5)
        self.assertIn("[2/5]", result)


class TestValidateConfig(unittest.TestCase):
    """validate_config のテスト"""

    def test_history_commands_skip_validation(self):
        # history 系コマンドはバリデーションをスキップする
        for cmd in ("history", "history-clear", "stats"):
            tweet_gen.validate_config({}, cmd)  # エラーなく通る

    def test_missing_twitter_cli_path(self):
        with self.assertRaises(SystemExit):
            tweet_gen.validate_config({}, "feed")

    def test_empty_twitter_cli_path(self):
        with self.assertRaises(SystemExit):
            tweet_gen.validate_config({"twitter_cli_path": "  "}, "feed")

    def test_nonexistent_twitter_cli_path(self):
        with self.assertRaises(SystemExit):
            tweet_gen.validate_config(
                {"twitter_cli_path": "/nonexistent/path"}, "feed"
            )


class TestDatabase(unittest.TestCase):
    """SQLite 履歴機能のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.tmp)

    def test_save_and_find_duplicate(self):
        tweet_gen.save_post("test tweet", article_url="https://example.com/post1")
        dup = tweet_gen.find_duplicate("https://example.com/post1")
        self.assertIsNotNone(dup)
        self.assertEqual(dup[1], "test tweet")

    def test_no_duplicate_for_different_url(self):
        tweet_gen.save_post("test tweet", article_url="https://example.com/post1")
        dup = tweet_gen.find_duplicate("https://example.com/post2")
        self.assertIsNone(dup)

    def test_find_duplicate_none_url(self):
        self.assertIsNone(tweet_gen.find_duplicate(None))

    def test_find_duplicate_empty_url(self):
        self.assertIsNone(tweet_gen.find_duplicate(""))

    def test_get_posted_urls(self):
        tweet_gen.save_post("tweet1", article_url="https://example.com/a")
        tweet_gen.save_post("tweet2", article_url="https://example.com/b")
        tweet_gen.save_post("tweet3", article_url=None)
        urls = tweet_gen.get_posted_urls()
        self.assertEqual(urls, {"https://example.com/a", "https://example.com/b"})

    def test_save_post_with_tone_and_thread(self):
        tweet_gen.save_post("thread tweet", tone="casual", is_thread=True)
        db = tweet_gen.init_db()
        row = db.execute("SELECT tone, is_thread FROM posts").fetchone()
        db.close()
        self.assertEqual(row[0], "casual")
        self.assertEqual(row[1], 1)


class TestTonePresets(unittest.TestCase):
    """トーンプリセットのテスト"""

    def test_all_tones_defined(self):
        expected = {"professional", "casual", "provocative", "technical", "humorous"}
        self.assertEqual(set(tweet_gen.TONE_PRESETS.keys()), expected)

    def test_tones_are_nonempty_strings(self):
        for name, desc in tweet_gen.TONE_PRESETS.items():
            self.assertIsInstance(desc, str, f"Tone '{name}' is not a string")
            self.assertTrue(len(desc) > 0, f"Tone '{name}' is empty")


class TestResolvePostData(unittest.TestCase):
    """resolve_post_data のテスト"""

    def test_url_input(self):
        args = MagicMock(input="https://example.com/article", topic=None, auto=False, force=False)
        result = tweet_gen.resolve_post_data(args, {})
        self.assertEqual(result["url"], "https://example.com/article")

    def test_topic_flag(self):
        args = MagicMock(input=None, topic="AI and ML", auto=False, force=False)
        result = tweet_gen.resolve_post_data(args, {})
        self.assertEqual(result["topic"], "AI and ML")

    def test_freeform_text_without_posts_file(self):
        args = MagicMock(input="some random topic", topic=None, auto=False, force=False)
        result = tweet_gen.resolve_post_data(args, {})
        self.assertEqual(result["topic"], "some random topic")


class TestCopyToClipboard(unittest.TestCase):
    """copy_to_clipboard のテスト"""

    @patch('tweet_gen.platform')
    @patch('tweet_gen.subprocess')
    def test_macos_pbcopy(self, mock_subprocess, mock_platform):
        mock_platform.system.return_value = "Darwin"
        result = tweet_gen.copy_to_clipboard("test text")
        self.assertTrue(result)
        mock_subprocess.run.assert_called_once()
        call_args = mock_subprocess.run.call_args
        self.assertEqual(call_args[0][0], ["pbcopy"])

    @patch('tweet_gen.platform')
    @patch('tweet_gen.subprocess')
    def test_linux_xclip(self, mock_subprocess, mock_platform):
        mock_platform.system.return_value = "Linux"
        result = tweet_gen.copy_to_clipboard("test text")
        self.assertTrue(result)

    @patch('tweet_gen.platform')
    def test_unsupported_os(self, mock_platform):
        mock_platform.system.return_value = "Windows"
        result = tweet_gen.copy_to_clipboard("test text")
        self.assertFalse(result)


class TestScheduleQueue(unittest.TestCase):
    """スケジュールキュー機能のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.tmp)

    def test_init_queue_db_creates_table(self):
        db = tweet_gen.init_queue_db()
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (tweet_gen.QUEUE_TABLE,)
        ).fetchone()
        db.close()
        self.assertIsNotNone(tables)

    def test_schedule_add_and_list(self):
        args = MagicMock(text="Test scheduled tweet", at="2026-04-06T18:00")
        tweet_gen.cmd_schedule_add(args, {})

        db = tweet_gen.init_queue_db()
        rows = db.execute(f"SELECT tweet_text, status FROM {tweet_gen.QUEUE_TABLE}").fetchall()
        db.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Test scheduled tweet")
        self.assertEqual(rows[0][1], "pending")

    def test_schedule_add_invalid_datetime(self):
        args = MagicMock(text="Test", at="not-a-date")
        with self.assertRaises(SystemExit):
            tweet_gen.cmd_schedule_add(args, {})

    def test_schedule_remove(self):
        args_add = MagicMock(text="To be removed", at="2026-04-06T18:00")
        tweet_gen.cmd_schedule_add(args_add, {})

        db = tweet_gen.init_queue_db()
        row = db.execute(f"SELECT id FROM {tweet_gen.QUEUE_TABLE}").fetchone()
        db.close()

        args_remove = MagicMock(id=row[0])
        tweet_gen.cmd_schedule_remove(args_remove, {})

        db = tweet_gen.init_queue_db()
        remaining = db.execute(f"SELECT id FROM {tweet_gen.QUEUE_TABLE}").fetchall()
        db.close()
        self.assertEqual(len(remaining), 0)


class TestValidateConfigNewCommands(unittest.TestCase):
    """新コマンドの validate_config テスト"""

    def test_schedule_commands_skip_validation(self):
        for cmd in ("schedule-add", "schedule-list", "schedule-remove"):
            tweet_gen.validate_config({}, cmd)  # エラーなく通る

    def test_draft_commands_skip_validation(self):
        for cmd in ("draft-save", "draft-list", "draft-edit", "draft-delete"):
            tweet_gen.validate_config({}, cmd)  # エラーなく通る


class TestDrafts(unittest.TestCase):
    """下書き機能のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.tmp)

    def test_init_drafts_db_creates_table(self):
        db = tweet_gen.init_drafts_db()
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (tweet_gen.DRAFTS_TABLE,)
        ).fetchone()
        db.close()
        self.assertIsNotNone(tables)

    def test_draft_save_and_list(self):
        args = MagicMock(text="My draft tweet", tone="casual")
        tweet_gen.cmd_draft_save(args, {})

        db = tweet_gen.init_drafts_db()
        rows = db.execute(f"SELECT text, tone FROM {tweet_gen.DRAFTS_TABLE}").fetchall()
        db.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "My draft tweet")
        self.assertEqual(rows[0][1], "casual")

    def test_draft_delete(self):
        args_save = MagicMock(text="To be deleted", tone=None)
        tweet_gen.cmd_draft_save(args_save, {})

        db = tweet_gen.init_drafts_db()
        row = db.execute(f"SELECT id FROM {tweet_gen.DRAFTS_TABLE}").fetchone()
        db.close()

        args_del = MagicMock(id=row[0])
        tweet_gen.cmd_draft_delete(args_del, {})

        db = tweet_gen.init_drafts_db()
        remaining = db.execute(f"SELECT id FROM {tweet_gen.DRAFTS_TABLE}").fetchall()
        db.close()
        self.assertEqual(len(remaining), 0)


class TestBuildTwitterArgs(unittest.TestCase):
    """_build_twitter_args ヘルパーのテスト"""

    def test_basic_command(self):
        args = MagicMock(compact=False, type=None, max=None, filter=False,
                         yaml=False, json=False, output=None)
        result = tweet_gen._build_twitter_args(args, "feed")
        self.assertEqual(result, ["feed"])

    def test_with_all_flags(self):
        args = MagicMock(compact=True, type="following", max=30, filter=True,
                         yaml=False, json=True, output="out.json")
        result = tweet_gen._build_twitter_args(args, "feed")
        self.assertIn("-c", result)
        self.assertIn("--json", result)
        self.assertIn("--max", result)
        self.assertIn("-o", result)

    def test_with_positional(self):
        args = MagicMock(compact=False, type=None, max=None, filter=False,
                         yaml=False, json=False, output=None)
        result = tweet_gen._build_twitter_args(args, "search", ["rust"])
        self.assertEqual(result, ["search", "rust"])


class TestScheduleRun(unittest.TestCase):
    """cmd_schedule_run のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.tmp)

    def test_run_posts_due_tweets(self):
        """予約時刻を過ぎたツイートが投稿される"""
        # 過去の日時で予約を追加
        args_add = MagicMock(text="Past tweet", at="2020-01-01T00:00")
        tweet_gen.cmd_schedule_add(args_add, {})

        with patch.object(tweet_gen, 'run_twitter') as mock_run:
            args_run = MagicMock(dry_run=False)
            tweet_gen.cmd_schedule_run(args_run, {"twitter_cli_path": "/tmp"})
            mock_run.assert_called_once()

        # ステータスが posted に更新されたことを確認
        db = tweet_gen.init_queue_db()
        row = db.execute(
            f"SELECT status FROM {tweet_gen.QUEUE_TABLE}"
        ).fetchone()
        db.close()
        self.assertEqual(row[0], "posted")

    def test_run_dry_run_does_not_post(self):
        """dry-run では投稿されない"""
        args_add = MagicMock(text="Dry run tweet", at="2020-01-01T00:00")
        tweet_gen.cmd_schedule_add(args_add, {})

        with patch.object(tweet_gen, 'run_twitter') as mock_run:
            args_run = MagicMock(dry_run=True)
            tweet_gen.cmd_schedule_run(args_run, {"twitter_cli_path": "/tmp"})
            mock_run.assert_not_called()

        # ステータスが pending のまま
        db = tweet_gen.init_queue_db()
        row = db.execute(
            f"SELECT status FROM {tweet_gen.QUEUE_TABLE}"
        ).fetchone()
        db.close()
        self.assertEqual(row[0], "pending")

    def test_run_skips_future_tweets(self):
        """未来の予約はスキップされる"""
        args_add = MagicMock(text="Future tweet", at="2099-12-31T23:59")
        tweet_gen.cmd_schedule_add(args_add, {})

        with patch.object(tweet_gen, 'run_twitter') as mock_run:
            args_run = MagicMock(dry_run=False)
            tweet_gen.cmd_schedule_run(args_run, {"twitter_cli_path": "/tmp"})
            mock_run.assert_not_called()

    def test_run_empty_queue(self):
        """キューが空の場合でもエラーにならない"""
        args_run = MagicMock(dry_run=False)
        tweet_gen.cmd_schedule_run(args_run, {})  # エラーなく通る


class TestDraftEditAndPost(unittest.TestCase):
    """cmd_draft_edit / cmd_draft_post のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.tmp)

    def test_draft_edit_updates_text(self):
        """下書き編集でテキストが更新される"""
        args_save = MagicMock(text="Original draft", tone=None)
        tweet_gen.cmd_draft_save(args_save, {})

        db = tweet_gen.init_drafts_db()
        row = db.execute(f"SELECT id FROM {tweet_gen.DRAFTS_TABLE}").fetchone()
        db.close()

        with patch.object(tweet_gen, 'edit_tweet', return_value="Edited draft"):
            args_edit = MagicMock(id=row[0])
            tweet_gen.cmd_draft_edit(args_edit, {})

        db = tweet_gen.init_drafts_db()
        updated = db.execute(f"SELECT text FROM {tweet_gen.DRAFTS_TABLE} WHERE id = ?", (row[0],)).fetchone()
        db.close()
        self.assertEqual(updated[0], "Edited draft")

    def test_draft_edit_nonexistent_id(self):
        """存在しない ID を指定してもエラーにならない"""
        args_edit = MagicMock(id=9999)
        tweet_gen.cmd_draft_edit(args_edit, {})  # エラーなく通る

    def test_draft_post_removes_draft(self):
        """投稿後に下書きが削除される"""
        args_save = MagicMock(text="Post me", tone=None)
        tweet_gen.cmd_draft_save(args_save, {})

        db = tweet_gen.init_drafts_db()
        row = db.execute(f"SELECT id FROM {tweet_gen.DRAFTS_TABLE}").fetchone()
        db.close()

        with patch.object(tweet_gen, 'run_twitter'), \
             patch('builtins.input', return_value='y'):
            args_post = MagicMock(id=row[0], dry_run=False)
            tweet_gen.cmd_draft_post(args_post, {"twitter_cli_path": "/tmp"})

        db = tweet_gen.init_drafts_db()
        remaining = db.execute(f"SELECT id FROM {tweet_gen.DRAFTS_TABLE}").fetchall()
        db.close()
        self.assertEqual(len(remaining), 0)

    def test_draft_post_dry_run_keeps_draft(self):
        """dry-run では下書きが残る"""
        args_save = MagicMock(text="Keep me", tone=None)
        tweet_gen.cmd_draft_save(args_save, {})

        db = tweet_gen.init_drafts_db()
        row = db.execute(f"SELECT id FROM {tweet_gen.DRAFTS_TABLE}").fetchone()
        db.close()

        args_post = MagicMock(id=row[0], dry_run=True)
        tweet_gen.cmd_draft_post(args_post, {})

        db = tweet_gen.init_drafts_db()
        remaining = db.execute(f"SELECT id FROM {tweet_gen.DRAFTS_TABLE}").fetchall()
        db.close()
        self.assertEqual(len(remaining), 1)


class TestEditTweet(unittest.TestCase):
    """edit_tweet のテスト"""

    @patch.dict(os.environ, {"EDITOR": "", "VISUAL": ""}, clear=False)
    def test_fallback_empty_input_keeps_original(self):
        """EDITOR 未設定 + 空入力で元のテキストが返る"""
        with patch('builtins.input', return_value=''):
            result = tweet_gen.edit_tweet("original text")
        self.assertEqual(result, "original text")

    @patch.dict(os.environ, {"EDITOR": "", "VISUAL": ""}, clear=False)
    def test_fallback_new_input_replaces(self):
        """EDITOR 未設定 + 入力ありで新しいテキストが返る"""
        with patch('builtins.input', return_value='new text'):
            result = tweet_gen.edit_tweet("original text")
        self.assertEqual(result, "new text")


class TestCmdHistory(unittest.TestCase):
    """cmd_history のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        # JSON エクスポートテストで export.json が生成されるため、
        # db ファイルだけでなく tmp 内の全ファイルを削除する
        for f in Path(self.tmp).iterdir():
            f.unlink()
        os.rmdir(self.tmp)

    def test_history_empty(self):
        """履歴なしの場合"""
        args = MagicMock(max=20, json=False, output=None)
        tweet_gen.cmd_history(args, {})  # エラーなく通る

    def test_history_json_export(self):
        """JSON エクスポートが正しく動作する"""
        tweet_gen.save_post("test tweet 1", article_url="https://example.com/a")
        tweet_gen.save_post("test tweet 2", tone="casual")

        out_file = Path(self.tmp) / "export.json"
        args = MagicMock(max=20, json=True, output=str(out_file))
        tweet_gen.cmd_history(args, {})

        self.assertTrue(out_file.exists())
        data = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 2)
        # 最新が先頭（DESC）
        self.assertEqual(data[0]["text"], "test tweet 2")
        self.assertEqual(data[0]["tone"], "casual")

    def test_history_respects_max(self):
        """--max が反映される"""
        for i in range(5):
            tweet_gen.save_post(f"tweet {i}")

        out_file = Path(self.tmp) / "export.json"
        args = MagicMock(max=2, json=True, output=str(out_file))
        tweet_gen.cmd_history(args, {})

        data = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 2)


class TestCmdStats(unittest.TestCase):
    """cmd_stats のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.tmp)

    def test_stats_empty(self):
        """履歴なしの場合"""
        args = MagicMock()
        tweet_gen.cmd_stats(args, {})  # エラーなく通る

    def test_stats_with_data(self):
        """データがある場合の統計表示"""
        tweet_gen.save_post("single tweet", article_url="https://example.com/a", tone="casual")
        tweet_gen.save_post("thread tweet", tone="professional", is_thread=True)
        tweet_gen.save_post("free tweet")

        args = MagicMock()
        # 例外が出ずに完了することを検証
        tweet_gen.cmd_stats(args, {})


class TestCmdHistoryClear(unittest.TestCase):
    """cmd_history_clear のテスト"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_history.db"
        self.patcher = patch.object(tweet_gen, 'get_db_path', return_value=self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.tmp)

    def test_clear_empty_history(self):
        """履歴なしで clear してもエラーにならない"""
        args = MagicMock()
        tweet_gen.cmd_history_clear(args, {})

    def test_clear_with_confirmation(self):
        """確認 'y' で履歴が削除される"""
        tweet_gen.save_post("to be deleted")
        tweet_gen.save_post("also deleted")

        with patch('builtins.input', return_value='y'):
            args = MagicMock()
            tweet_gen.cmd_history_clear(args, {})

        db = tweet_gen.init_db()
        count = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        db.close()
        self.assertEqual(count, 0)

    def test_clear_cancelled(self):
        """確認 'n' で履歴が残る"""
        tweet_gen.save_post("should remain")

        with patch('builtins.input', return_value='n'):
            args = MagicMock()
            tweet_gen.cmd_history_clear(args, {})

        db = tweet_gen.init_db()
        count = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        db.close()
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
