from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy import Column, Date, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.orm import relationship

from dataactcore.models.baseModel import Base


def concat_tas(context):
    """Create a concatenated TAS string for insert into database."""
    tas1 = context.current_parameters['allocation_transfer_agency']
    tas1 = tas1 if tas1 else '000'
    tas2 = context.current_parameters['agency_identifier']
    tas2 = tas2 if tas2 else '000'
    tas3 = context.current_parameters['beginning_period_of_availa']
    tas3 = tas3 if tas3 else '0000'
    tas4 = context.current_parameters['ending_period_of_availabil']
    tas4 = tas4 if tas4 else '0000'
    tas5 = context.current_parameters['availability_type_code']
    tas5 = tas5 if tas5 else ' '
    tas6 = context.current_parameters['main_account_code']
    tas6 = tas6 if tas6 else '0000'
    tas7 = context.current_parameters['sub_account_code']
    tas7 = tas7 if tas7 else '000'
    tas = '{}{}{}{}{}{}{}'.format(tas1, tas2, tas3, tas4, tas5, tas6, tas7)
    return tas


TAS_COMPONENTS = (
    'allocation_transfer_agency', 'agency_identifier', 'beginning_period_of_availa', 'ending_period_of_availabil',
    'availability_type_code', 'main_account_code', 'sub_account_code'
)


class TASLookup(Base):
    """An entry of CARS history -- this TAS was present in the CARS file
    between internal_start_date and internal_end_date (potentially null)
    """
    __tablename__ = "tas_lookup"
    tas_id = Column(Integer, primary_key=True)
    account_num = Column(Integer, index=True, nullable=False)
    allocation_transfer_agency = Column(Text, nullable=True, index=True)
    agency_identifier = Column(Text, nullable=True, index=True)
    beginning_period_of_availa = Column(Text, nullable=True, index=True)
    ending_period_of_availabil = Column(Text, nullable=True, index=True)
    availability_type_code = Column(Text, nullable=True, index=True)
    main_account_code = Column(Text, nullable=True, index=True)
    sub_account_code = Column(Text, nullable=True, index=True)
    internal_start_date = Column(Date, nullable=False)
    internal_end_date = Column(Date, nullable=True)
    financial_indicator2 = Column(Text, nullable=True)

    def component_dict(self):
        """We'll often want to copy TAS component fields; this method returns
        a dictionary of field_name to value"""
        return {field_name: getattr(self, field_name) for field_name in TAS_COMPONENTS}

Index("ix_tas",
      TASLookup.allocation_transfer_agency,
      TASLookup.agency_identifier,
      TASLookup.beginning_period_of_availa,
      TASLookup.ending_period_of_availabil,
      TASLookup.availability_type_code,
      TASLookup.main_account_code,
      TASLookup.sub_account_code,
      TASLookup.internal_start_date,
      TASLookup.internal_end_date)


def is_not_distinct_from(left, right):
    """Postgres' IS NOT DISTINCT FROM is an equality check that accounts for
    NULLs. Unfortunately, it doesn't make use of indexes. Instead, we'll
    imitate it here"""
    return sa.or_(left == right, sa.and_(left.is_(None), right.is_(None)))


def matching_cars_subquery(sess, model_class, start_date, end_date):
    """We frequently need to mass-update records to look up their CARS history
    entry. This function creates a subquery to be used in that update call. We
    pass in the database session to avoid circular dependencies"""
    # Why min()?
    # Our data schema doesn't prevent two TAS history entries with the same
    # TAS components (ATA, AI, etc.) from being valid at the same time. When
    # that happens (unlikely), we select the minimum (i.e. older) of the
    # potential TAS history entries.
    subquery = sess.query(sa.func.min(TASLookup.account_num))

    # Filter to matching TAS components, accounting for NULLs
    for field_name in TAS_COMPONENTS:
        tas_col = getattr(TASLookup, field_name)
        model_col = getattr(model_class, field_name)
        subquery = subquery.filter(is_not_distinct_from(tas_col, model_col))

    day_after_end = end_date + timedelta(days=1)
    model_dates = sa.tuple_(start_date, end_date)
    tas_dates = sa.tuple_(TASLookup.internal_start_date, sa.func.coalesce(TASLookup.internal_end_date, day_after_end))
    subquery = subquery.filter(model_dates.op('OVERLAPS')(tas_dates))
    return subquery.as_scalar()


class CGAC(Base):
    __tablename__ = "cgac"
    cgac_id = Column(Integer, primary_key=True)
    cgac_code = Column(Text, nullable=False, index=True, unique=True)
    agency_name = Column(Text)


class SubTierAgency(Base):
    __tablename__ = "sub_tier_agency"
    sub_tier_agency_id = Column(Integer, primary_key=True)
    sub_tier_agency_code = Column(Text, nullable=False, index=True, unique=True)
    sub_tier_agency_name = Column(Text)
    cgac_id = Column(Integer, ForeignKey("cgac.cgac_id", name='fk_sub_tier_agency_cgac'), nullable=False)
    cgac = relationship('CGAC', foreign_keys='SubTierAgency.cgac_id')


class ObjectClass(Base):
    __tablename__ = "object_class"
    object_class_id = Column(Integer, primary_key=True)
    object_class_code = Column(Text, nullable=False, index=True, unique=True)
    object_class_name = Column(Text)


class SF133(Base):
    """Represents GTAS records"""
    __tablename__ = "sf_133"
    sf133_id = Column(Integer, primary_key=True)
    agency_identifier = Column(Text, nullable=False)
    allocation_transfer_agency = Column(Text)
    availability_type_code = Column(Text)
    beginning_period_of_availa = Column(Text)
    ending_period_of_availabil = Column(Text)
    main_account_code = Column(Text, nullable=False)
    sub_account_code = Column(Text, nullable=False)
    tas = Column(Text, nullable=False, default=concat_tas)
    fiscal_year = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)
    line = Column(Integer, nullable=False)
    amount = Column(Numeric, nullable=False, default=0, server_default="0")
    tas_id = Column(Integer, nullable=True)

Index("ix_sf_133_tas",
      SF133.tas,
      SF133.fiscal_year,
      SF133.period,
      SF133.line,
      unique=True)


class ProgramActivity(Base):
    __tablename__ = "program_activity"
    program_activity_id = Column(Integer, primary_key=True)
    budget_year = Column(Text, nullable=False)
    agency_id = Column(Text, nullable=False)
    allocation_transfer_id = Column(Text)
    account_number = Column(Text, nullable=False)
    program_activity_code = Column(Text, nullable=False)
    program_activity_name = Column(Text, nullable=False)

Index("ix_pa_tas_pa",
      ProgramActivity.budget_year,
      ProgramActivity.agency_id,
      ProgramActivity.allocation_transfer_id,
      ProgramActivity.account_number,
      ProgramActivity.program_activity_code,
      ProgramActivity.program_activity_name,
      unique=True)
