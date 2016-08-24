import os
import pandas as pd
import boto
import glob
from dataactvalidator.filestreaming.loaderUtils import LoaderUtils
from dataactvalidator.interfaces.validatorValidationInterface import ValidatorValidationInterface
from dataactcore.models.domainModels import CGAC,ObjectClass,ProgramActivity,SF133
from dataactcore.config import CONFIG_BROKER
from dataactvalidator.filestreaming.csvS3Reader import CsvS3Reader
from sqlalchemy import and_


def loadCgac(filename):
    interface = ValidatorValidationInterface()
    model = CGAC

    # for CGAC, delete and replace values
    interface.session.query(model).delete()
    interface.session.commit()

    # read CGAC values from csv
    data = pd.read_csv(filename, dtype=str)
    # toss out rows with missing CGAC codes
    data = data[data['CGAC'].notnull()]
    # clean data
    data = LoaderUtils.cleanData(
        data,
        model,
        {"cgac": "cgac_code", "agency": "agency_name"},
        {"cgac_code": {"pad_to_length": 3}}
    )
    # de-dupe
    data.drop_duplicates(subset=['cgac_code'], inplace=True)
    # Fix up cells that have spaces instead of being empty.
    # Set the truly empty cells to None so they get inserted to db as NULL
    # TODO: very ugly function below...is there a better way?
    data = data.applymap(lambda x: str(x).strip() if len(str(x).strip()) else None)
    # insert to db
    LoaderUtils.insertDataframe(data, model.__table__.name, interface.engine)


def loadObjectClass(filename):
    interface = ValidatorValidationInterface()
    model = ObjectClass

    # for object class, delete and replace values
    interface.session.query(model).delete()
    interface.session.commit()

    data = pd.read_csv(filename, dtype=str)
    # toss out blank rows
    data.dropna(inplace=True)
    data = LoaderUtils.cleanData(
        data,
        model,
        {"max_oc_code":"object_class_code",
         "max_object_class_name": "object_class_name"},
        {}
    )
    # de-dupe
    data.drop_duplicates(subset=['object_class_code'], inplace=True)
    # TODO: very ugly function below...is there a better way?
    data = data.applymap(lambda x: str(x).strip() if len(str(x).strip()) else None)
    # insert to db
    LoaderUtils.insertDataframe(data, model.__table__.name, interface.engine)


def loadProgramActivity(filename):
    interface = ValidatorValidationInterface()
    model = ProgramActivity

    # for program activity, delete and replace values??
    interface.session.query(model).delete()
    interface.session.commit()

    data = pd.read_csv(filename, dtype=str)
    data = LoaderUtils.cleanData(
        data,
        model,
        {"year": "budget_year",
         "agency_id": "agency_id",
         "alloc_id": "allocation_transfer_id",
         "account": "account_number",
         "pa_code": "program_activity_code",
         "pa_name": "program_activity_name"},
        {"program_activity_code": {"pad_to_length": 4},
         "agency_id": {"pad_to_length": 3},
         "account_number": {"pad_to_length": 4},
         "allocation_transfer_id": {"pad_to_length": 3}}
    )
    # because we're only loading a subset of program activity info,
    # there will be duplicate records in the dataframe. this is ok,
    # but need to de-duped before the db load.
    data.drop_duplicates(inplace=True)
    # TODO: very ugly function below...is there a better way?
    data = data.applymap(lambda x: str(x).strip() if len(str(x).strip()) else None)
    # insert to db
    LoaderUtils.insertDataframe(data, model.__table__.name, interface.engine)


def loadSF133(filename, fiscal_year, fiscal_period, force_load=False):
    interface = ValidatorValidationInterface()
    model = SF133

    existing_records = interface.session.query(model).filter(
        and_(model.fiscal_year == fiscal_year, model.period == fiscal_period))
    if force_load:
        # force a reload of this period's current data
        print('Force SF 133 load: deleting existing records for {} {}'.format(
            fiscal_year, fiscal_period))
        existing_records.delete()
        interface.session.commit()
    elif existing_records.count():
        # if there's existing data & we're not forcing a load, skip
        print('SF133 {} {} already in database ({} records). Skipping file.'.format(
            fiscal_year, fiscal_period, existing_records.count()))
        return

    data = pd.read_csv(filename, dtype=str, keep_default_na=False)
    data = LoaderUtils.cleanData(
        data,
        model,
        {"ata": "allocation_transfer_agency",
         "aid": "agency_identifier",
         "availability_type_code": "availability_type_code",
         "bpoa": "beginning_period_of_availa",
         "epoa": "ending_period_of_availabil",
         "main_account": "main_account_code",
         "sub_account": "sub_account_code",
         "fiscal_year": "fiscal_year",
         "period": "period",
         "line_num": "line",
         "amount_summed":
        "amount"},
        {"allocation_transfer_agency": {"pad_to_length": 3},
         "agency_identifier": {"pad_to_length": 3},
         "main_account_code": {"pad_to_length": 4},
         "sub_account_code": {"pad_to_length": 3},
         "amount": {"strip_commas": True}}
    )

    # todo: find out how to handle dup rows (e.g., same tas/period/line number)
    # line numbers 2002 and 2012 are the only duped SF 133 report line numbers,
    # and they are not used by the validation rules, so for now
    # just remove them before loading our SF-133 table
    dupe_line_numbers = ['2002', '2102']
    data = data[~data.line.isin(dupe_line_numbers)]

    # add concatenated TAS field for internal use (i.e., joining to staging tables)
    data['tas'] = data.apply(lambda row: formatInternalTas(row), axis=1)

    # zero out line numbers not supplied in the file
    pivot_idx = ['created_at', 'updated_at', 'agency_identifier', 'allocation_transfer_agency',
                 'availability_type_code', 'beginning_period_of_availa', 'ending_period_of_availabil',
                 'main_account_code', 'sub_account_code', 'tas', 'fiscal_year', 'period']
    data.amount = data.amount.astype(float)  # this line triggers the settingwithcopy warning
    data = pd.pivot_table(data, values='amount', index=pivot_idx, columns=['line'], fill_value=0).reset_index()
    data = pd.melt(data, id_vars=pivot_idx, value_name='amount')

    # Now that we've added zero lines for EVERY tas and SF 133 line number, get rid of the ones
    # we don't actually use in the validations. Arguably, it would be better just to include
    # everything, but that drastically increases the number of records we're inserting to the
    # sf_133 table. If we ever decide that we need *all* SF 133 lines that are zero value,
    # uncomment the next line.
    sf_133_validation_lines = ['1910',	'1000',	'1160',	'1180',	'1260',
                               '1280',	'1540',	'1640',	'1340',	'1440',	'1750',
                               '1850',	'1032',	'1033',	'1022',	'1030',	'1029',
                               '1025',	'1021',	'1040',	'1026',	'1010',	'1024',
                               '1020',	'1011',	'1041',	'1013',	'1012',	'1031',
                               '1042',	'1023',	'3020',	'2940',	'2190',	'2500',
                               '1021',	'1033',	'4801',	'4802',	'4881',	'4882',
                               '4901',	'4902',	'4908',	'4981',	'4982']
    data = data[(data.line.isin(sf_133_validation_lines)) | (data.amount != 0)]

    # TODO: very ugly function below...is there a better way?
    data = data.applymap(lambda x: str(x).strip() if len(str(x).strip()) else None)
    # insert to db
    LoaderUtils.insertDataframe(data, model.__table__.name, interface.engine)


def formatInternalTas(row):
    """Concatenate TAS components into a single field for internal use."""
    # This formatting should match formatting in dataactcore.models.stagingModels concatTas
    tas = '{}{}{}{}{}{}{}'.format(
        row['allocation_transfer_agency'] if row['allocation_transfer_agency'] else '000',
        row['agency_identifier'] if row['agency_identifier'] else '000',
        row['beginning_period_of_availa'] if row['beginning_period_of_availa'].strip() else '0000',
        row['ending_period_of_availabil'] if row['ending_period_of_availabil'].strip() else '0000',
        row['availability_type_code'].strip() if row['availability_type_code'].strip() else ' ',
        row['main_account_code'] if row['main_account_code'] else '0000',
        row['sub_account_code'] if row['sub_account_code'] else '000')
    return tas


def loadDomainValues(basePath, localSFPath = None, localProgramActivity = None):
    """Load all domain value files, localSFPath is used to point to a SF-133 file, if not provided it will be downloaded from S3."""
    print("Loading CGAC")
    loadCgac(os.path.join(basePath,"cgac.csv"))
    print("Loading object class")
    loadObjectClass(os.path.join(basePath,"object_class.csv"))
    print("Loading program activity")
    if localProgramActivity is not None:
        loadProgramActivity(localProgramActivity)
    else:
        loadProgramActivity(os.path.join(basePath, "program_activity.csv"))

    if localSFPath is not None:
        print("Loading local SF-133")
        # get list of SF 133 files in the specified local directory
        sf133Files = glob.glob(os.path.join(localSFPath, 'sf_133*.csv'))
        for sf133 in sf133Files:
            file = os.path.basename(sf133).replace('.csv', '')
            fileParts = file.split('_')
            if len(fileParts) < 4:
                print('{}Skipping SF 133 file with invalid name: {}'.format(
                    os.linesep, sf133))
                continue
            year = file.split('_')[-2]
            period = file.split('_')[-1]
            print('{}Starting {}...'.format(os.linesep, sf133))
            loadSF133(sf133, year, period)
    else:
        print("Loading SF-133")
        reader = CsvS3Reader()
        if(CONFIG_BROKER["use_aws"]):
            # get list of SF 133 files in the config bucket on S3
            s3connection = boto.s3.connect_to_region(CONFIG_BROKER['aws_region'])
            s3bucket = s3connection.lookup(CONFIG_BROKER['aws_bucket'])
            # get bucketlistresultset with all sf_133 files
            sf133Files = s3bucket.list(
                prefix='{}/sf_133'.format(CONFIG_BROKER['sf_133_folder']))
            for sf133 in sf133Files:
                file = sf133.name.split(
                    CONFIG_BROKER['sf_133_folder'])[-1].replace('.csv', '')
                fileParts = file.split('_')
                if len(fileParts) < 4:
                    print('{}Skipping SF 133 file with invalid name: {}'.format(
                        os.linesep, sf133))
                    continue
                year = file.split('_')[-2]
                period = file.split('_')[-1]
                print('{}Starting {}...'.format(os.linesep,sf133.name))
                loadSF133(sf133, year, period)

if __name__ == '__main__':
    loadDomainValues(
        os.path.join(CONFIG_BROKER["path"], "dataactvalidator", "config"))
