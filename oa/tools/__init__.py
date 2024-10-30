import importlib
import inspect
from .config import INSTALLED_TOOLS


FUNCTION_DEFINITIONS = []


for module_name in INSTALLED_TOOLS:
    # Import the module
    module = importlib.import_module(f"oa.tools.{module_name}")

    # Get all classes in the module
    classes = inspect.getmembers(module, inspect.isclass)

    for class_name, cls in classes:
        # Ensure the class is defined in the current module (not imported)
        if cls.__module__ == module.__name__:
            # Check if the class has a `definition` method
            if hasattr(cls, 'definition') and callable(getattr(cls, 'definition')):
                # Call the method directly without initializing, as it's a class method
                definition = cls.definition()

                # Add the definition output to FUNCTION_DEFINITIONS
                FUNCTION_DEFINITIONS.append(definition)
