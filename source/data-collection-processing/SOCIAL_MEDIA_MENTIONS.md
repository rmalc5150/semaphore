# Social media company mention monitor

This collector searches company names, identifies the publisher, scores the
message, and records comments, shares/reposts, and reactions. It supports:

- Reddit via OAuth (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`)
- Bluesky via the public AppView API (no credentials)
- YouTube via `YOUTUBE_API_KEY`
- WeChat or licensed vendor exports via normalized JSONL

WeChat does not provide a general API for searching every public post. Export
data you are authorized to access as one JSON object per line. Accepted fields
are `company`, `platform`, `post_id`/`id`, `author`, `text`/`content`, `url`,
`published_at`, `comments`, `shares`, and `reactions`/`likes`. If `company` is
omitted, the importer matches a supplied company name in the content.

```bash
cd /home/ec2-user/data-collection-processing

# Public, credential-free example
python social_media_mentions.py "Pfizer" "BeiGene" --platforms bluesky

# All live connectors
export REDDIT_CLIENT_ID='...'
export REDDIT_CLIENT_SECRET='...'
export YOUTUBE_API_KEY='...'
python social_media_mentions.py "Pfizer" "BeiGene" \
  --platforms reddit,bluesky,youtube --output results.json

# Add an authorized WeChat export
python social_media_mentions.py "Pfizer" --platforms bluesky \
  --import-jsonl wechat-export.jsonl
```

The output includes raw normalized mentions plus company-level totals and an
engagement-weighted sentiment score. Engagement is
`ln(1 + 2*comments + 3*shares + reactions)`, deliberately weighting active
discussion and redistribution more than likes. The built-in sentiment model is
a lightweight, explainable English/Chinese baseline; use a reviewed domain
model before making investment, compliance, or reputation decisions.

Run tests with:

```bash
python -m unittest test_social_media_mentions.py
```
