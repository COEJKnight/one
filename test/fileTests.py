import unittest
import requests
import json
from testUtils import TestUtils
from baseTest import BaseTest
class FileTests(BaseTest):
    """ Test file submission routes """
    fileResponse = None


    def call_file_submission(self):
        # If fileResponse doesn't exist, send the request
        fileJson = '{"appropriations":"test1.csv","award_financial":"test2.csv","award":"test3.csv","procurement":"test4.csv"}'
        if(self.fileResponse == None):
            self.utils.login()
            self.fileResponse = self.utils.postRequest("/v1/submit_files/",fileJson)

    def test_file_submission(self):
        self.call_file_submission()
        # Test that status is 200
        assert(self.fileResponse.status_code==200)
        # Test Content-Type header
        assert("Content-Type" in self.fileResponse.headers)
        assert(self.fileResponse.headers["Content-Type"]=="application/json")
        # Test message parts for urls
        assert("_test1.csv" in self.fileResponse.json()["appropriations_url"] )
        assert("_test2.csv" in self.fileResponse.json()["award_financial_url"])
        assert("_test3.csv" in self.fileResponse.json()["award_url"])
        assert("_test4.csv" in self.fileResponse.json()["procurement_url"])
        assert("?Signature" in self.fileResponse.json()["appropriations_url"] )
        assert("?Signature" in self.fileResponse.json()["award_financial_url"])
        assert("?Signature" in self.fileResponse.json()["award_url"])
        assert("?Signature" in self.fileResponse.json()["procurement_url"])
        assert("&AWSAccessKeyId" in self.fileResponse.json()["appropriations_url"] )
        assert("&AWSAccessKeyId" in self.fileResponse.json()["award_financial_url"])
        assert("&AWSAccessKeyId" in self.fileResponse.json()["award_url"])
        assert("&AWSAccessKeyId" in self.fileResponse.json()["procurement_url"])
        # Test that job ids are returned
        responseDict = self.fileResponse.json()
        idKeys = ["procurement_id", "award_id", "award_financial_id", "appropriations_id"]
        for key in idKeys:
            assert(key in responseDict)
            try:
                int(responseDict[key])
            except:
                self.fail("One of the job ids returned was not an integer")
            # Call upload complete route for each id
        self.check_upload_complete(responseDict["procurement_id"])

    def check_upload_complete(self, jobId):
        jobJson = json.dumps({"upload_id":jobId})
        self.utils.login()

        finalizeResponse = self.utils.postRequest("/v1/submit_files/",jobJson)

        if(finalizeResponse.status_code != 200):
            print(finalizeResponse.status_code)
            print(finalizeResponse.json()["errorType"])
            print(finalizeResponse.json()["message"])
            print(finalizeResponse.json()["trace"])
        assert(finalizeResponse.status_code == 200)

if __name__ == '__main__':
    unittest.main()
