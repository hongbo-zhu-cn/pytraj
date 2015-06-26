# distutil: language = c++

from libcpp.string cimport string
from .DispatchObject cimport _DispatchObject, DispatchObject, DispatchAllocatorType
from .TopologyList cimport _TopologyList, TopologyList
from .DataFileList cimport _DataFileList, DataFileList
from ._FunctPtr cimport FunctPtr
from ..Topology cimport _Topology, Topology
from ..AtomMask cimport _AtomMask, AtomMask
from ..Frame cimport _Frame, Frame
from ..ArgList cimport _ArgList, ArgList
from ..datasets.DataSetList cimport _DataSetList, DataSetList

cdef extern from "ActionList.h":
    cdef cppclass _ActionList "ActionList":
        _ActionList()
        void Clear()
        void SetDebug(int)
        int Debug()
        int AddAction(DispatchAllocatorType, _ArgList&,
                      _TopologyList*, 
                      _DataSetList*, _DataFileList*)
        int SetupActions(_Topology**)
        bint DoActions(_Frame **, int)
        void Print()
        void List()
        bint Empty()
        int Naction()
        const string& CmdString(int)
        DispatchAllocatorType ActionAlloc(int i)

cdef class ActionList:
    cdef _ActionList* thisptr

    # alias for TopologyList (self.process(top))
    cdef object toplist

    # check if self.process is already called or not
    cdef bint top_is_processed
