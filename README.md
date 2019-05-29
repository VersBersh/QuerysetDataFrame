# QuerysetDataFrame
A pandas DataFrame constructed from a queryset.

For instance, if you have a django model, `MyModel`, then you can quickly convert it to a dataframe with

```df = QuerysetDataFrame(MyModel.objects.all())```

Further, you can quickly add a new column by defining a function that takes one parameter, an instance of MyModel,
and return some value

```
def new_column(inst):
    """ inst is an instance of MyModel """
    return inst.some_forein_key.some_property

df.add_col(new_column)
```


# TO DO
upgrade for Python 3

