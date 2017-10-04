import os
import re
import logging
import math
import boto
import urllib.request
import zipfile
import numpy as np
import sys
import pandas as pd
from pandas.util.testing import assert_frame_equal
from sqlalchemy import func

from dataactcore.logging import configure_logging
from dataactcore.config import CONFIG_BROKER
from dataactcore.interfaces.db import GlobalDB
from dataactcore.models.jobModels import Submission # noqa
from dataactcore.models.userModel import User # noqa
from dataactcore.models.stagingModels import PublishedAwardFinancialAssistance
from dataactcore.models.domainModels import SubTierAgency, CountyCode, States, Zips, ZipCity, CityCode
from dataactvalidator.health_check import create_app
from dataactvalidator.scripts.loaderUtils import clean_data, insert_dataframe

logger = logging.getLogger(__name__)
errors = {}
progress = []


def parse_fabs_file(f, file_name):
    logger.info("starting file " + str(f.name))
    df1 = pd.read_csv(f.name, dtype=str, encoding="ISO-8859-1")
    df1['afa_generated_unique'] = df1.apply(lambda x: generate_unique_string(x), axis=1)
    df1.sort_values("uri", axis=0, ascending=True, inplace=True, kind='quicksort', na_position='last')
    df1['file_name'] = file_name
    return df1.set_index('afa_generated_unique')


def main():
    if len(sys.argv) < 2:
        logger.info('Not enough params passed')

    # first arg should be the directory name
    base_path = os.path.join(CONFIG_BROKER["path"], "dataactvalidator", "test", sys.argv[1])
    file_list = [f for f in os.listdir(base_path)]
    if '.DS_Store' in file_list:
        file_list.remove('.DS_Store')
    file_count = len(file_list)
    raw = []
    length = 0
    pos = 0
    for file in file_list:
        raw.append(parse_fabs_file(open(os.path.join(base_path, file)), file))
        logger.info(file + " has number of rows: " + str(len(raw[pos].index)))
        if length == 0:
            length = len(raw[pos].index)
        elif len(raw[pos].index) != length:
            logger.info(file + " has incorrect number of rows: " + str(len(raw[pos].index)))
            return

    # match that all share the indexes
    index_list = {}
    index_valid = []
    index_invalid = []
    for raw_file in raw:
        for index in raw_file.index:
            if index not in index_list:
                index_list[index] = 1
            else:
                index_list[index] +=1

    for index in index_list:
        if index_list[index] == file_count:
            index_valid.append(index)
        else:
            index_invalid.append(index)
    print('Identifiers not present in all files')
    print(index_invalid)

    # Get unique and shared columns
    shared_columns = []
    unique_columns = []
    all_columns = {}
    for raw_file in raw:
        for column in raw_file.columns:
            if column not in all_columns:
                all_columns[column] = 1
            else:
                all_columns[column] += 1

    for key in all_columns:
        if all_columns[key] == file_count:
            shared_columns.append(key)
        else:
            unique_columns.append(key)
    print("These columns are not present in all files")
    print(unique_columns)

    shared_columns.remove('file_name')

    for pos, index in enumerate(index_valid):
        if int((pos * 100)/length) %10 == 0:
            prog = int((pos * 100)/length)
            if prog not in progress:
                progress.append(prog)
                logger.info("You are "+ str(prog) +"% done")
        # use the first row as base
        base_row = raw[0].loc[index, :]
        for file_num, raw_file in enumerate(raw):
            # first file is base so dont need to check
            if file_num != 0:
                # get the compare row

                row = raw_file.loc[index, :]
                for column in shared_columns:
                    val1 = clean_value(base_row[column], column, base_row['file_name'])
                    val2 = clean_value(row[column], column, row['file_name'])
                    if val1 != val2:
                        # logger.info(column + ' does not match: ' + clean_value(base_row[column]) +" | "+clean_value(row[column]))
                        msg = column + ' does not match: ' + base_row['file_name'] + ":"+ val1 + " | " + row['file_name'] + ":"+ val2
                        if msg not in errors:
                            errors[msg] = 1
                        else:
                            errors[msg] += 1

    for error in errors:
        # return
        print(error + " occured " + str(errors[error]) + " times")
        val = 0

    logger.info("Comparison is complete")


def clean_value(val, col, fn):
    if type(val) == float and math.isnan(val):
        return ''
    val = str(val)
    # if re.match('-*[0-9]*\.[0-9]*$', val):
    #     return val.strip('0').strip('.')
    return val.strip().replace('-', '').strip('0').strip('.').strip('0').strip().lower()

def generate_unique_string(row):

    # create unique string from the awarding_sub_tier_agency_c, award_modification_amendme, fain, and uri
    astac = row['awardingsubtieragencycode'] if row['awardingsubtieragencycode'] is not None else '-none-'
    ama = row['awardmodificationamendmentnumber'] if row['awardmodificationamendmentnumber'] is not None else '-none-'
    fain = row['fain'] if row['fain'] is not None else '-none-'
    uri = row['uri'] if row['uri'] is not None else '-none-'

    if type(astac) == float and math.isnan(astac):
        astac = "-none-"
    if type(ama) == float and math.isnan(ama):
        ama = "-none-"
    if type(fain) == float and math.isnan(fain):
        fain = "-none-"
    if type(uri) == float and math.isnan(uri):
        uri = "-none-"
    return ama + "___" + astac + "___" + fain + "___" + uri


if __name__ == '__main__':
    configure_logging()
    with create_app().app_context():
        main()
