from inspect import getmembers, ismethod
import warnings

import pandas as pd
from django.db.models import QuerySet

from .dataframe_methods import recasting_methods, non_recasting_methods


def return_queryset_dataframe(cls):
    class wrapper(object):
        def __init__(self, func):
            self.func = func
            self.instance = None
            self.name = func.im_func.__name__
            
        def __get__(self, instance, owner):
            self.instance = instance
            return self
            
        def __call__(self, *args, **kwargs):
            ret = self.func(self.instance, *args, **kwargs)
            if type(ret) is pd.DataFrame:
                assert self.instance is not None
                assert '_qs' in ret._internal_names_set
                qs = self.instance._qs.filter(id__in=ret.index)
                if qs.count() == len(ret):
                    return QuerysetDataFrame(qs)
            return ret
    return wrapper


class QuerysetDataFrameMeta(type):           
    def __new__(mcs, name, bases, attrs):        
        cls = super(QuerysetDataFrameMeta, mcs).__new__(
            mcs, name, bases, attrs
        )
        for name, method in getmembers(cls, ismethod):
            if (name.startswith('_')
                    or name in non_recasting_methods
                    or name == 'add_col'):
                continue  # don't touch private methods
            else:                
                setattr(cls, name, return_queryset_dataframe(cls)(method))
                if name not in recasting_methods:
                    warnings.warn(
                        'new pandas function: {}. Must decide '
                        'whether to recast return value to '
                        'QuerysetDataFrame or not'.format(name)
                    )
        return cls


class QuerysetDataFrame(pd.DataFrame):
    """ 
     a dataframe constructed from a queryset with 
     a method add_col() which takes a function and 
     uses it to add a column to the dataframe. The 
     function must take only one parameter, which 
     is an instance of the model from the queryset
    """
    __metaclass__ = QuerysetDataFrameMeta
    
    def __init__(self, queryset):
        if isinstance(queryset, QuerySet):
            self._internal_names_set.add('_qs')
            self._qs = queryset      
            super(QuerysetDataFrame, self).__init__(
                list(self._qs.values())
            )        
            if queryset:
                self.set_index('id', inplace=True)      

    def _calc(self, func):
        try:
            return self.apply(func, axis=1)
        except:
            return [func(obj) for obj in self._qs]
        
    def add_col(self, func):
        if not self.empty:
            self[func.__name__] = self._calc(func)

if False:
    from apps.test import QuerysetDataFrame
    from anki.models import Record
    x = QuerysetDataFrame(Record.objects.all())
    type(x.copy())