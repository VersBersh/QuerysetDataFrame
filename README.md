# QDataFrame
A pandas DataFrame constructed from a queryset.

For instance, if you have a django model, `MyModel`, then you can quickly convert it to a dataframe with

```df = QDataFrame(MyModel.objects.all())```

or

```df = QDataFrame(MyModel.objects.all(), values=['field1', 'field2', 'fkey__field2'])```

You can quickly add a new column by defining a function that takes one parameter, an instance of MyModel,
and return some value

```python
def new_column(inst):
    """ inst is an instance of MyModel """
    return inst.some_forein_key.some_property

df.add_col(new_column)
```

You can also add multiples columns at once by returning a dictionary

```python
def new_columns(inst):
    return {
        'new_col_name_1': inst.some_property,
        'new_col_name_2': inst.some_other_propery,
    }
    
df.add_col(new_columns)
```

# TO DO
upgrade for Python 3

