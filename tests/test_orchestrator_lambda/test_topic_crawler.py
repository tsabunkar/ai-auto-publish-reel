from unittest.mock import MagicMock, patch

import pytest

from aws.orchestrator_lambda.topic_crawler import TopicCrawler
from aws.shared.exceptions import TopicCrawlError


class TestTopicCrawler:
    def test_crawl_returns_titles(self):
        crawler = TopicCrawler()
        with patch("feedparser.parse") as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(title="First Topic"),
                MagicMock(title="Second Topic"),
                MagicMock(title=""),
            ]
            mock_parse.return_value = mock_feed
            topics = crawler.crawl(["https://example.com/feed"], max_items=5)
        assert topics == ["First Topic", "Second Topic"]

    def test_crawl_strips_whitespace(self):
        crawler = TopicCrawler()
        with patch("feedparser.parse") as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(title="  Spaced Title  "),
            ]
            mock_parse.return_value = mock_feed
            topics = crawler.crawl(["https://example.com/feed"], max_items=5)
        assert topics == ["Spaced Title"]

    def test_crawl_handles_empty_feed(self):
        crawler = TopicCrawler()
        with patch("feedparser.parse") as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed
            topics = crawler.crawl(["https://example.com/feed"], max_items=5)
        assert topics == []

    def test_crawl_raises_on_failure(self):
        crawler = TopicCrawler()
        with patch("feedparser.parse", side_effect=Exception("Network error")), pytest.raises(TopicCrawlError, match="Network error"):
                crawler.crawl(["https://example.com/feed"], max_items=5)

    def test_crawl_limits_items(self):
        crawler = TopicCrawler()
        with patch("feedparser.parse") as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(title=f"Topic {i}") for i in range(10)
            ]
            mock_parse.return_value = mock_feed
            topics = crawler.crawl(["https://example.com/feed"], max_items=3)
        assert len(topics) == 3

    def test_crawl_multiple_feeds(self):
        crawler = TopicCrawler()
        with patch("feedparser.parse") as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = [MagicMock(title="Topic")]
            mock_parse.return_value = mock_feed
            topics = crawler.crawl(
                ["https://feed1.com", "https://feed2.com"], max_items=5
            )
        assert len(topics) == 2
