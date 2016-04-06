import os
from flask import session ,request
from datetime import datetime, timedelta
from werkzeug import secure_filename
from sqlalchemy.orm.exc import NoResultFound,MultipleResultsFound
from dataactcore.aws.s3UrlHandler import s3UrlHandler
from dataactcore.utils.requestDictionary import RequestDictionary
from dataactcore.utils.jsonResponse import JsonResponse
from dataactcore.utils.statusCode import StatusCode
from dataactcore.utils.responseException import ResponseException
from dataactcore.config import CONFIG_BROKER
from dataactbroker.handlers.managerProxy import ManagerProxy
from dataactbroker.handlers.interfaceHolder import InterfaceHolder
from dataactbroker.handlers.aws.session import LoginSession

class FileHandler:
    """ Responsible for all tasks relating to file upload

    Static fields:
    FILE_TYPES -- list of file labels that can be included

    Instance fields:
    request -- A flask request object, comes with the request
    s3manager -- instance of s3UrlHandler, manages calls to S3
    """

    FILE_TYPES = ["appropriations","award_financial","award","program_activity"]
    VALIDATOR_RESPONSE_FILE = "validatorResponse"

    def __init__(self,request,interfaces = None,isLocal= False,serverPath =""):
        """

        Arguments:
        request - HTTP request object for this route
        """
        self.request = request
        if(interfaces != None):
            self.interfaces = interfaces
            self.jobManager = interfaces.jobDb
        self.isLocal = isLocal
        self.serverPath = serverPath

    def addInterfaces(self,interfaces):
        self.interfaces = interfaces
        self.jobManager = interfaces.jobDb

    def getErrorReportURLsForSubmission(self):
        """
        Gets the Signed URLs for download based on the submissionId
        """
        try :
            self.s3manager = s3UrlHandler(CONFIG_BROKER["aws_bucket"])
            safeDictionary = RequestDictionary(self.request)
            submissionId = safeDictionary.getValue("submission_id")
            responseDict ={}
            for jobId in self.jobManager.getJobsBySubmission(submissionId):
                if(self.jobManager.getJobType(jobId) == "csv_record_validation"):
                    if(not self.isLocal):
                        responseDict["job_"+str(jobId)+"_error_url"] = self.s3manager.getSignedUrl("errors",self.jobManager.getReportPath(jobId),"GET")
                    else:
                        path = os.path.join(self.serverPath, self.jobManager.getReportPath(jobId))
                        responseDict["job_"+str(jobId)+"_error_url"] = path
            return JsonResponse.create(StatusCode.OK,responseDict)
        except ResponseException as e:
            return JsonResponse.error(e,StatusCode.CLIENT_ERROR)
        except Exception as e:
            # Unexpected exception, this is a 500 server error
            return JsonResponse.error(e,StatusCode.INTERNAL_ERROR)


    # Submit set of files
    def submit(self,name,CreateCredentials):
        """ Builds S3 URLs for a set of files and adds all related jobs to job tracker database

        Flask request should include keys from FILE_TYPES class variable above

        Arguments:
        name -- User ID from the session handler

        Returns:
        Flask response returned will have key_url and key_id for each key in the request
        key_url is the S3 URL for uploading
        key_id is the job id to be passed to the finalize_submission route
        """
        try:
            responseDict= {}
            fileNameMap = []
            safeDictionary = RequestDictionary(self.request)
            for fileType in FileHandler.FILE_TYPES :
                filename = safeDictionary.getValue(fileType)
                if( safeDictionary.exists(fileType)) :
                    if(not self.isLocal):
                        uploadName =  str(name)+"/"+s3UrlHandler.getTimestampedFilename(filename)
                    else:
                        uploadName = filename
                    responseDict[fileType+"_key"] = uploadName
                    fileNameMap.append((fileType,uploadName,filename))

            fileJobDict = self.jobManager.createJobs(fileNameMap,name)
            for fileType in fileJobDict.keys():
                if (not "submission_id" in fileType) :
                    responseDict[fileType+"_id"] = fileJobDict[fileType]
            if(CreateCredentials and not self.isLocal) :
                self.s3manager = s3UrlHandler(CONFIG_BROKER["aws_bucket"])
                responseDict["credentials"] = self.s3manager.getTemporaryCredentials(name)
            else :
                responseDict["credentials"] ={"AccessKeyId" : "local","SecretAccessKey" :"local","SessionToken":"local" ,"Expiration" :"local"}

            responseDict["submission_id"] = fileJobDict["submission_id"]
            if self.isLocal:
                responseDict["bucket_name"] = CONFIG_BROKER["broker_files"]
            else:
                responseDict["bucket_name"] = CONFIG_BROKER["aws_bucket"]
            return JsonResponse.create(StatusCode.OK,responseDict)
        except (ValueError , TypeError, NotImplementedError) as e:
            return JsonResponse.error(e,StatusCode.CLIENT_ERROR)
        except Exception as e:
            # Unexpected exception, this is a 500 server error
            return JsonResponse.error(e,StatusCode.INTERNAL_ERROR)
        except:
            return JsonResponse.error(Exception("Failed to catch exception"),StatusCode.INTERNAL_ERROR)

    def finalize(self):
        """ Set upload job in job tracker database to finished, allowing dependent jobs to be started

        Flask request should include key "upload_id", which holds the job_id for the file_upload job

        Returns:
        A flask response object, if successful just contains key "success" with value True, otherwise value is False
        """
        responseDict = {}
        try:
            inputDictionary = RequestDictionary(self.request)
            jobId = inputDictionary.getValue("upload_id")
            # Compare user ID with user who submitted job, if no match return 400
            job = self.jobManager.getJobById(jobId)
            submission = self.jobManager.getSubmissionForJob(job)
            if(submission.user_id != LoginSession.getName(session)):
                # This user cannot finalize this job
                raise ResponseException("Cannot finalize a job created by a different user", StatusCode.CLIENT_ERROR)
            # Change job status to finished
            if(self.jobManager.checkUploadType(jobId)):
                self.jobManager.changeToFinished(jobId)
                responseDict["success"] = True
                return JsonResponse.create(StatusCode.OK,responseDict)
            else:
                raise ResponseException("Wrong job type for finalize route",StatusCode.CLIENT_ERROR)

        except ( ValueError , TypeError ) as e:
            return JsonResponse.error(e,StatusCode.CLIENT_ERROR)
        except ResponseException as e:
            return JsonResponse.error(e,e.status)
        except Exception as e:
            # Unexpected exception, this is a 500 server error
            return JsonResponse.error(e,StatusCode.INTERNAL_ERROR)

    def getStatus(self):
        """ Get description and status of all jobs in the submission specified in request object

        Returns:
            A flask response object to be sent back to client, holds a JSON where each job ID has a dictionary holding file_type, job_type, status, and filename
        """
        try:
            inputDictionary = RequestDictionary(self.request)

            submissionId = inputDictionary.getValue("submission_id")
            # Get jobs in this submission

            jobs = self.jobManager.getJobsBySubmission(submissionId)

            # Build dictionary of submission info with info about each job
            submissionInfo = {}
            for job in jobs:
                jobInfo = {}
                if(self.jobManager.getJobType(job) != "csv_record_validation"):
                    continue
                jobInfo["job_status"] = self.jobManager.getJobStatus(job)
                jobInfo["job_type"] = self.jobManager.getJobType(job)
                jobInfo["filename"] = self.jobManager.getOriginalFilenameById(job)
                try:
                    jobInfo["file_status"] = self.interfaces.errorDb.getStatusLabelByJobId(job)
                except ResponseException as e:
                    # Job ID not in error database, probably did not make it to validation, or has not yet been validated
                    jobInfo["file_status"] = ""
                    jobInfo["missing_headers"] = ""
                else:
                    # If job ID was found in file_status, we should be able to get header error lists
                    missingHeaderString = self.interfaces.errorDb.getMissingHeadersByJobId(job)
                    if missingHeaderString is not None:
                        jobInfo["missing_headers"] = missingHeaderString.split(",")
                        for i in range(0,len(jobInfo["missing_headers"])):
                            jobInfo["missing_headers"][i] = jobInfo["missing_headers"][i].strip()
                    else:
                        jobInfo["missing_headers"] = []
                    duplicatedHeaderString = self.interfaces.errorDb.getDuplicatedHeadersByJobId(job)
                    if duplicatedHeaderString is not None:
                        jobInfo["duplicated_headers"] = duplicatedHeaderString.split(",")
                        for i in range(0,len(jobInfo["duplicated_headers"])):
                            jobInfo["duplicated_headers"][i] = jobInfo["duplicated_headers"][i].strip()
                    else:
                        jobInfo["duplicated_headers"] = []
                try :
                    jobInfo["file_type"] = self.jobManager.getFileType(job)
                except Exception as e:
                    jobInfo["file_type"]  = ''
                submissionInfo[job] = jobInfo

            # Build response object holding dictionary
            return JsonResponse.create(StatusCode.OK,submissionInfo)
        except ResponseException as e:
            return JsonResponse.error(e,e.status)
        except Exception as e:
            # Unexpected exception, this is a 500 server error
            return JsonResponse.error(e,StatusCode.INTERNAL_ERROR)

    def getErrorMetrics(self) :
        """ Returns an Http response object containing error information for every validation job in specified submission """
        responseDict = {}
        returnDict = {}
        try:
            safeDictionary = RequestDictionary(self.request)
            submission_id =  safeDictionary.getValue("submission_id")
            jobIds = self.jobManager.getJobsBySubmission(submission_id)
            for currentId in jobIds :
                if(self.jobManager.getJobType(currentId) == "csv_record_validation"):
                    fileName = self.jobManager.getFileType(currentId)
                    dataList = self.interfaces.errorDb.getErrorMetricsByJobId(currentId)
                    returnDict[fileName]  = dataList
            return JsonResponse.create(StatusCode.OK,returnDict)
        except ( ValueError , TypeError ) as e:
            return JsonResponse.error(e,StatusCode.CLIENT_ERROR)
        except ResponseException as e:
            return JsonResponse.error(e,e.status)
        except Exception as e:
            # Unexpected exception, this is a 500 server error
            return JsonResponse.error(e,StatusCode.INTERNAL_ERROR)
    def uploadFile(self):
        """saves a file and returns the saved path"""
        try:
            if(self.isLocal):
                uploadedFile = request.files['file']
                if(uploadedFile):
                    seconds = int((datetime.utcnow()-datetime(1970,1,1)).total_seconds())
                    filename = "".join([str(seconds),"_", secure_filename(uploadedFile.filename)])
                    path = os.path.join(self.serverPath, filename)
                    uploadedFile.save(path)
                    returnDict = {"path":path}
                    return JsonResponse.create(StatusCode.OK,returnDict)
                else:
                    exc = ResponseException("Failure to read file", StatusCode.CLIENT_ERROR)
                    return JsonResponse.error(exc,exc.status)
            else :
                exc = ResponseException("Route Only Valid For Local Installs", StatusCode.CLIENT_ERROR)
                return JsonResponse.error(exc,exc.status)
        except ( ValueError , TypeError ) as e:
            return JsonResponse.error(e,StatusCode.CLIENT_ERROR)
        except ResponseException as e:
            return JsonResponse.error(e,e.status)
        except Exception as e:
            # Unexpected exception, this is a 500 server error
            return JsonResponse.error(e,StatusCode.INTERNAL_ERROR)
