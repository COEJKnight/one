from dataactvalidator.interfaces.errorInterface import ErrorInterface
from dataactvalidator.interfaces.jobTrackerInterface import JobTrackerInterface
from dataactvalidator.interfaces.stagingInterface import StagingInterface
from dataactvalidator.interfaces.validationInterface import ValidationInterface

class InterfaceHolder:
    """ This class holds an interface to each database, to allow reuse of connections throughout one thread """

    def __init__(self):
        """ Create the interfaces """
        self.jobDb = JobTrackerInterface()
        self.errorDb = ErrorInterface()
        self.stagingDb = StagingInterface()
        self.validationDb = ValidationInterface()

    def close(self):
        """ Close all open connections """
        InterfaceHolder.closeOne(self.jobDb)
        InterfaceHolder.closeOne(self.errorDb)
        InterfaceHolder.closeOne(self.stagingDb)
        InterfaceHolder.closeOne(self.validationDb)

    @staticmethod
    def closeOne(interface):
        """ Close all aspects of one interface """
        if(interface == None):
            # No need to close a nonexistent connection
            return

        # Try to close the session and connection, on error try a rollback
        try:
            interface.session.close()
        except:
            try:
                interface.session.rollback()
                interface.session.close()
            except:
                pass