#!/usr/bin/env python

from __future__ import print_function
import unittest
import numpy as np
import pytraj as pt
from utils import fn
from pytraj.testing import aa_eq
import pytest

from utils import tz2_trajin, tz2_top


class TestPCA(unittest.TestCase):
    def test_pca_noref(self):
        '''test_pca_noref: no reference
        
        pytraj: pt.pca(traj, mask, n_vecs=2) 
        '''

        command = '''
        # Step one. Generate average structure.
        # RMS-Fit to first frame to remove global translation/rotation.
        parm {tz2_top}
        trajin {tz2_trajin}

        rms first !@H=
        average crdset AVG
        run

        # Step two. RMS-Fit to average structure. Calculate covariance matrix.
        # Save the fit coordinates.
        rms ref AVG !@H=
        matrix covar name MyMatrix !@H=
        createcrd CRD1
        run

        # Step three. Diagonalize matrix.
        runanalysis diagmatrix MyMatrix vecs 2 name MyEvecs

        # Step four. Project saved fit coordinates along eigenvectors 1 and 2
        crdaction CRD1 projection evecs MyEvecs !@H= out project.dat beg 1 end 2
        '''.format(
            tz2_top=tz2_top, tz2_trajin=tz2_trajin)

        traj = pt.load(fn('tz2.nc'), fn('tz2.parm7'))

        # no reference
        state = pt.load_cpptraj_state(command)
        state.run()

        mask = '!@H='

        data = pt.pca(traj, mask, n_vecs=2)
        cpp_data = state.data[-2:].values
        # use absolute values
        aa_eq(np.abs(data[0]), np.abs(cpp_data), decimal=3)

    def test_pca_noref_nofit(self):
        '''test_pca_noref_nofit:  no reference and do not do fitting
        
        from drroe: " Also, not fitting at all should be considered a legitimate option - 
        you may want to include global rotational and translational motion in your eigenvectors."

        pytraj: pt.pca(traj, mask, n_vecs=2, fit=False)
        '''

        command = '''
        parm {}
        trajin {}

        matrix covar name MyMatrix !@H=
        createcrd CRD1
        run

        # Step three. Diagonalize matrix.
        runanalysis diagmatrix MyMatrix vecs 2 name MyEvecs

        # Step four. Project saved fit coordinates along eigenvectors 1 and 2
        crdaction CRD1 projection evecs MyEvecs !@H= out project.dat beg 1 end 2
        '''.format(tz2_top, tz2_trajin)

        traj = pt.load(fn('tz2.nc'), fn('tz2.parm7'))

        # no reference
        state = pt.load_cpptraj_state(command)
        state.run()

        mask = '!@H='

        data = pt.pca(traj, mask, n_vecs=2, fit=False)
        data_ref = pt.pca(
            traj, mask, n_vecs=2, fit=False, ref=3, ref_mask='@CA')
        cpp_data = state.data[-2:].values
        # use absolute values
        aa_eq(np.abs(data[0]), np.abs(cpp_data), decimal=3)
        # if fit=True, ref will be ignored
        aa_eq(np.abs(data_ref[0]), np.abs(cpp_data), decimal=3)

    def test_pca_with_ref(self):
        '''test_pca_with_ref: has reference

        from drroe: "If the user provides their own reference structure, do not create an average structure"

        pytraj: pt.pca(traj, mask, n_vecs=2, ref=ref)
        '''

        command_ref_provided = '''
        parm {}
        trajin {}
        reference {}

        rms reference !@H=

        matrix covar name MyMatrix !@H=
        createcrd CRD1
        run

        # Step three. Diagonalize matrix.
        runanalysis diagmatrix MyMatrix vecs 2 name MyEvecs

        # Step four. Project saved fit coordinates along eigenvectors 1 and 2
        crdaction CRD1 projection evecs MyEvecs !@H= out project.dat beg 1 end 2
        '''.format(tz2_top, tz2_trajin, fn('tz2.rst7'))

        traj = pt.load(fn('tz2.nc'), fn('tz2.parm7'))
        ref = pt.load(fn('tz2.rst7'), traj.top)

        state = pt.load_cpptraj_state(command_ref_provided)
        state.run()

        mask = '!@H='

        data = pt.pca(traj, mask, n_vecs=2, ref=ref)
        cpp_data = state.data[-2:].values

        # use absolute values
        aa_eq(np.abs(data[0]), np.abs(cpp_data), decimal=3)

    def test_pca_with_ref_with_different_mask_from_matrix(self):
        '''test_pca_with_ref_with_different_mask_from_matrix
        has reference. Use !@H= for ref_mask and use * for covariance matrix  and projection

        from drroe: "You should be able to supply separate masks for fitting and creating the covariance matrix
        It is common enough for example to only perform rms-fitting on heavy atoms while still wanting all atoms in eigenvectors."

        pytraj: pt.pca(traj, mask=mask_matrix, n_vecs=2, ref=ref, ref_mask=mask_ref)
        '''

        command_ref_provided = '''
        parm {}
        trajin {} 1 3

        reference {}

        # only perform fitting on heavy atoms
        rms reference !@H=

        # all atoms
        matrix covar name MyMatrix *
        createcrd CRD1
        run

        # Step three. Diagonalize matrix.
        runanalysis diagmatrix MyMatrix vecs 2 name MyEvecs

        # Step four. Project saved fit coordinates along eigenvectors 1 and 2
        # all atoms
        crdaction CRD1 projection evecs MyEvecs * out project.dat beg 1 end 2
        '''.format(tz2_top, tz2_trajin, fn('tz2.rst7'))

        traj = pt.load(fn('tz2.nc'), fn('tz2.parm7'),
                frame_indices=range(0, 3))
        traj_on_disk = pt.iterload(fn('tz2.nc'), fn('tz2.parm7'),
                frame_slice=[(0, 3)])
        ref = pt.load(fn('tz2.rst7'), traj.top)

        state = pt.load_cpptraj_state(command_ref_provided)
        state.run()

        mask_ref = '!@H='
        mask_matrix = '*'

        data = pt.pca(
            traj, mask=mask_matrix, n_vecs=2, ref=ref, ref_mask=mask_ref)
        data2 = pt.pca(
            traj_on_disk,
            mask=mask_matrix,
            n_vecs=2,
            ref=ref,
            ref_mask=mask_ref)
        cpp_data = state.data[-2:].values
        # use absolute values
        aa_eq(np.abs(data[0]), np.abs(cpp_data), decimal=3)
        aa_eq(np.abs(data2[0]), np.abs(cpp_data), decimal=3)

    def test_traj_on_disk_nofit(self):
        """test_traj_on_disk_nofit
        """
        fit = False
        traj_on_disk = pt.iterload(fn('tz2.nc'), fn('tz2.parm7'))
        traj_on_mem = pt.load(fn('tz2.nc'), fn('tz2.parm7'))
        data0, _ = pt.pca(traj_on_disk, mask='@CA', n_vecs=2, fit=fit)
        data1, _ = pt.pca(traj_on_mem, mask='@CA', n_vecs=2, fit=fit)
        aa_eq(np.abs(data0), np.abs(data1))

    def test_traj_on_disk_default_values(self):
        """test_traj_on_disk_default_values
        """
        traj_on_disk = pt.iterload(fn('tz2.nc'), fn('tz2.parm7'))
        traj_on_mem = pt.load(fn('tz2.nc'), fn('tz2.parm7'))

        data0, _ = pt.pca(traj_on_disk, mask='@CA')
        data1, _ = pt.pca(traj_on_mem, mask='@CA')
        aa_eq(np.abs(data0), np.abs(data1))

    def test_traj_on_disk_fit_to_given_reference(self):
        """test_traj_on_disk_fit_to_given_reference
        """
        fit = True
        traj_on_disk = pt.iterload(fn('tz2.nc'), fn('tz2.parm7'))
        traj_on_mem = pt.load(fn('tz2.nc'), fn('tz2.parm7'))
        ref0 = traj_on_disk[0]
        ref1 = traj_on_mem[0]

        data0, _ = pt.pca(
            traj_on_disk, mask='@CA', n_vecs=2, fit=fit, ref=ref0)
        data1, _ = pt.pca(traj_on_mem, mask='@CA', n_vecs=2, fit=fit, ref=ref1)
        aa_eq(np.abs(data0), np.abs(data1))
        # try again
        # https://github.com/Amber-MD/pytraj/issues/1452
        data2, _ = pt.pca(
            traj_on_disk, mask='@CA', n_vecs=2, fit=fit, ref=ref0)
        aa_eq(np.abs(data0), np.abs(data2))

    def test_traj_on_disk_fit_to_given_reference_and_restore_transform_commands(
            self):
        """test_traj_on_disk_fit_to_given_reference_and_restore_transform_commands
        """
        traj_on_disk = pt.iterload(fn('tz2.nc'), fn('tz2.parm7'))
        ref = traj_on_disk[0]

        assert not traj_on_disk._transform_commands

        pt.pca(traj_on_disk, mask='@CA', ref=ref, fit=True)
        assert not traj_on_disk._transform_commands

        traj_on_disk2 = pt.iterload(fn('tz2.nc'), fn('tz2.parm7'))
        traj_on_disk2.superpose()
        pt.pca(traj_on_disk2, mask='@CA', ref=ref, fit=True)
        assert len(traj_on_disk2._transform_commands) == 1

    def test_raises(self):
        frame = pt.iterload(fn('tz2.nc'), fn('tz2.parm7'))[0]
        with pytest.raises(ValueError):
            pt.pca(frame, mask='@CA')


if __name__ == "__main__":
    unittest.main()
