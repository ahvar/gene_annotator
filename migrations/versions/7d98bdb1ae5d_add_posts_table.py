"""add posts table

Revision ID: 7d98bdb1ae5d
Revises: 087f1c8b75f4
Create Date: 2025-05-11 21:29:58.321677

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d98bdb1ae5d'
down_revision = '087f1c8b75f4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('body', sa.String(length=140), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('researcher_id', sa.Integer(), nullable=False),
    sa.Column('language', sa.String(length=5), nullable=True),
    sa.ForeignKeyConstraint(['researcher_id'], ['researcher.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_post_researcher_id'), ['researcher_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_post_timestamp'), ['timestamp'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_post_timestamp'))
        batch_op.drop_index(batch_op.f('ix_post_researcher_id'))

    op.drop_table('post')
    # ### end Alembic commands ###
