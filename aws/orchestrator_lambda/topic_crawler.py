
import feedparser

from aws.shared.exceptions import TopicCrawlError


class TopicCrawler:
    def crawl(self, feed_urls: list[str], max_items: int = 5) -> list[str]:
        topics: list[str] = []
        for url in feed_urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_items]:
                    title = entry.get("title", "").strip()
                    if title:
                        topics.append(title)
            except Exception as exc:
                raise TopicCrawlError(f"Failed to crawl {url}: {exc}") from exc
        return topics
