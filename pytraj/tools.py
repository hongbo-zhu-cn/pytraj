"""seperate module, only use stdlib
If want to use external package, import it inside the function

This module stores all useful functions that does not fit to anywhere else.
"""
from __future__ import absolute_import
import sys as _sys
import os
from glob import glob
from itertools import islice
import functools
from collections import OrderedDict, defaultdict


def groupby(key, seq):
    # lightly adapted from `toolz` package.
    # see license in $PYTRAJHOME/licenses/externals/toolz.txt
    '''
    Examples
    --------
    >>> names = ['Alice', 'Bob', 'Charlie', 'Dan', 'Edith', 'Frank']
    >>> groupby(len, names)  
    {3: ['Bob', 'Dan'], 5: ['Alice', 'Edith', 'Frank'], 7: ['Charlie']}
    '''
    d = defaultdict(lambda: seq.__class__().append)
    for item in seq:
        d[key(item)](item)
    rv = {}
    for k, v in iteritems(d):
        rv[k] = v.__self__
    return rv

def _array_to_cpptraj_range(seq):
    # use "i+1" since cpptraj use 1-based index for mask
    '''
    Examples
    --------
    >>> _array_to_cpptraj_range([2, 4])
    '3,5'
    '''
    return ",".join((str(i + 1) for i in seq))

# string_types, PY2, PY3, iteritems were copied from six.py
# see license in $PYTRAJHOME/license/externals/
PY2 = _sys.version_info[0] == 2
PY3 = _sys.version_info[0] == 3

if PY3:
    _iteritems = "items"
    string_types = str
else:
    _iteritems = "iteritems"
    string_types = basestring


def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))


try:
    # PY3
    from functools import reduce
except ImportError:
    #
    pass

# this module gathers commonly used functions
# from toolz, stackoverflow, ... and from myself
# should make this independent from pytraj

try:
    import numpy as np
except ImportError:
    np = None


def _dispatch_value(func):
    def inner(data, *args, **kwd):
        if hasattr(data, 'values'):
            _data = data.values
        else:
            _data = data
        return func(_data, *args, **kwd)

    inner.__doc__ = func.__doc__
    return inner


def _not_yet_tested(func):
    @functools.wraps(func)
    def inner(*args, **kwd):
        return func(*args, **kwd)

    msg = "This method is not tested. Use it with your own risk"
    inner.__doc__ = "\n".join((func.__doc__, "\n", msg))
    return inner


@_dispatch_value
def split(data, n_chunks_or_array):
    """split `self.data` to n_chunks

    Notes : require numpy (same as `array_split`)
    """
    return np.array_split(data, n_chunks_or_array)


def chunk_average(self, n_chunk, restype='same'):
    '''average by chunk'''
    import numpy as np
    from pytraj.array import DataArray

    data = np.array(list(map(np.mean, split(self, n_chunk))))
    if restype == 'same' and isinstance(self, DataArray):
        new_array = self.shallow_copy()
        new_array.values = data
        return new_array
    else:
        return data


def moving_average(data, n):
    """moving average

    Notes
    -----
    from `stackoverflow <http://stackoverflow.com/questions/11352047/finding-moving-average-from-data-points-in-python>`_
    """
    window = np.ones(int(n)) / float(n)
    new_data = np.convolve(data, window, 'same')
    if hasattr(data, 'values'):
        new_array = data.shallow_copy()
        new_array.values = new_data
        return new_array
    else:
        return new_data


def pipe(obj, func, *args, **kwargs):
    """Notes: copied from pandas PR
    https://github.com/ghl3/pandas/blob/groupby-pipe/pandas/tools/util.py
    see license in pytraj/license/

    Apply a function to a obj either by
    passing the obj as the first argument
    to the function or, in the case that
    the func is a tuple, interpret the first
    element of the tuple as a function and
    pass the obj to that function as a keyword
    arguemnt whose key is the value of the
    second element of the tuple
    """
    if isinstance(func, tuple):
        func, target = func
        if target in kwargs:
            msg = '%s is both the pipe target and a keyword argument' % target
            raise ValueError(msg)
        kwargs[target] = obj
        return func(*args, **kwargs)
    else:
        return func(obj, *args, **kwargs)


def _compose2(f, g):
    # copied from pandas
    # see license in pytraj/license/
    """Compose 2 callables"""
    return lambda *args, **kwargs: f(g(*args, **kwargs))


def compose(*funcs):
    """
    Notes: copied from pandas (added pytraj's example)
    see license in pytraj/license/

    Compose 2 or more callables

    Examples
    --------
    >>> import pytraj as pt
    >>> from pytraj.testing import get_fn
    >>> func = compose(pt.calc_radgyr, pt.iterload)
    >>> fname, tname = get_fn('tz2')
    >>> func(fname, tname)
    array([ 18.91114428,  18.93654996,  18.84969884,  18.90449256,
            18.8568644 ,  18.88917208,  18.9430491 ,  18.88878079,
            18.91669565,  18.87069722])
    """
    assert len(funcs) > 1, 'At least 2 callables must be passed to compose'
    return reduce(_compose2, funcs)


def grep_key(self, key):
    """grep key

    Examples
    --------
    >>> import pytraj as pt
    >>> traj  = pt.load_sample_data('tz2')
    >>> dslist = pt.calc_multidihedral(traj, dtype='dataset') 
    >>> pt.tools.grep_key(dslist, 'psi')[0] # doctest: +SKIP
    <pytraj.array.DataArray: size=10, key=psi:1, dtype=float64, ndim=1>
    values:
    [ 176.6155643   166.82129574  168.79510009  167.42561927  151.18334989
      134.17610997  160.99207908  165.1126967   147.94332109  145.42901383]
    """
    new_self = self.__class__()
    for d in self:
        if key in d.key:
            new_self.append(d)
    return new_self


def flatten(x):
    """Returns a single, flat list which contains all elements retrieved
    from the sequence and all recursively contained sub-sequences
    (iterables).

    Notes
    -----
    from: http://kogs-www.informatik.uni-hamburg.de/~meine/python_tricks

    Examples
    --------
    >>> [1, 2, [3,4], (5,6)]
    [1, 2, [3, 4], (5, 6)]
    >>> flatten([[[1,2,3], (42,None)], [4,5], [6], 7, (8,9,10)])
    [1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10]"""

    result = []
    for el in x:
        # if isinstance(el, (list, tuple)):
        if hasattr(el, "__iter__") and not isinstance(el, string_types):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result


def n_grams(a, n, asarray=False):
    """n_grams

    Parameters
    ----------
    a : sequence
    n : number of elements
    asarray : bool, default False
        if False: return an iterator
        if True: return a numpy array

    Examples
    --------
    >>> list(n_grams([2, 3, 4 ,5], 2))
    [(2, 3), (3, 4), (4, 5)]

    Notes
    -----
    adapted from: http://sahandsaba.com/thirty-python-language-features-and-tricks-you-may-not-know.html
    """

    z = (islice(a, i, None) for i in range(n))
    it = zip(*z)

    if not asarray:
        return it
    else:
        import numpy as np
        return np.array([x for x in it])


def dict_to_ndarray(dict_of_array):
    """convert OrderedDict to numpy array

    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.load_sample_data('tz2')
    >>> dslist = pt.multidihedral(traj, dhtypes='phi psi', resrange='2', dtype='dict')
    >>> list(dslist.keys())
    ['phi:2', 'psi:2']
    >>> dict_to_ndarray(dslist)
    array([[-128.72617304, -109.44321317, -130.93278259, ..., -146.70146067,
            -121.58263643, -112.74485175],
           [ 150.11249102,  142.52303293,  131.11609265, ...,  123.44883266,
             141.18992429,  120.03168126]])
    """
    if not isinstance(dict_of_array, OrderedDict):
        raise NotImplementedError("support only OrderedDict")
    from pytraj.externals.six import iteritems

    return np.array([v for _, v in iteritems(dict_of_array)])


def concat_dict(iterables):
    """concat dict

    Examples
    --------
    >>> dict_0 = {'x' : [1, 2, 3,]}
    >>> dict_1 = {'x' : [4, 5]}
    >>> concat_dict((dict_0, dict_1))
    OrderedDict([('x', array([1, 2, 3, 4, 5]))])
    """
    new_dict = OrderedDict()
    for i, d in enumerate(iterables):
        if i == 0:
            # make a copy of first dict
            new_dict.update(d)
        else:
            for k, v in iteritems(new_dict):
                new_dict[k] = np.concatenate((new_dict[k], d[k]))
    return new_dict


def merge_coordinates(iterables):
    """merge_coordinates from frames

    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.load_sample_data('tz2')
    >>> merge_coordinates(traj(0, 3)) # doctest: +SKIP
    array([[ 15.55458927,  28.54844856,  17.18908691],
           [ 16.20579147,  29.07935524,  17.74959946],
           [ 14.95065975,  29.27651787,  16.83513069],
           ...,
           [ 34.09399796,   7.88915873,  15.6500845 ],
           [ 34.4160347 ,   8.53098011,  15.01716137],
           [ 34.29132462,   8.27471733,  16.50368881]])
    """
    return np.vstack((f.xyz.copy() for f in iterables))


def merge_frames(iterables):
    """merge from frames to a single Frame. Order matters.
    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.load_sample_data('tz2')
    >>> traj[0]
    <Frame with 5293 atoms>
    >>> merge_frames(traj(0, 3))
    <Frame with 15879 atoms>
    """
    from pytraj import Frame
    xyz = np.vstack((f.xyz.copy() for f in iterables))
    frame = Frame()
    frame.append_xyz(xyz)
    return frame


def merge_frame_from_trajs(trajlist):
    """
    Examples
    --------
    >>> import pytraj as pt
    >>> traj0 = pt.load_sample_data('tz2')[:3]
    >>> traj1 = pt.load_sample_data('tz2')[3:6]
    >>> traj2 = pt.load_sample_data('tz2')[6:9]
    >>> print(traj0.n_atoms, traj1.n_atoms, traj2.n_atoms)
    5293 5293 5293
    >>> for frame in pt.tools.merge_frame_from_trajs((traj0, traj1, traj2)): print(frame)
    <Frame with 15879 atoms>
    <Frame with 15879 atoms>
    <Frame with 15879 atoms>
    """
    if not isinstance(trajlist, (list, tuple)):
        raise ValueError('input must be a list or tuple of trajectories')
    for iterables in zip(*trajlist):
        yield merge_frames(iterables)


def rmsd_1darray(a1, a2):
    '''rmsd of a1 and a2

    Examples
    --------
    >>> a0 = [1, 3, 4]
    >>> a1 = [1.4, 3.5, 4.2]
    >>> rmsd_1darray(a0, a1)
    0.3872983346207417
    '''
    import numpy as np
    from math import sqrt
    arr1 = np.asarray(a1)
    arr2 = np.asarray(a2)

    if len(arr1.shape) > 1 or len(arr2.shape) > 1:
        raise ValueError("1D array only")

    if arr1.shape != arr2.shape:
        raise ValueError("must have the same shape")

    tmp = sum((arr1 - arr2) ** 2)
    return sqrt(tmp / arr1.shape[0])


def rmsd(a1, a2, flatten=True):
    """rmsd for two array with the same shape

    Parameters
    ----------
    a1, a2: np.ndarray
    flatten : bool, default True
        if True: always flatten two input arrays

    Examples
    --------
    >>> import pytraj as pt
    >>> t0 = pt.load_sample_data('ala3')
    >>> t1 = t0[:]
    >>> t1.xyz += 1.
    >>> rmsd(t0.xyz, t1.xyz)
    1.0

    Notes
    -----
    This method is different from ``pytraj.rmsd``
    """
    import numpy as np
    a1 = np.asarray(a1)
    a2 = np.asarray(a2)
    if a1.shape != a2.shape and not flatten:
        raise ValueError("must have the same shape")
    return rmsd_1darray(a1.flatten(), a2.flatten())


def mean_and_error(a1, a2):
    """calculate mean and error from two 1D array-like

    Examples
    --------
    >>> import pytraj as pt
    >>> a0 = [2, 4, 6]
    >>> a1 = [3, 5, 7]
    >>> mean_and_error(a0, a1)
    (4.5, 0.5)
    """
    import numpy as np
    mean = np.mean

    a1 = np.asarray(a1)
    a2 = np.asarray(a2)
    assert len(a1.shape) == len(a2.shape) == 1, "1D array"
    return (mean(a1 + a2) / 2, mean(np.abs(a1 - a2)) / 2)


def split_traj_by_residues(traj, start=0, stop=-1, step=1):
    '''return a generator

    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.datafiles.load_rna()
    >>> g = pt.tools.split_traj_by_residues(traj)
    >>> t0 = next(g)
    >>> print(t0.top.n_residues)
    1
    '''
    from pytraj.compat import range
    from pytraj._cyutils import get_positive_idx

    _stop = get_positive_idx(stop, traj.top.n_residues)

    for i in range(start, _stop, step):
        j = ':' + str(i + 1)
        # example: traj[':3']
        yield traj[j]


def find_lib(libname, unique=False):
    """return a list of all library files"""
    paths = os.environ.get('LD_LIBRARY_PATH', '').split(':')
    lib_path_list = []
    key = "lib" + libname + "*"

    for path in paths:
        path = path.strip()
        fnamelist = glob(os.path.join(path, key))
        for fname in fnamelist:
            if os.path.isfile(fname):
                lib_path_list.append(fname)

    if not lib_path_list:
        return None
    else:
        if unique:
            return set(lib_path_list)
        else:
            return lib_path_list


def read_orca_trj(fname):
    """return numpy 2D array
    """
    # http://stackoverflow.com/questions/14645789/
    # numpy-reading-file-with-filtering-lines-on-the-fly
    import numpy as np
    regexp = r'\s+\w+' + r'\s+([-.0-9]+)' * 3 + r'\s*\n'
    return np.fromregex(fname, regexp, dtype='f')


def read_gaussian_output(filename=None, top=None):
    """return a `pytraj.api.Trajectory` object

    Parameters
    ----------
    fname : str, filename
    top : {str, Topology}, optional, default None
        pytraj.Topology or a filename or None
        if None, use `antechamber` to generate mol2 file, need set $AMBERHOME env

    Requires
    --------
    cclib (``pip install cclib``)

    >>> import pytraj as pt
    >>> pt.tools.read_gaussian_output("gau.out", "mytest.pdb") # doctest: +SKIP
    """
    import cclib
    from pytraj.api import Trajectory
    from pytraj.utils.context import goto_temp_folder
    from pytraj._get_common_objects import _get_topology

    _top = _get_topology(None, top)
    gau = cclib.parser.Gaussian(filename)
    go = gau.parse()

    if _top is None:
        try:
            amberhome = os.environ['AMBERHOME']
        except KeyError:
            raise KeyError("must set AMBERHOME")

        fpath = os.path.abspath(filename)

        with goto_temp_folder():
            at = amberhome + "/bin/antechamber"
            out = "-i %s -fi gout -o tmp.mol2 -fo mol2 -at amber" % fpath
            cm = " ".join((at, out))
            os.system(cm)

            return Trajectory(xyz=go.atomcoords, top="tmp.mol2")
    else:
        return Trajectory(xyz=go.atomcoords, top=_top)


def read_to_array(fname):
    '''read text from file to numpy array'''
    import numpy as np
    with open(fname, 'r') as fh:
        arr0 = np.array([[x for x in line.split()] for line in fh.readlines()])
        return np.array(flatten(arr0), dtype='f8')


def merge_trajs(traj1, traj2, start_new_mol=True, n_frames=None):
    """

    Examples
    --------
    >>> import pytraj as pt
    >>> import numpy as np
    >>> traj1 = pt.load_sample_data('ala3')[:1]
    >>> traj2 = pt.load_sample_data('tz2')[:1]
    >>> traj3 = merge_trajs(traj1, traj2)
    >>> # from frame_iter for saving memory
    >>> traj3 = merge_trajs((traj1(0, 10, 2), traj1.top), (traj2(100, 110, 2), traj2.top), n_frames=6)

    Notes
    -----
    Code might be changed
    """
    from pytraj.compat import zip
    from pytraj import Trajectory
    import numpy as np

    if isinstance(traj1, (list, tuple)):
        n_frames_1 = n_frames
        top1 = traj1[1]
        _traj1 = traj1[0]
    else:
        n_frames_1 = traj1.n_frames
        top1 = traj1.top
        _traj1 = traj1

    if isinstance(traj2, (list, tuple)):
        n_frames_2 = n_frames
        top2 = traj2[1]  # example: (traj(0, 5), traj.top)
        _traj2 = traj2[0]
    else:
        n_frames_2 = traj2.n_frames
        top2 = traj2.top
        _traj2 = traj2

    if n_frames_1 != n_frames_2:
        raise ValueError("must have the same n_frames")

    traj = Trajectory()
    traj._allocate(n_frames_1, top1.n_atoms + top2.n_atoms)

    # merge Topology
    top = top1.copy()
    if start_new_mol:
        top.start_new_mol()
    top.join(top2)
    traj.top = top

    # update coords
    for f1, f2, frame in zip(_traj1, _traj2, traj):
        frame.xyz = np.vstack((f1.xyz, f2.xyz))

    return traj


def as_2darray(traj_or_xyz):
    '''reshape traj.xyz to 2d array, shape=(n_frames, n_atoms * 3)

    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.load_sample_data('tz2')
    >>> traj.xyz.shape
    (10, 5293, 3)
    >>> as_2darray(traj).shape
    (10, 15879)

    Notes
    -----
    if ``traj`` is mutable, this method return a view of its coordinates.
    '''
    import numpy as np

    if hasattr(traj_or_xyz, 'xyz'):
        traj = traj_or_xyz
        # Trajectory-like
        return traj.xyz.reshape(traj.n_frames, traj.n_atoms * 3)
    else:
        # array-like, assume 3D
        xyz = np.asarray(traj_or_xyz)
        assert xyz.ndim == 3, 'xyz must has ndim=3'
        shape = xyz.shape
        return xyz.reshape(shape[0], shape[1] * shape[2])


def as_3darray(xyz):
    '''reshape xyz to 3d array, shape=(n_frames, n_atoms, 3)

    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.load_sample_data('tz2')
    >>> traj.xyz.shape
    (10, 5293, 3)
    >>> xyz_2d = as_2darray(traj)
    >>> xyz_2d.shape
    (10, 15879)
    >>> as_3darray(xyz_2d).shape
    (10, 5293, 3)
    '''
    shape = xyz.shape
    if len(shape) != 2:
        raise ValueError('shape must be 2')
    new_shape = (shape[0], int(shape[1] / 3), 3)
    return xyz.reshape(new_shape)


def split_and_write_traj(self,
                         n_chunks=None,
                         root_name="trajx",
                         ext='nc', *args, **kwd):
    '''
    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.load_sample_data('tz2')
    >>> split_and_write_traj(traj, n_chunks=3, root_name='output/trajx')
    '''

    chunksize = self.n_frames // n_chunks
    for idx, traj in enumerate(self.iterchunk(chunksize=chunksize)):
        fname = ".".join((root_name, str(idx), ext))
        traj.save(fname, *args, **kwd)