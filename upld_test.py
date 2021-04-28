## @file
# This file is used to provide board specific image information.
#
#  Copyright (c) 2021, Intel Corporation. All rights reserved.<BR>
#
#  SPDX-License-Identifier: BSD-2-Clause-Patent
#

import os
import sys
import shutil
import subprocess

def fatal (msg):
    sys.stdout.flush()
    raise Exception (msg)


def clone_repo (clone_dir, repo, branch, commit = 'HEAD'):
    if not os.path.exists(clone_dir + '/.git'):
        print ('Cloning the repo ... %s' % repo)
        cmd = 'git clone %s %s' % (repo, clone_dir)
        ret = subprocess.call(cmd.split(' '))
        if ret:
            fatal ('Failed to clone repo to directory %s !' % clone_dir)
        print ('Done\n')
    else:
        print ('Update the repo ...')
        cmd = 'git fetch origin'
        ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
        if ret:
            fatal ('Failed to update repo in directory %s !' % clone_dir)
        print ('Done\n')

    print ('Checking out specified version ... %s' % commit)

    cmd = 'git checkout %s -f' % branch
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to check out specified branch !')
    print ('Done\n')

    cmd = 'git pull'
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to pull commit !')
    print ('Done\n')


def main ():

    if os.name != 'posix':
        fatal ('Only Linux is supported!')

    out_dir = 'Outputs'
    sbl_dir = 'SlimBoot'
    clone_repo  (sbl_dir, 'https://github.com/universalpayload/slimbootloader.git', 'upld_elf')
    shutil.copy ('QemuFspBins/Fsp.bsf', 'SlimBoot/Silicon/QemuSocPkg/FspBin/Fsp.bsf')
    shutil.copy ('QemuFspBins/FspRel.bin', 'SlimBoot/Silicon/QemuSocPkg/FspBin/FspRel.bin')

    # Build SBL
    cmd = 'python BuildLoader.py build qemu -k'
    ret = subprocess.call(cmd.split(' '), cwd=sbl_dir)
    if ret:
        fatal ('Failed to build SBL!')

    # Build Linux Payload 32
    cmd = 'BuildLoader.py build_dsc -p UniversalPayloadPkg/UniversalPayloadPkg.dsc'
    ret = subprocess.call(cmd.split(' '), cwd=sbl_dir)
    if ret:
        fatal ('Failed to build Linux Payload 32!')
    shutil.copy ('%s/Build/UniversalPayloadPkg/DEBUG_GCC5/IA32/UniversalPayloadPkg/LinuxLoaderStub/LinuxLoaderStub/DEBUG/LinuxLoaderStub.dll' % sbl_dir, '%s/LinuxPld32.elf' % out_dir)

    # Build Linux Payload 64
    cmd = 'BuildLoader.py build_dsc -a x64 -p UniversalPayloadPkg/UniversalPayloadPkg.dsc'
    ret = subprocess.call(cmd.split(' '), cwd=sbl_dir)
    if ret:
        fatal ('Failed to build Linux Payload 64!')
    shutil.copy ('%s/Build/UniversalPayloadPkg/DEBUG_GCC5/X64/UniversalPayloadPkg/LinuxLoaderStub/LinuxLoaderStub/DEBUG/LinuxLoaderStub.dll' % sbl_dir, '%s/LinuxPld64.elf' % out_dir)

    return 0


if __name__ == '__main__':
    sys.exit(main())
