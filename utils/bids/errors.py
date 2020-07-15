### BIDS Exceptions
class BIDSException(Exception):
    status_code = 2

    default_msg = "There was an error with the BIDS operation"

    def __init__(self, msg=None, errors=None, log=False, log_msg=None):
        """Construct a BIDSException

        Arguments:
            msg (str): The optional message (otherwise default_msg will be used)
            errors (dict): An optional dictionary of additional error properties to include in the response
            log (bool): If True, the system will log the `msg` parameter as a warning
            log_msg (str): The optional log message override if the error message is not descriptive enough

        """
        if not msg:
            msg = self.default_msg
        super(BIDSException, self).__init__(msg)
        self.errors = errors

        # Always log if user sent a unique log message
        if log_msg:
            self.log = True
        else:
            self.log = log

        self.log_msg = log_msg if log_msg else msg


class BIDSImportError(BIDSException):
    status_code = 3

    default_msg = "There was an error with the BIDS import"


class BIDSExportError(BIDSException):
    status_code = 4

    default_msg = "There was an error with the BIDS export"


class BIDSCurationError(BIDSException):
    status_code = 5

    default_msg = "There was an error with the BIDS curation"
