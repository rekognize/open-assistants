import requests
from time import sleep
from googlesearch import search
from bs4 import BeautifulSoup
import feedparser
from .base import AssistantTool


class FeedParser(AssistantTool):
    """
    Parses the RSS feed at the given URL.
    """

    def __init__(self, feed_url):
        """
        :param feed_url: The URL of the RSS feed
        """
        self.feed_url = feed_url

    def main(self):
        feed = feedparser.parse(self.feed_url)

        if not feed.entries:
            return

        feed_md = 'Below are the RSS entries. Fetch the contents you find relevant. \n\n'
        for entry in feed.entries:
            print(entry)
            feed_md += (
                f"# {entry.title}\n"
                f"{entry.published}\n"
                f"{entry.summary}\n"
                f"Tags: {', '.join([tag.term for tag in entry.tags])}\n"
                f"URL: {entry.link}\n"
            )

        return feed_md


class WebPageReader(AssistantTool):
    """
    Gets the contents of a web page.
    """
    headers = {
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    }

    def __init__(self, url):
        """
        :param url: The URL of the web page to fetch
        """
        self.url = url

    def main(self):
        response = requests.get(self.url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove non-content elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()

            def preserve_links(tag):
                """Convert a tag's contents to string, preserving <a> links."""
                if tag.name == 'a':
                    return f"[{tag.get_text()}]({tag.get('href')})"
                return tag.get_text()

            # Collect all text, with links formatted
            content = []
            for element in soup.find_all(['p', 'li', 'div', 'span']):
                content.append(preserve_links(element))

            if content:
                text = '\n'.join(content)
                return (
                    f"Below are the contents of the URL: {self.url}. "
                    f"If you think it is required to extend your research, "
                    f"you can request the contents of the relevant URLs mentioned in this page "
                    f"by calling the WebPageReader again.\n\n"
                    f"PAGE CONTENTS:\n\n{text}"
                )


class WebSearch(AssistantTool):
    """
    Get Google search results for a query.
    """
    max_retries = 5

    def __init__(self, query):
        """
        :param query: The search query string.
        """
        self.query = query

    def main(self):
        try:
            results = list(search(self.query, num_results=100, advanced=True))  # Convert generator to list
        except (requests.HTTPError, requests.ReadTimeout):
            return "[Error: Too Many Requests]"
        retry = 1
        while not results and retry < self.max_retries:
            # May be rate limited; retry
            sleep(.5 * retry)
            results = list(search(self.query, num_results=100, advanced=True))
            retry += 1
        if results:
            results_markdown = (
                f'Below are the list of items returned for your query: "{self.query}".\n'
                f'For the items you find to be relevant to your quest, '
                f'you can call the "fetch_content" function to retrieve the full content.\n\n'
            )
            for item in results:
                results_markdown += f"### [{item.title}]({item.url})\n{item.description}\n\n"
            return results_markdown

