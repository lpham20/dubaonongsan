"""add agri input price tables

Revision ID: 20260522_0007
Revises: 20260521_0006
Create Date: 2026-05-22
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import random

from alembic import op
import sqlalchemy as sa


revision = "20260522_0007"
down_revision = "20260521_0006"
branch_labels = None
depends_on = None


PRODUCTS = [
    ("ure", "Urê", "Phân đơn", "46% N", "Bao 50 kg", 50, 590_000, ["Phú Mỹ", "Cà Mau"]),
    ("dap", "DAP", "Phân đơn", "18-46-0", "Bao 50 kg", 50, 1_030_000, ["Đình Vũ", "Nhập khẩu"]),
    ("kali-mop", "Kali MOP", "Phân đơn", "60% K2O", "Bao 50 kg", 50, 760_000, ["Phú Mỹ", "Nhập khẩu"]),
    ("kali-sop", "Kali SOP", "Phân đơn", "50% K2O + 18% S", "Bao 50 kg", 50, 1_050_000, ["Nhập khẩu", "SOP tiêu chuẩn"]),
    ("sa", "SA", "Phân đơn", "21% N + 24% S", "Bao 50 kg", 50, 350_000, ["Nhập khẩu", "Phú Mỹ"]),
    ("lan-nung-chay", "Lân nung chảy", "Phân lân", "P2O5 + CaO + MgO", "Bao 50 kg", 50, 245_000, ["Lâm Thao", "Văn Điển"]),
    ("npk-16-16-8", "NPK 16-16-8", "Phân hỗn hợp", "16-16-8", "Bao 50 kg", 50, 690_000, ["Bình Điền", "Phú Mỹ"]),
    ("npk-20-20-15", "NPK 20-20-15", "Phân hỗn hợp", "20-20-15", "Bao 50 kg", 50, 870_000, ["Bình Điền", "Cà Mau"]),
    ("npk-15-15-15", "NPK 15-15-15", "Phân hỗn hợp", "15-15-15", "Bao 50 kg", 50, 650_000, ["Bình Điền", "Lâm Thao"]),
    ("phan-huu-co-vi-sinh", "Phân hữu cơ vi sinh", "Phân hữu cơ", "Hữu cơ + vi sinh", "Bao 25 kg", 25, 145_000, ["Hữu cơ miền Tây", "Hữu cơ Tây Nguyên"]),
]

PROVINCES = [
    ("Đắk Lắk", "Tây Nguyên", 1.02),
    ("Lâm Đồng", "Tây Nguyên", 1.03),
    ("Đồng Tháp", "Đồng bằng sông Cửu Long", 0.99),
    ("Tiền Giang", "Đồng bằng sông Cửu Long", 1.0),
]


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in set(inspector.get_table_names())


def _month_starts(start: datetime, count: int) -> list[datetime]:
    rows = []
    year = start.year
    month = start.month
    for _ in range(count):
        rows.append(datetime(year, month, 1, tzinfo=timezone.utc))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return rows


def _seed_reference_data() -> None:
    bind = op.get_bind()
    product_count = bind.scalar(sa.text("SELECT COUNT(*) FROM agri_input_products"))
    if product_count:
        return

    now = datetime.now(timezone.utc)
    product_rows = []
    for slug, name, product_type, nutrient, package_label, package_size, *_ in PRODUCTS:
        product_rows.append(
            {
                "slug": slug,
                "name": name,
                "category": "fertilizer",
                "product_type": product_type,
                "nutrient_profile": nutrient,
                "standard_unit": "kg",
                "package_label": package_label,
                "package_size_kg": package_size,
                "notes": "Dữ liệu nền tham chiếu; cần đối chiếu với báo giá đại lý trước khi ra quyết định mua bán.",
                "is_active": True,
            }
        )
    bind.execute(
        sa.text(
            """
            INSERT INTO agri_input_products
                (slug, name, category, product_type, nutrient_profile, standard_unit, package_label, package_size_kg, notes, is_active)
            VALUES
                (:slug, :name, :category, :product_type, :nutrient_profile, :standard_unit, :package_label, :package_size_kg, :notes, :is_active)
            """
        ),
        product_rows,
    )

    product_id_by_slug = dict(
        bind.execute(sa.text("SELECT slug, product_id FROM agri_input_products")).all()
    )
    rng = random.Random(20260522)
    observations = []
    for slug, _name, _product_type, _nutrient, _package_label, package_size, base_price, brands in PRODUCTS:
        product_id = product_id_by_slug[slug]
        for month_idx, observed_at in enumerate(_month_starts(datetime(2025, 6, 1, tzinfo=timezone.utc), 12)):
            seasonal = 1 + math.sin(month_idx / 2.3) * 0.025
            slow_trend = 1 + (month_idx - 6) * 0.004
            for province, region_name, province_factor in PROVINCES:
                for brand_idx, brand in enumerate(brands):
                    brand_factor = 1 + (brand_idx * 0.025)
                    noise = rng.uniform(-0.018, 0.018)
                    package_price = round(
                        base_price * seasonal * slow_trend * province_factor * brand_factor * (1 + noise),
                        -3,
                    )
                    observations.append(
                        {
                            "product_id": product_id,
                            "observed_at": observed_at,
                            "province": province,
                            "region_name": region_name,
                            "brand": brand,
                            "seller_name": None,
                            "source_name": "Dữ liệu tham chiếu nền",
                            "source_url": None,
                            "package_price_vnd": package_price,
                            "normalized_price_vnd": round(package_price / package_size, 2),
                            "normalized_unit": "kg",
                            "package_size_kg": package_size,
                            "confidence_score": 0.55,
                            "data_kind": "reference",
                            "created_at": now,
                        }
                    )
    bind.execute(
        sa.text(
            """
            INSERT INTO agri_input_price_observations
                (product_id, observed_at, province, region_name, brand, seller_name, source_name, source_url,
                 package_price_vnd, normalized_price_vnd, normalized_unit, package_size_kg, confidence_score,
                 data_kind, created_at)
            VALUES
                (:product_id, :observed_at, :province, :region_name, :brand, :seller_name, :source_name, :source_url,
                 :package_price_vnd, :normalized_price_vnd, :normalized_unit, :package_size_kg, :confidence_score,
                 :data_kind, :created_at)
            """
        ),
        observations,
    )


def upgrade() -> None:
    if not _has_table("agri_input_products"):
        op.create_table(
            "agri_input_products",
            sa.Column("product_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False, server_default="fertilizer"),
            sa.Column("product_type", sa.String(length=80), nullable=False),
            sa.Column("nutrient_profile", sa.String(length=120), nullable=True),
            sa.Column("standard_unit", sa.String(length=30), nullable=False, server_default="kg"),
            sa.Column("package_label", sa.String(length=80), nullable=True),
            sa.Column("package_size_kg", sa.Numeric(8, 2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.UniqueConstraint("slug", name="uq_agri_input_products_slug"),
        )
        op.create_index("ix_agri_input_products_slug", "agri_input_products", ["slug"])
        op.create_index("ix_agri_input_products_category", "agri_input_products", ["category"])
        op.create_index("ix_agri_input_products_product_type", "agri_input_products", ["product_type"])
        op.create_index("ix_agri_input_products_is_active", "agri_input_products", ["is_active"])

    if not _has_table("agri_input_price_observations"):
        op.create_table(
            "agri_input_price_observations",
            sa.Column("observation_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("agri_input_products.product_id"), nullable=False),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("province", sa.String(length=100), nullable=False),
            sa.Column("region_name", sa.String(length=100), nullable=True),
            sa.Column("brand", sa.String(length=120), nullable=True),
            sa.Column("seller_name", sa.String(length=160), nullable=True),
            sa.Column("source_name", sa.String(length=160), nullable=False),
            sa.Column("source_url", sa.String(length=800), nullable=True),
            sa.Column("package_price_vnd", sa.Numeric(14, 2), nullable=True),
            sa.Column("normalized_price_vnd", sa.Numeric(14, 2), nullable=False),
            sa.Column("normalized_unit", sa.String(length=30), nullable=False, server_default="kg"),
            sa.Column("package_size_kg", sa.Numeric(8, 2), nullable=True),
            sa.Column("confidence_score", sa.Numeric(4, 2), nullable=False, server_default="0.55"),
            sa.Column("data_kind", sa.String(length=40), nullable=False, server_default="reference"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "product_id",
                "observed_at",
                "province",
                "brand",
                "source_name",
                name="uq_agri_input_price_grain",
            ),
        )
        op.create_index("ix_agri_input_price_observations_product_id", "agri_input_price_observations", ["product_id"])
        op.create_index("ix_agri_input_price_observations_observed_at", "agri_input_price_observations", ["observed_at"])
        op.create_index("ix_agri_input_price_observations_province", "agri_input_price_observations", ["province"])
        op.create_index("ix_agri_input_price_observations_region_name", "agri_input_price_observations", ["region_name"])
        op.create_index("ix_agri_input_price_observations_brand", "agri_input_price_observations", ["brand"])
        op.create_index("ix_agri_input_price_observations_source_name", "agri_input_price_observations", ["source_name"])
        op.create_index("ix_agri_input_price_observations_data_kind", "agri_input_price_observations", ["data_kind"])
        op.create_index("ix_agri_input_price_observations_created_at", "agri_input_price_observations", ["created_at"])
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_agri_input_price_product_province_date "
            "ON agri_input_price_observations (product_id, province, observed_at DESC)"
        )

    _seed_reference_data()


def downgrade() -> None:
    for index_name in [
        "ix_agri_input_price_product_province_date",
        "ix_agri_input_price_observations_created_at",
        "ix_agri_input_price_observations_data_kind",
        "ix_agri_input_price_observations_source_name",
        "ix_agri_input_price_observations_brand",
        "ix_agri_input_price_observations_region_name",
        "ix_agri_input_price_observations_province",
        "ix_agri_input_price_observations_observed_at",
        "ix_agri_input_price_observations_product_id",
        "ix_agri_input_products_is_active",
        "ix_agri_input_products_product_type",
        "ix_agri_input_products_category",
        "ix_agri_input_products_slug",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    if _has_table("agri_input_price_observations"):
        op.drop_table("agri_input_price_observations")
    if _has_table("agri_input_products"):
        op.drop_table("agri_input_products")
