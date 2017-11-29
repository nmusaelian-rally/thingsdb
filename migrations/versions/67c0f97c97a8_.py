"""empty message

Revision ID: 67c0f97c97a8
Revises: 204306fb46cb
Create Date: 2017-11-28 21:40:20.603081

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67c0f97c97a8'
down_revision = '204306fb46cb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('things', sa.Column('date', sa.Date(), nullable=True))
    op.create_unique_constraint(None, 'things', ['date'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'things', type_='unique')
    op.drop_column('things', 'date')
    # ### end Alembic commands ###
