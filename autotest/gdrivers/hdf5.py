#!/usr/bin/env python
# -*- coding: utf-8 -*-
###############################################################################
# $Id$
#
# Project:  GDAL/OGR Test Suite
# Purpose:  Test read functionality for HDF5 driver.
# Author:   Even Rouault <even dot rouault at mines dash paris dot org>
#
###############################################################################
# Copyright (c) 2008-2013, Even Rouault <even dot rouault at mines-paris dot org>
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
import shutil

import pytest

from osgeo import gdal


import gdaltest

from uffd import uffd_compare

###############################################################################
# Test if HDF5 driver is present


pytestmark = pytest.mark.require_driver('HDF5')


@pytest.fixture(autouse=True)
def check_no_file_leaks():
    num_files = len(gdaltest.get_opened_files())

    yield

    diff = len(gdaltest.get_opened_files()) - num_files
    assert diff == 0, 'Leak of file handles: %d leaked' % diff


###############################################################################
# Confirm expected subdataset information.


def test_hdf5_2():
    ds = gdal.Open('data/groups.h5')

    sds_list = ds.GetMetadata('SUBDATASETS')

    if len(sds_list) != 4:
        print(sds_list)
        gdaltest.post_reason('Did not get expected subdataset count.')
        return 'fail'

    if sds_list['SUBDATASET_1_NAME'] != 'HDF5:"data/groups.h5"://MyGroup/Group_A/dset2' \
       or sds_list['SUBDATASET_2_NAME'] != 'HDF5:"data/groups.h5"://MyGroup/dset1':
        print(sds_list)
        gdaltest.post_reason('did not get expected subdatasets.')
        return 'fail'

    ds = None

    if gdaltest.is_file_open('data/groups.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    return 'success'

###############################################################################
# Confirm that single variable files can be accessed directly without
# subdataset stuff.


def test_hdf5_3():

    ds = gdal.Open('HDF5:"data/u8be.h5"://TestArray')

    cs = ds.GetRasterBand(1).Checksum()
    if cs != 135:
        gdaltest.post_reason('did not get expected checksum')
        return 'fail'

    ds = None

    if gdaltest.is_file_open('data/u8be.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    return 'success'

###############################################################################
# Confirm subdataset access, and checksum.


def test_hdf5_4():

    ds = gdal.Open('HDF5:"data/u8be.h5"://TestArray')

    cs = ds.GetRasterBand(1).Checksum()
    if cs != 135:
        gdaltest.post_reason('did not get expected checksum')
        return 'fail'

    return 'success'

###############################################################################
# Similar check on a 16bit dataset.


def test_hdf5_5():

    ds = gdal.Open('HDF5:"data/groups.h5"://MyGroup/dset1')

    cs = ds.GetRasterBand(1).Checksum()
    if cs != 18:
        gdaltest.post_reason('did not get expected checksum')
        return 'fail'

    return 'success'

###############################################################################
# Test generating an overview on a subdataset.


def test_hdf5_6():

    shutil.copyfile('data/groups.h5', 'tmp/groups.h5')

    ds = gdal.Open('HDF5:"tmp/groups.h5"://MyGroup/dset1')
    ds.BuildOverviews(overviewlist=[2])
    ds = None

    if gdaltest.is_file_open('tmp/groups.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    ds = gdal.Open('HDF5:"tmp/groups.h5"://MyGroup/dset1')
    if ds.GetRasterBand(1).GetOverviewCount() != 1:
        gdaltest.post_reason('failed to find overview')
        return 'fail'
    ds = None

    # confirm that it works with a different path. (#3290)

    ds = gdal.Open('HDF5:"data/../tmp/groups.h5"://MyGroup/dset1')
    if ds.GetRasterBand(1).GetOverviewCount() != 1:
        gdaltest.post_reason('failed to find overview with alternate path')
        return 'fail'
    ovfile = ds.GetMetadataItem('OVERVIEW_FILE', 'OVERVIEWS')
    if ovfile[:11] != 'data/../tmp':
        print(ovfile)
        gdaltest.post_reason('did not get expected OVERVIEW_FILE.')
        return 'fail'
    ds = None

    gdaltest.clean_tmp()

    return 'success'

###############################################################################
# Coarse metadata check (regression test for #2412).


def test_hdf5_7():

    ds = gdal.Open('data/metadata.h5')
    metadata = ds.GetMetadata()
    metadataList = ds.GetMetadata_List()
    ds = None

    if gdaltest.is_file_open('data/metadata.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    if len(metadata) != len(metadataList):
        gdaltest.post_reason('error in metadata dictionary setup')
        return 'fail'

    metadataList = [item.split('=', 1)[0] for item in metadataList]
    for key in metadataList:
        try:
            metadata.pop(key)
        except KeyError:
            gdaltest.post_reason('unable to find "%s" key' % key)
            return 'fail'
    return 'success'

###############################################################################
# Test metadata names.


def test_hdf5_8():

    ds = gdal.Open('data/metadata.h5')
    metadata = ds.GetMetadata()
    ds = None

    if not metadata:
        gdaltest.post_reason('no metadata found')
        return 'fail'

    h5groups = ['G1', 'Group with spaces', 'Group_with_underscores',
                'Group with spaces_and_underscores']
    h5datasets = ['D1', 'Dataset with spaces', 'Dataset_with_underscores',
                  'Dataset with spaces_and_underscores']
    attributes = {
        'attribute': 'value',
        'attribute with spaces': 0,
        'attribute_with underscores': 0,
        'attribute with spaces_and_underscores': .1,
    }

    def scanMetadata(parts):
        for attr in attributes:
            name = '_'.join(parts + [attr])
            name = name.replace(' ', '_')
            if name not in metadata:
                gdaltest.post_reason('unable to find metadata: "%s"' % name)
                return 'fail'

            value = metadata.pop(name)

            value = value.strip(' d')
            value = type(attributes[attr])(value)
            if value != attributes[attr]:
                gdaltest.post_reason('incorrect metadata value for "%s": '
                                     '"%s" != "%s"' % (name, value,
                                                       attributes[attr]))
                return 'fail'

    # level0
    if scanMetadata([]) is not None:
        return 'fail'

    # level1 datasets
    for h5dataset in h5datasets:
        if scanMetadata([h5dataset]) is not None:
            return 'fail'

    # level1 groups
    for h5group in h5groups:
        if scanMetadata([h5group]) is not None:
            return 'fail'

        # level2 datasets
        for h5dataset in h5datasets:
            if scanMetadata([h5group, h5dataset]) is not None:
                return 'fail'

    return 'success'

###############################################################################
# Variable length string metadata check (regression test for #4228).


def test_hdf5_9():

    if int(gdal.VersionInfo('VERSION_NUM')) < 1900:
        gdaltest.post_reason('would crash')
        return 'skip'

    ds = gdal.Open('data/vlstr_metadata.h5')
    metadata = ds.GetRasterBand(1).GetMetadata()
    ds = None
    if gdaltest.is_file_open('data/vlstr_metadata.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    ref_metadata = {
        'TEST_BANDNAMES': 'SAA',
        'TEST_CODING': '0.6666666667 0.0000000000 TRUE',
        'TEST_FLAGS': '255=noValue',
        'TEST_MAPPING': 'Geographic Lat/Lon 0.5000000000 0.5000000000 27.3154761905 -5.0833333333 0.0029761905 0.0029761905 WGS84 Degrees',
        'TEST_NOVALUE': '255',
        'TEST_RANGE': '0 255 0 255',
    }

    if len(metadata) != len(ref_metadata):
        gdaltest.post_reason('incorrect number of metadata: '
                             'expected %d, got %d' % (len(ref_metadata),
                                                      len(metadata)))
        return 'fail'

    for key in metadata:
        if key not in ref_metadata:
            gdaltest.post_reason('unexpected metadata key "%s"' % key)
            return 'fail'

        if metadata[key] != ref_metadata[key]:
            gdaltest.post_reason('incorrect metadata value for key "%s": '
                                 'expected "%s", got "%s" ' %
                                 (key, ref_metadata[key], metadata[key]))
            return 'fail'

    return 'success'

###############################################################################
# Test CSK_DGM.h5 (#4160)


def test_hdf5_10():

    # Try opening the QLK subdataset to check that no error is generated
    gdal.ErrorReset()
    ds = gdal.Open('HDF5:"data/CSK_DGM.h5"://S01/QLK')
    if ds is None or gdal.GetLastErrorMsg() != '':
        return 'fail'
    ds = None

    ds = gdal.Open('HDF5:"data/CSK_DGM.h5"://S01/SBI')
    got_gcpprojection = ds.GetGCPProjection()
    if got_gcpprojection.find('GEOGCS["WGS 84",DATUM["WGS_1984"') != 0:
        print(got_gcpprojection)
        return 'fail'

    got_gcps = ds.GetGCPs()
    if len(got_gcps) != 4:
        return 'fail'

    if abs(got_gcps[0].GCPPixel - 0) > 1e-5 or abs(got_gcps[0].GCPLine - 0) > 1e-5 or \
       abs(got_gcps[0].GCPX - 12.2395902509238) > 1e-5 or abs(got_gcps[0].GCPY - 44.7280047434954) > 1e-5:
        return 'fail'

    ds = None
    if gdaltest.is_file_open('data/CSK_DGM.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    return 'success'

###############################################################################
# Test CSK_GEC.h5 (#4160)


def test_hdf5_11():

    # Try opening the QLK subdataset to check that no error is generated
    gdal.ErrorReset()
    ds = gdal.Open('HDF5:"data/CSK_GEC.h5"://S01/QLK')
    if ds is None or gdal.GetLastErrorMsg() != '':
        return 'fail'
    ds = None

    ds = gdal.Open('HDF5:"data/CSK_GEC.h5"://S01/SBI')
    got_projection = ds.GetProjection()
    if got_projection.find('PROJCS["Transverse_Mercator",GEOGCS["WGS 84",DATUM["WGS_1984"') != 0:
        print(got_projection)
        return 'fail'

    got_gt = ds.GetGeoTransform()
    expected_gt = (275592.5, 2.5, 0.0, 4998152.5, 0.0, -2.5)
    for i in range(6):
        if abs(got_gt[i] - expected_gt[i]) > 1e-5:
            print(got_gt)
            return 'fail'

    ds = None

    if gdaltest.is_file_open('data/CSK_GEC.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    return 'success'

###############################################################################
# Test ODIM_H5 (#5032)


def test_hdf5_12():

    if not gdaltest.download_file('http://trac.osgeo.org/gdal/raw-attachment/ticket/5032/norsa.ss.ppi-00.5-dbz.aeqd-1000.20070601T000039Z.hdf', 'norsa.ss.ppi-00.5-dbz.aeqd-1000.20070601T000039Z.hdf'):
        return 'skip'

    ds = gdal.Open('tmp/cache/norsa.ss.ppi-00.5-dbz.aeqd-1000.20070601T000039Z.hdf')
    got_projection = ds.GetProjection()
    if got_projection.find('Azimuthal_Equidistant') < 0:
        print(got_projection)
        return 'fail'

    got_gt = ds.GetGeoTransform()
    expected_gt = (-240890.02470187756, 1001.7181388478905, 0.0, 239638.21326987055, 0.0, -1000.3790932482976)
    # Proj 4.9.3
    expected_gt2 = (-240889.94573659054, 1001.7178235672992, 0.0, 239638.28570609915, 0.0, -1000.3794089534567)

    if max([abs(got_gt[i] - expected_gt[i]) for i in range(6)]) > 1e-5 and \
       max([abs(got_gt[i] - expected_gt2[i]) for i in range(6)]) > 1e-5:
        print(got_gt)
        return 'fail'

    return 'success'

###############################################################################
# Test MODIS L2 HDF5 GCPs (#6666)


def test_hdf5_13():

    if not gdaltest.download_file('http://oceandata.sci.gsfc.nasa.gov/cgi/getfile/A2016273115000.L2_LAC_OC.nc', 'A2016273115000.L2_LAC_OC.nc'):
        return 'skip'

    ds = gdal.Open('HDF5:"tmp/cache/A2016273115000.L2_LAC_OC.nc"://geophysical_data/Kd_490')

    got_gcps = ds.GetGCPs()
    if len(got_gcps) != 3030:
        return 'fail'

    if abs(got_gcps[0].GCPPixel - 0.5) > 1e-5 or abs(got_gcps[0].GCPLine - 0.5) > 1e-5 or \
       abs(got_gcps[0].GCPX - 33.1655693) > 1e-5 or abs(got_gcps[0].GCPY - 39.3207207) > 1e-5:
        print(got_gcps[0])
        return 'fail'

    return 'success'

###############################################################################
# Test complex data subsets


def test_hdf5_14():

    ds = gdal.Open('data/complex.h5')
    sds_list = ds.GetMetadata('SUBDATASETS')

    if len(sds_list) != 6:
        print(sds_list)
        gdaltest.post_reason('Did not get expected complex subdataset count.')
        return 'fail'

    if sds_list['SUBDATASET_1_NAME'] != 'HDF5:"data/complex.h5"://f16' \
            or sds_list['SUBDATASET_2_NAME'] != 'HDF5:"data/complex.h5"://f32' \
            or sds_list['SUBDATASET_3_NAME'] != 'HDF5:"data/complex.h5"://f64':
        print(sds_list)
        gdaltest.post_reason('did not get expected subdatasets.')
        return 'fail'

    ds = None

    if gdaltest.is_file_open('data/complex.h5'):
        gdaltest.post_reason('file still opened.')
        return 'fail'

    return 'success'

###############################################################################
# Confirm complex subset data access and checksum
# Start with Float32


def test_hdf5_15():

    ds = gdal.Open('HDF5:"data/complex.h5"://f32')

    cs = ds.GetRasterBand(1).Checksum()
    if cs != 523:
        gdaltest.post_reason('did not get expected checksum')
        return 'fail'

    return 'success'

# Repeat for Float64


def test_hdf5_16():

    ds = gdal.Open('HDF5:"data/complex.h5"://f64')

    cs = ds.GetRasterBand(1).Checksum()
    if cs != 511:
        gdaltest.post_reason('did not get expected checksum')
        return 'fail'

    return 'success'

# Repeat for Float16


def test_hdf5_17():

    ds = gdal.Open('HDF5:"data/complex.h5"://f16')

    cs = ds.GetRasterBand(1).Checksum()
    if cs != 412:
        gdaltest.post_reason('did not get expected checksum')
        return 'fail'

    return 'success'


def test_hdf5_single_char_varname():

    ds = gdal.Open('HDF5:"data/single_char_varname.h5"://e')
    if ds is None:
        return 'fail'

    return 'success'


def test_hdf5_virtual_file():
    hdf5_files = [
        'CSK_GEC.h5',
        'vlstr_metadata.h5',
        'groups.h5',
        'complex.h5',
        'single_char_varname.h5',
        'CSK_DGM.h5',
        'u8be.h5',
        'metadata.h5'
    ]
    for hdf5_file in hdf5_files:
        if uffd_compare(hdf5_file) is not True:
            return 'fail'

    return 'success'


# FIXME: This FTP server seems to have disappeared. Replace with something else?
hdf5_list = [
    ('ftp://ftp.hdfgroup.uiuc.edu/pub/outgoing/hdf_files/hdf5/samples/convert', 'C1979091.h5',
        'HDF4_PALGROUP/HDF4_PALETTE_2', 7488, -1),
    ('ftp://ftp.hdfgroup.uiuc.edu/pub/outgoing/hdf_files/hdf5/samples/convert', 'C1979091.h5',
        'Raster_Image_#0', 3661, -1),
    ('ftp://ftp.hdfgroup.uiuc.edu/pub/outgoing/hdf_files/hdf5/geospatial/DEM', 'half_moon_bay.grid',
        'HDFEOS/GRIDS/DEMGRID/Data_Fields/Elevation', 30863, -1),
]


@pytest.mark.parametrize(
    'downloadURL,fileName,subdatasetname,checksum,download_size',
    hdf5_list,
    ids=['HDF5:"' + item[1] + '"://' + item[2] for item in hdf5_list],
)
def test_hdf5(downloadURL, fileName, subdatasetname, checksum, download_size):
    if not gdaltest.download_file(downloadURL + '/' + fileName, fileName, download_size):
        pytest.skip('no download')

    ds = gdal.Open('HDF5:"tmp/cache/' + fileName + '"://' + subdatasetname)

    assert ds.GetRasterBand(1).Checksum() == checksum, 'Bad checksum. Expected %d, got %d' % (checksum, ds.GetRasterBand(1).Checksum())


gdaltest_list = [
    test_hdf5_2,
    test_hdf5_3,
    test_hdf5_4,
    test_hdf5_5,
    test_hdf5_6,
    test_hdf5_7,
    test_hdf5_8,
    test_hdf5_9,
    test_hdf5_10,
    test_hdf5_11,
    test_hdf5_12,
    test_hdf5_13,
    test_hdf5_14,
    test_hdf5_15,
    test_hdf5_16,
    test_hdf5_17,
    test_hdf5_single_char_varname,
    test_hdf5_virtual_file,
]


if __name__ == '__main__':

    gdaltest.setup_run('hdf5')

    gdaltest.run_tests(gdaltest_list)

    sys.exit(gdaltest.summarize())
