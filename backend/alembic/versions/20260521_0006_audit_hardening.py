"""audit hardening for auth, slugs and token revocation

Revision ID: 20260521_0006
Revises: 20260521_0005
Create Date: 2026-05-21
"""
from __future__ import annotations

from urllib.parse import urlparse
import re

from alembic import op
import sqlalchemy as sa


revision = "20260521_0006"
down_revision = "20260521_0005"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in set(inspector.get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _slug_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9\-]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:120] or "bai-viet"


def _slug_from_url(url: str, fallback: str = "bai-viet") -> str:
    try:
        parsed = urlparse(url or "")
        tail = parsed.path.rstrip("/").split("/")[-1] or fallback
    except Exception:
        tail = fallback
    tail = re.sub(r"\.(html?|aspx?)$", "", tail.split("?", 1)[0], flags=re.IGNORECASE)
    return _slug_text(tail)


def _public_guide_slug(slug: str) -> str:
    return re.sub(r"^(hainong|hai-nong|hai_nong)-+", "", slug or "", flags=re.IGNORECASE)


def upgrade() -> None:
    if not _has_column("app_users", "failed_login_attempts"):
        op.add_column(
            "app_users",
            sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_column("app_users", "locked_until"):
        op.add_column("app_users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    if not _has_table("revoked_tokens"):
        op.create_table(
            "revoked_tokens",
            sa.Column("jti", sa.String(length=64), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.user_id"), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])
        op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])
        op.create_index("ix_revoked_tokens_revoked_at", "revoked_tokens", ["revoked_at"])

    if not _has_column("guide_posts", "public_slug"):
        op.add_column("guide_posts", sa.Column("public_slug", sa.String(length=180), nullable=True))
        op.create_index("ix_guide_posts_public_slug", "guide_posts", ["public_slug"])
    if not _has_column("news_articles", "public_slug"):
        op.add_column("news_articles", sa.Column("public_slug", sa.String(length=180), nullable=True))
        op.create_index("ix_news_articles_public_slug", "news_articles", ["public_slug"])

    bind = op.get_bind()
    if _has_column("guide_posts", "public_slug"):
        rows = bind.execute(sa.text("SELECT post_id, slug FROM guide_posts")).mappings().all()
        for row in rows:
            bind.execute(
                sa.text("UPDATE guide_posts SET public_slug = :public_slug WHERE post_id = :post_id"),
                {"public_slug": _public_guide_slug(row["slug"]), "post_id": row["post_id"]},
            )
    if _has_column("news_articles", "public_slug"):
        rows = bind.execute(sa.text("SELECT article_id, source_url, title FROM news_articles")).mappings().all()
        for row in rows:
            public_slug = f'{row["article_id"]}-{_slug_from_url(row["source_url"], row["title"])}'
            bind.execute(
                sa.text("UPDATE news_articles SET public_slug = :public_slug WHERE article_id = :article_id"),
                {"public_slug": public_slug[:180], "article_id": row["article_id"]},
            )


def downgrade() -> None:
    for index_name in [
        "ix_news_articles_public_slug",
        "ix_guide_posts_public_slug",
        "ix_revoked_tokens_revoked_at",
        "ix_revoked_tokens_expires_at",
        "ix_revoked_tokens_user_id",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    if _has_table("revoked_tokens"):
        op.drop_table("revoked_tokens")
    for table_name, column_name in [
        ("news_articles", "public_slug"),
        ("guide_posts", "public_slug"),
        ("app_users", "locked_until"),
        ("app_users", "failed_login_attempts"),
    ]:
        if _has_column(table_name, column_name):
            op.drop_column(table_name, column_name)
