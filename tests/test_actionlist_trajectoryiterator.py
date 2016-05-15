#!/usr/bin/env python

from __future__ import print_function
import unittest
import pytraj as pt
from pytraj.testing import get_fn, aa_eq, eq
import nose.tools as nt

fn, tn = get_fn('tz2_dry')

class TestActionList(unittest.TestCase):
    def test_transform_trajectory_iterator(self):
        
        traj0 = pt.load(fn, tn)
        traj1 = pt.load(fn, tn)
        traj2 = pt.load(fn, tn)
        
        # Use ActionList for traj0
        actlist = pt.ActionList(top=traj0.top)
        actlist.add("translate", "x 1.2")
        actlist.add("center", "origin")
        actlist.add("rotate", "x 45.")
        
        for frame in traj0:
            actlist.compute(frame)
        
        # use transformation
        itertraj = pt.transform(traj1, by=['translate x 1.2', 'center origin', 'rotate x 45.'])
        for frame in itertraj:
            pass
        
        aa_eq(traj0.xyz, traj1.xyz)
        
        # use API
        traj2.translate('x 1.2')
        traj2.center('origin')
        traj2.rotate('x 45.')
        
        aa_eq(traj0.xyz, traj2.xyz)

    def test_transform_trajectory_iterator_API(self):
        traj_on_disk = pt.iterload(fn, tn)
        traj_on_mem = pt.load(fn, tn)

        (traj_on_mem
         .translate('x 1.2')
         .center('origin')
         .rotate('x 40.'))

        (traj_on_disk
         .translate('x 1.2')
         .center('origin')
         .rotate('x 40.'))

        aa_eq(traj_on_disk.xyz, traj_on_mem.xyz)

    def test_combination_of_differnt_transformations(self):
        traj_on_disk = pt.iterload(fn, tn)
        traj_on_disk_2 = pt.iterload(fn, tn)
        traj_on_mem = pt.load(fn, tn)

        ref = pt.autoimage(traj_on_disk[:1])

        # note: if using autoimage, must provide pre-processed reference
        (traj_on_mem
         .autoimage()
         .superpose(ref=ref)
         .scale('x 1.2'))

        (traj_on_disk
         .autoimage()
         .superpose(ref=ref)
         .scale('x 1.2'))

        aa_eq(traj_on_disk.xyz, traj_on_mem.xyz)

        # remove
        traj_on_disk._remove_transformations()
        aa_eq(traj_on_disk.xyz, traj_on_disk_2.xyz)

        nt.assert_equal(len(traj_on_disk._cdslist), 0)

    def test_autoimage_and_slicing(self):
        traj_on_disk = pt.datafiles.load_tz2_ortho()
        traj_on_mem = traj_on_disk[:]
        aa_eq(traj_on_disk.xyz, traj_on_mem.xyz)

        aa_eq(traj_on_disk.autoimage().xyz, traj_on_mem.autoimage().xyz)

        aa_eq(traj_on_mem[:1].xyz, traj_on_disk[:1].xyz)
        aa_eq(traj_on_mem[:].xyz, traj_on_disk[:].xyz)

        from pytraj.externals.six import zip

        for f0, f1 in zip(traj_on_disk(0, 8, 2), traj_on_mem(0, 8, 2)):
            aa_eq(f0.xyz, f1.xyz)


if __name__ == "__main__":
    unittest.main()
