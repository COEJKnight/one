from dataactcore.models.errorModels import FileStatus, ErrorData
from dataactcore.models.errorInterface import ErrorInterface
from dataactvalidator.validation_handlers.validationError import ValidationError

class ValidatorErrorInterface(ErrorInterface):
    """ Manages communication with the error database """

    def __init__(self):
        """ Create empty row error dict """
        self.rowErrors = {}
        super(ValidatorErrorInterface, self).__init__()

    def writeFileError(self, jobId, filename, errorType, extraInfo = None):
        """ Write a file-level error to the file status table

        Args:
            jobId: ID of job in job tracker
            filename: name of error report in S3
            errorType: type of error, value will be mapped to ValidationError class

        Returns:
            True if successful
        """
        try:
            int(jobId)
        except:
            raise ValueError("".join(["Bad jobId: ",str(jobId)]))

        fileError = FileStatus(job_id = jobId, filename = filename, status_id = self.getStatusId(ValidationError.getErrorTypeString(errorType)))
        if(ValidationError.getErrorTypeString(errorType) == "missing_header_error"):
            fileError.headers_missing = extraInfo

        self.session.add(fileError)
        self.session.commit()
        return True

    def markFileComplete(self, jobId, filename):
        """ Marks file status as complete

        Args:
            jobId: ID of job in job tracker
            filename: name of error report in S3

        Returns:
            True if successful
        """

        fileComplete = FileStatus(job_id = jobId, filename = filename, status_id = self.getStatusId("complete"))
        self.session.add(fileComplete)
        self.session.commit()
        return True

    def recordRowError(self, jobId, filename, fieldName, errorType, row):
        """ Add this error to running sum of error types

        Args:
            jobId: ID of job in job tracker
            filename: name of error report in S3
            fieldName: name of field where error occurred
            errorType: type of error, value will be mapped to ValidationError class, for rule failures this will hold entire message

        Returns:
            True if successful
        """
        key = "".join([str(jobId),fieldName,str(errorType)])
        if(key in self.rowErrors):
            self.rowErrors[key]["numErrors"] += 1
        else:
            errorDict = {"filename":filename, "fieldName":fieldName, "jobId":jobId,"errorType":errorType,"numErrors":1, "firstRow":row}
            self.rowErrors[key] = errorDict

    def writeAllRowErrors(self, jobId):
        """ Writes all recorded errors to database

        Args:
            jobId: ID to write errors for

        Returns:
            True if successful
        """
        for key in self.rowErrors.keys():
            errorDict = self.rowErrors[key]
            # Set info for this error
            thisJob = errorDict["jobId"]
            if(int(jobId) != int(thisJob)):
                # This row is for a different job, skip it
                continue
            fieldName = errorDict["fieldName"]
            try:
                # If last part of key is an int, it's one of our prestored messages
                errorType = int(errorDict["errorType"])
            except ValueError:
                # For rule failures, it will hold the error message
                errorMsg = errorDict["errorType"]
                errorRow = ErrorData(job_id = thisJob, filename = errorDict["filename"], field_name = fieldName, rule_failed = errorMsg, occurrences = errorDict["numErrors"], first_row = errorDict["firstRow"])
            else:
                # This happens if cast to int was successful
                errorString = ValidationError.getErrorTypeString(errorType)
                errorId = self.getTypeId(errorString)
                # Create error data
                errorRow = ErrorData(job_id = thisJob, filename = errorDict["filename"], field_name = fieldName, error_type_id = errorId, occurrences = errorDict["numErrors"], first_row = errorDict["firstRow"])

            self.session.add(errorRow)

        # Commit the session to write all rows
        self.session.commit()
        # Clear the dictionary
        self.rowErrors = {}

    def writeMissingHeaders(self, jobId, missingHeaders):
        """ Write list of missing headers into headers_missing field

        Args:
            jobId: Job to write error for
            missingHeaders: List of missing headers

        """
        fileStatus = self.getFileStatusByJobId(jobId)
        # Create single string out of missing header list
        fileStatus.headers_missing = ", ".join(missingHeaders)
        self.session.commit()