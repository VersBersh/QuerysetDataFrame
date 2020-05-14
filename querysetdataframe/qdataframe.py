import functools
import inspect
import itertools
from operator import attrgetter
from typing import Callable, Optional, Sequence

from django.db.models import QuerySet
from django.db.models.fields import AutoField
import pandas as pd
from pandas.core.indexing import (
    _IXIndexer, _iLocIndexer, _LocIndexer, _iAtIndexer, _AtIndexer
)

from .attributetypes import Field, Meth, Prop


def cast_if_dataframe(df: pd.DataFrame, caller: "QDataFrame") -> "QDataFrame":
    """ cast a dataframe to a QDataFrame """

    if isinstance(df, pd.DataFrame):
        df.__class__ = QDataFrame
        try:
            df._qs = caller._qs
        except AttributeError:
            pass

    # noinspection PyTypeChecker
    return df


def qmethod(func: Callable) -> Callable:
    """ decorator to cast a function's return value to a QDataFrame """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        ret = func(self, *args, **kwargs)
        return cast_if_dataframe(ret, self)

    return wrapper


class QIndexerMixin:
    """ cast the return values from pandas indexers to a QDataFrame """

    def __getitem__(self, *args, **kwargs):
        ret = super().__getitem__(*args, **kwargs)
        return cast_if_dataframe(ret, self.obj)


class QIXIndexer(QIndexerMixin, _IXIndexer): pass
class QiLocIndexer(QIndexerMixin, _iLocIndexer): pass
class QLocIndexer(QIndexerMixin, _LocIndexer): pass
class QiAtIndexer(QIndexerMixin, _iAtIndexer): pass
class QAtIndexer(QIndexerMixin, _AtIndexer): pass


class QDataFrameMeta(type):

    def __new__(mcs, name, bases, attrs):
        """ decorate DataFrame methods with qmethod """

        cls = super().__new__(mcs, name, bases, attrs)
        for name, member in inspect.getmembers(cls):
            if not inspect.isfunction(member):
                continue

            dont_decorate = (
                (name.startswith("_") and (name != "__getitem__")) or
                name.startswith("to") or
                name in ("set_index", "reindex", "add_col")
            )
            if not dont_decorate:
                setattr(cls, name, qmethod(member))

        return cls


class QDataFrame(pd.DataFrame, metaclass=QDataFrameMeta):
    """ a dataframe that can be constructed from a queryset """

    def __new__(cls,
                queryset: Optional[QuerySet] = None,
                values: Optional[list] = None,
                *args, **kwargs):

        if (queryset is None) or not isinstance(queryset, QuerySet):
            return super().__new__(cls)

        if values is None:
            # default to all concrete fields on the model
            props = ()
            meths = ()
            cfields = ()
            sfields = ("pk",)  # always include the pk for the DataFrame index
            sfields += tuple(f.name for f in queryset.model._meta.concrete_fields
                             if not isinstance(f, AutoField))
        else:
            props = tuple(f for f in values if isinstance(f, Prop))
            meths = tuple(f for f in values if isinstance(f, Meth))
            cfields = tuple(f for f in values if isinstance(f, Field))
            sfields = ("pk",)
            sfields += tuple(f for f in values if isinstance(f, str))
            sfields += tuple(f.name for f in cfields)

        # ensure iteration is deterministic or order_by was not already set
        if len(queryset.query.order_by) == 0:
            queryset = queryset.order_by("pk")

        # concrete model fields can be extracted with one SQL query
        data = queryset.values(*sfields)
        df = pd.DataFrame.from_records(data)

        if len(data) == 0:
            return df

        df = df.set_index("pk")

        for obj in cfields:
            df = df.rename(columns={obj.name: obj.column_name})
            df[obj.column_name] = obj.cast_to_dtype(df[obj.column_name], df.index)

        for obj in itertools.chain(props, meths):
            new_column = [obj.value(inst) for inst in queryset]
            df[obj.column_name] = obj.cast_to_dtype(new_column, df.index)

        if values is not None:
            df = df[list(map(str, values))]  # reorder the columns

        setattr(df, "_ix", QIXIndexer(df, "ix"))
        setattr(df, "_iloc", QiLocIndexer(df, "iloc"))
        setattr(df, "_loc", QLocIndexer(df, "loc"))
        setattr(df, "_iat", QiAtIndexer(df, "iat"))
        setattr(df, "_at", QAtIndexer(df, "at"))

        df._internal_names_set.add("_qs")
        df._qs = {inst.pk: inst for inst in queryset}
        df.__class__ = cls  # finally cast to QDataFrame

        return df

    def __init__(self, queryset: Optional[QuerySet] = None, *args, **kwargs):
        # only call __init__ when defaulting to non-queryset initialisation
        if queryset is None:
            super().__init__(*args, **kwargs)
        elif not isinstance(queryset, QuerySet):
            super().__init__(queryset, *args, **kwargs)

    def _calc(self, func: Callable, fast: bool) -> list:
        try:
            # calculate from existing columns
            return self.apply(func, axis=1).tolist()
        except:  # noqa
            if fast:
                raise
            try:
                instances = [self._qs.get(pk) for pk in self.index]
            except KeyError as err:
                raise IndexError(
                    f"primary key {err.args[0]} does not exist in the queryset. Have "
                    f"you changed the index of the QDataFrame?"
                )
            return [func(inst) for inst in instances]

    def add_col(self, func: Callable, fast: bool = False) -> None:
        """ takes a function and uses it to add a column to the QDataFrame.

         Args:
            func: a function that takes one parameter. The parameter must
                be an instance of the model from the queryset. The function
                may return a value, or a dictionary of values with the new
                column names as the keys
            fast: set to True if function only uses properties of the model
                that already exist in the QDataFrame and therefore can be
                calculated without any database queries.
        """
        if not self.empty:
            res = self._calc(func, fast)
            if (len(res) > 0) and isinstance(res[0], dict):
                df = pd.DataFrame.from_records(
                    res, index=self.index, columns=res[0].keys()
                )
                self[df.columns] = df
            else:
                self[func.__name__] = res

    def to_dataframe(self) -> pd.DataFrame:
        """ cast to an ordinary pandas.DataFrame """
        # noinspection PyTypeChecker
        return super().copy()

    def __getstate__(self) -> dict:
        """ make QDataFrame pickle-able """
        state = super().__getstate__()
        if hasattr(self, "_qs"):
            state["_qs"] = self._qs
        return state
