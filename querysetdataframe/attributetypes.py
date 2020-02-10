
class Prop:
    """ specifies a property on the model """

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class Meth:
    """ specifies a method on the model """

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args if (args is not None) else ()
        self.kwargs = kwargs if (kwargs is not None) else {}

    def __str__(self):
        return self.name

    def call(self, inst):
        return getattr(inst, self.name)(*self.args, **self.kwargs)
