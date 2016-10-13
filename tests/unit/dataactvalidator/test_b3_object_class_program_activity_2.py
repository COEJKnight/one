from tests.unit.dataactcore.factories.staging import ObjectClassProgramActivityFactory
from tests.unit.dataactvalidator.utils import number_of_errors, query_columns
from random import uniform, randint
from decimal import Decimal

_FILE = 'b3_object_class_program_activity_2'


def test_column_headers(database):
    expected_subset = {'row_number', "obligations_undelivered_or_cpe", "ussgl480100_undelivered_or_cpe",
	    "ussgl488100_upward_adjustm_cpe"}
    actual = set(query_columns(_FILE, database))
    assert (actual & expected_subset) == expected_subset


def test_success(database):
    """ Test that calculation passes with equal values and with a null """

    value_one = Decimal(randint(0,100000)) / Decimal(100)
    value_two = Decimal(randint(0,100000)) / Decimal(100)
    ocpa = ObjectClassProgramActivityFactory(obligations_undelivered_or_cpe = value_one+value_two,
                                             ussgl480100_undelivered_or_cpe = value_one,
                                             ussgl488100_upward_adjustm_cpe = value_two)
    ocpa_null = ObjectClassProgramActivityFactory(obligations_undelivered_or_cpe = value_one,
                                                  ussgl480100_undelivered_or_cpe = None,
                                                  ussgl488100_upward_adjustm_cpe = value_one)

    assert number_of_errors(_FILE, database, models=[ocpa, ocpa_null]) == 0

def test_failure(database):
    """ Test that calculation fails for unequal values """
    value = Decimal(randint(0,100000)) / Decimal(100)
    value2 = Decimal(randint(100001,200000)) / Decimal(100)
    ocpa = ObjectClassProgramActivityFactory(obligations_undelivered_or_cpe = value,
                                             ussgl480100_undelivered_or_cpe = value2,
                                             ussgl488100_upward_adjustm_cpe = value2)

    assert number_of_errors(_FILE, database, models=[ocpa]) == 1
