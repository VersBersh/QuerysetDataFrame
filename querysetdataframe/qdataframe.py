import functools
import inspect
from operator import attrgetter
from typing import Sequence, Callable

from django.db.models import QuerySet
import pandas as pd
from pandas.core.indexing import (
    _IXIndexer, _iLocIndexer, _LocIndexer, _iAtIndexer, _AtIndexer
)

from .attributetypes import Meth, Prop


def cast_if_dataframe(df: pd.DataFrame, caller: "QDataFrame") -> "QDataFrame":
    """ cast a dataframe to a QDataFrame """

    if isinstance(df, pd.DataFrame):
        df.__class__ = QDataFrame
        try:
            df._qs = caller._qs
        except KeyError:
            pass

    return df


def qmethod(func: Callable) -> Callable:
    """ decorator to cast a function's return value to a QDataFrame """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        print(args, kwargs)
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

    def __new__(cls, queryset: QuerySet = None, values: list = None, *args, **kwargs):
        if (queryset is None) or not isinstance(queryset, QuerySet):
            return super().__new__(cls, *args, **kwargs)

        if values is None and len(args) == 2:
            values = args[1]
        if values is None:
            props = ()
            meths = ()
            fields = ("pk", *map(attrgetter("name"), queryset.model._meta.fields))
        else:
            props = (f for f in values if isinstance(f, Prop))
            meths = (f for f in values if isinstance(f, Meth))
            fields = ("pk",) + tuple(f for f in values if not isinstance(f, (Prop, Meth)))

        data = queryset.values(*fields)
        df = pd.DataFrame.from_records(data)

        if len(data) == 0:
            return df

        df = df.set_index("pk")

        for p in props:
            df[p.name] = [getattr(inst, p.name) for inst in queryset]

        for m in meths:
            df[m.name] = [m.call(inst) for inst in queryset]

        if values is not None:
            df = df[list(map(str, values))]  # reorder the columns

        setattr(df, "_ix", QiLocIndexer(df, "ix"))
        setattr(df, "_iloc", QiLocIndexer(df, "iloc"))
        setattr(df, "_loc", QiLocIndexer(df, "loc"))
        setattr(df, "_iat", QiLocIndexer(df, "iat"))
        setattr(df, "_at", QiLocIndexer(df, "at"))

        df._internal_names_set.add("_qs")
        df._qs = {inst.pk: inst for inst in queryset}
        df.__class__ = cls  # finally cast to QDataFrame

        return df

    def __init__(self, queryset: QuerySet = None, *args, **kwargs):
        if (queryset is None) or not isinstance(queryset, QuerySet):
            # only call __init__ when defaulting to non-queryset initialisation
            super().__init__(*args, **kwargs)

    def _calc(self, func: Callable, fast: bool) -> Sequence:
        try:
            # calculate from existing columns
            return self.apply(func, axis=1)
        except:
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
            if isinstance(res[0], dict):
                df = pd.DataFrame(res, index=self.index)
                self[df.columns] = df
            else:
                self[func.__name__] = res

    def to_dataframe(self) -> pd.DataFrame:
        """ cast to an ordinary pandas.DataFrame """
        return super().copy()

    def to_queryset(self) -> QuerySet:
        """ cast to a queryset

         This will only work if the index hasn't been reset
        """
        return self._qs.filter(pk__in=self.index)
