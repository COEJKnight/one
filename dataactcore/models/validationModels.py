""" These classes define the ORM models to be used by sqlalchemy for the job tracker database """

from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from dataactcore.utils.timeStampMixin import TimeStampBase

Base = declarative_base(cls=TimeStampBase)

class FileType(Base):
    __tablename__ = "file_type"

    file_id = Column(Integer, primary_key=True)
    name = Column(Text)
    description = Column(Text)

class FieldType(Base):
    __tablename__ = "field_type"

    field_type_id = Column(Integer, primary_key=True)
    name = Column(Text)
    description = Column(Text)

    TYPE_DICT = None

class RuleType(Base):
    __tablename__ = "rule_type"

    rule_type_id = Column(Integer, primary_key=True)
    name = Column(Text)
    description = Column(Text)

    TYPE_DICT = None

class FileColumn(Base):
    __tablename__ = "file_columns"

    file_column_id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("file_type.file_id"), nullable=True)
    file = relationship("FileType", uselist=False)
    field_types_id = Column(Integer, ForeignKey("field_type.field_type_id"), nullable=True)
    field_type = relationship("FieldType", uselist=False)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    required = Column(Boolean, nullable=True)
    rules = relationship("Rule", cascade = "delete, delete-orphan")

class Rule(Base):
    __tablename__ = "rule"
    rule_id = Column(Integer, primary_key=True)
    file_column_id = Column(Integer, ForeignKey("file_columns.file_column_id"), nullable=True)
    rule_type_id  = Column(Integer, ForeignKey("rule_type.rule_type_id"), nullable=True)
    rule_text_1 = Column(Text, nullable=True)
    rule_text_2 = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    rule_type = relationship("RuleType", uselist=False)
    file_column = relationship("FileColumn", uselist=False)
    rule_timing_id = Column(Integer, ForeignKey("rule_timing.rule_timing_id", name="fk_rule_timing_id"), nullable=False, default=1)
    rule_timing = relationship("RuleTiming", uselist=False)
    rule_label = Column(Text)
    file_id = Column(Integer, ForeignKey("file_type.file_id"), nullable=True)
    file_type = relationship(
        "FileType", foreign_keys="Rule.file_id", uselist=False)
    target_file_id = Column(Integer, ForeignKey(
        "file_type.file_id", name="fk_target_file_id"), nullable=True)
    target_file_type = relationship(
        "FileType", foreign_keys="Rule.target_file_id", uselist=False)

class RuleTiming(Base):
    __tablename__ = "rule_timing"
    rule_timing_id = Column(Integer, primary_key=True)
    name = Column(Text,nullable=False)
    description = Column(Text, nullable=False)

    TIMING_DICT = None

class TASLookup(Base) :
    __tablename__ = "tas_lookup"
    tas_id = Column(Integer, primary_key=True)
    allocation_transfer_agency = Column(Text, nullable=True, index=True)
    agency_identifier = Column(Text, nullable=True, index=True)
    beginning_period_of_availability = Column(Text, nullable=True, index=True)
    ending_period_of_availability = Column(Text, nullable=True, index=True)
    availability_type_code = Column(Text, nullable=True, index=True)
    main_account_code = Column(Text, nullable=True, index=True)
    sub_account_code = Column(Text, nullable=True, index=True)
