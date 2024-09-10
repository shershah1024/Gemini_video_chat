"""Initial migration

Revision ID: 23d8ed08de8d
Revises: 
Create Date: 2024-09-10 16:25:56.386904

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '23d8ed08de8d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=120),
               type_=sa.String(length=255),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=120),
               existing_nullable=False)

    # ### end Alembic commands ###
