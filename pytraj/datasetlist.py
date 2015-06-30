from __future__ import absolute_import
from array import array
from pytraj.datasets.DataSetList import DataSetList as DSL
from pytraj.externals._json import to_json, read_json
from pytraj.externals._pickle import to_pickle, read_pickle
from pytraj.utils import _import_numpy, _import_pandas, is_int, is_array, is_generator
from pytraj._xyz import XYZ
from pytraj.compat import string_types, callable
from pytraj.core.DataFile import DataFile
from pytraj.ArgList import ArgList
from pytraj.compat import map
from pytraj.array import DataArray

_, np = _import_numpy()

__all__ = ['load_datafile', 'stack', 'DatasetList',
           'from_pickle', 'from_json']


def from_pickle(filename):
    dslist = DatasetList()
    dslist.from_pickle(filename)
    return dslist


def from_json(filename):
    dslist = DatasetList()
    dslist.from_json(filename)
    return dslist


def load_datafile(filename):
    """load cpptraj's output"""
    ds = DatasetList()
    ds.read_data(filename)
    return ds


def _from_full_dict(full_dict):
    return DatasetList()._from_full_dict(full_dict)


def from_sequence(seq):
    return DatasetList().from_sequence(seq)


def stack(args):
    """return a new DatasetList by joining (vstack)

    Parameters
    ----------
    args : list/tuple of DatasetList

    Notes
    -----
        similiar to numpy.vstack

    Examples
    --------
        d1 = calc_dssp(traj1, dtype='dataset')
        d2 = calc_dssp(traj2, dtype='dataset')
        d3 = stack((d1, d2))
    """
    is_subcriptable = not (isinstance(args, map) or is_generator(args))

    if not isinstance(args, (list, tuple, map)) and not is_generator(args):
        raise ValueError("must a tuple/list/map/generator")

    if is_subcriptable:
        dslist0 = args[0].copy()
    else:
        dslist0 = next(args)

    dslist_iter = args[1:] if is_subcriptable else args

    for dslist in dslist_iter:
        for d0, d in zip(dslist0, dslist):
            if d0.dtype != d.dtype:
                raise TypeError("Dont support stack different dtype together")
            if d0.key != d.key:
                raise KeyError("Don't support stack different key")
            d0.append(d.copy())
    return dslist0


class DatasetList(list):

    def __init__(self, dslist=None):
        if dslist:
            for d0 in dslist:
                self.append(DataArray(d0))

    def copy(self):
        dslist = self.__class__()
        for d0 in self:
            dslist.append(d0.copy())
        return dslist

    def from_pickle(self, filename):
        ddict = read_pickle(filename)
        self._from_full_dict(ddict)

    def from_json(self, filename):
        ddict = read_json(filename)
        self._from_full_dict(ddict)

    def to_pickle(self, filename, use_numpy=True):
        to_pickle(self._to_full_dict(use_numpy), filename)

    def to_json(self, filename, use_numpy=True):
        full_dict = self._to_full_dict(use_numpy=use_numpy)
        for key in self.keys():
            d = full_dict[key]['values']
            if hasattr(d, 'dtype') and 'int' in d.dtype.name:
                full_dict[key]['values'] = d.tolist()
        to_json(full_dict, filename)

    def _from_full_dict(self, ddict):
        from pytraj.array import DataArray
        da = DataArray()

        if not isinstance(ddict, dict):
            raise ValueError("must be a dict")
        ordered_keys = ddict['ordered_keys']

        for legend in ordered_keys:
            d = ddict[legend]
            da.values = d['values']
            da.aspect = d['aspect']
            da.name = d['name']
            da.idx = d['idx']
            da.legend = legend
            self.append(da)
        return self

    def _to_full_dict(self, use_numpy=True):
        """
        """
        ddict = {}
        ddict['ordered_keys'] = []
        for d in self:
            ddict['ordered_keys'].append(d.legend)
            ddict[d.legend] = {}
            _d = ddict[d.legend]
            if use_numpy:
                _d['values'] = d.values
            else:
                _d['values'] = list(d.values)
            _d['name'] = d.name
            _d['dtype'] = d.dtype
            _d['aspect'] = d.aspect
            _d['idx'] = d.idx
        return ddict

    def to_dataframe(self, engine='pandas'):
        if engine == 'pandas':
            try:
                import pandas as pd
                return pd.DataFrame(self.to_dict(use_numpy=True))
            except ImportError:
                raise ImportError("must have pandas")
        else:
            raise NotImplementedError(
                "currently support only pandas' DataFrame")

    def hist(self, plot=False):
        """
        Paramters
        ---------
        plot : bool, default False
            if False, return a dictionary of 2D numpy array
            if True, return a dictionary of matplotlib object
        """
        return dict(map(lambda x: (x.legend,  x.hist(plot=plot)), self))

    def count(self):
        from collections import Counter
        return dict((d0.legend, Counter(d0.values)) for d0 in self)

    def chunk_average(self, n_chunks):
        return dict((d0.legend, d0.chunk_average(n_chunks)) for d0 in self)

    def dtypes(self):
        return self.get_dtypes()

    def aspects(self):
        return self.get_aspects()

    def pipe(self, *funcs):
        """apply a series of functions to self's data
        """
        values = self.values
        for func in funcs:
            values = func(values)
        return values

    def apply(self, func):
        """update self's values from `funcs` and return `self`
        """
        for d0 in self:
            func(d0)
        return self

    def to_pyarray(self):
        if self.size > 1:
            raise NotImplementedError("only use `to_pyarray` for DataSet_1D")

        return self[0].to_pyarray()

    def __str__(self):
        has_pd, _ = _import_pandas()
        safe_msg = "<pytraj.DatasetList with %s datasets>" % self.size
        if self.size == 0:
            return safe_msg
        if not has_pd:
            msg = "<pytraj.DatasetList with %s datasets> (install pandas for pretty print)" % self.size
            return msg
        else:
            try:
                df = self.to_dataframe().T
                return safe_msg + "\n" + df.__str__()
            except (ImportError, ValueError):
                return safe_msg

    def __repr__(self):
        return self.__str__()

    def __call__(self, *args, **kwd):
        return self.filter(*args, **kwd)

    def clear(self):
        self = []

    def is_empty(self):
        return self != []

    @property
    def size(self):
        return len(self)

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def __getitem__(self, idx):
        """return a DataSet instance
        Memory view is applied (which mean this new insance is just alias of self[idx])
        Should we use a copy instead?
        """
        if self.size == 0:
            raise ValueError("size = 0: can not index")

        if is_int(idx):
            return super(DatasetList, self).__getitem__(idx)
        elif isinstance(idx, string_types):
            for d0 in self:
                if d0.legend.upper() == idx.upper():
                    d0._base = self
                    return d0
        elif isinstance(idx, slice):
            # return new view of `self`
            start, stop, step = idx.indices(self.size)
            new_dslist = self.__class__()
            for _idx in range(start, stop, step):
                new_dslist.append(self[_idx])
            return new_dslist
        elif is_array(idx) or isinstance(idx, list):
            new_dslist = self.__class__()
            for _idx in idx:
                new_dslist.append(self[_idx])
            return new_dslist
        elif isinstance(idx, tuple) and len(idx) == 2:
            return self[idx[0]][idx[1]]
        else:
            raise ValueError()

    def get_legends(self):
        """return a list"""
        tmp_list = []
        for d0 in self:
            tmp_list.append(d0.legend)
        return tmp_list

    def get_aspects(self, is_set=True):
        """return a set of uniqure aspects if "is_set" = True
        else: return a full list
        """

        tmp_list = []
        for d0 in self:
            tmp_list.append(d0.aspect)
        if is_set:
            return set(tmp_list)
        else:
            return tmp_list

    def get_scalar_types(self):
        """return a list"""
        tmp_list = []
        for d0 in self:
            tmp_list.append(d0.scalar_type)
        return tmp_list

    def get_scalar_modes(self):
        """return a list"""
        tmp_list = []
        for d0 in self:
            tmp_list.append(d0.scalar_mode)
        return tmp_list

    def get_dtypes(self):
        """return a list"""
        tmp_list = []
        for d0 in self:
            tmp_list.append(d0.dtype)
        return tmp_list

    def keys(self):
        return self.get_legends()

    def iteritems(self):
        for key in self.keys():
            yield key, self[key]

    def items(self):
        return self.iteritems()

    def map(self, func):
        for d0 in self:
            yield func(d0)

    def filter(self, func, *args, **kwd):
        """return a new view of DatasetList of func return True"""
        dslist = self.__class__()

        if isinstance(func, (string_types, list, tuple)):
            return self.grep(func, *args, **kwd)
        elif callable(func):
            for d0 in self:
                if func(d0, *args, **kwd):
                    dslist.append(d0)
            return dslist
        else:
            raise NotImplementedError("func must be a string or callable")

    def grep(self, key, mode='legend'):
        """"return a new DatasetList object as a view of `self`

        Parameters
        ----------
        key : str or list
            keyword for searching
        mode: str, default='legend'
            mode = 'legend' | 'name' | 'dtype' | 'aspect'
        """
        import re

        # use __class__ so we can `filter` return the same class
        # we subclass this Cython class to python level
        dtmp = self.__class__()

        # dont free mem here
        for d0 in self:
            att = getattr(d0, mode)
            if isinstance(key, string_types):
                if re.search(key, att):
                    dtmp.append(d0)
            elif isinstance(key, (list, tuple)):
                for _key in key:
                    if re.search(_key, att):
                        dtmp.append(d0)
            else:
                raise ValueError("support string or list/tuple of strings")
        return dtmp

    def tolist(self):
        """return a list of list/array"""
        try:
            return [d0.tolist() for d0 in self]
        except:
            raise NotImplementedError("dont know how to convert to list")

    def to_dict(self, use_numpy=True, ordered_dict=False):
        """return a dict object with key=legend, value=list"""
        _dict = dict
        if ordered_dict:
            # use OrderedDict
            from collections import OrderedDict
            _dict = OrderedDict
        if use_numpy:
            return _dict((d0.legend, d0.to_ndarray(copy=True)) for d0 in self)
        else:
            return _dict((d0.legend, d0.tolist()) for d0 in self)

    @property
    def values(self):
        """return read-only ndarray"""
        from pytraj._xyz import XYZ
        # read-only
        try:
            return XYZ(self.to_ndarray())
        except:
            raise ValueError("don't know how to cast to numpy array")

    def to_ndarray(self):
        """
        Notes: require numpy
        """
        # make sure to use copy=True to avoid memory error for memoryview
        has_np, np = _import_numpy()
        if has_np:
            try:
                if self.size == 1:
                    return self[0].to_ndarray(copy=True)
                else:
                    # more than one set
                    return np.asarray([d0.to_ndarray(copy=True) for d0 in self])
            except:
                raise ValueError("don't know how to convert to ndarray")
        else:
            raise ImportError("don't have numpy")

    def to_dataframe(self):
        """return pandas' DataFrame

        Requires
        --------
        pandas
        """
        from collections import OrderedDict as dict
        _, pandas = _import_pandas()
        my_dict = dict((d0.legend, d0.to_ndarray(copy=True)) for d0 in self)
        return pandas.DataFrame(my_dict)

    def apply(self, func):
        for d in self:
            arr = np.asarray(d.data)
            arr[:] = func(arr)
        return self

    def mean(self, axis=1):
        """
        Notes: require numpy
        """
        return self.to_ndarray().mean(axis=axis)

    def median(self, axis=1):
        """
        Notes: require numpy
        """
        return np.median(self.to_ndarray(), axis=axis)

    def std(self, axis=1):
        """
        Notes: require numpy
        """
        return np.std(self.to_ndarray(), axis=axis)

    def min(self):
        from collections import OrderedDict as dict
        return dict((x.legend, x.min()) for x in self)

    def max(self):
        from collections import OrderedDict as dict
        return dict((x.legend, x.max()) for x in self)

    def sum(self, legend=None, axis=1):
        """
        Notes: require numpy
        """
        _, np = _import_numpy()
        if not legend:
            return np.sum(self.to_ndarray(), axis=axis)
        else:
            return self.filter(legend).sum(axis=axis)

    def cumsum(self, axis=1):
        """Return the cumulative sum of the elements along a given axis.
        (from numpy doc)
        """
        return np.cumsum(self.to_ndarray(), axis=axis)

    def mean_with_error(self, other):
        from collections import defaultdict

        ddict = defaultdict(tuple)
        for key, dset in self.iteritems():
            ddict[key] = dset.mean_with_error(other[key])
        return ddict

    def count(self, number=None):
        from collections import OrderedDict as dict
        return dict((d0.legend, d0.count(number)) for d0 in self)

    def read_data(self, filename, arg=""):
        df = DataFile()
        from pytraj.datasets.DataSetList import DataSetList
        dslist = DataSetList()
        df.read_data(filename, ArgList(arg), dslist)

        for d0 in dslist:
            self.append(d0.copy())

    # pandas related
    def describe(self):
        _, pd = _import_pandas()
        if not pd:
            raise ImportError("require pandas")
        else:
            return self.to_dataframe().describe()

    def write_all_datafiles(self, filenames=None):
        from pytraj.core.DataFileList import DataFileList
        df = DataFileList()

        for idx, d in enumerate(self):
            if filenames is None:
                # make default name
                d.legend = d.legend.replace(":", "_")
                fname = "pytraj_datafile_" + d.legend + ".txt"
            else:
                fname = filenames[i]
            df.add_dataset(fname, d)
        df.write_all_datafiles()

    def savetxt(self, filename='dslist_default_name.txt', labels=None):
        """just like `numpy.savetxt`
        Notes: require numpy
        """
        import numpy as np
        if labels is None:
            headers = "\t".join([d.legend for d in self])
            headers = "frame\t" + headers
        else:
            headers = "frame\t" + labels

        frame_number = np.arange(self[0].size)
        # transpose `values` first
        values = np.column_stack((frame_number, self.values.T))
        formats = ['%8i'] + [d.format for d in self]
        np.savetxt(filename, values, fmt=formats, header=headers)

    def plot(self, show=False, use_seaborn=False, *args, **kwd):
        """very simple plot for quickly visualize the data

        >>> dslist[['psi:7', 'phi:7']].plot()
        >>> dslist[['psi:7', 'phi:7']].plot(show=True)
        """
        if use_seaborn:
            try:
                import seaborn as snb
                snb.set()
            except ImportError:
                raise ImportError("need seaborn")
        try:
            from matplotlib import pyplot as plt
            fig = plt.figure()
            ax = fig.add_subplot(111)
            for d0 in self:
                ax.plot(d0, *args, **kwd)
            if show:
                plt.show()
            return ax
        except ImportError:
            raise ImportError("require matplotlib")

    def append(self, dset, copy=True):
        if copy:
            d0 = dset.copy()
        else:
            d0 = dset
        for key in self.keys():
            if d0.legend == key:
                raise KeyError("must have different legend", dset.legend)
        super(DatasetList, self).append(d0)

    def remove(self, dset):
        for idx, d in enumerate(self):
            if dset.legend == d.legend:
                # do not work with
                # super(DatasetList, self).remove(d)
                # TypeError: 'NotImplementedType' object is not callable
                # why?
                super(DatasetList, self).remove(self.__getitem__(idx))

    def from_datasetlist(self, dslist, copy=True):
        self.from_sequence(dslist, copy=copy)
        return self

    def from_sequence(self, dslist, copy=True):
        for d in dslist:
            self.append(d, copy=copy)
        return self

    def chunk_average(self, n_chunks):
        return dict(map(lambda x: (x.legend, x.chunk_average(n_chunks)), self))

    def topk(self, k):
        return dict((x.legend, x.topk(k)) for x in self)

    def lowk(self, k):
        from heapq import nsmallest
        return dict((x.legend, list(nsmallest(k, x))) for x in self)

    def head(self, k):
        return dict((x.legend, x.head(k, restype='list')) for x in self)

    def tail(self, k):
        return dict((x.legend, x.tail(k)) for x in self)
