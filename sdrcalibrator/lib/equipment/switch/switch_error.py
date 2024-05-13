""" Error class for the switch """


class RF_Switch_Error(Exception):
    def __init__(self, err_code=99, err_head="", err_body=""):
        self.err_code = err_code+500
        self.err_head = err_head
        self.err_body = err_body

        # Call the super function
        err = "RF Switch error code: {}\r\n".format(self.err_code)
        err += "!!! {} !!!\r\n".format(self.err_head)
        err += "{}".format(self.err_body)
        super(RF_Switch_Error, self).__init__(err)
