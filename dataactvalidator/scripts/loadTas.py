from collections import defaultdict
from datetime import date
import os
import logging

import pandas as pd
import boto

from dataactcore.config import CONFIG_BROKER
from dataactcore.interfaces.db import GlobalDB
from dataactcore.logging import configure_logging
from dataactcore.models.domainModels import TAS_COMPONENTS, TASLookup
from dataactvalidator.app import createApp
from dataactvalidator.scripts.loaderUtils import clean_data


logger = logging.getLogger(__name__)


def clean_tas(csv_path):
    """Read a CSV into a dataframe, then use a configured `clean_data` and
    return the results"""
    data = pd.read_csv(csv_path, dtype=str)
    data = clean_data(
        data,
        TASLookup,
        {"a": "availability_type_code",
         "acct_num": "account_num",
         "aid": "agency_identifier",
         "ata": "allocation_transfer_agency",
         "bpoa": "beginning_period_of_availa",
         "epoa": "ending_period_of_availabil",
         "main": "main_account_code",
         "sub": "sub_account_code",
         "financial_indicator_type2": "financial_indicator2",
         },
        {"allocation_transfer_agency": {"pad_to_length": 3, "keep_null": True},
         "agency_identifier": {"pad_to_length": 3},
         # Account for " " cells
         "availability_type_code": {"pad_to_length": 0, "keep_null": True},
         "beginning_period_of_availa": {"pad_to_length": 0, "keep_null": True},
         "ending_period_of_availabil": {"pad_to_length": 0, "keep_null": True},
         "main_account_code": {"pad_to_length": 4},
         "sub_account_code": {"pad_to_length": 3},
         }
    )
    data["account_num"] = pd.to_numeric(data['account_num'])
    return data.where(pd.notnull(data), None)


def update_tas_lookups(csv_path):
    """Load TAS data from the provided CSV and replace/insert any
    TASLookups"""
    sess = GlobalDB.db().session

    data = clean_tas(csv_path)
    add_start_date(data)
    add_existing_id(data)

    # Mark all TAS we don't see as "ended"
    existing_ids = [int(i) for i in data['existing_id'] if pd.notnull(i)]
    sess.query(TASLookup).\
        filter(TASLookup.internal_end_date.is_(None)).\
        filter(~TASLookup.tas_id.in_(existing_ids)).\
        update({'internal_end_date': date.today()}, synchronize_session=False)

    new_data = data[data['existing_id'].isnull()]
    del new_data['existing_id']

    # instead of using the pandas to_sql dataframe method like some of the
    # other domain load processes, iterate through the dataframe rows so we
    # can load using the orm model (note: toyed with the SQLAlchemy bulk load
    # options but ultimately decided not to go outside the unit of work for
    # the sake of a performance gain)
    for _, row in new_data.iterrows():
        sess.add(TASLookup(**row))

    sess.commit()
    logger.info('%s records in CSV, %s existing',
                len(data.index), sum(data['existing_id'].notnull()))


def load_tas(tas_file=None):
    """Load TAS file into broker database. """
    # read TAS file to dataframe, to make sure all is well
    # with the file before firing up a db transaction
    if not tas_file:
        if CONFIG_BROKER["use_aws"]:
            s3connection = boto.s3.connect_to_region(CONFIG_BROKER['aws_region'])
            s3bucket = s3connection.lookup(CONFIG_BROKER['sf_133_bucket'])
            tas_file = s3bucket.get_key("cars_tas.csv").generate_url(expires_in=600)
        else:
            tas_file = os.path.join(
                CONFIG_BROKER["path"],
                "dataactvalidator",
                "config",
                "cars_tas.csv")

    with createApp().app_context():
        update_tas_lookups(tas_file)


def add_start_date(data):
    """We generally want to set the start date to the current quarter.
    However, if this is a fresh install, we'll give more breathing room for
    submissions, starting the epoch at 2015-01-01."""
    if GlobalDB.db().session.query(TASLookup).count() == 0:  # i.e. fresh db
        data['internal_start_date'] = date(2015, 1, 1)
    else:
        today = date.today()
        fiscal_quarter_offset = (today.month - 1) % 3
        fiscal_quarter_month = today.month - fiscal_quarter_offset
        beginning_of_quarter = date(today.year, fiscal_quarter_month, 1)
        data['internal_start_date'] = beginning_of_quarter


def add_existing_id(data):
    """Look up the ids of existing TASes. Use account_num as a non-unique
    identifier to help filter results"""
    existing = defaultdict(list)
    query = GlobalDB.db().session.query(TASLookup).\
        filter(TASLookup.account_num.in_(int(i) for i in data['account_num']))
    for tas in query:
        existing[tas.account_num].append(tas)

    data['existing_id'] = data.apply(existing_id, axis=1, existing=existing)


def existing_id(row, existing):
    """ Check for a TASLookup which matches this `row` in the `existing` data.
        Args:
            row: row to check in
            existing: Dict[account_num, List[TASLookup]]
    """
    for potential_match in existing[row['account_num']]:
        if all(row[f] == getattr(potential_match, f) for f in TAS_COMPONENTS):
            return potential_match.tas_id


if __name__ == '__main__':
    configure_logging()
    load_tas()
