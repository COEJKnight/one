"""Adding indexing to zips in detached_award_financial_assistance table

Revision ID: 9589687eea88
Revises: 97bf80bdd459
Create Date: 2017-09-12 13:45:54.398890

"""

# revision identifiers, used by Alembic.
revision = '9589687eea88'
down_revision = '97bf80bdd459'
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
    op.create_index(op.f('ix_detached_award_financial_assistance_legal_entity_zip5'), 'detached_award_financial_assistance', ['legal_entity_zip5'], unique=False)
    op.create_index(op.f('ix_detached_award_financial_assistance_legal_entity_zip_last4'), 'detached_award_financial_assistance', ['legal_entity_zip_last4'], unique=False)
    ### end Alembic commands ###


def downgrade_data_broker():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_detached_award_financial_assistance_legal_entity_zip_last4'), table_name='detached_award_financial_assistance')
    op.drop_index(op.f('ix_detached_award_financial_assistance_legal_entity_zip5'), table_name='detached_award_financial_assistance')
    ### end Alembic commands ###
