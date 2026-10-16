"""Marketaux discovery links enriched with original publisher article text."""
from finlight_content import Capture as BaseCapture, apply

VERSION = 'marketaux-fulltext-1.0'

class Capture(BaseCapture):
    source = 'marketaux'
    version = VERSION

    def get(self, row, historical=True, force=False):
        # Marketaux descriptions/snippets are never full bodies. Keep the
        # original provider row intact, including UUID and Chinese text.
        article = {'link': row['url'], 'title': row.get('title'),
                   'summary': row.get('description') or row.get('snippet')}
        return super().get(article, historical=historical, force=force)
