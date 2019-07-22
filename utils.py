import logging
from .querysetdataframe import QDataFrame

log = logging.getLogger(__name__)

def column(qdf):
    """ 
     decorator that calls .add_col when the function is defined
    """
    if not isinstance(qdf, QDataFrame):
        raise TypeError('df must be type QDataFrame')
    def wrapper(func):
        log.info('adding column: {}'.format(func.__name__))
        qdf.add_col(func)
        return func
    return wrapper
