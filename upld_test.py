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

def run_process (arg_list, print_cmd = False, capture_out = False):
    sys.stdout.flush()
    if os.name == 'nt' and os.path.splitext(arg_list[0])[1] == '' and \
       os.path.exists (arg_list[0] + '.exe'):
        arg_list[0] += '.exe'
    if print_cmd:
        print (' '.join(arg_list))

    exc    = None
    result = 0
    output = ''
    try:
        if capture_out:
            output = subprocess.check_output(arg_list).decode()
        else:
            result = subprocess.call (arg_list)
    except Exception as ex:
        result = 1
        exc    = ex

    if result:
        if not print_cmd:
            print ('Error in running process:\n  %s' % ' '.join(arg_list))
        if exc is None:
            sys.exit(1)
        else:
            raise exc

    return output

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


def get_objcopy ():
    objcopy = 'llvm-objcopy-10'
    cmd = '%s -V' % objcopy
    try:
        run_process(cmd.split(' '), capture_out = True)
        ret = 0
    except:
        ret = -1
    if ret:
        objcopy = 'objcopy'
    return objcopy


def main ():

    if os.name != 'posix':
        fatal ('Only Linux is supported!')

    out_dir = 'Outputs'
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    sbl_dir = 'SlimBoot'
    clone_repo  (sbl_dir, 'https://github.com/universalpayload/slimbootloader.git', 'upld_elf')
    shutil.copy ('QemuFspBins/Fsp.bsf', 'SlimBoot/Silicon/QemuSocPkg/FspBin/Fsp.bsf')
    shutil.copy ('QemuFspBins/FspRel.bin', 'SlimBoot/Silicon/QemuSocPkg/FspBin/FspRel.bin')

    # Build SBL
    cmd = 'python BuildLoader.py build qemu -k'
    ret = subprocess.call(cmd.split(' '), cwd=sbl_dir)
    if ret:
        fatal ('Failed to build SBL!')

    objcopy = get_objcopy()

    # Build Linux Payload 32
    cmd = 'python BuildLoader.py build_dsc -p UniversalPayloadPkg/UniversalPayloadPkg.dsc'
    ret = subprocess.call(cmd.split(' '), cwd=sbl_dir)
    if ret:
        fatal ('Failed to build Linux Payload 32!')
    shutil.copy ('%s/Build/UniversalPayloadPkg/DEBUG_GCC5/IA32/UniversalPayloadPkg/LinuxLoaderStub/LinuxLoaderStub/DEBUG/LinuxLoaderStub.dll' % sbl_dir, '%s/LinuxPld32.elf' % out_dir)

    # Inject sections
    cmd = 'python Script/upld_info.py %s/upld_info.bin Linux32' % out_dir
    run_process (cmd.split(' '))
    cmd = objcopy + " -I elf32-i386 -O elf32-i386 --add-section .upld.initrd=LinuxBins/initrd --add-section .upld.cmdline=LinuxBins/config.cfg --add-section .upld.kernel=LinuxBins/vmlinuz --add-section .upld_info=%s/upld_info.bin %s/LinuxPld32.elf" % (out_dir, out_dir)
    run_process (cmd.split(' '))
    cmd = objcopy + " -I elf32-i386 -O elf32-i386 --set-section-alignment .upld.kernel=256 --set-section-alignment .upld.initrd=4096 --set-section-alignment .upld.cmdline=16 --set-section-alignment .upld.info=16 %s/LinuxPld32.elf" % (out_dir)
    run_process (cmd.split(' '))


    # Build Linux Payload 64
    cmd = 'python BuildLoader.py build_dsc -a x64 -p UniversalPayloadPkg/UniversalPayloadPkg.dsc'
    ret = subprocess.call(cmd.split(' '), cwd=sbl_dir)
    if ret:
        fatal ('Failed to build Linux Payload 64!')
    shutil.copy ('%s/Build/UniversalPayloadPkg/DEBUG_GCC5/X64/UniversalPayloadPkg/LinuxLoaderStub/LinuxLoaderStub/DEBUG/LinuxLoaderStub.dll' % sbl_dir, '%s/LinuxPld64.elf' % out_dir)

    # Inject sections
    cmd = 'python Script/upld_info.py %s/upld_info.bin Linux64' % out_dir
    run_process (cmd.split(' '))
    cmd = objcopy + " -I elf64-x86-64 -O elf64-x86-64 --add-section .upld.initrd=LinuxBins/initrd --add-section .upld.cmdline=LinuxBins/config.cfg --add-section .upld.kernel=LinuxBins/vmlinuz --add-section .upld_info=%s/upld_info.bin %s/LinuxPld64.elf" % (out_dir, out_dir)
    run_process (cmd.split(' '))
    cmd = objcopy + " -I elf64-x86-64 -O elf64-x86-64 --set-section-alignment .upld.kernel=256 --set-section-alignment .upld.initrd=4096 --set-section-alignment .upld.cmdline=16 --set-section-alignment .upld.info=16 %s/LinuxPld64.elf" % (out_dir)
    run_process (cmd.split(' '))

    return 0


if __name__ == '__main__':
    sys.exit(main())
