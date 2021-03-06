#!/usr/bin/env python
## @ upld_info.py
#
# Universal Payload info header generator
#
# Copyright (c) 2021, Intel Corporation. All rights reserved.<BR>
#  SPDX-License-Identifier: BSD-2-Clause-Patent

##
# Import Modules
#
import os
import sys
import re
import errno
import shutil
import argparse
import subprocess
import multiprocessing
from   ctypes import *

sys.dont_write_bytecode = True

class UPLD_INFO_HEADER(Structure):
    _pack_ = 1
    _fields_ = [
        ('Identifier',           ARRAY(c_char, 4)),
        ('HeaderLength',         c_uint32),
        ('SpecRevision',         c_uint16),
        ('Reserved',             c_uint16),
        ('Revision',             c_uint32),
        ('Attribute',            c_uint32),
        ('Capability',           c_uint32),
        ('ProducerId',           ARRAY(c_char, 16)),
        ('ImageId',              ARRAY(c_char, 16)),
        ]

    def __init__(self):
        self.Identifier     =  b'UPLD'
        self.HeaderLength   = sizeof(UPLD_INFO_HEADER)
        self.HeaderRevision = 0x0075
        self.Revision       = 0x0000010105
        self.ImageId        = b'UEFI'
        self.ProducerId     = b'INTEL'

def main():
    upld_info_hdr =  UPLD_INFO_HEADER()
    upld_info_hdr.ImageId = sys.argv[2].encode()[:16]
    fp = open(sys.argv[1], 'wb')
    fp.write(bytearray(upld_info_hdr))
    fp.close()

if __name__ == '__main__':
    main()


