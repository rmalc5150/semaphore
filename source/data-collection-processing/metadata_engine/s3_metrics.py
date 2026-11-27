"""Transparent S3 client wrapper used for per-worker request accounting."""

from collections import Counter


class _Paginator:
    def __init__(self, paginator, counts, operation):
        self._paginator, self._counts, self._operation = paginator, counts, operation

    def paginate(self, *args, **kwargs):
        for page in self._paginator.paginate(*args, **kwargs):
            self._counts[self._operation] += 1
            yield page

    def __getattr__(self, name):
        return getattr(self._paginator, name)


class MeteredS3:
    """Count SDK operations without changing their arguments or responses."""

    def __init__(self, client):
        self._client = client
        self._counts = Counter()

    def get_paginator(self, operation_name):
        return _Paginator(self._client.get_paginator(operation_name), self._counts, operation_name)

    def counts(self):
        return dict(sorted(self._counts.items()))

    def __getattr__(self, name):
        value = getattr(self._client, name)
        if not callable(value):
            return value

        def call(*args, **kwargs):
            self._counts[name] += 1
            return value(*args, **kwargs)
        return call
