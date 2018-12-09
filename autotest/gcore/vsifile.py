#!/usr/bin/env python
# -*- coding: utf-8 -*-
###############################################################################
# $Id$
#
# Project:  GDAL/OGR Test Suite
# Purpose:  Test VSI file primitives
# Author:   Even Rouault <even dot rouault at mines dash parid dot org>
#
###############################################################################
# Copyright (c) 2011-2013, Even Rouault <even dot rouault at mines-paris dot org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

import sys
import time
from osgeo import gdal


import gdaltest

###############################################################################
# Generic test


def vsifile_generic(filename):

    start_time = time.time()

    fp = gdal.VSIFOpenL(filename, 'wb+')
    if fp is None:
        return 'fail'

    if gdal.VSIFWriteL('0123456789', 1, 10, fp) != 10:
        return 'fail'

    if gdal.VSIFFlushL(fp) != 0:
        return 'fail'

    if gdal.VSIFTruncateL(fp, 20) != 0:
        return 'fail'

    if gdal.VSIFTellL(fp) != 10:
        return 'fail'

    if gdal.VSIFTruncateL(fp, 5) != 0:
        return 'fail'

    if gdal.VSIFTellL(fp) != 10:
        return 'fail'

    if gdal.VSIFSeekL(fp, 0, 2) != 0:
        return 'fail'

    if gdal.VSIFTellL(fp) != 5:
        return 'fail'

    gdal.VSIFWriteL('XX', 1, 2, fp)
    gdal.VSIFCloseL(fp)

    statBuf = gdal.VSIStatL(filename, gdal.VSI_STAT_EXISTS_FLAG | gdal.VSI_STAT_NATURE_FLAG | gdal.VSI_STAT_SIZE_FLAG)
    if statBuf.size != 7:
        print(statBuf.size)
        return 'fail'
    if abs(start_time - statBuf.mtime) > 2:
        print(statBuf.mtime)
        return 'fail'

    fp = gdal.VSIFOpenL(filename, 'rb')
    buf = gdal.VSIFReadL(1, 7, fp)
    if gdal.VSIFWriteL('a', 1, 1, fp) != 0:
        return 'fail'
    if gdal.VSIFTruncateL(fp, 0) == 0:
        return 'fail'
    gdal.VSIFCloseL(fp)

    if buf.decode('ascii') != '01234XX':
        print(buf.decode('ascii'))
        return 'fail'

    # Test append mode on existing file
    fp = gdal.VSIFOpenL(filename, 'ab')
    gdal.VSIFWriteL('XX', 1, 2, fp)
    gdal.VSIFCloseL(fp)

    statBuf = gdal.VSIStatL(filename, gdal.VSI_STAT_EXISTS_FLAG | gdal.VSI_STAT_NATURE_FLAG | gdal.VSI_STAT_SIZE_FLAG)
    if statBuf.size != 9:
        print(statBuf.size)
        return 'fail'

    if gdal.Unlink(filename) != 0:
        return 'fail'

    statBuf = gdal.VSIStatL(filename, gdal.VSI_STAT_EXISTS_FLAG)
    if statBuf is not None:
        return 'fail'

    # Test append mode on non existing file
    fp = gdal.VSIFOpenL(filename, 'ab')
    gdal.VSIFWriteL('XX', 1, 2, fp)
    gdal.VSIFCloseL(fp)

    statBuf = gdal.VSIStatL(filename, gdal.VSI_STAT_EXISTS_FLAG | gdal.VSI_STAT_NATURE_FLAG | gdal.VSI_STAT_SIZE_FLAG)
    if statBuf.size != 2:
        print(statBuf.size)
        return 'fail'

    if gdal.Unlink(filename) != 0:
        return 'fail'

    return 'success'

###############################################################################
# Test /vsimem


def test_vsifile_1():
    return vsifile_generic('/vsimem/vsifile_1.bin')

###############################################################################
# Test regular file system


def test_vsifile_2():

    ret = vsifile_generic('tmp/vsifile_2.bin')
    if ret != 'success' and gdaltest.skip_on_travis():
        # FIXME
        # Fails on Travis with 17592186044423 (which is 0x10 00 00 00 00 07 instead of 7) at line 63
        # Looks like a 32/64bit issue with Python bindings of VSIStatL()
        return 'skip'
    return ret

###############################################################################
# Test ftruncate >= 32 bit


def test_vsifile_3():

    if not gdaltest.filesystem_supports_sparse_files('tmp'):
        return 'skip'

    filename = 'tmp/vsifile_3'

    fp = gdal.VSIFOpenL(filename, 'wb+')
    gdal.VSIFTruncateL(fp, 10 * 1024 * 1024 * 1024)
    gdal.VSIFSeekL(fp, 0, 2)
    pos = gdal.VSIFTellL(fp)
    if pos != 10 * 1024 * 1024 * 1024:
        gdal.VSIFCloseL(fp)
        gdal.Unlink(filename)
        print(pos)
        return 'fail'
    gdal.VSIFSeekL(fp, 0, 0)
    gdal.VSIFSeekL(fp, pos, 0)
    pos = gdal.VSIFTellL(fp)
    if pos != 10 * 1024 * 1024 * 1024:
        gdal.VSIFCloseL(fp)
        gdal.Unlink(filename)
        print(pos)
        return 'fail'

    gdal.VSIFCloseL(fp)

    statBuf = gdal.VSIStatL(filename, gdal.VSI_STAT_EXISTS_FLAG | gdal.VSI_STAT_NATURE_FLAG | gdal.VSI_STAT_SIZE_FLAG)
    gdal.Unlink(filename)

    if statBuf.size != 10 * 1024 * 1024 * 1024:
        print(statBuf.size)
        return 'fail'

    return 'success'

###############################################################################
# Test fix for #4583 (short reads)


def test_vsifile_4():

    fp = gdal.VSIFOpenL('vsifile.py', 'rb')
    data = gdal.VSIFReadL(1000000, 1, fp)
    # print(len(data))
    gdal.VSIFSeekL(fp, 0, 0)
    data = gdal.VSIFReadL(1, 1000000, fp)
    if not data:
        return 'fail'
    gdal.VSIFCloseL(fp)

    return 'success'

###############################################################################
# Test vsicache


def test_vsifile_5():

    fp = gdal.VSIFOpenL('tmp/vsifile_5.bin', 'wb')
    ref_data = ''.join(['%08X' % i for i in range(5 * 32768)])
    gdal.VSIFWriteL(ref_data, 1, len(ref_data), fp)
    gdal.VSIFCloseL(fp)

    gdal.SetConfigOption('VSI_CACHE', 'YES')

    for i in range(3):
        if i == 0:
            gdal.SetConfigOption('VSI_CACHE_SIZE', '0')
        elif i == 1:
            gdal.SetConfigOption('VSI_CACHE_SIZE', '65536')
        else:
            gdal.SetConfigOption('VSI_CACHE_SIZE', None)

        fp = gdal.VSIFOpenL('tmp/vsifile_5.bin', 'rb')

        gdal.VSIFSeekL(fp, 50000, 0)
        if gdal.VSIFTellL(fp) != 50000:
            gdal.SetConfigOption('VSI_CACHE_SIZE', None)
            gdal.SetConfigOption('VSI_CACHE', None)
            return 'fail'

        gdal.VSIFSeekL(fp, 50000, 1)
        if gdal.VSIFTellL(fp) != 100000:
            gdal.SetConfigOption('VSI_CACHE_SIZE', None)
            gdal.SetConfigOption('VSI_CACHE', None)
            return 'fail'

        gdal.VSIFSeekL(fp, 0, 2)
        if gdal.VSIFTellL(fp) != 5 * 32768 * 8:
            gdal.SetConfigOption('VSI_CACHE_SIZE', None)
            gdal.SetConfigOption('VSI_CACHE', None)
            return 'fail'
        gdal.VSIFReadL(1, 1, fp)

        gdal.VSIFSeekL(fp, 0, 0)
        data = gdal.VSIFReadL(1, 3 * 32768, fp)
        if data.decode('ascii') != ref_data[0:3 * 32768]:
            gdal.SetConfigOption('VSI_CACHE_SIZE', None)
            gdal.SetConfigOption('VSI_CACHE', None)
            return 'fail'

        gdal.VSIFSeekL(fp, 16384, 0)
        data = gdal.VSIFReadL(1, 5 * 32768, fp)
        if data.decode('ascii') != ref_data[16384:16384 + 5 * 32768]:
            gdal.SetConfigOption('VSI_CACHE_SIZE', None)
            gdal.SetConfigOption('VSI_CACHE', None)
            return 'fail'

        data = gdal.VSIFReadL(1, 50 * 32768, fp)
        if data[0:1130496].decode('ascii') != ref_data[16384 + 5 * 32768:]:
            gdal.SetConfigOption('VSI_CACHE_SIZE', None)
            gdal.SetConfigOption('VSI_CACHE', None)
            return 'fail'

        gdal.VSIFCloseL(fp)

    gdal.SetConfigOption('VSI_CACHE_SIZE', None)
    gdal.SetConfigOption('VSI_CACHE', None)
    gdal.Unlink('tmp/vsifile_5.bin')

    return 'success'

###############################################################################
# Test vsicache above 2 GB


def test_vsifile_6():

    if not gdaltest.filesystem_supports_sparse_files('tmp'):
        return 'skip'

    offset = 4 * 1024 * 1024 * 1024

    ref_data = 'abcd'.encode('ascii')
    fp = gdal.VSIFOpenL('tmp/vsifile_6.bin', 'wb')
    gdal.VSIFSeekL(fp, offset, 0)
    gdal.VSIFWriteL(ref_data, 1, len(ref_data), fp)
    gdal.VSIFCloseL(fp)

    # Sanity check without VSI_CACHE
    fp = gdal.VSIFOpenL('tmp/vsifile_6.bin', 'rb')
    gdal.VSIFSeekL(fp, offset, 0)
    got_data = gdal.VSIFReadL(1, len(ref_data), fp)
    gdal.VSIFCloseL(fp)

    if ref_data != got_data:
        print(got_data)
        return 'fail'

    # Real test now
    gdal.SetConfigOption('VSI_CACHE', 'YES')
    fp = gdal.VSIFOpenL('tmp/vsifile_6.bin', 'rb')
    gdal.SetConfigOption('VSI_CACHE', None)
    gdal.VSIFSeekL(fp, offset, 0)
    got_data = gdal.VSIFReadL(1, len(ref_data), fp)
    gdal.VSIFCloseL(fp)

    if ref_data != got_data:
        print(got_data)
        return 'fail'

    gdal.Unlink('tmp/vsifile_6.bin')

    return 'success'

###############################################################################
# Test limit cases on /vsimem


def test_vsifile_7():

    if gdal.GetConfigOption('SKIP_MEM_INTENSIVE_TEST') is not None:
        return 'skip'

    # Test extending file beyond reasonable limits in write mode
    fp = gdal.VSIFOpenL('/vsimem/vsifile_7.bin', 'wb')
    if gdal.VSIFSeekL(fp, 0x7FFFFFFFFFFFFFFF, 0) != 0:
        return 'fail'
    if gdal.VSIStatL('/vsimem/vsifile_7.bin').size != 0:
        return 'fail'
    gdal.PushErrorHandler()
    ret = gdal.VSIFWriteL('a', 1, 1, fp)
    gdal.PopErrorHandler()
    if ret != 0:
        return 'fail'
    if gdal.VSIStatL('/vsimem/vsifile_7.bin').size != 0:
        return 'fail'
    gdal.VSIFCloseL(fp)

    # Test seeking  beyond file size in read-only mode
    fp = gdal.VSIFOpenL('/vsimem/vsifile_7.bin', 'rb')
    if gdal.VSIFSeekL(fp, 0x7FFFFFFFFFFFFFFF, 0) != 0:
        return 'fail'
    if gdal.VSIFEofL(fp) != 0:
        return 'fail'
    if gdal.VSIFTellL(fp) != 0x7FFFFFFFFFFFFFFF:
        return 'fail'
    if gdal.VSIFReadL(1, 1, fp):
        return 'fail'
    if gdal.VSIFEofL(fp) != 1:
        return 'fail'
    gdal.VSIFCloseL(fp)

    gdal.Unlink('/vsimem/vsifile_7.bin')

    return 'success'

###############################################################################
# Test renaming directory in /vsimem


def test_vsifile_8():

    # octal 0666 = decimal 438
    gdal.Mkdir('/vsimem/mydir', 438)
    fp = gdal.VSIFOpenL('/vsimem/mydir/a', 'wb')
    gdal.VSIFCloseL(fp)
    gdal.Rename('/vsimem/mydir', '/vsimem/newdir'.encode('ascii').decode('ascii'))
    if gdal.VSIStatL('/vsimem/newdir') is None:
        return 'fail'
    if gdal.VSIStatL('/vsimem/newdir/a') is None:
        return 'fail'
    gdal.Unlink('/vsimem/newdir/a')
    gdal.Rmdir('/vsimem/newdir')

    return 'success'

###############################################################################
# Test ReadDir()


def test_vsifile_9():

    lst = gdal.ReadDir('.')
    if len(lst) < 4:
        return 'fail'
    # Test truncation
    lst_truncated = gdal.ReadDir('.', int(len(lst) / 2))
    if len(lst_truncated) <= int(len(lst) / 2):
        return 'fail'

    gdal.Mkdir('/vsimem/mydir', 438)
    for i in range(10):
        fp = gdal.VSIFOpenL('/vsimem/mydir/%d' % i, 'wb')
        gdal.VSIFCloseL(fp)

    lst = gdal.ReadDir('/vsimem/mydir')
    if len(lst) < 4:
        return 'fail'
    # Test truncation
    lst_truncated = gdal.ReadDir('/vsimem/mydir', int(len(lst) / 2))
    if len(lst_truncated) <= int(len(lst) / 2):
        return 'fail'

    for i in range(10):
        gdal.Unlink('/vsimem/mydir/%d' % i)
    gdal.Rmdir('/vsimem/mydir')

    return 'success'

###############################################################################
# Test fuzzer friendly archive


def test_vsifile_10():

    gdal.FileFromMemBuffer('/vsimem/vsifile_10.tar',
                           """FUZZER_FRIENDLY_ARCHIVE
***NEWFILE***:test.txt
abc***NEWFILE***:huge.txt
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
01234567890123456789012345678901234567890123456789012345678901234567890123456789
0123456789012345678901234567890123456789012345678901234567890123456789012345678X
***NEWFILE***:small.txt
a""")
    contents = gdal.ReadDir('/vsitar//vsimem/vsifile_10.tar')
    if contents is None:
        gdal.Unlink('/vsimem/vsifile_10.tar')
        return 'skip'
    if contents != ['test.txt', 'huge.txt', 'small.txt']:
        print(contents)
        return 'fail'
    if gdal.VSIStatL('/vsitar//vsimem/vsifile_10.tar/test.txt').size != 3:
        print(gdal.VSIStatL('/vsitar//vsimem/vsifile_10.tar/test.txt').size)
        return 'fail'
    if gdal.VSIStatL('/vsitar//vsimem/vsifile_10.tar/huge.txt').size != 3888:
        print(gdal.VSIStatL('/vsitar//vsimem/vsifile_10.tar/huge.txt').size)
        return 'fail'
    if gdal.VSIStatL('/vsitar//vsimem/vsifile_10.tar/small.txt').size != 1:
        print(gdal.VSIStatL('/vsitar//vsimem/vsifile_10.tar/small.txt').size)
        return 'fail'

    gdal.FileFromMemBuffer('/vsimem/vsifile_10.tar',
                           """FUZZER_FRIENDLY_ARCHIVE
***NEWFILE***:x
abc""")
    contents = gdal.ReadDir('/vsitar//vsimem/vsifile_10.tar')
    if contents != ['x']:
        print(contents)
        return 'fail'

    gdal.FileFromMemBuffer('/vsimem/vsifile_10.tar',
                           """FUZZER_FRIENDLY_ARCHIVE
***NEWFILE***:x
abc***NEWFILE***:""")
    contents = gdal.ReadDir('/vsitar//vsimem/vsifile_10.tar')
    if contents != ['x']:
        print(contents)
        return 'fail'

    gdal.Unlink('/vsimem/vsifile_10.tar')

    return 'success'

###############################################################################
# Test generic Truncate implementation for file extension


def test_vsifile_11():
    f = gdal.VSIFOpenL('/vsimem/vsifile_11', 'wb')
    gdal.VSIFCloseL(f)

    f = gdal.VSIFOpenL('/vsisubfile/0_,/vsimem/vsifile_11', 'wb')
    gdal.VSIFWriteL('0123456789', 1, 10, f)
    if gdal.VSIFTruncateL(f, 10 + 4096 + 2) != 0:
        return 'fail'
    if gdal.VSIFTellL(f) != 10:
        return 'fail'
    if gdal.VSIFTruncateL(f, 0) != -1:
        return 'fail'
    gdal.VSIFCloseL(f)

    f = gdal.VSIFOpenL('/vsimem/vsifile_11', 'rb')
    data = gdal.VSIFReadL(1, 10 + 4096 + 2, f)
    gdal.VSIFCloseL(f)
    import struct
    data = struct.unpack('B' * len(data), data)
    if data[0] != 48 or data[9] != 57 or data[10] != 0 or data[10 + 4096 + 2 - 1] != 0:
        print(data)
        return 'fail'

    gdal.Unlink('/vsimem/vsifile_11')

    return 'success'

###############################################################################
# Test regular file system sparse file support


def test_vsifile_12():

    target_dir = 'tmp'

    if gdal.VSISupportsSparseFiles(target_dir) == 0:
        return 'skip'

    # Minimum value to make it work on NTFS
    block_size = 65536
    f = gdal.VSIFOpenL(target_dir + '/vsifile_12', 'wb')
    gdal.VSIFWriteL('a', 1, 1, f)
    if gdal.VSIFTruncateL(f, block_size * 2) != 0:
        return 'fail'
    ret = gdal.VSIFGetRangeStatusL(f, 0, 1)
    # We could get unknown on nfs
    if ret == gdal.VSI_RANGE_STATUS_UNKNOWN:
        print('Range status unknown')
    else:
        if ret != gdal.VSI_RANGE_STATUS_DATA:
            print(ret)
            return 'fail'
        ret = gdal.VSIFGetRangeStatusL(f, block_size * 2 - 1, 1)
        if ret != gdal.VSI_RANGE_STATUS_HOLE:
            print(ret)
            return 'fail'
    gdal.VSIFCloseL(f)

    gdal.Unlink(target_dir + '/vsifile_12')

    return 'success'

###############################################################################
# Test reading filename with prefixes without terminating slash


def test_vsifile_13():

    gdal.VSIFOpenL('/vsigzip', 'rb')
    gdal.VSIFOpenL('/vsizip', 'rb')
    gdal.VSIFOpenL('/vsitar', 'rb')
    gdal.VSIFOpenL('/vsimem', 'rb')
    gdal.VSIFOpenL('/vsisparse', 'rb')
    gdal.VSIFOpenL('/vsisubfile', 'rb')
    gdal.VSIFOpenL('/vsicurl', 'rb')
    gdal.VSIFOpenL('/vsis3', 'rb')
    gdal.VSIFOpenL('/vsicurl_streaming', 'rb')
    gdal.VSIFOpenL('/vsis3_streaming', 'rb')
    gdal.VSIFOpenL('/vsistdin', 'rb')

    fp = gdal.VSIFOpenL('/vsistdout', 'wb')
    if fp is not None:
        gdal.VSIFCloseL(fp)

    gdal.VSIStatL('/vsigzip')
    gdal.VSIStatL('/vsizip')
    gdal.VSIStatL('/vsitar')
    gdal.VSIStatL('/vsimem')
    gdal.VSIStatL('/vsisparse')
    gdal.VSIStatL('/vsisubfile')
    gdal.VSIStatL('/vsicurl')
    gdal.VSIStatL('/vsis3')
    gdal.VSIStatL('/vsicurl_streaming')
    gdal.VSIStatL('/vsis3_streaming')
    gdal.VSIStatL('/vsistdin')
    gdal.VSIStatL('/vsistdout')

    return 'success'

###############################################################################
# Check performance issue (https://bugs.chromium.org/p/oss-fuzz/issues/detail?id=1673)


def test_vsifile_14():

    with gdaltest.error_handler():
        gdal.VSIFOpenL('/vsitar//vsitar//vsitar//vsitar//vsitar//vsitar//vsitar//vsitar/a.tgzb.tgzc.tgzd.tgze.tgzf.tgz.h.tgz.i.tgz', 'rb')
    return 'success'

###############################################################################
# Test issue with Eof() not detecting end of corrupted gzip stream (#6944)


def test_vsifile_15():

    fp = gdal.VSIFOpenL('/vsigzip/data/corrupted_z_buf_error.gz', 'rb')
    if fp is None:
        return 'fail'
    file_len = 0
    while not gdal.VSIFEofL(fp):
        with gdaltest.error_handler():
            file_len += len(gdal.VSIFReadL(1, 4, fp))
    if file_len != 6469:
        return 'fail'

    with gdaltest.error_handler():
        file_len += len(gdal.VSIFReadL(1, 4, fp))
    if file_len != 6469:
        return 'fail'

    with gdaltest.error_handler():
        if gdal.VSIFSeekL(fp, 0, 2) == 0:
            return 'fail'

    if gdal.VSIFSeekL(fp, 0, 0) != 0:
        return 'fail'

    len_read = len(gdal.VSIFReadL(1, file_len, fp))
    if len_read != file_len:
        print(len_read)
        return 'fail'

    gdal.VSIFCloseL(fp)

    return 'success'

###############################################################################
# Test failed gdal.Rename() with exceptions enabled


def test_vsifile_16():

    old_val = gdal.GetUseExceptions()
    gdal.UseExceptions()
    try:
        gdal.Rename('/tmp/i_do_not_exist_vsifile_16.tif', '/tmp/me_neither.tif')
        ret = 'fail'
    except RuntimeError:
        ret = 'success'
    if not old_val:
        gdal.DontUseExceptions()
    return ret

###############################################################################
# Test gdal.GetActualURL() on a non-network based filesystem


def test_vsifile_17():

    if gdal.GetActualURL('foo') is not None:
        return 'fail'

    if gdal.GetSignedURL('foo') is not None:
        return 'fail'

    return 'success'

###############################################################################
# Test gdal.GetFileSystemsPrefixes()


def test_vsifile_18():

    prefixes = gdal.GetFileSystemsPrefixes()
    if '/vsimem/' not in prefixes:
        print(prefixes)
        return 'fail'

    return 'success'

###############################################################################
# Test gdal.GetFileSystemOptions()


def test_vsifile_19():

    for prefix in gdal.GetFileSystemsPrefixes():
        options = gdal.GetFileSystemOptions(prefix)
        # Check that the options is XML correct
        if options is not None:
            ret = gdal.ParseXMLString(options)
            if ret is None:
                print(prefix, options)
                return 'fail'

    return 'success'

###############################################################################
# Test gdal.VSIFReadL with None fp


def test_vsifile_20():

    try:
        gdal.VSIFReadL(1, 1, None)
    except ValueError:
        return 'success'

    return 'fail'

###############################################################################
# Test gdal.VSIGetMemFileBuffer_unsafe() and gdal.VSIFWriteL() reading buffers


def test_vsifile_21():

    filename = '/vsimem/read.tif'
    filename_write = '/vsimem/write.tif'
    data = 'This is some data'

    vsifile = gdal.VSIFOpenL(filename, 'wb')
    if gdal.VSIFWriteL(data, 1, len(data), vsifile) != len(data):
        return 'fail'
    gdal.VSIFCloseL(vsifile)

    vsifile = gdal.VSIFOpenL(filename, 'rb')
    gdal.VSIFSeekL(vsifile, 0, 2)
    vsilen = gdal.VSIFTellL(vsifile)
    gdal.VSIFSeekL(vsifile, 0, 0)
    data_read = gdal.VSIFReadL(1, vsilen, vsifile)
    data_mem = gdal.VSIGetMemFileBuffer_unsafe(filename)
    if data_read != data_mem[:]:
        return 'fail'
    gdal.VSIFCloseL(vsifile)
    vsifile_write = gdal.VSIFOpenL(filename_write, 'wb')
    if gdal.VSIFWriteL(data_mem, 1, len(data_mem), vsifile_write) != len(data_mem):
        return 'fail'
    gdal.VSIFCloseL(vsifile_write)
    gdal.Unlink(filename)
    gdal.Unlink(filename_write)
    with gdaltest.error_handler():
        data3 = gdal.VSIGetMemFileBuffer_unsafe(filename)
        if data3 != None:
            return 'fail'

    return 'success'


def test_vsifile_22():
    # VSIOpenL doesn't set errorno
    gdal.VSIErrorReset()
    if gdal.VSIGetLastErrorNo() != 0:
        gdaltest.post_reason("Expected Err=0 after VSIErrorReset(), got %d" % gdal.VSIGetLastErrorNo())
        return 'fail'

    fp = gdal.VSIFOpenL('tmp/not-existing', 'r')
    if fp is not None:
        gdaltest.post_reason("Expected None from VSIFOpenL")
        return 'fail'
    if gdal.VSIGetLastErrorNo() != 0:
        gdaltest.post_reason("Expected Err=0 from VSIFOpenL, got %d" % gdal.VSIGetLastErrorNo())
        return 'fail'

    # VSIOpenExL does
    fp = gdal.VSIFOpenExL('tmp/not-existing', 'r', 1)
    if fp is not None:
        gdaltest.post_reason("Expected None from VSIFOpenExL")
        return 'fail'
    if gdal.VSIGetLastErrorNo() != 1:
        gdaltest.post_reason("Expected Err=1 from VSIFOpenExL, got %d" % gdal.VSIGetLastErrorNo())
        return 'fail'
    if len(gdal.VSIGetLastErrorMsg()) == 0:
        gdaltest.post_reason("Expected a VSI error message")
        return 'fail'
    gdal.VSIErrorReset()
    if gdal.VSIGetLastErrorNo() != 0:
        gdaltest.post_reason("Expected Err=0 after VSIErrorReset(), got %d" % gdal.VSIGetLastErrorNo())
        return 'fail'

    return 'success'


###############################################################################
# Test bugfix for https://github.com/OSGeo/gdal/issues/675


def test_vsitar_bug_675():

    content = gdal.ReadDir('/vsitar/data/tar_with_star_base256_fields.tar')
    if len(content) != 1:
        print(content)
        return 'fail'
    return 'success'

###############################################################################
# Test multithreaded compression


def test_vsigzip_multi_thread():

    with gdaltest.config_options({'GDAL_NUM_THREADS': 'ALL_CPUS',
                                  'CPL_VSIL_DEFLATE_CHUNK_SIZE': '32K'}):
        f = gdal.VSIFOpenL('/vsigzip//vsimem/vsigzip_multi_thread.gz', 'wb')
        for i in range(100000):
            gdal.VSIFWriteL('hello', 1, 5, f)
        gdal.VSIFCloseL(f)

    f = gdal.VSIFOpenL('/vsigzip//vsimem/vsigzip_multi_thread.gz', 'rb')
    data = gdal.VSIFReadL(100000, 5, f).decode('ascii')
    gdal.VSIFCloseL(f)

    gdal.Unlink('/vsimem/vsigzip_multi_thread.gz')

    if data != 'hello' * 100000:
        for i in range(10000):
            if data[i*5:i*5+5] != 'hello':
                print(i*5, data[i*5:i*5+5], data[i*5-5:i*5+5-5])
                break

        return 'fail'

    return 'success'

###############################################################################
# Test vsisync()


def test_vsisync():

    with gdaltest.error_handler():
        if gdal.Sync('/i_do/not/exist', '/vsimem/'):
            return 'fail'

    with gdaltest.error_handler():
        if gdal.Sync('vsifile.py', '/i_do/not/exist'):
            return 'fail'

    # Test copying a file
    for i in range(2):
        if not gdal.Sync('vsifile.py', '/vsimem/'):
            return 'fail'
        if gdal.VSIStatL('/vsimem/vsifile.py').size != gdal.VSIStatL('vsifile.py').size:
            return 'fail'
    gdal.Unlink('/vsimem/vsifile.py')

    # Test copying the content of a directory
    gdal.Mkdir('/vsimem/test_sync', 0)
    gdal.FileFromMemBuffer('/vsimem/test_sync/foo.txt', 'bar')
    gdal.Mkdir('/vsimem/test_sync/subdir', 0)
    gdal.FileFromMemBuffer('/vsimem/test_sync/subdir/bar.txt', 'baz')

    if sys.platform != 'win32':
        with gdaltest.error_handler():
            if gdal.Sync('/vsimem/test_sync/', '/i_do_not/exist'):
                return 'fail'

    if not gdal.Sync('/vsimem/test_sync/', '/vsimem/out'):
        return 'fail'
    if gdal.ReadDir('/vsimem/out') != [ 'foo.txt', 'subdir' ]:
        print(gdal.ReadDir('/vsimem/out'))
        return 'fail'
    if gdal.ReadDir('/vsimem/out/subdir') != [ 'bar.txt' ]:
        print(gdal.ReadDir('/vsimem/out/subdir'))
        return 'fail'
    # Again
    if not gdal.Sync('/vsimem/test_sync/', '/vsimem/out'):
        return 'fail'

    gdal.RmdirRecursive('/vsimem/out')

    # Test copying a directory
    pct_values = []
    def my_progress(pct, message, user_data):
        pct_values.append(pct)

    if not gdal.Sync('/vsimem/test_sync', '/vsimem/out', callback = my_progress):
        return 'fail'

    if pct_values != [0.5, 1.0]:
        print(pct_values)
        return 'fail'

    if gdal.ReadDir('/vsimem/out') != [ 'test_sync' ]:
        print(gdal.ReadDir('/vsimem/out'))
        return 'fail'
    if gdal.ReadDir('/vsimem/out/test_sync') != [ 'foo.txt', 'subdir' ]:
        print(gdal.ReadDir('/vsimem/out/test_sync'))
        return 'fail'

    gdal.RmdirRecursive('/vsimem/test_sync')
    gdal.RmdirRecursive('/vsimem/out')

    return 'success'

###############################################################################
# Test gdal.OpenDir()

def test_vsifile_opendir():

    # Non existing dir
    d = gdal.OpenDir('/vsimem/i_dont_exist')
    if d:
        return 'fail'

    gdal.Mkdir('/vsimem/vsifile_opendir', 0o755)

    # Empty dir
    d = gdal.OpenDir('/vsimem/vsifile_opendir')
    if not d:
        return 'fail'
    entry = gdal.GetNextDirEntry(d)
    if entry:
        return 'fail'
    gdal.CloseDir(d)

    gdal.FileFromMemBuffer('/vsimem/vsifile_opendir/test', 'foo')
    gdal.Mkdir('/vsimem/vsifile_opendir/subdir', 0o755)
    gdal.Mkdir('/vsimem/vsifile_opendir/subdir/subdir2', 0o755)
    gdal.FileFromMemBuffer('/vsimem/vsifile_opendir/subdir/subdir2/test2', 'bar')

    # Unlimited depth
    d = gdal.OpenDir('/vsimem/vsifile_opendir')

    entry = gdal.GetNextDirEntry(d)
    if entry.name != 'subdir':
        print(entry.name)
        return 'fail'
    if entry.mode != 16384:
        print(entry.mode)
        return 'fail'

    entry = gdal.GetNextDirEntry(d)
    if entry.name != 'subdir/subdir2':
        print(entry.name)
        return 'fail'
    if entry.mode != 16384:
        print(entry.mode)
        return 'fail'

    entry = gdal.GetNextDirEntry(d)
    if entry.name != 'subdir/subdir2/test2':
        print(entry.name)
        return 'fail'
    if entry.mode != 32768:
        print(entry.mode)
        return 'fail'

    entry = gdal.GetNextDirEntry(d)
    if entry.name != 'test':
        print(entry.name)
        return 'fail'
    if entry.mode != 32768:
        print(entry.mode)
        return 'fail'
    if not entry.modeKnown:
        return 'fail'
    if entry.size != 3:
        return 'fail'
    if not entry.sizeKnown:
        return 'fail'
    if entry.mtime == 0:
        return 'fail'
    if not entry.mtimeKnown:
        return 'fail'
    if entry.extra:
        return 'fail'

    entry = gdal.GetNextDirEntry(d)
    if entry:
        return 'fail'
    gdal.CloseDir(d)

    # Only top level
    d = gdal.OpenDir('/vsimem/vsifile_opendir', 0)
    entry = gdal.GetNextDirEntry(d)
    if entry.name != 'subdir':
        print(entry.name)
        return 'fail'
    entry = gdal.GetNextDirEntry(d)
    if entry.name != 'test':
        print(entry.name)
        return 'fail'
    entry = gdal.GetNextDirEntry(d)
    if entry:
        return 'fail'
    gdal.CloseDir(d)

    # Depth 1
    files = [l_entry.name for l_entry in gdal.listdir('/vsimem/vsifile_opendir', 1)]
    if files != ['subdir', 'subdir/subdir2', 'test']:
        print(files)
        return 'fail'

    gdal.RmdirRecursive('/vsimem/vsifile_opendir')

    return 'success'


gdaltest_list = [test_vsifile_1,
                 test_vsifile_2,
                 test_vsifile_3,
                 test_vsifile_4,
                 test_vsifile_5,
                 test_vsifile_6,
                 test_vsifile_7,
                 test_vsifile_8,
                 test_vsifile_9,
                 test_vsifile_10,
                 test_vsifile_11,
                 test_vsifile_12,
                 test_vsifile_13,
                 test_vsifile_14,
                 test_vsifile_15,
                 test_vsifile_16,
                 test_vsifile_17,
                 test_vsifile_18,
                 test_vsifile_19,
                 test_vsifile_20,
                 test_vsifile_21,
                 test_vsifile_22,
                 test_vsitar_bug_675,
                 test_vsigzip_multi_thread,
                 test_vsifile_opendir,
                 test_vsisync]

if __name__ == '__main__':

    gdaltest.setup_run('vsifile')

    gdaltest.run_tests(gdaltest_list)

    sys.exit(gdaltest.summarize())
