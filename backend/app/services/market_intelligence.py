from collections import defaultdict
from datetime import UTC, datetime
from io import StringIO
import csv
import unicodedata

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.ml_engine.lstm_forecaster import ForecastConfig, LSTMForecaster
from app.models import DailyMarketPrice, DurianVariety, ModelTrainingRun, NewsArticle, ProductionRegion, ScrapeRun
from app.services.data_loader import DataLoader


SYNTHETIC_SOURCE = "Nội suy từ giá vùng"
DERIVED_SOURCE_PREFIX = "Hiệu chỉnh từ "
NON_PRODUCTION_REGIONS = {"Thị trường Việt Nam", "Chợ đầu mối TP.HCM"}


class MarketIntelligenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def data_quality(self, crop: str, region_id: int | None = None, variety_id: int | None = None) -> dict:
        stmt = (
            select(DailyMarketPrice)
            .where(DailyMarketPrice.crop_type == crop)
            .order_by(DailyMarketPrice.record_timestamp.desc())
        )
        if region_id:
            stmt = stmt.where(DailyMarketPrice.region_id == region_id)
        if variety_id:
            stmt = stmt.where(DailyMarketPrice.variety_id == variety_id)
        rows = self.db.scalars(stmt.limit(1000)).all()
        total = len(rows)
        synthetic = sum(1 for row in rows if _is_backfill_source(row.exchange_source))
        calibrated = sum(1 for row in rows if _is_calibrated_source(row.exchange_source))
        observed = total - synthetic - calibrated
        trusted_observed = _trusted_observed_points(observed, calibrated)
        sources = sorted({row.exchange_source for row in rows if row.exchange_source})
        latest = max((row.record_timestamp for row in rows), default=None)
        freshness_days = self._freshness_days(latest)
        score = self._quality_score(total, trusted_observed, len(sources), freshness_days)
        return {
            "score": score,
            "history_points": total,
            "observed_points": observed,
            "calibrated_points": calibrated,
            "trusted_observed_points": round(trusted_observed, 2),
            "synthetic_points": synthetic,
            "observed_ratio": round(trusted_observed / total, 4) if total else 0,
            "source_count": len(sources),
            "sources": sources[:8],
            "latest_timestamp": latest,
            "freshness_days": freshness_days,
            "note": self._quality_note(score, observed, synthetic, calibrated),
            "risk_flags": self._risk_flags(score, observed, synthetic, calibrated, freshness_days),
        }

    def data_quality_bulk(self, crop: str, region_ids: list[int], variety_ids: list[int]) -> dict[tuple[int, int], dict]:
        if not region_ids or not variety_ids:
            return {}
        rows = self.db.execute(
            select(
                DailyMarketPrice.region_id,
                DailyMarketPrice.variety_id,
                DailyMarketPrice.exchange_source,
                DailyMarketPrice.record_timestamp,
            )
            .where(DailyMarketPrice.crop_type == crop)
            .where(DailyMarketPrice.region_id.in_(region_ids))
            .where(DailyMarketPrice.variety_id.in_(variety_ids))
            .order_by(DailyMarketPrice.record_timestamp.desc())
        ).all()
        grouped: dict[tuple[int, int], list] = defaultdict(list)
        for row in rows:
            key = (row.region_id, row.variety_id)
            if len(grouped[key]) < 1000:
                grouped[key].append(row)

        result: dict[tuple[int, int], dict] = {}
        for key, pair_rows in grouped.items():
            total = len(pair_rows)
            synthetic = sum(1 for row in pair_rows if _is_backfill_source(row.exchange_source))
            calibrated = sum(1 for row in pair_rows if _is_calibrated_source(row.exchange_source))
            observed = total - synthetic - calibrated
            trusted_observed = _trusted_observed_points(observed, calibrated)
            sources = sorted({row.exchange_source for row in pair_rows if row.exchange_source})
            latest = max((row.record_timestamp for row in pair_rows), default=None)
            freshness_days = self._freshness_days(latest)
            score = self._quality_score(total, trusted_observed, len(sources), freshness_days)
            result[key] = {
                "score": score,
                "history_points": total,
                "observed_points": observed,
                "calibrated_points": calibrated,
                "trusted_observed_points": round(trusted_observed, 2),
                "synthetic_points": synthetic,
                "source_count": len(sources),
                "freshness_days": freshness_days,
                "risk_flags": self._risk_flags(score, observed, synthetic, calibrated, freshness_days),
            }
        return result

    def source_health(self, crop: str) -> list[dict]:
        rows = self.db.execute(
            select(
                DailyMarketPrice.exchange_source,
                func.count(DailyMarketPrice.id),
                func.max(DailyMarketPrice.record_timestamp),
            )
            .where(DailyMarketPrice.crop_type == crop)
            .where(DailyMarketPrice.exchange_source.is_not(None))
            .group_by(DailyMarketPrice.exchange_source)
            .order_by(func.count(DailyMarketPrice.id).desc())
        ).all()
        latest_runs: dict[str, ScrapeRun] = {}
        for run in self.db.scalars(select(ScrapeRun).order_by(ScrapeRun.started_at.desc())).all():
            if run.source not in latest_runs:
                latest_runs[run.source] = run
        result = []
        for source, count, latest_price_at in rows:
            run = latest_runs.get(source)
            freshness_days = self._freshness_days(latest_price_at)
            is_derived = _is_derived_source(source)
            is_system_generated = source == SYNTHETIC_SOURCE or is_derived
            status = "nội suy" if source == SYNTHETIC_SOURCE else ("hiệu chỉnh" if is_derived else (run.status if run else "quan sát"))
            if not is_system_generated and freshness_days is not None and freshness_days > 7:
                status = "sources-broken"
            elif not is_system_generated and freshness_days is not None and freshness_days > 3:
                status = "stale"
            result.append(
                {
                    "source": source,
                    "status": status,
                    "record_count": int(count),
                    "latest_price_at": latest_price_at,
                    "freshness_days": freshness_days,
                    "is_synthetic": is_derived,
                    "last_scrape_at": run.finished_at if run else None,
                    "last_scrape_status": run.status if run else None,
                }
            )
        return result

    def top_movers(self, crop: str, limit: int = 8) -> dict:
        rows = self._recent_price_rows(crop, limit=4000)
        grouped: dict[tuple[str, str, str | None], list[dict]] = defaultdict(list)
        for row in rows:
            if not self._is_production_point(row):
                continue
            grouped[(row["variety"], row["region"], row["province"])].append(row)

        movers = []
        for (variety, region, province), points in grouped.items():
            points = sorted(points, key=lambda item: item["timestamp"])
            if len(points) < 8:
                continue
            latest = points[-1]
            previous = points[-8]
            latest_price = float(latest["max_price_vnd"] or 0)
            previous_price = float(previous["max_price_vnd"] or 0)
            if not latest_price or not previous_price:
                continue
            change_vnd = latest_price - previous_price
            change_pct = change_vnd / previous_price * 100
            movers.append(
                {
                    "variety": variety,
                    "region": region,
                    "province": province,
                    "latest_price_vnd": round(latest_price, 2),
                    "previous_price_vnd": round(previous_price, 2),
                    "change_vnd": round(change_vnd, 2),
                    "change_pct": round(change_pct, 2),
                    "timestamp": latest["timestamp"],
                }
            )
        gainers = sorted(movers, key=lambda item: item["change_pct"], reverse=True)[:limit]
        losers = sorted(movers, key=lambda item: item["change_pct"])[:limit]
        return {"gainers": gainers, "losers": losers}

    def heatmap(self, crop: str) -> list[dict]:
        rows = self._recent_price_rows(crop, limit=6000)
        grouped: dict[tuple[int, str, str | None, str], list[dict]] = defaultdict(list)
        for row in rows:
            if not self._is_production_point(row):
                continue
            region_id = row.get("region_id")
            if not region_id:
                continue
            grouped[(region_id, row["region"], row["province"], row["variety"])].append(row)

        region_totals: dict[tuple[int, str, str | None], dict[str, list[float]]] = defaultdict(
            lambda: {"latest": [], "previous": []}
        )
        for (region_id, region, province, _variety), points in grouped.items():
            points = sorted(points, key=lambda item: item["timestamp"])
            if len(points) < 2:
                continue
            latest = points[-1]
            previous = points[-8] if len(points) >= 8 else points[0]
            latest_price = float(latest["max_price_vnd"] or 0)
            previous_price = float(previous["max_price_vnd"] or 0)
            if not latest_price or not previous_price:
                continue
            bucket = region_totals[(region_id, region, province)]
            bucket["latest"].append(latest_price)
            bucket["previous"].append(previous_price)

        quality_by_region = self._region_quality_bulk(crop, [region_id for region_id, _region, _province in region_totals])
        cells = []
        for (region_id, region, province), values in region_totals.items():
            latest_prices = values["latest"]
            previous_prices = values["previous"]
            latest_avg = sum(latest_prices) / len(latest_prices) if latest_prices else 0
            previous_avg = sum(previous_prices) / len(previous_prices) if previous_prices else latest_avg
            cells.append(
                {
                    "region_id": region_id,
                    "region": region,
                    "province": province,
                    "avg_price_vnd": round(latest_avg, 2),
                    "change_pct": round(((latest_avg - previous_avg) / previous_avg * 100), 2) if previous_avg else 0,
                    "variety_count": len(latest_prices),
                    "quality_score": quality_by_region.get(region_id, 0),
                }
            )
        return sorted(cells, key=lambda item: item["avg_price_vnd"], reverse=True)

    def _recent_price_rows(self, crop: str, limit: int) -> list[dict]:
        rows = self.db.execute(
            select(
                DailyMarketPrice.record_timestamp,
                DailyMarketPrice.quality_grade,
                DailyMarketPrice.exchange_source,
                DailyMarketPrice.min_price_vnd,
                DailyMarketPrice.max_price_vnd,
                DailyMarketPrice.volume_traded_tons,
                DailyMarketPrice.region_id,
                DurianVariety.name,
                ProductionRegion.region_name,
                ProductionRegion.province,
            )
            .join(DurianVariety, DurianVariety.variety_id == DailyMarketPrice.variety_id)
            .join(ProductionRegion, ProductionRegion.region_id == DailyMarketPrice.region_id)
            .where(DailyMarketPrice.crop_type == crop)
            .where(DailyMarketPrice.quality_grade == "Loại A")
            .where(DailyMarketPrice.max_price_vnd.is_not(None))
            .order_by(DailyMarketPrice.record_timestamp.desc())
            .limit(limit)
        ).all()
        return [
            {
                "timestamp": row.record_timestamp,
                "variety": row.name,
                "region": row.region_name,
                "province": row.province,
                "quality_grade": row.quality_grade,
                "exchange_source": row.exchange_source,
                "min_price_vnd": float(row.min_price_vnd) if row.min_price_vnd is not None else None,
                "max_price_vnd": float(row.max_price_vnd) if row.max_price_vnd is not None else None,
                "volume_traded_tons": float(row.volume_traded_tons) if row.volume_traded_tons is not None else None,
                "region_id": row.region_id,
            }
            for row in rows
        ]

    def _region_quality_bulk(self, crop: str, region_ids: list[int]) -> dict[int, int]:
        if not region_ids:
            return {}
        rows = self.db.execute(
            select(
                DailyMarketPrice.region_id,
                DailyMarketPrice.exchange_source,
                DailyMarketPrice.record_timestamp,
            )
            .where(DailyMarketPrice.crop_type == crop)
            .where(DailyMarketPrice.region_id.in_(list(set(region_ids))))
            .order_by(DailyMarketPrice.record_timestamp.desc())
        ).all()
        grouped: dict[int, list] = defaultdict(list)
        for row in rows:
            if len(grouped[row.region_id]) < 1000:
                grouped[row.region_id].append(row)
        scores: dict[int, int] = {}
        for region_id, region_rows in grouped.items():
            total = len(region_rows)
            synthetic = sum(1 for row in region_rows if _is_backfill_source(row.exchange_source))
            calibrated = sum(1 for row in region_rows if _is_calibrated_source(row.exchange_source))
            observed = total - synthetic - calibrated
            trusted_observed = _trusted_observed_points(observed, calibrated)
            sources = {row.exchange_source for row in region_rows if row.exchange_source}
            latest = max((row.record_timestamp for row in region_rows), default=None)
            scores[region_id] = self._quality_score(total, trusted_observed, len(sources), self._freshness_days(latest))
        return scores

    def alerts(self, crop: str, region_id: int, variety_id: int) -> list[dict]:
        loader = DataLoader(self.db)
        history = loader.historical_prices(crop_type=crop, region_id=region_id, variety_id=variety_id, quality_grade="Loại A", limit=90)
        window = loader.latest_feature_window(crop_type=crop, region_id=region_id, variety_id=variety_id)
        forecast = LSTMForecaster(
            ForecastConfig(),
            crop_type=crop,
            region_id=region_id,
            variety_id=variety_id,
        ).predict_30_days(window)
        alerts: list[dict] = []
        if history and forecast:
            latest = float(history[-1]["max_price_vnd"] or 0)
            forecast_end = float(forecast[-1])
            delta_pct = (forecast_end - latest) / latest * 100 if latest else 0
            if delta_pct >= 4:
                alerts.append(
                    {
                        "level": "Cơ hội",
                        "title": "Dự báo tăng giá",
                        "message": f"Giá dự báo 30 ngày cao hơn hiện tại khoảng {delta_pct:.1f}%.",
                    }
                )
            elif delta_pct <= -4:
                alerts.append(
                    {
                        "level": "Rủi ro",
                        "title": "Dự báo giảm giá",
                        "message": f"Giá dự báo 30 ngày thấp hơn hiện tại khoảng {abs(delta_pct):.1f}%.",
                    }
                )
            else:
                alerts.append(
                    {
                        "level": "Theo dõi",
                        "title": "Biên dự báo hẹp",
                        "message": "Dự báo 30 ngày chưa lệch mạnh so với giá hiện tại.",
                    }
                )
        latest_run = self.db.scalar(
            select(ModelTrainingRun)
            .where(ModelTrainingRun.crop_type == crop)
            .order_by(desc(ModelTrainingRun.started_at))
            .limit(1)
        )
        if latest_run and latest_run.rmse_vnd_per_kg:
            alerts.append(
                {
                    "level": "Model",
                    "title": "Sai số backtest",
                    "message": f"RMSE backtest gần nhất khoảng {round(float(latest_run.rmse_vnd_per_kg)):,} VND/kg.",
                }
            )
        quality = self.data_quality(crop, region_id=region_id, variety_id=variety_id)
        alerts.append(
            {
                "level": "Dữ liệu",
                "title": f"Độ tin cậy {quality['score']}/100",
                "message": quality["note"],
            }
        )
        return alerts

    def market_index(self, crop: str) -> dict:
        rows = self._recent_price_rows(crop, limit=6000)
        by_date: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            if self._is_production_point(row) and row.get("max_price_vnd"):
                by_date[str(row["timestamp"].date())].append(float(row["max_price_vnd"]))
        series = []
        for date, prices in sorted(by_date.items()):
            if prices:
                series.append({"date": date, "index_price_vnd": round(sum(prices) / len(prices), 2)})
        latest = series[-1]["index_price_vnd"] if series else 0
        previous = series[-8]["index_price_vnd"] if len(series) >= 8 else latest
        change_pct = ((latest - previous) / previous * 100) if previous else 0
        names = {
            "ca_phe": "Chỉ số giá cà phê",
            "sau_rieng": "Chỉ số giá sầu riêng",
            "ho_tieu": "Chỉ số giá hồ tiêu",
            "lua": "Chỉ số giá lúa",
        }
        return {
            "name": names.get(crop, "Chỉ số giá nông sản"),
            "latest_value_vnd": round(latest, 2),
            "change_pct_7d": round(change_pct, 2),
            "series": series[-90:],
        }

    def explain_change(self, crop: str, region_id: int, variety_id: int) -> dict:
        rows = DataLoader(self.db).historical_prices(
            crop_type=crop,
            region_id=region_id,
            variety_id=variety_id,
            quality_grade="Loại A",
            limit=90,
        )
        if len(rows) < 8:
            return {
                "summary": "Chưa đủ dữ liệu để giải thích biến động.",
                "drivers": [],
                "recommendation": "Tiếp tục theo dõi thêm dữ liệu quan sát.",
            }
        latest = rows[-1]
        previous = rows[-8]
        latest_price = float(latest["max_price_vnd"] or 0)
        previous_price = float(previous["max_price_vnd"] or 0)
        change_pct = ((latest_price - previous_price) / previous_price * 100) if previous_price else 0
        drivers = []

        recent = rows[-14:]
        recent_avg = sum(float(row["max_price_vnd"] or 0) for row in recent) / len(recent)
        older = rows[-42:-14] or rows[: -14]
        older_avg = sum(float(row["max_price_vnd"] or 0) for row in older) / len(older) if older else recent_avg
        momentum = ((recent_avg - older_avg) / older_avg * 100) if older_avg else 0
        drivers.append(
            {
                "name": "Động lượng giá",
                "impact": round(momentum, 2),
                "direction": "tăng" if momentum >= 0 else "giảm",
                "detail": "Giá trung bình 14 ngày gần nhất so với giai đoạn trước.",
            }
        )

        avg_rain = sum(float(row.get("precipitation_mm") or 0) for row in recent) / len(recent)
        drivers.append(
            {
                "name": "Mưa và thời tiết",
                "impact": round(avg_rain, 2),
                "direction": "rủi ro cung" if avg_rain >= 22 else "ổn định",
                "detail": "Mưa cao có thể làm gián đoạn thu hoạch và logistics.",
            }
        )

        synthetic_ratio = sum(1 for row in recent if row.get("is_synthetic")) / len(recent)
        drivers.append(
            {
                "name": "Chất lượng dữ liệu",
                "impact": round(synthetic_ratio * 100, 1),
                "direction": "cần thận trọng" if synthetic_ratio > 0.4 else "tốt",
                "detail": "Tỷ lệ điểm nội suy trong chuỗi gần nhất.",
            }
        )
        drivers.extend(self._news_context_drivers(crop))

        if change_pct >= 3:
            recommendation = "Ưu tiên chốt bán từng phần khi giá đang thuận lợi, nhưng vẫn cần đối chiếu nhịp xuất khẩu, chính sách cửa khẩu và chi phí logistics trước khi bán toàn bộ."
            summary = f"Giá đang tăng khoảng {change_pct:.1f}% so với 7 phiên trước; cần đọc cùng đơn hàng xuất khẩu, tỷ giá và các tin chính sách mới."
        elif change_pct <= -3:
            recommendation = "Thận trọng khi giá yếu; ưu tiên kiểm tra tin xuất khẩu, chính sách kiểm dịch, chi phí vận chuyển và sức mua từ thị trường chính trước khi ra quyết định lớn."
            summary = f"Giá đang giảm khoảng {abs(change_pct):.1f}% so với 7 phiên trước; biến động này có thể bị khuếch đại nếu xuất khẩu hoặc chính sách ngành xuất hiện tín hiệu bất lợi."
        else:
            recommendation = "Giữ nhịp theo dõi, chưa cần hành động gấp; nếu có tin mới về xuất khẩu, chính sách kiểm dịch hoặc logistics thì nên cập nhật lại kịch bản ngay."
            summary = "Giá biến động hẹp trong tuần gần đây; bối cảnh xuất khẩu, chính sách và chi phí đầu vào sẽ quyết định khả năng phá biên."
        return {"summary": summary, "drivers": drivers[:6], "recommendation": recommendation}

    def _news_context_drivers(self, crop: str) -> list[dict]:
        rows = self.db.scalars(
            select(NewsArticle)
            .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.scraped_at.desc())
            .limit(160)
        ).all()
        crop_terms = _crop_terms(crop)
        buckets = [
            (
                "Giá xuất khẩu và đầu ra",
                "Theo dõi đơn hàng",
                ["xuat khau", "kim ngach", "don hang", "trung quoc", "cua khau", "usd", "ty gia", "logistics"],
            ),
            (
                "Tin chính sách ngành",
                "Có thể đổi biên giao dịch",
                ["chinh sach", "nghi dinh", "thong tu", "bo nong nghiep", "kiem dich", "ma so vung trong", "quy dinh"],
            ),
            (
                "Địa chính trị và vận chuyển",
                "Rủi ro bên ngoài",
                ["dia chinh tri", "chien su", "xung dot", "van tai", "logistics", "cuoc tau", "bien dong"],
            ),
        ]
        result: list[dict] = []
        for label, direction, keywords in buckets:
            matches = []
            for article in rows:
                text = _fold(f"{article.title} {article.summary} {article.category}")
                if not any(keyword in text for keyword in keywords):
                    continue
                if crop_terms and not any(term in text for term in crop_terms) and "nong san" not in text and "phan bon" not in text:
                    continue
                matches.append(article)
                if len(matches) >= 3:
                    break
            if matches:
                result.append(
                    {
                        "name": label,
                        "impact": len(matches),
                        "direction": direction,
                        "detail": f"Ghi nhận {len(matches)} tin liên quan gần đây; đáng chú ý: {_compact_title(matches[0].title)}.",
                    }
                )
            else:
                result.append(
                    {
                        "name": label,
                        "impact": 0,
                        "direction": "Chưa có tín hiệu nổi bật",
                        "detail": "Chưa thấy tin mới đủ mạnh trong kho tin hiện tại; giữ vai trò biến số cần theo dõi khi cập nhật bản tin tiếp theo.",
                    }
                )
        return result

    def compare_markets(self, crop: str, region_id: int, variety_id: int) -> dict:
        selected = DataLoader(self.db).historical_prices(
            crop_type=crop,
            region_id=region_id,
            variety_id=variety_id,
            quality_grade="Loại A",
            limit=30,
        )
        selected_avg = (
            sum(float(row["max_price_vnd"] or 0) for row in selected) / len(selected)
            if selected
            else 0
        )
        rows = self._recent_price_rows(crop, limit=6000)
        grouped: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            if row.get("variety") == (selected[-1]["variety"] if selected else None) and self._is_production_point(row):
                grouped[row["province"] or row["region"]].append(float(row["max_price_vnd"] or 0))
        peers = []
        for label, prices in grouped.items():
            if prices:
                avg = sum(prices[:30]) / min(30, len(prices))
                peers.append({"label": label, "avg_price_vnd": round(avg, 2), "premium_pct": round(((selected_avg - avg) / avg * 100), 2) if avg else 0})
        return {
            "selected_avg_price_vnd": round(selected_avg, 2),
            "peers": sorted(peers, key=lambda item: item["avg_price_vnd"], reverse=True)[:10],
        }

    def export_csv(self, crop: str, region_id: int | None, variety_id: int | None) -> str:
        rows = DataLoader(self.db).historical_prices(
            crop_type=crop,
            region_id=region_id,
            variety_id=variety_id,
            quality_grade=None,
            limit=1000,
        )
        output = StringIO()
        output.write("\ufeff")
        fieldnames = [
            "timestamp",
            "crop",
            "variety",
            "region",
            "province",
            "quality_grade",
            "exchange_source",
            "min_price_vnd",
            "max_price_vnd",
            "volume_traded_tons",
            "temp_max_celsius",
            "precipitation_mm",
            "maturity_index",
            "data_kind",
        ]
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            safe_row = {key: row.get(key, "") for key in fieldnames}
            safe_row["crop"] = crop
            timestamp = safe_row.get("timestamp")
            if hasattr(timestamp, "isoformat"):
                safe_row["timestamp"] = timestamp.isoformat()
            for key, value in list(safe_row.items()):
                if value is None:
                    safe_row[key] = ""
            writer.writerow(safe_row)
        return output.getvalue()

    @staticmethod
    def _is_production_point(row: dict) -> bool:
        return row.get("province") is not None and row.get("region") not in NON_PRODUCTION_REGIONS

    @staticmethod
    def _freshness_days(latest: datetime | None) -> int | None:
        if latest is None:
            return None
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=UTC)
        return max(0, (datetime.now(UTC) - latest).days)

    @staticmethod
    def _quality_score(total: int, observed: float, source_count: int, freshness_days: int | None) -> int:
        history_score = min(30, total / 120 * 30)
        observed_score = (observed / total * 35) if total else 0
        source_score = min(20, source_count * 5)
        freshness_score = 15 if freshness_days is not None and freshness_days <= 7 else 8 if freshness_days is not None and freshness_days <= 45 else 3
        return int(round(history_score + observed_score + source_score + freshness_score))

    @staticmethod
    def _quality_note(score: int, observed: int, synthetic: int, calibrated: int) -> str:
        if score >= 80:
            return "Chuỗi dữ liệu mạnh, có thể dùng cho cảnh báo và backtest."
        if calibrated > observed and synthetic <= calibrated:
            return "Chuỗi đủ dùng, phần lớn được hiệu chỉnh từ nguồn giá công khai; nên bổ sung thêm điểm quan sát trực tiếp."
        if observed == 0 and synthetic > 0:
            return "Chuỗi đủ để chạy model nhưng phụ thuộc nhiều vào nội suy."
        if score >= 60:
            return "Chuỗi đủ dùng, nên tiếp tục bổ sung thêm nguồn quan sát."
        return "Chuỗi còn yếu, cần tăng nguồn scrape thật và lịch sử quan sát."

    @staticmethod
    def _risk_flags(score: int, observed: int, synthetic: int, calibrated: int, freshness_days: int | None) -> list[str]:
        flags = []
        if synthetic > observed + calibrated:
            flags.append("Phụ thuộc nhiều vào nội suy")
        if calibrated > observed:
            flags.append("Cần thêm điểm quan sát trực tiếp")
        if freshness_days is None or freshness_days > 14:
            flags.append("Nguồn giá chưa đủ mới")
        if score < 70:
            flags.append("Cần bổ sung nguồn quan sát")
        return flags


def _is_derived_source(source: str | None) -> bool:
    return bool(source and (source == SYNTHETIC_SOURCE or source.startswith(DERIVED_SOURCE_PREFIX)))


def _is_backfill_source(source: str | None) -> bool:
    return bool(source and source == SYNTHETIC_SOURCE)


def _is_calibrated_source(source: str | None) -> bool:
    return bool(source and source.startswith(DERIVED_SOURCE_PREFIX))


def _trusted_observed_points(observed: int, calibrated: int) -> float:
    # Public-source calibration is more useful than pure interpolation, but it
    # still should not count as strongly as a directly scraped local quote.
    return observed + calibrated * 0.68


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d")


def _crop_terms(crop: str) -> list[str]:
    return {
        "ca_phe": ["ca phe", "robusta", "arabica"],
        "sau_rieng": ["sau rieng", "durian"],
        "ho_tieu": ["ho tieu", "tieu den", "tieu trang", "pepper"],
        "lua": ["lua", "gao", "rice", "om 5451", "st25"],
    }.get(crop, [])


def _compact_title(title: str, limit: int = 92) -> str:
    clean = " ".join(title.split())
    return clean if len(clean) <= limit else f"{clean[: limit - 1].rstrip()}…"
