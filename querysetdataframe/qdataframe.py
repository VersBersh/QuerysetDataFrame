import functools
import pandas as pd
from inspect import getmembers, ismethod
from django.db.models import QuerySet


class _QMethod(object):
    """
     descriptor for a method on a pd.DataFrame. If 
     the method returns a DataFrame then it is cast 
     to a QDataFrame and the quaryset (_qs) from the
     caller is copied accross
    """
    def __init__(self, func):
        self.func = func
        self.instance = None
        functools.update_wrapper(self, func)
        
    def __get__(self, instance, owner):  
        self.instance = instance        
        return self
    
    def __call__(self, *args, **kwargs):
        ret = self.func(self.instance, *args, **kwargs)
        if isinstance(ret, pd.DataFrame):
            ret.__class__ = QDataFrame
            ret._qs = self.instance._qs
        return ret


class _QIndexer(object):
    """
     similar to QMethod, but for Indexers of a 
     pd.DataFrame (loc, iloc, ...). pandas indexers 
     use _getitem_axis rather than __getitem__ so this
     is the method that's overwritten
    """
    def __init__(self, descriptor):
        # indexers already are descriptors
        self.descriptor = descriptor
            
    @staticmethod
    def new_getitem_axis(old_getitem_axis, queryset):
        def inner(*args, **kwargs):  # closure
            ret = old_getitem_axis(*args, **kwargs)
            if isinstance(ret, pd.DataFrame):
                ret.__class__ = QDataFrame
                ret._qs = queryset
            return ret
        return inner
        
    def __get__(self, instance, owner):
        prop = self.descriptor.__get__(instance, owner)
        if hasattr(instance, '_qs'):
            prop._getitem_axis = self.new_getitem_axis(prop._getitem_axis, instance._qs)
        return prop
    
    
class _QDataFrameMeta(type):  
    """
     hook the methods of pd.DataFrame and cast the 
     return values to QDataFrames
    """
    def __new__(mcs, name, bases, attrs):        
        cls = super(_QDataFrameMeta, mcs).__new__(mcs, name, bases, attrs)
        for name, member in getmembers(cls):
            if name in ('loc', 'iloc', 'at', 'iat', 'ix'): 
                setattr(cls, name, _QIndexer(member))
            elif ismethod(member) and not (
                    name.startswith('_') or 
                    name.startswith('to') or
                    name in ('set_index', 'reindex', 'add_col')):
                setattr(cls, name, _QMethod(member))
        return cls

    
class QDataFrame(pd.DataFrame):
    """ 
     a dataframe that can be constructed from a
     queryset, and an option parameter `values`
     that would be arguments to qs.value()
     
     add_col() takes a function and uses it to add
     a column to the dataframe. The function must 
     take only one parameter, which is an instance 
     of the model from the queryset. It can either 
     return a value, or a dictionary of values with
     the new column names as the keys
     
     to_dataframe() will cast QDataFrame back to an
     ordinary pandas DataFrame
    """
    
    __metaclass__ = _QDataFrameMeta
    
    def __init__(self, *args, **kwargs):
        queryset = args[0]
        if not isinstance(queryset, QuerySet):
            super(QDataFrame, self).__init__(*args, **kwargs)
        else:
            self._internal_names_set.add('_qs')
            self._qs = {inst.id: inst for inst in queryset}
            values = kwargs.get('values', None)
            if (not values) or len(values) == 0:
                super(QDataFrame, self).__init__(list(queryset.values()))
            else:
                if 'id' not in values:
                    values.append('id')
                super(QDataFrame, self).__init__(
                    list(queryset.values_list(*values)), columns=values
                )                     

            if queryset:
                self.set_index('id', inplace=True) 

    def _calc(self, func):
        try:
            # fast method: if properties of instance that are
            # accessed in func are already columns of df then 
            # there's no need to query the database
            return self.apply(func, axis=1)
        except:
            try:
                instances = [self._qs.get(id_) for id_ in self.index]
            except KeyError as err:
                raise IndexError(
                    'id {} does not exist in the queryset. Have you '
                    'changed the index of the dataframe?'.format(err.args[0])
                )
            return [func(inst) for inst in instances]

    def add_col(self, func):
        if not self.empty:
            res = self._calc(func)
            if isinstance(res, list) and isinstance(res[0], dict):
                df = pd.DataFrame(res, index=self.index)
                self[df.columns] = df
            else:
                self[func.__name__] = res
            
    def to_dataframe(self):
        return super(QDataFrame, self).copy()
