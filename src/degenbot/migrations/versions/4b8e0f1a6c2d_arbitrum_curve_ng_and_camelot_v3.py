"""arbitrum curve ng and camelot v3

Revision ID: 4b8e0f1a6c2d
Revises: e0aaad8ad486
Create Date: 2026-05-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4b8e0f1a6c2d"
down_revision: str | Sequence[str] | None = "e0aaad8ad486"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "camelot_v3_pools",
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"]),
        sa.PrimaryKeyConstraint("pool_id"),
    )
    op.create_table(
        "curve_stableswap_ng_pools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("address", sa.String(length=42), nullable=False),
        sa.Column("chain", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("implementation", sa.String(length=42), nullable=True),
        sa.Column("is_meta", sa.Boolean(), nullable=False),
        sa.Column("n_coins", sa.Integer(), nullable=False),
        sa.Column("coins_json", sa.Text(), nullable=False),
        sa.Column("decimals_json", sa.Text(), nullable=False),
        sa.Column("asset_types_json", sa.Text(), nullable=False),
        sa.Column("balances_json", sa.Text(), nullable=False),
        sa.Column("last_updated_block", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_curve_stableswap_ng_pool_address_chain",
        "curve_stableswap_ng_pools",
        ["address", "chain"],
        unique=True,
    )
    op.create_index(
        op.f("ix_curve_stableswap_ng_pools_exchange_id"),
        "curve_stableswap_ng_pools",
        ["exchange_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_curve_stableswap_ng_pools_exchange_id"),
        table_name="curve_stableswap_ng_pools",
    )
    op.drop_index(
        "ix_curve_stableswap_ng_pool_address_chain",
        table_name="curve_stableswap_ng_pools",
    )
    op.drop_table("curve_stableswap_ng_pools")
    op.drop_table("camelot_v3_pools")
