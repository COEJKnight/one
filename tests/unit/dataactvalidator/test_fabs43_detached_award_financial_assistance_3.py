from tests.unit.dataactcore.factories.staging import DetachedAwardFinancialAssistanceFactory
from tests.unit.dataactvalidator.utils import number_of_errors, query_columns
from dataactcore.models.domainModels import StateCongressional

_FILE = 'fabs43_detached_award_financial_assistance_3'


def test_column_headers(database):
    expected_subset = {"row_number", "place_of_performance_code", "place_of_performance_congr", "record_type"}
    actual = set(query_columns(_FILE, database))
    assert expected_subset == actual


def test_success(database):
    """ Test PrimaryPlaceOfPerformanceCongressionalDistrict exists in the state indicated by the
        PrimaryPlaceOfPerformanceCode or is 90 in a state with multiple districts or when PrimaryPlaceOfPerformanceCode
        is 00*****. PrimaryPlaceOfPerformanceCongressionalDistrict is null for record type 3 """
    state_congr_1 = StateCongressional(congressional_district_no="01", state_code="NY")
    state_congr_2 = StateCongressional(congressional_district_no="02", state_code="NY")
    det_award_1 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="NY12345",
                                                          place_of_performance_congr="01",
                                                          record_type=2)
    det_award_2 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="ny*****",
                                                          place_of_performance_congr="02",
                                                          record_type=1)
    det_award_3 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="Ny12345",
                                                          place_of_performance_congr="90",
                                                          record_type=2)
    det_award_4 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="00*****",
                                                          place_of_performance_congr="90",
                                                          record_type=1)
    det_award_5 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="NY12345",
                                                          place_of_performance_congr="",
                                                          record_type=2)
    det_award_6 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="Ny12345",
                                                          place_of_performance_congr='',
                                                          record_type=3)
    det_award_7 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="Ny12345",
                                                          place_of_performance_congr=None,
                                                          record_type=3)

    errors = number_of_errors(_FILE, database, models=[det_award_1, det_award_2, det_award_3, det_award_4, det_award_5,
                                                       det_award_6, det_award_7, state_congr_1, state_congr_2])
    assert errors == 0


def test_failure(database):
    """ Test failure PrimaryPlaceOfPerformanceCongressionalDistrict exists in the state indicated by the
        PrimaryPlaceOfPerformanceCode or is 90 in a state with multiple districts or when PrimaryPlaceOfPerformanceCode
        is 00*****. PrimaryPlaceOfPerformanceCongressionalDistrict is null for record type 3"""
    state_congr_1 = StateCongressional(congressional_district_no="01", state_code="NY")
    state_congr_2 = StateCongressional(congressional_district_no="02", state_code="NY")
    state_congr_3 = StateCongressional(congressional_district_no="01", state_code="PA")
    det_award_1 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="nY12345",
                                                          place_of_performance_congr="03",
                                                          record_type=2)
    det_award_2 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="PA12345",
                                                          place_of_performance_congr="02",
                                                          record_type=2)
    det_award_3 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="PA**345",
                                                          place_of_performance_congr="90",
                                                          record_type=2)
    det_award_4 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="00*****",
                                                          place_of_performance_congr="01",
                                                          record_type=1)
    det_award_5 = DetachedAwardFinancialAssistanceFactory(place_of_performance_code="NY12345",
                                                          place_of_performance_congr="02",
                                                          record_type=3)

    errors = number_of_errors(_FILE, database, models=[det_award_1, det_award_2, det_award_3, det_award_4, det_award_5,
                                                       state_congr_1, state_congr_2, state_congr_3])
    assert errors == 5
