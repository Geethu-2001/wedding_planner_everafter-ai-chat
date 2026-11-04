"""Add provider research and selection fields (safe for fresh and existing databases)."""
from alembic import op
import sqlalchemy as sa

revision = "0002_vendor_selection_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

COLUMNS = [
    ("price_text", sa.String(length=240), "Not published"),
    ("package_details", sa.Text(), ""),
    ("contact_details", sa.Text(), ""),
    ("result_summary", sa.Text(), ""),
    ("quoted_amount", sa.Numeric(14, 2), None),
    ("selection_status", sa.String(length=30), "not_selected"),
    ("notes", sa.Text(), ""),
    ("researched_at", sa.DateTime(), None),
]


def upgrade():
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("vendors")}
    for name, column_type, default in COLUMNS:
        if name not in existing:
            kwargs = {"nullable": True}
            if default is not None:
                kwargs["server_default"] = str(default)
                kwargs["nullable"] = False
            op.add_column("vendors", sa.Column(name, column_type, **kwargs))


def downgrade():
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("vendors")}
    for name, _, _ in reversed(COLUMNS):
        if name in existing:
            op.drop_column("vendors", name)
