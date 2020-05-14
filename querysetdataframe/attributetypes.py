import datetime
from functools import reduce
from typing import Any, Callable, Optional, Sequence

import pandas as pd


def default(obj: Any, default_value: Any) -> Any:
    """ set a default value if obj is None """
    if obj is not None:
        return obj
    else:
        return default_value


class BaseAttribute:
    """ base class for a method or property """

    def __init__(self,
                 name: str,
                 column_name: Optional[str] = None,
                 dtype: Optional[Any] = None):
        self.name = name
        self.column_name = default(column_name, name)
        self._dtype = dtype

    def __str__(self):
        return self.column_name

    def __repr__(self):
        return f"{type(self).__name__}: {self.name}"

    def cast_to_dtype(self, values: Sequence, index: pd.Index) -> pd.Series:
        """ corece values to the appropriate numpy dtype """
        if self._dtype is None:
            if isinstance(values, pd.Series):
                return values
            return pd.Series(values, index=index)
        elif self._dtype in (float, int, str, bool):
            # pd.to_numeric won't cast decimal.Decimal -> float
            if isinstance(values, pd.Series):
                return values.astype(self._dtype)  # noqa
            return pd.Series(values, index=index, dtype=self._dtype)
        elif self._dtype in (datetime.date, datetime.datetime, "date"):
            return pd.to_datetime(values)
        else:
            raise ValueError(f"unrecognised dtype: {self._dtype}")


class Field(BaseAttribute):
    """ a field on the model """
    pass


class Meth(BaseAttribute):
    """ specifies a method on the model """

    def __init__(self,
                 name: str,
                 args: Optional[tuple] = None,
                 kwargs: Optional[dict] = None,
                 column_name: Optional[str] = None,
                 dtype: Any = None):
        super().__init__(name, column_name, dtype)
        self.args = default(args, ())
        self.kwargs = default(kwargs, {})

    def value(self, inst):
        """ call the method with the given args and kwargs and return the value """
        return getattr(inst, self.name)(*self.args, **self.kwargs)


class Prop(BaseAttribute):
    """ specifies a property on the model """

    def __init__(self,
                 name: str,
                 column_name: Optional[str] = None,
                 dtype: Any = None):
        super().__init__(name.replace('.', '_'), column_name, dtype)
        self.prop_list = name.split('.')

    def value(self, inst):
        """ return the value of the model field / property """
        return reduce(getattr, self.prop_list, inst)
