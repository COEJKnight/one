"""Adding unique PK to fpds_update

Revision ID: 5f1470603fa0
Revises: 7597deb348fb
Create Date: 2018-03-05 13:25:41.189603

"""

# revision identifiers, used by Alembic.
revision = '5f1470603fa0'
down_revision = '7597deb348fb'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_data_broker():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('fpds_update', sa.Column('fpds_update_id', sa.Integer(), server_default='1', nullable=False))
    op.execute("ALTER TABLE fpds_update DROP CONSTRAINT fpds_update_pkey")
    op.execute("ALTER TABLE fpds_update ADD CONSTRAINT fpds_update_pkey PRIMARY KEY (fpds_update_id)")
    op.alter_column('fpds_update', 'update_date',
               existing_type=sa.DATE(),
               nullable=True)
    ### end Alembic commands ###


def downgrade_data_broker():
    ### commands auto generated by Alembic - please adjust! ###
    op.execute("ALTER TABLE fpds_update DROP CONSTRAINT fpds_update_pkey")
    op.execute("ALTER TABLE fpds_update ADD CONSTRAINT fpds_update_pkey PRIMARY KEY (update_date)")
    op.alter_column('fpds_update', 'update_date',
               existing_type=sa.DATE(),
               nullable=False)
    op.drop_column('fpds_update', 'fpds_update_id')
    ### end Alembic commands ###

