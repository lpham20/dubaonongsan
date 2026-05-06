ALTER TABLE app_users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_app_users_is_admin
    ON app_users (is_admin)
    WHERE is_admin = TRUE;

CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_region
    ON daily_market_prices (crop_type, region_id);

CREATE INDEX IF NOT EXISTS ix_daily_market_prices_grade_a_recent
    ON daily_market_prices (crop_type, variety_id, region_id, record_timestamp DESC)
    WHERE quality_grade = 'Loại A';

CREATE INDEX IF NOT EXISTS ix_news_articles_scraped
    ON news_articles (scraped_at DESC);

CREATE INDEX IF NOT EXISTS ix_watchlist_user_created
    ON watchlist_items (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_subscribers_source
    ON subscribers (source, created_at DESC);

-- Optional TimescaleDB compression. Run only after daily_market_prices has been
-- converted to a hypertable in production.
-- ALTER TABLE daily_market_prices SET (
--     timescaledb.compress,
--     timescaledb.compress_segmentby = 'variety_id, region_id, crop_type'
-- );
-- SELECT add_compression_policy('daily_market_prices', INTERVAL '90 days', if_not_exists => TRUE);
