from tests.unit.dataactcore.factories.staging import ObjectClassProgramActivityFactory
from tests.unit.dataactvalidator.utils import number_of_errors, query_columns
import copy

_FILE = 'b12_object_class_program_activity_1'


def test_column_headers(database):
    expected_subset = {'row_number', 'by_direct_reimbursable_fun'}
    actual = set(query_columns(_FILE, database))
    assert (actual & expected_subset) == expected_subset


def test_success(database):
    """ Test for USSGL 48XX & 49XX (except 487X & 497X) if any one is provided then
    by_direct_reimbursable_fun is not empty """

    op = ObjectClassProgramActivityFactory()
    assert number_of_errors(_FILE, database, models=[op]) == 0

    op = ObjectClassProgramActivityFactory(object_class=1234, by_direct_reimbursable_fun=None)
    assert number_of_errors(_FILE, database, models=[op]) == 0



def test_failure(database):
    """ Test for USSGL 48XX & 49XX (except 487X & 497X) if any one is provided and
    by_direct_reimbursable_fun is empty the rule fails """

    op_dict = {'by_direct_reimbursable_fun': None, 'object_class': 123, 'ussgl480100_undelivered_or_fyb': None,
               'ussgl480100_undelivered_or_cpe': None, 'ussgl483100_undelivered_or_cpe': None,
               'ussgl488100_upward_adjustm_cpe': None, 'ussgl490100_delivered_orde_fyb': None,
               'ussgl490100_delivered_orde_cpe': None, 'ussgl493100_delivered_orde_cpe': None,
               'ussgl498100_upward_adjustm_cpe': None, 'ussgl498100_upward_adjustm_cpe': None,
               'ussgl480200_undelivered_or_fyb': None, 'ussgl480200_undelivered_or_cpe': None,
               'ussgl483200_undelivered_or_cpe': None, 'ussgl488200_upward_adjustm_cpe': None,
               'ussgl490200_delivered_orde_cpe': None, 'ussgl490800_authority_outl_fyb': None,
               'ussgl490800_authority_outl_cpe': None, 'ussgl498200_upward_adjustm_cpe': None}

    keys = ['ussgl480100_undelivered_or_fyb', 'ussgl480100_undelivered_or_cpe', 'ussgl483100_undelivered_or_cpe',
            'ussgl488100_upward_adjustm_cpe', 'ussgl490100_delivered_orde_fyb', 'ussgl490100_delivered_orde_cpe',
            'ussgl493100_delivered_orde_cpe', 'ussgl498100_upward_adjustm_cpe', 'ussgl498100_upward_adjustm_cpe',
            'ussgl480200_undelivered_or_fyb', 'ussgl480200_undelivered_or_cpe', 'ussgl483200_undelivered_or_cpe',
            'ussgl488200_upward_adjustm_cpe', 'ussgl490200_delivered_orde_cpe', 'ussgl490800_authority_outl_fyb',
            'ussgl490800_authority_outl_cpe', 'ussgl498200_upward_adjustm_cpe']

    for i in range(len(keys)):
        op_dict_copy = copy.deepcopy(op_dict)
        op_dict_copy.pop(keys[i])
        op = ObjectClassProgramActivityFactory(**op_dict_copy)
        assert number_of_errors(_FILE, database, models=[op]) == 1

    op = ObjectClassProgramActivityFactory(by_direct_reimbursable_fun=None, object_class=123)
    assert number_of_errors(_FILE, database, models=[op]) == 1


