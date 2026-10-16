"""Publisher bodies for RSS source material; feed descriptions remain metadata."""
from finlight_content import Capture as BaseCapture, apply

VERSION = 'people-rss-fulltext-1.0'

class Capture(BaseCapture):
    source = 'people_rss'
    version = VERSION

    def get(self, row, historical=True, force=False):
        return super().get({'link':row['url'], 'title':row.get('title'),
            'summary':row.get('text')}, historical=historical, force=force)
