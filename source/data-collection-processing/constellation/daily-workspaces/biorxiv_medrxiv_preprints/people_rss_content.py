"""Full RSS articles: explicit feed body, publisher retrieval, then bounded Decodo."""
from finlight_content import Capture as BaseCapture, apply, public_url, extract_html
from collection_operations import load_stored
from collection_storage import now, write_json
from regulatory_collection import SourceIssue

VERSION = 'people-rss-fulltext-2.0'

def feed_text(fragment):
    return extract_html(('<html><body><article>'+fragment+'</article></body></html>').encode(), 'https://publisher.invalid/article', '')

class Capture(BaseCapture):
    source = 'people_rss'
    version = VERSION

    def publisher(self, url, summary):
        if getattr(self, '_inline_feed', None):
            fragment, refs = self._inline_feed
            try:
                text = feed_text(fragment)
                self.evidence.evidence.extend(refs)
                return text, 'rss_full_content'
            except SourceIssue:
                pass
        try:
            return super().publisher(url, summary)
        except SourceIssue as error:
            if error.partial or error.code == 'article_access_restricted':
                raise
            direct_error = error.code
        public_url(url)
        if self.remaining <= 0:
            raise SourceIssue('fulltext_run_budget_reached', True)
        key = 'operations/news/fulltext/people_rss/decodo-budgets/' + now()[:10] + '.json'
        state, token = load_stored(self.store, key)
        count = (state or {}).get('requests', 0)
        if count >= 40:
            raise SourceIssue('rss_decodo_daily_budget_reached', True)
        write_json(self.store, key, {'requests':count+1,'updated_at':now()}, token)
        self.remaining -= 1
        from decodo_scraping_api import scrape_url, ScrapeError
        try:
            html = scrape_url(url, headless='html')
        except ScrapeError as error:
            raise SourceIssue(str(error), error.retryable) from None
        raw = html.encode('utf-8')
        if len(raw) > 8*1024*1024:
            raise SourceIssue('rss_rendered_article_too_large')
        self.evidence.save(raw, url, 'text/html')
        self.evidence.evidence[-1]['retrieval_method'] = 'decodo_rendered_html'
        self.evidence.evidence[-1]['direct_attempt_reason'] = direct_error
        return extract_html(raw, url, summary), 'decodo_rendered_html'

    def get(self, row, historical=True, force=False):
        self._inline_feed = (row['feed_content'],row['_feed_evidence']) if row.get('feed_content') and row.get('_feed_evidence') else None
        # Old unavailable receipts must be retried once with the new fallback.
        from research_contract import digest
        key = 'operations/news/fulltext/people_rss/content/' + digest(row['url']) + '.json'
        old, _ = load_stored(self.store, key)
        if old and old.get('version') != VERSION and old.get('status') != 'captured':
            force = True
        return super().get({'link':row['url'],'title':row.get('title'),
            'summary':row.get('text')}, historical=historical, force=force)
