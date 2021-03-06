QDataFtarame
============

A pandas DataFrame constructed from a django QuerySet. 


Initializing
----------------

If you have a django model, `MyModel`, then you can quickly convert it to a dataframe 
with:

```python
from utilities.querysetdataframe import QDataFrame

df = QDataFrame(MyModel.objects.all())
```

or you can specify the model fields you want as columns

```python
df = QDataFrame(MyModel.objects.all(), values=["field1", "field2", "fkey__field2"])
```

you can also specify fields, properties or methods on the model by using `Field()`,
`Prop()` and `Meth()`. Further, you can use the `column_name` parameter to rename 
the columns in the returned dataframe, or the `dtype` to cast the column dtype

```python
import datetime
from utilities.querysetdataframe import QDataFrame
from utilities.querysetdataframe import Field, Meth, Prop

df = QDataFrame(
    MyModel.objects.all(),
    values=[
        "field1", 
        "field2", 
        "fkey__field3",
        Field("field4", column_name="new_name")
        Prop("property1"),
        Prop("property2.subproperty"),
        Prop("fkey__field4", column_name="foobar")
        Prop("datefield", dtype=datetime.date)
        Meth("method1"),
        Meth("method2", args=(arg1,), kwargs={"kwarg_name": kwarg_val})
    ]
)
```

And the column order will be as specified.

note: if passing arguments via `Meth()` then the same arguments will be passed to the 
method for each instance (in the queryset). If you want the arguments to be dynamic 
then you should add the column as specified below


Adding columns
--------------

You can quickly add a new column by defining a function that takes one parameter, an
 instance of MyModel, and returns some value

```python
from myapp.models import MyModel

def new_column(inst: MyModel) -> float:
    ret = inst.some_forein_key.some_property
    # more calculation ...
    return ret

df.add_col(new_column)
```

You can also add multiples columns at once by returning a dictionary

```python
def new_columns(inst):
    return {
        "new_col_name_1": inst.some_property,
        "new_col_name_2": inst.some_other_propery,
    }
    
df.add_col(new_columns)
```

Finally, use can use the `column` decorator to add columns as you define the functions

```python
from querysetdataframe import column

@column(df)
def new_column2(inst):
    return inst.some_forein_key.some_property
```

The QDataFrame stores the primary key of the model as the dataframe index. If you change
the index then `add_column` will no longer work. Otherwise, you can sort and filter the 
QDataFrame and still add columns.
