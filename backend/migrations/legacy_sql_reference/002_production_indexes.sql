CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_region_variety_time
    ON daily_market_prices (crop_type, region_id, variety_id, record_timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_time
    ON daily_market_prices (crop_type, record_timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_source
    ON daily_market_prices (crop_type, exchange_source);

CREATE INDEX IF NOT EXISTS ix_weather_region_time_desc
    ON weather_environmental_metrics (region_id, record_timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_iot_region_time_desc
    ON iot_sensor_telemetry (region_id, record_timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_news_articles_category_published
    ON news_articles (category, published_at DESC, scraped_at DESC);

CREATE INDEX IF NOT EXISTS ix_news_articles_published
    ON news_articles (published_at DESC, scraped_at DESC);

CREATE INDEX IF NOT EXISTS ix_guide_posts_crop_category_published
    ON guide_posts (crop_type, category, published_at DESC);

CREATE INDEX IF NOT EXISTS ix_platform_job_runs_name_started
    ON platform_job_runs (job_name, started_at DESC);

CREATE INDEX IF NOT EXISTS ix_model_training_runs_crop_started
    ON model_training_runs (crop_type, started_at DESC);
