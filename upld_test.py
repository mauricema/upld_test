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
import fnmatch
import argparse

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

    cmd = 'git submodule init'
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to init submodules !')
    print ('Done\n')

    cmd = 'git submodule update'
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to update submodules !')
    print ('Done\n')

    cmd = 'git pull'
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to pull latest code !')

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


def qemu_test (test_pat):

    if 'SBL_KEY_DIR' not in os.environ:
        os.environ['SBL_KEY_DIR'] = "SblKeys/"

    # check QEMU SlimBootloader.bin
    sbl_img  = 'SlimBoot/Outputs/qemu/SlimBootloader.bin'
    tst_img  = 'Outputs/SlimBootloader.bin'
    if not os.path.exists(sbl_img):
        print ('Could not find QEMU SlimBootloader.bin image !')
        return -1

    disk_dir = 'Disk'
    out_dir  = 'Outputs'
    if not os.path.exists(disk_dir):
        os.mkdir(disk_dir)


    # run test cases
    test_cases = [
      ('sbl_upld.py',  [tst_img, disk_dir, 'uboot_32'], 'UbootPld.elf'),
      ('sbl_upld.py',  [tst_img, disk_dir, 'linux_32'], 'LinuxPld32.elf'),
      ('sbl_upld.py',  [tst_img, disk_dir, 'linux_64'], 'LinuxPld64.elf'),
      ('sbl_upld.py',  [tst_img, disk_dir, 'uefi_32'],  'UefiPld32.elf'),
      ('sbl_upld.py',  [tst_img, disk_dir, 'uefi_64'],  'UefiPld64.elf'),
    ]

    test_cnt = 0
    for test_file, test_args, upld_img in test_cases:
        if test_pat:
            filtered = fnmatch.filter([upld_img.lower()], test_pat)
            if len(filtered) == 0:
                continue

        print ('######### Running run test %s' % test_file)
        # create new IFWI using the upld
        cmd = [ sys.executable, 'Script/upld_swap.py', '-i', sbl_img, '-p', 'Outputs/%s' % upld_img, '-o', out_dir]
        run_process (cmd)

        # run QEMU test cases
        cmd = [ sys.executable, 'Script/%s' % test_file] + test_args
        try:
            output = subprocess.run (cmd)
            output.check_returncode()
        except subprocess.CalledProcessError:
            print ('Failed to run test %s !' % test_file)
            return -3
        print ('######### Completed test %s\n\n' % test_file)
        test_cnt += 1

    print ('\nAll %d test cases passed !\n' % test_cnt)

    return 0


def build_sbl_images (dir_dict):
    out_dir = dir_dict['out_dir']
    sbl_dir = dir_dict['sbl_dir']

    clone_repo  (sbl_dir, 'https://github.com/universalpayload/slimbootloader.git', 'upld_elf')
    shutil.copy ('QemuFspBins/Fsp.bsf', '%s/Silicon/QemuSocPkg/FspBin/Fsp.bsf' % sbl_dir)
    shutil.copy ('QemuFspBins/FspRel.bin', '%s/Silicon/QemuSocPkg/FspBin/FspRel.bin' % sbl_dir)

    # Build SBL
    cmd = 'python BuildLoader.py build qemu -k'
    ret = subprocess.call(cmd.split(' '), cwd=sbl_dir)
    if ret:
        fatal ('Failed to build SBL!')

    return 0

def build_linux_images (dir_dict):
    out_dir = dir_dict['out_dir']
    sbl_dir = dir_dict['sbl_dir']
    objcopy = dir_dict['objcopy_path']

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


def build_uboot_images (dir_dict):
    out_dir = dir_dict['out_dir']
    objcopy = dir_dict['objcopy_path']

    # Copy u-boot image
    shutil.copy ('UbootBin/u-boot', '%s/UbootPld.elf' % out_dir)
    cmd = 'strip --strip-unneeded %s/UbootPld.elf' % out_dir
    run_process (cmd.split(' '))

    # Inject sections
    cmd = 'python Script/upld_info.py %s/upld_info.bin u-boot' % out_dir
    run_process (cmd.split(' '))

    cmd = objcopy + " -I elf32-i386 -O elf32-i386 --add-section .upld_info=%s/upld_info.bin %s/UbootPld.elf" % (out_dir, out_dir)
    run_process (cmd.split(' '))
    cmd = objcopy + " -I elf32-i386 -O elf32-i386 --set-section-alignment .upld_info=16 %s/UbootPld.elf" % (out_dir)
    run_process (cmd.split(' '))

    return 0



def build_uefi_images (dir_dict):
    out_dir  = dir_dict['out_dir']
    uefi_dir = dir_dict['uefi_dir']
    objcopy  = dir_dict['objcopy_path']
    clone_repo  (uefi_dir, 'https://github.com/universalpayload/edk2.git', 'upld_elf')

    # Build UEFI
    for target in ['32', '64']:
        cmd = 'python BuildPayload.py build'
        if target == '64':
            cmd += ' -a x64'
            fmt  = 'elf64-x86-64'
        else:
            fmt  = 'elf32-i386'
        ret = subprocess.call(cmd.split(' '), cwd=uefi_dir)
        if ret:
            fatal ('Failed to build SBL!')
        shutil.copy ('%s/Build/UefiPayloadPkg/DEBUG_GCC5/FV/UefiPld%s.elf' % (uefi_dir, target),  '%s/UefiPld%s.elf' % (out_dir, target))
        shutil.copy ('%s/Build/UefiPayloadPkg/DEBUG_GCC5/FV/DXEFV.Fv' % uefi_dir,  '%s/DXEFV%s.fv' % (out_dir, target))

        # Inject sections
        cmd = 'python Script/upld_info.py %s/upld_info.bin UEFI%s' % (out_dir, target)
        run_process (cmd.split(' '))
        bin_fmt = " -I %s -O %s" % (fmt, fmt)
        cmd = objcopy + bin_fmt + " --add-section .upld_info=%s/upld_info.bin --add-section .upld.uefi_fv=%s/DXEFV32.fv %s/UefiPld%s.elf" % (out_dir, out_dir, out_dir, target)
        run_process (cmd.split(' '))
        cmd = objcopy + bin_fmt + " --set-section-alignment .upld.info=16 --set-section-alignment .upld.uefi_fv=4096 %s/UefiPld%s.elf" % (out_dir, target)
        run_process (cmd.split(' '))

    return 0

def main ():
    dir_dict = {
                  'out_dir'      : 'Outputs',
                  'sbl_dir'      : 'SlimBoot',
                  'uefi_dir'     : 'UefiPayload',
                  'objcopy_path' : get_objcopy(),
               }

    arg_parse  = argparse.ArgumentParser()
    arg_parse.add_argument('-sb',   dest='skip_build', action='store_true', help='Specify name pattern for payloads to be built')
    arg_parse.add_argument('-t',   dest='test',  type=str, help='Specify name pattern for payloads to be tested', default = '')
    args = arg_parse.parse_args()

    if os.name != 'posix':
        fatal ('Only Linux is supported!')

    if not os.path.exists(dir_dict['out_dir']):
        os.mkdir(dir_dict['out_dir'])

    if not args.skip_build:
        if build_uboot_images (dir_dict):
            return 1

        if build_sbl_images (dir_dict):
            return 2

        if build_linux_images (dir_dict):
            return 3

        if build_uefi_images (dir_dict):
            return 4

    if qemu_test (args.test):
        return 5

    return 0

if __name__ == '__main__':
    sys.exit(main())
