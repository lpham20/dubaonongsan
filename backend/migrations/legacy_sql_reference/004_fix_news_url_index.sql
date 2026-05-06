DROP INDEX IF EXISTS news_articles_source_url_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_news_url_hash ON news_articles (md5(source_url));
