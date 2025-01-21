import inspect
import docstring_parser


class AssistantTool(object):
    def main(self):
        raise NotImplementedError

    def execute(self):
        try:
            self.main()
        except Exception as e:
            return {'Error': str(e)}

    @classmethod
    def definition(cls):
        """
        Generate a JSON description of the class in the format expected by the assistant
        """
        # Get class name and docstring
        class_name = cls.__name__
        class_docstring = inspect.getdoc(cls)

        # Initialize JSON structure
        json_description = {
            "name": class_name,
            "description": class_docstring,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

        # Inspect the __init__ method to find parameters and their annotations
        init_method = cls.__init__
        if init_method:
            # Parse the docstring of __init__ to get parameter descriptions
            init_docstring = inspect.getdoc(init_method)
            if init_docstring:
                parsed_docstring = docstring_parser.parse(init_docstring)
                param_descriptions = {param.arg_name: param.description for param in parsed_docstring.params}

            sig = inspect.signature(init_method)

            # Loop through parameters in the __init__ method
            for name, param in sig.parameters.items():
                # Skip 'self' parameter
                if name == 'self':
                    continue

                # Get the parameter type and use parsed description if available
                param_type = param.annotation if param.annotation != inspect._empty else "string"
                param_description = param_descriptions.get(name, "")

                # Populate properties
                json_description["parameters"]["properties"][name] = {
                    "type": param_type if isinstance(param_type, str) else param_type.__name__,
                    "description": param_description
                }

                # Add to required list if there's no default value
                if param.default == inspect._empty:
                    json_description["parameters"]["required"].append(name)

        return json_description

