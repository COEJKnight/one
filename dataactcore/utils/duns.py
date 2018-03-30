import logging
import os
import re
import time
import zipfile
from collections import OrderedDict

import numpy as np
import pandas as pd
from sqlalchemy.exc import IntegrityError

from dataactcore.config import CONFIG_BROKER
from dataactcore.models.domainModels import DUNS
from dataactvalidator.health_check import create_app
from dataactvalidator.scripts.loaderUtils import clean_data, insert_dataframe

logger = logging.getLogger(__name__)

REMOTE_SAM_DIR = '/current/SAM/2_FOUO/UTF-8/'


def get_config():
    sam_config = CONFIG_BROKER.get('sam_duns')

    if sam_config:
        return sam_config.get('username'), sam_config.get('password'), sam_config.get('host'), \
               sam_config.get('port')

    return None, None, None, None, None


def get_relevant_models(data, sess, benchmarks=False):
    # Get a list of the duns we're gonna work off of to prevent multiple calls to the database
    if benchmarks:
        get_models = time.time()
    logger.info("Getting relevant models")
    duns_found = [duns.strip().zfill(9) for duns in list(data["awardee_or_recipient_uniqu"].unique())]
    dun_objects_found = sess.query(DUNS).filter(DUNS.awardee_or_recipient_uniqu.in_(duns_found))
    models = {duns.awardee_or_recipient_uniqu: duns for duns in dun_objects_found}
    logger.info("Getting models with activation dates already set")
    activated_models = {duns_num: duns for duns_num, duns in models.items() if duns.activation_date is not None}
    if benchmarks:
        logger.info("Getting models took {} seconds".format(time.time() - get_models))
    return models, activated_models


def load_duns_by_row(data, sess, models, activated_models, benchmarks=False):
    # data = activation_check(data, activated_models, benchmarks).where(pd.notnull(data), None)
    update_duns(models, data, benchmarks=benchmarks)
    sess.add_all(models.values())


# Removed this function when adding registration_date
# def activation_check(data, activated_models, benchmarks=False):
#     # if activation_date's already set, keep it, otherwise update it (default)
#     logger.info("going through activation check")
#     if benchmarks:
#         activation_check_start = time.time()
#     lambda_func = (lambda duns_num: pd.Series([activated_models[duns_num].activation_date
#                                                if duns_num in activated_models else np.nan]))
#     data = data.assign(old_activation_date=data["awardee_or_recipient_uniqu"].apply(lambda_func))
#     data.loc[pd.notnull(data["old_activation_date"]), "activation_date"] = data["old_activation_date"]
#     del data["old_activation_date"]
#     if benchmarks:
#         logger.info("Activation check took {} seconds".format(time.time()-activation_check_start))
#     return data

def update_duns(models, new_data, benchmarks=False):
    """Modify existing models or create new ones"""
    logger.info("Updating duns")
    if benchmarks:
        update_duns_start = time.time()
    for _, row in new_data.iterrows():
        awardee_or_recipient_uniqu = row['awardee_or_recipient_uniqu']
        if awardee_or_recipient_uniqu not in models:
            models[awardee_or_recipient_uniqu] = DUNS()
        for field, value in row.items():
            setattr(models[awardee_or_recipient_uniqu], field, value)
    if benchmarks:
        logger.info("Updating duns took {} seconds".format(time.time() - update_duns_start))


def clean_sam_data(data):
    return clean_data(data, DUNS, {
        "awardee_or_recipient_uniqu": "awardee_or_recipient_uniqu",
        "activation_date": "activation_date",
        "deactivation_date": "deactivation_date",
        "registration_date": "registration_date",
        "expiration_date": "expiration_date",
        "last_sam_mod_date": "last_sam_mod_date",
        "sam_extract_code": "sam_extract_code",
        "legal_business_name": "legal_business_name"
    }, {})


def parse_sam_file(file_path, sess, monthly=False, benchmarks=False):
    parse_start_time = time.time()
    logger.info("Starting file " + str(file_path))

    dat_file_name = os.path.splitext(os.path.basename(file_path))[0]+'.dat'
    sam_file_type = "MONTHLY" if monthly else "DAILY"
    dat_file_date = re.findall(".*{}_(.*).dat".format(sam_file_type), dat_file_name)[0]

    with create_app().app_context():

        column_header_mapping = {
            "awardee_or_recipient_uniqu": 0,
            "sam_extract_code": 4,
            "registration_date": 6,
            "expiration_date": 7,
            "last_sam_mod_date": 8,
            "activation_date": 9,
            "legal_business_name": 10
        }
        column_header_mapping_ordered = OrderedDict(sorted(column_header_mapping.items(), key=lambda c: c[1]))

        # Initial sweep of the file to see rows and possibly what DUNS we're updating
        if benchmarks:
            initial_sweep = time.time()
        nrows = 0
        with zipfile.ZipFile(file_path) as zip_file:
            with zip_file.open(dat_file_name) as dat_file:
                nrows = len(dat_file.readlines())
        if benchmarks:
            logger.info("Initial sweep took {} seconds".format(time.time() - initial_sweep))

        block_size = 10000
        batches = nrows//block_size
        # skip the first line again if the last batch is also the first batch
        skiplastrows = 2 if batches == 0 else 1
        last_block_size = (nrows % block_size)-skiplastrows
        batch = 0
        added_rows = 0
        while batch <= batches:
            skiprows = 1 if batch == 0 else (batch*block_size)
            nrows = (((batch+1)*block_size)-skiprows) if (batch < batches) else last_block_size
            logger.info('Loading rows %s to %s', skiprows+1, nrows+skiprows)

            with zipfile.ZipFile(file_path) as zip_file:
                with zip_file.open(dat_file_name) as dat_file:
                    csv_data = pd.read_csv(dat_file, dtype=str, header=None, skiprows=skiprows, nrows=nrows, sep='|',
                                           usecols=column_header_mapping_ordered.values(),
                                           names=column_header_mapping_ordered.keys(), quoting=3)

                    # add deactivation_date column for delete records
                    lambda_func = (lambda sam_extract: pd.Series([dat_file_date if sam_extract == "1" else np.nan]))
                    csv_data = csv_data.assign(deactivation_date=pd.Series([np.nan], name='deactivation_date')
                                               if monthly else csv_data["sam_extract_code"].apply(lambda_func))
                    # removing rows where DUNS number isn't even provided
                    csv_data = csv_data.where(csv_data["awardee_or_recipient_uniqu"].notnull())
                    # cleaning and replacing NaN/NaT with None's
                    csv_data = clean_sam_data(csv_data.where(pd.notnull(csv_data), None))

                    if monthly:
                        logger.info("Adding all monthly data with bulk load")
                        if benchmarks:
                            bulk_month_load = time.time()
                        del csv_data["sam_extract_code"]
                        insert_dataframe(csv_data, DUNS.__table__.name, sess.connection())
                        if benchmarks:
                            logger.info("Bulk month load took {} seconds".format(time.time()-bulk_month_load))
                    else:
                        add_data = csv_data[csv_data.sam_extract_code == '2']
                        update_delete_data = csv_data[(csv_data.sam_extract_code == '3') |
                                                      (csv_data.sam_extract_code == '1')]
                        for dataframe in [add_data, update_delete_data]:
                            del dataframe["sam_extract_code"]

                        if not add_data.empty:
                            try:
                                logger.info("Attempting to bulk load add data")
                                insert_dataframe(add_data, DUNS.__table__.name, sess.connection())
                            except IntegrityError:
                                logger.info("Bulk loading add data failed, loading add data by row")
                                sess.rollback()
                                models, activated_models = get_relevant_models(add_data, sess, benchmarks=benchmarks)
                                logger.info("Loading add data ({} rows)".format(len(add_data.index)))
                                load_duns_by_row(add_data, sess, models, activated_models, benchmarks=benchmarks)
                        if not update_delete_data.empty:
                            models, activated_models = get_relevant_models(update_delete_data, sess,
                                                                           benchmarks=benchmarks)
                            logger.info("Loading update_delete data ({} rows)".format(len(update_delete_data.index)))
                            load_duns_by_row(update_delete_data, sess, models, activated_models, benchmarks=benchmarks)
                    sess.commit()

            added_rows += nrows
            batch += 1
            logger.info('%s DUNS records inserted', added_rows)
        if benchmarks:
            logger.info("Parsing {} took {} seconds with {} rows".format(dat_file_name, time.time()-parse_start_time,
                                                                         added_rows))


def process_from_dir(root_dir, file_name, sess, local, sftp=None, monthly=False, benchmarks=False):
    file_path = os.path.join(root_dir, file_name)
    if not local:
        logger.info("Pulling {}".format(file_name))
        with open(file_path, "wb") as zip_file:
            sftp.getfo(''.join([REMOTE_SAM_DIR, '/', file_name]), zip_file)
    parse_sam_file(file_path, sess, monthly=monthly, benchmarks=benchmarks)
    if not local:
        os.remove(file_path)
