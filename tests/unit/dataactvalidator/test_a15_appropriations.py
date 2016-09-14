from dataactcore.models.stagingModels import Appropriation
from dataactcore.models.domainModels import SF133
from tests.unit.dataactvalidator.utils import number_of_errors


_FILE = 'a15_appropriations'
_TAS = 'a15_appropriations_tas'


def test_success(database):
    """ Tests that SF 133 amount sum for line 2490 matches Appropriation unobligated_balance_cpe
        for the specified fiscal year and period """
    tas = "".join([_TAS, "_success"])

    sf = SF133(line=2490, tas=tas, period=1, fiscal_year=2016, amount=1, agency_identifier="sys",
               main_account_code="000", sub_account_code="000")
    ap = Appropriation(job_id=1, row_number=1, tas=tas, unobligated_balance_cpe=1)

    assert number_of_errors(_FILE, database.stagingDb, models=[sf, ap]) == 0


def test_failure(database):
    """ Tests that SF 133 amount sum for line 2490 does not match Appropriation unobligated_balance_cpe
        for the specified fiscal year and period """
    tas = "".join([_TAS, "_failure"])

    sf = SF133(line=2490, tas=tas, period=1, fiscal_year=2016, amount=1, agency_identifier="sys",
               main_account_code="000", sub_account_code="000")
    ap = Appropriation(job_id=1, row_number=1, tas=tas, unobligated_balance_cpe=0)

    assert number_of_errors(_FILE, database.stagingDb, models=[sf, ap]) == 1
