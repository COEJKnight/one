"""empty message

Revision ID: 9f7136e38e21
Revises: a62138efd429, fc6be41471a3
Create Date: 2016-11-29 13:54:49.342595

"""

# revision identifiers, used by Alembic.
revision = '9f7136e38e21'
down_revision = ('a62138efd429', 'fc6be41471a3')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_data_broker():
    pass


def downgrade_data_broker():
    pass

