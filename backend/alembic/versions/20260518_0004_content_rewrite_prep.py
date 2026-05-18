"""prepare guide content rewrite metadata and redirects

Revision ID: 20260518_0004
Revises: 20260506_0003
Create Date: 2026-05-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260518_0004"
down_revision = "20260506_0003"
branch_labels = None
depends_on = None


OLD_54_SLUG = "quy-trinh-ngam-u-hat-giong-lua-vu-dong-xuan-cc6c9ecf-d4f9-47e9-80a3-994335288ba4-1271"
OLD_102_SLUG = "phong-tru-sau-duc-than-78c511cd-8ed2-4078-88f2-10f5d0fcf20f-1364"
NEW_102_SLUG = "phong-tru-sau-duc-than-xen-toc-xoai-1364"


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("guide_posts", "tags"):
        op.add_column("guide_posts", sa.Column("tags", sa.String(length=500), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE guide_posts
            SET title = :new_title
            WHERE post_id = 116
              AND title = :old_title
            """
        ),
        {
            "old_title": "Hướng dẫn thu hoạch lúa hiệu qảu",
            "new_title": "Hướng dẫn thu hoạch lúa hiệu quả",
        },
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM guide_posts
            WHERE post_id = 54
              AND slug = :old_slug
            """
        ),
        {"old_slug": OLD_54_SLUG},
    )
    bind.execute(
        sa.text(
            """
            UPDATE guide_posts
            SET slug = :new_slug
            WHERE post_id = 102
              AND slug = :old_slug
            """
        ),
        {"old_slug": OLD_102_SLUG, "new_slug": NEW_102_SLUG},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE guide_posts
            SET title = :old_title
            WHERE post_id = 116
              AND title = :new_title
            """
        ),
        {
            "old_title": "Hướng dẫn thu hoạch lúa hiệu qảu",
            "new_title": "Hướng dẫn thu hoạch lúa hiệu quả",
        },
    )
    bind.execute(
        sa.text(
            """
            UPDATE guide_posts
            SET slug = :old_slug
            WHERE post_id = 102
              AND slug = :new_slug
            """
        ),
        {"old_slug": OLD_102_SLUG, "new_slug": NEW_102_SLUG},
    )
    # Deleted duplicate post #54 is intentionally not restored by downgrade.
    if _has_column("guide_posts", "tags"):
        op.drop_column("guide_posts", "tags")
