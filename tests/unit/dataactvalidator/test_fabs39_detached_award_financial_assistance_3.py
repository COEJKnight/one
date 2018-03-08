from tests.unit.dataactcore.factories.staging import DetachedAwardFinancialAssistanceFactory
from tests.unit.dataactvalidator.utils import number_of_errors, query_columns

_FILE = 'fabs39_detached_award_financial_assistance_3'


def test_column_headers(database):
    expected_subset = {"row_number", "record_type", "place_of_performance_code", "place_of_performance_zip4a"}
    actual = set(query_columns(_FILE, database))
    assert expected_subset == actual


def test_success(database):
    """ PrimaryPlaceofPerformanceZIP+4 should not be provided for any format of PrimaryPlaceOfPerformanceCode
        other than XX##### for record type 1 and 2. """

    # place_of_performance_code = None should technically be a failure based on the rule, but because it is
    # tested elsewhere we want to ignore it.
    det_award_1 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="NY12345",
                                                          place_of_performance_zip4a="1234", record_type=1)
    det_award_2 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="ny98765",
                                                          place_of_performance_zip4a="4312", record_type=1)
    det_award_3 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code=None,
                                                          place_of_performance_zip4a="4312", record_type=2)
    det_award_4 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="ny**987",
                                                          place_of_performance_zip4a=None, record_type=2)
    det_award_5 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="00*****",
                                                          place_of_performance_zip4a="", record_type=1)
    det_award_6 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="00*****",
                                                          place_of_performance_zip4a="abcde", record_type=3)
    errors = number_of_errors(_FILE, database, models=[det_award_1, det_award_2, det_award_3, det_award_4, det_award_5,
                                                       det_award_6])
    assert errors == 0


def test_failure(database):
    """ Test failure for PrimaryPlaceofPerformanceZIP+4 should not be provided for any format of
        PrimaryPlaceOfPerformanceCode other than XX##### for record type 1 and 2. """

    det_award_1 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="00FORGN",
                                                          place_of_performance_zip4a="1234", record_type=1)
    det_award_2 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="00*****",
                                                          place_of_performance_zip4a="4312", record_type=1)
    det_award_3 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="ny**987",
                                                          place_of_performance_zip4a="4312", record_type=2)
    errors = number_of_errors(_FILE, database, models=[det_award_1, det_award_2, det_award_3])
    assert errors == 3
