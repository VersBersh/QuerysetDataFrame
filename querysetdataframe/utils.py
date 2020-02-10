from .qdataframe import QDataFrame

import logging
log = logging.getLogger(__name__)


def column(qdf: QDataFrame, fast=False):
    """ decorator that calls .add_col when the function is defined

     Args:
        qdf: a QDataFrame to add the column to
        fast: set to True if function only uses properties of the model
            that already exist in the QDataFrame and therefore can be
            calculated without any database queries.
    """

    if not isinstance(qdf, QDataFrame):
        raise TypeError('qdf must be a QDataFrame')

    def wrapper(func):
        log.info(f"adding column: {func.__name__}")
        qdf.add_col(func, fast)
        return func

    return wrapper
