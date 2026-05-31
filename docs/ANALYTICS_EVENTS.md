# GA4 analytics events

## Runtime rules

- GA4 is configured with `VITE_GA_MEASUREMENT_ID`; the real `G-...` ID is never committed.
- Analytics storage and all ad-related storage default to `denied`.
- The Google Analytics script is not requested until the visitor accepts analytics cookies.
- Consent is stored in local storage under `marketai.consent.v1`.
- Event delivery is best-effort only. Analytics failures must not interrupt application workflows.
- Event parameter names that resemble PII or secrets are removed. Do not send email, phone, name, IP address, tokens, passwords, authorization headers, or free-form search text.

## Events

| Event | Trigger | Parameters |
|---|---|---|
| `signup_completed` | Successful account registration | `method` |
| `login_completed` | Successful account login | `method` |
| `logout` | Account logout | none |
| `fertilizer_recommend_requested` | Fertilizer recommendation request starts | `crop`, `province` |
| `fertilizer_recommend_received` | Fertilizer recommendation response received | `crop`, `confidence_tier` |
| `roi_calculate_submitted` | Profit calculation request starts | `crop`, `area_ha` |
| `roi_calculate_received` | Profit calculation response received | `crop`, rounded `roi_pct` |
| `watchlist_item_added` | A market is pinned | `crop_type` |
| `watchlist_item_removed` | A pinned market is removed | `crop_type` |
| `news_article_viewed` | News detail loads | `article_id`, `category` |
| `guide_post_viewed` | Guide detail loads | `post_id`, `category` |
| `forecast_chart_viewed` | Crop forecast chart loads for a selected market | `crop`, `region_id` |
| `world_fertilizer_viewed` | World fertilizer commodity view opens or changes | `commodity` |
| `language_changed` | Site language changes | `from`, `to` |
| `search_query_submitted` | Debounced news search contains text | `query_length` only |
| `exception` | Sentry accepts a frontend error | generic `description`, `fatal` |

## GA4 dashboard setup

Create these event-scoped custom dimensions after the first live events arrive:

| Dimension name | Event parameter |
|---|---|
| Crop type | `crop` |
| Province | `province` |
| Category | `category` |
| Method | `method` |
| From language | `from` |
| To language | `to` |

Mark these events as conversions:

- `signup_completed`
- `fertilizer_recommend_received`
- `roi_calculate_received`
- `watchlist_item_added`

Operational GA4 setup still required in the Google dashboard:

- Create the GA4 web stream and provide its `G-...` Measurement ID.
- Verify live page views and custom events in Realtime after the ID is deployed.
- Set data retention to 14 months.
- Configure an internal traffic rule for developer IP addresses.
- Confirm the built-in known-bot filter remains enabled.
