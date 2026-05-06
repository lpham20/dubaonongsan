CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS durian_varieties (
    variety_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    crop_type VARCHAR(30) DEFAULT 'sau_rieng',
    description TEXT
);

CREATE TABLE IF NOT EXISTS production_regions (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    province VARCHAR(100),
    export_code VARCHAR(50),
    risk_level_index NUMERIC(3, 2) DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS daily_market_prices (
    id BIGSERIAL,
    record_timestamp TIMESTAMPTZ NOT NULL,
    variety_id INT REFERENCES durian_varieties(variety_id),
    crop_type VARCHAR(30) DEFAULT 'sau_rieng',
    quality_grade VARCHAR(50),
    region_id INT REFERENCES production_regions(region_id),
    exchange_source VARCHAR(100),
    min_price_vnd NUMERIC(12, 2),
    max_price_vnd NUMERIC(12, 2),
    volume_traded_tons NUMERIC(10, 2)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_market_prices_grain
    ON daily_market_prices (record_timestamp, variety_id, region_id, quality_grade, exchange_source);

SELECT create_hypertable('daily_market_prices', 'record_timestamp', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS weather_environmental_metrics (
    id BIGSERIAL,
    record_timestamp TIMESTAMPTZ NOT NULL,
    region_id INT REFERENCES production_regions(region_id),
    temp_max_celsius NUMERIC(5, 2),
    temp_min_celsius NUMERIC(5, 2),
    humidity_percent NUMERIC(5, 2),
    precipitation_mm NUMERIC(5, 2),
    wind_speed_kmh NUMERIC(5, 2),
    cloud_cover_index NUMERIC(5, 2)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_weather_grain
    ON weather_environmental_metrics (record_timestamp, region_id);

SELECT create_hypertable('weather_environmental_metrics', 'record_timestamp', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS iot_sensor_telemetry (
    id BIGSERIAL,
    record_timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(50),
    region_id INT REFERENCES production_regions(region_id),
    maturity_index NUMERIC(4, 2),
    status VARCHAR(50)
);

SELECT create_hypertable('iot_sensor_telemetry', 'record_timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS ix_daily_market_prices_region_time
    ON daily_market_prices (region_id, record_timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_daily_market_prices_variety_time
    ON daily_market_prices (variety_id, record_timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_weather_region_time
    ON weather_environmental_metrics (region_id, record_timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_iot_region_time
    ON iot_sensor_telemetry (region_id, record_timestamp DESC);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100),
    source_url VARCHAR(500),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    status VARCHAR(30),
    records_found INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_scrape_runs_source_started
    ON scrape_runs (source, started_at DESC);

CREATE TABLE IF NOT EXISTS app_users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    item_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES app_users(user_id),
    crop_type VARCHAR(30),
    region_id INT REFERENCES production_regions(region_id),
    variety_id INT REFERENCES durian_varieties(variety_id),
    label VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ,
    CONSTRAINT uq_watchlist_market UNIQUE (user_id, crop_type, region_id, variety_id)
);

CREATE TABLE IF NOT EXISTS platform_job_runs (
    job_id SERIAL PRIMARY KEY,
    job_name VARCHAR(80),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    status VARCHAR(30),
    summary TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS model_training_runs (
    run_id SERIAL PRIMARY KEY,
    crop_type VARCHAR(30),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    status VARCHAR(30),
    rmse_vnd_per_kg NUMERIC(12, 2),
    mae_vnd_per_kg NUMERIC(12, 2),
    backtest_samples INT DEFAULT 0,
    evaluated_series INT DEFAULT 0,
    note TEXT
);

CREATE TABLE IF NOT EXISTS news_articles (
    article_id SERIAL PRIMARY KEY,
    source_name VARCHAR(120),
    source_url VARCHAR(800) UNIQUE,
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    excerpt TEXT,
    category VARCHAR(80) DEFAULT 'Tin nông nghiệp',
    image_url VARCHAR(800),
    published_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS guide_posts (
    post_id SERIAL PRIMARY KEY,
    slug VARCHAR(180) UNIQUE,
    title VARCHAR(300) NOT NULL,
    crop_type VARCHAR(30),
    category VARCHAR(100),
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(120) DEFAULT 'Nông nghiệp số',
    published_at TIMESTAMPTZ
);
