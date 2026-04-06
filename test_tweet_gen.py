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


if __name__ == "__main__":
    unittest.main()
