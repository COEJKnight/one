from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, Column, Integer, Text, Numeric, Boolean
from dataactvalidator.interfaces.interfaceHolder import InterfaceHolder

class StagingTable(object):

    BATCH_INSERT = False
    INSERT_BY_ORM = True
    BATCH_SIZE = 100

    def __init__(self):
        # Start first batch
        self.batch = []
        self.interface = InterfaceHolder.STAGING

    def createTable(self, fileType, filename, jobId, tableName=None):
        """ Create staging table for new file
        Args:
        fileType -- type of file to create a table for (e.g. Award, AwardFinancial)

        Returns:
        tableName if created, exception otherwise
        """
        if(tableName==None):
            tableName = "job"+str(jobId)
        self.name = tableName

        if(self.interface.tableExists(tableName)):
            # Now an exception, could change the name here if desired
            raise ValueError("Table already exists")

        # Alternate way of naming tables
        #tableName = "data" + tableName.replace("/","").replace("\\","").replace(".","")
        # Write tableName to related job in job tracker

        jobTracker = InterfaceHolder.JOB_TRACKER
        jobTracker.addStagingTable(jobId,tableName)
        validationDB = InterfaceHolder.VALIDATION
        fields = validationDB.getFieldsByFile(fileType)

        """ Might not need sequence for ORM
        # Create sequence to be used for primary key
        sequenceName = tableName + "Serial"
        sequenceStatement = "CREATE SEQUENCE " + sequenceName + " START 1"
        try:
            self.runStatement(sequenceStatement)
        except ProgrammingError:
            # Sequence already exists
            pass
        """
        primaryAssigned = False
        # Create empty dict for field names and values
        classFieldDict = {"__tablename__":tableName}
        # Add each column
        for key in fields.iterkeys():
            # Build column statement for this key
            # Get correct type name
            fieldTypeName = fields[key].field_type.name
            if(fieldTypeName.lower() == "string"):
                fieldTypeName = Text
            elif(fieldTypeName.lower() == "int"):
                fieldTypeName = Integer
            elif(fieldTypeName.lower() == "decimal"):
                fieldTypeName = Numeric
            elif(fieldTypeName.lower() == "boolean"):
                fieldTypeName = Boolean
            else:
                raise ValueError("Bad field type")
            # Get extra parameters (primary key or not null)
            extraParam = ""
            if(fields[key].field_type.description == "PRIMARY_KEY"):
                classFieldDict[key.replace(" ","_")] = Column(fieldTypeName, primary_key=True)
                primaryAssigned = True
            elif(fields[key].required):
                classFieldDict[key.replace(" ","_")] = Column(fieldTypeName, nullable=False)
            else:
                classFieldDict[key.replace(" ","_")] = Column(fieldTypeName)


        if(not primaryAssigned):
            # If no primary key assigned, add one based on table name
            classFieldDict[tableName + "id"] = Column(Integer, primary_key = True)


        # Create ORM class based on dict
        self.orm = type(tableName,(declarative_base(),),classFieldDict)
        self.jobId = jobId

        # Create table
        self.orm.__table__.create(self.interface.engine)

    def endBatch(self):
        """ Called at end of process to send the last batch """
        if not self.BATCH_INSERT:
            # Not batching, just return
            return False
        if(len(self.batch)>0):
            self.interface.connection.execute(self.orm.__table__.insert(),self.batch)
            self.batch = []
            return True
        else:
            return False

    def insertList(self, data):
        """ Writes some number of validated records to staging database
        Args:
        data -- records to be written (array of dicts, each dict is a row)

        Returns:
        True if all rows were successful
        """

        success = True
        for row in data:
            if(not self.insert(row)):
                success = False
        return success

    def insert(self, record):
        """ Write single record to this table
        Args:
        record -- dict with column names as keys

        Returns:
        True if successful
        """

        if(self.BATCH_INSERT):
            if(self.INSERT_BY_ORM):
                raise NotImplementedError("Have not implemented ORM method for batch insert")
            else:
                self.batch.append(record)
                if(len(self.batch)>self.BATCH_SIZE):
                    # Time to write the batch
                    self.interface.connection.execute(self.orm.__table__.insert(),self.batch)
                    # Reset batch
                    self.batch = []
                return True
        else:
            if(self.INSERT_BY_ORM):
                try:
                    recordOrm = self.orm()
                except:
                    # createTable was not called
                    raise Exception("Must call createTable before writing")

                attributes = self.getPublicMembers(recordOrm)

                # For each field, add value to ORM object
                for key in record.iterkeys():
                    attr = key.replace(" ","_")
                    setattr(recordOrm,attr,record[key])

                self.interface.session.add(recordOrm)
                self.interface.session.commit()
                return True
            else:
                raise ValueError("Must do either batch or use ORM, cannot set both to False")

    @staticmethod
    def getPublicMembers(obj):
        response = []
        for member in dir(obj):
            if(member[0] != "_"):
                response.append(member)
        return response
