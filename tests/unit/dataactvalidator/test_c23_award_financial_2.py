from random import choice
from string import ascii_uppercase, ascii_lowercase, digits
from tests.unit.dataactcore.factories.staging import AwardFinancialFactory, AwardProcurementFactory
from tests.unit.dataactvalidator.utils import number_of_errors, query_columns


_FILE = 'c23_award_financial_2'


def test_column_headers(database):
    expected_subset = {"row_number", "transaction_obligated_amou_sum", "federal_action_obligation_sum"}
    actual = set(query_columns(_FILE, database))
    assert expected_subset <= actual


def test_success(database):
    """ Test that a four digit object class with no flag is a success, and a three digit object class with
        a flag is a success. Only finds rows with matching piid AND parent_award_id from AwardFinancialFactory and
        doesn't care about rows with null parent_award_id in AwardFinancialFactory """
    # Create a 12 character random parent_award_id
    parent_award_id = ''.join(choice(ascii_uppercase + ascii_lowercase + digits) for _ in range(12))
    parent_award_id_two = ''.join(choice(ascii_uppercase + ascii_lowercase + digits) for _ in range(12))
    parent_award_id_three = ''.join(choice(ascii_uppercase + ascii_lowercase + digits) for _ in range(12))
    first_parent_award_id_row_one = AwardFinancialFactory(transaction_obligated_amou=1100, piid="1234",
                                                          parent_award_id=parent_award_id,
                                                          allocation_transfer_agency=None)
    first_parent_award_id_row_two = AwardFinancialFactory(transaction_obligated_amou=11, piid="1234",
                                                          parent_award_id=parent_award_id,
                                                          allocation_transfer_agency=None)
    first_parent_award_id_row_three = AwardFinancialFactory(transaction_obligated_amou=11, piid=None,
                                                            parent_award_id=parent_award_id,
                                                            allocation_transfer_agency=None)
    first_parent_award_id_row_four = AwardFinancialFactory(transaction_obligated_amou=11, piid='',
                                                           parent_award_id=parent_award_id,
                                                           allocation_transfer_agency=None)
    # And add a row for a different parent_award_id
    second_parent_award_id_row_one = AwardFinancialFactory(transaction_obligated_amou=9999, piid="1234",
                                                           parent_award_id=parent_award_id_two,
                                                           allocation_transfer_agency=None)
    third_parent_award_id_row_one = AwardFinancialFactory(transaction_obligated_amou=8888, piid="1234",
                                                          parent_award_id=parent_award_id_three,
                                                          allocation_transfer_agency=123)

    first_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id, piid="1234",
                                           federal_action_obligation=-1100)
    second_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id, piid="1234", federal_action_obligation=-10)
    third_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id, piid="1234", federal_action_obligation=-1)
    other_parent_award_id_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id_two, piid="1234",
                                                           federal_action_obligation=-9999)
    third_parent_award_id_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id_three, piid="1234",
                                                           federal_action_obligation=-9999)

    errors = number_of_errors(_FILE, database, models=[first_parent_award_id_row_one, first_parent_award_id_row_two,
                                                       first_parent_award_id_row_three, first_parent_award_id_row_four,
                                                       second_parent_award_id_row_one, first_ap_row, second_ap_row,
                                                       third_ap_row, other_parent_award_id_ap_row,
                                                       third_parent_award_id_row_one, third_parent_award_id_ap_row])
    assert errors == 0


def test_failure(database):
    """ Test that a three digit object class with no flag is an error. Only finds rows with matching piid AND
        parent_award_id from AwardFinancialFactory and doesn't care about rows with null parent_award_id in
        AwardFinancialFactory """
    # Create a 12 character random parent_award_id
    parent_award_id = ''.join(choice(ascii_uppercase + ascii_lowercase + digits) for _ in range(12))
    parent_award_id_two = ''.join(choice(ascii_uppercase + ascii_lowercase + digits) for _ in range(12))
    first_parent_award_id_row_one = AwardFinancialFactory(transaction_obligated_amou=1100, piid="1234",
                                                          parent_award_id=parent_award_id,
                                                          allocation_transfer_agency=None)
    first_parent_award_id_row_two = AwardFinancialFactory(transaction_obligated_amou=11, piid="1234",
                                                          parent_award_id=parent_award_id,
                                                          allocation_transfer_agency=None)
    first_parent_award_id_row_three = AwardFinancialFactory(transaction_obligated_amou=11, piid="1234",
                                                            parent_award_id=None,
                                                            allocation_transfer_agency=None)
    # And add a row that is wrong
    second_parent_award_id_row_one = AwardFinancialFactory(transaction_obligated_amou=9999, piid="1234",
                                                           parent_award_id=parent_award_id_two,
                                                           allocation_transfer_agency=None)
    first_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id, piid="1234",
                                           federal_action_obligation=-1100)
    second_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id, piid="1234", federal_action_obligation=-10)
    third_ap_row = AwardProcurementFactory(parent_award_id="1234", piid="1234", federal_action_obligation=-10)
    other_parent_award_id_ap_row = AwardProcurementFactory(parent_award_id=parent_award_id_two, piid="1234",
                                                           federal_action_obligation=-1111)

    errors = number_of_errors(_FILE, database, models=[first_parent_award_id_row_one, first_parent_award_id_row_two,
                                                       first_parent_award_id_row_three, second_parent_award_id_row_one,
                                                       first_ap_row, second_ap_row, third_ap_row,
                                                       other_parent_award_id_ap_row])
    assert errors == 2
