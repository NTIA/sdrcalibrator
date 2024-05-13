from __future__ import print_function
import sys

from io import open

class Logger:
    def __init__(self, quiet_mode=False, log_to_file=True):
        self.quiet_mode = quiet_mode
        self.log_to_file = log_to_file
        self.indent_level = 0
        self.beginning_of_line = True
        self.log_buffer = ""
        self.log_file_name = False

    # Handle quiet mode operations
    def enable_quiet_mode(self):
        self.quiet_mode = True

    def disable_quiet_mode(self):
        self.quiet_mode = False

    # Handle log-to-file operations
    def enable_log_to_file(self):
        self.log_to_file = True

    def disable_log_to_file(self):
        self.log_to_file = False
        self.log_buffer = ""

    def define_log_file(self, log_file_name):
        self.log_file_name = log_file_name
        with open(self.log_file_name, 'w+') as file:
            file.close()

    def flush(self):
        if self.log_to_file and self.log_file_name:
            with open(self.log_file_name, 'a+') as file:
                file.write(self.log_buffer)
                file.close()
        self.log_buffer = ""

    # Perform the actual logging
    def log(
                self,
                s="",
                indent=None,
                override_quiet_mode=False,
                is_error=False
            ):
        if is_error:
            indent = 0
            override_quiet_mode = True
        if self.beginning_of_line:
            if indent is None:
                indent = self.indent_level
            for i in range(indent):
                s = "    "+s
        self.beginning_of_line = False
        if self.log_to_file:
            self.log_buffer = self.log_buffer + s
        if self.quiet_mode and not override_quiet_mode:
            return
        if is_error:
            print(s, end="", file=sys.stderr)
        else:
            print(s, end="", file=sys.stdout)
        sys.stdout.flush()

    # Handle logging with a newline
    def logln(
                self,
                s="",
                indent=None,
                override_quiet_mode=False,
                is_error=False
            ):
        s = s+"\r\n"
        self.log(
                s,
                indent=indent,
                override_quiet_mode=override_quiet_mode,
                is_error=is_error
            )
        self.beginning_of_line = True

    # Handle indenting
    def stepin(self, step_in_num=1):
        self.indent_level = self.indent_level + step_in_num
        self.force_new_line()

    def stepout(self, step_out_num=1):
        self.indent_level = self.indent_level - step_out_num
        if self.indent_level < 0:
            self.indent_level = 0
        self.force_new_line()

    # Automatically force the log to the next new line
    def force_new_line(self):
        if not self.beginning_of_line:
            self.logln("", override_quiet_mode=True)

    # Query the user's response
    def query(self, s, indent=None):
        self.log(s, indent=indent, override_quiet_mode=True)
        return input("")
        #return raw_input("")

    # Pretty print and units
    def to_MHz(self, f):
        return "{}MHz".format(round(f/1e3)/1e3)

    def to_dBm(self, p):
        return "{}dBm".format(p)

    # Make sure that the logger flushed before it's deleted
    def __del__(self):
        self.flush()
