""" Error class for the SDR """


class SDR_Error(Exception):
    def __init__(self, err_code=99, err_head="", err_body=""):
        self.err_code = err_code+200
        self.err_head = err_head
        self.err_body = err_body

        # Call the super function
        err = "SDR error code: {}\r\n".format(self.err_code)
        err += "!!! {} !!!\r\n".format(self.err_head)
        err += "{}".format(self.err_body)
        super(SDR_Error, self).__init__(err)

""" List of SDR Error Codes: 
    TODO: Fill out list of SDR error codes for consistency
"""