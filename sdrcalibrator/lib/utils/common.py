import argparse
import os
import sys
from importlib import import_module
from contextlib import contextmanager
import numpy as np

from sdrcalibrator.lib.utils.dictdotaccessor import DictDotAccessor
import sdrcalibrator.lib.utils.error as Error
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error


""" Detect if we're running python 2 or 3 """
def is_python3():
    return (sys.version_info > (3, 0))


""" Open a profile and load it as a DictDotAccessor """
def load_profile(profile_file):
    raw_profile = {}
    #execfile(profile_file, {}, raw_profile)
    exec(open(profile_file).read(), {}, raw_profile)
    return DictDotAccessor(raw_profile)


""" Execute a test based on a loaded profile """
def execute_test(profile):
    # Check that the test type has been set in the profile
    if not hasattr(profile, 'test_type'):
        ehead = "No test type defined in profile"
        ebody = "The test type must be defined to load the correct test.\r\n"
        ebody += "The easiest way to define a test is to copy and modify\r\n"
        ebody += "one of the example test profiles."
        err = SDR_Test_Error(0, ehead, ebody)
        Error.error_out_pre_logger(err)

    # Load the test script
    test_script = "sdrcalibrator.lib.scripts.{}".format(profile.test_type)
    try:
        test_function = import_object(test_script, "SDR_Test")
        test = test_function(profile)
    except ImportError as e:
        raise e
        ehead = "Could not find test type '{}'".format(profile.test_type)
        ebody = "See the documentation for a list of predefined test types\r\n"
        ebody += "or double check the profile if this is a custom one."
        err = SDR_Test_Error(1, ehead, ebody)
        Error.error_out_pre_logger(err)

    # Run the test
    test.run()




"""Return file name if file exists, else raise ArgumentTypeError"""
def filetype(fname):
    if os.path.isfile(fname):
        return fname
    else:
        errmsg = "file {} does not exist".format(fname)
        raise argparse.ArgumentTypeError(errmsg)


def import_object(path, obj):
    _obj = import_module(path)
    return getattr(_obj, obj)


def remove_duplicates(l1,l2=None,l3=None):
    # Handle both np arrays and lists by converting to lists
    reconvert_l1 = False
    if type(l1) is np.ndarray:
        l1 = l1.tolist()
        reconvert_l1 = True
    reconvert_l2 = False
    if type(l2) is np.ndarray:
        l2 = l2.tolist()
        reconvert_l2 = True
    reconvert_l3 = False
    if type(l3) is np.ndarray:
        l3 = l3.tolist()
        reconvert_l3 = True
    
    # Iterate and remove duplicates
    for i in range(len(l1)-1,0,-1):
        for j in range(i):
            if l1[i] == l1[j]:
                del l1[i]
                if l2 is not None:
                    del l2[i]
                if l3 is not None:
                    del l3[i]
                break

    # Reconvert to np arrays if needed
    if reconvert_l1:
        l1 = np.asarray(l1)
    if reconvert_l2:
        l2 = np.asarray(l2)
    if reconvert_l3:
        l3 = np.asarray(l3)

    # Only return what was sent
    if l2 is None:
        return l1
    elif l3 is None:
        return l1,l2
    else:
        return l1,l2,l3

def stack_matrices(a,b):
    # Handle both np arrays and lists by converting to lists
    reconvert_a = False
    if type(a) is np.ndarray:
        a = a.tolist()
        reconvert_a = True
    reconvert_b = False
    if type(b) is np.ndarray:
        b = b.tolist()
        reconvert_b = True
    
    # Stack the arrays
    c = []
    for i in range(len(a)):
        c.append(a[i])
    for i in range(len(b)):
        c.append(b[i])

    # Reconvert to lists if needed
    if reconvert_a and reconvert_b:
        c = np.asarray(c)
    return c

def transpose_matrix(m):
    m_t = np.zeros((len(m[0]),len(m))).tolist()
    for i in range(len(m)):
        for j in range(len(m[0])):
            m_t[j][i] = m[i][j]
    return m_t

def sort_matrix_by_list(m,x):
    for i in range(1, len(x)):
        j = i-1
        m_key = m[i]
        x_key = x[i]
        while (x[j] > x_key) and (j >= 0):
           m[j+1] = m[j]
           x[j+1] = x[j]
           j = j - 1
        m[j+1] = m_key
        x[j+1] = x_key
    return m,x

def sort_matrix_by_lists(m,x=None,y=None):
    if x is not None:
        m = transpose_matrix(m)
        m,x = sort_matrix_by_list(m,x)
        m = transpose_matrix(m)
    if y is not None:
        m,y = sort_matrix_by_list(m,y)
    if x is None and y is not None:
        return m,y
    if x is not None and y is None:
        return m,x
    if x is None and y is None:
        return m
    if x is not None and y is not None:
        return m,x,y


# Get the nearest index in an array
def get_nearest_low_index(v,arr):
    for i in range(len(arr)):
        if arr[i] >= v:
            return i-1
    return len(arr)-1


# Interpolate between points in one dimension
def interpolate_1d(x,x1,x2,y1,y2):
    return y1*(x2-x)/(x2-x1) + y2*(x-x1)/(x2-x1)

# Interpolate between points in two dimensions
def interpolate_2d(x,y,x1,x2,y1,y2,z11,z21,z12,z22):
    z_y1 = interpolate_1d(x,x1,x2,z11,z21)
    z_y2 = interpolate_1d(x,x1,x2,z12,z22)
    return interpolate_1d(y,y1,y2,z_y1,z_y2)


# Enable or disable print TODO: FIX THIS
def block_print():
    sys.stdout = open(os.devnull, 'w')


def enable_print():
    return True
    # sys.stdout = sys.__stdout__


@contextmanager
def suppress_output():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
