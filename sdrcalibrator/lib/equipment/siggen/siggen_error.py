""" Error class for the siggen """


class Signal_Generator_Error(Exception):
    def __init__(self, err_code=99, err_head="", err_body=""):
        self.err_code = err_code+300
        self.err_head = err_head
        self.err_body = err_body

        print("***")
        print(err_head), print(err_body)
        # Call the super function
        err = "Signal Generator error code: {}\r\n".format(self.err_code)
        err += "!!! {} !!!\r\n".format(self.err_head)
        err += "{}".format(self.err_body)
        super(Signal_Generator_Error, self).__init__(err)
