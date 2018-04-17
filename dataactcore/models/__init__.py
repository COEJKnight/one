import pkgutil
import importlib
import sys


def import_models():
    """Imports all model modules in the models directory to avoid having to import related modules in scripts"""

    models_module = sys.modules[__name__]

    for module_loader, module_name, is_pkg in pkgutil.iter_modules(models_module.__path__,
                                                                   models_module.__name__ + '.'):

        importlib.import_module(module_name, module_loader.path)


import_models()
