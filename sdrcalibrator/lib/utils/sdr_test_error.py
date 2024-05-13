""" Error class for SDR Test """


class SDR_Test_Error(Exception):
    def __init__(self, err_code=99, err_head="", err_body=""):
        self.err_code = err_code+100
        self.err_head = err_head
        self.err_body = err_body

        # Call the super function
        err = "SDR Test error code: {}\r\n".format(self.err_code)
        err += "!!! {} !!!\r\n".format(self.err_head)
        err += "{}".format(self.err_body)
        super(SDR_Test_Error, self).__init__(err)
