from agent.registry import TOOL_FUNCTIONS


def execute_tool(name, arguments):

    if name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown tool: {name}")

    function = TOOL_FUNCTIONS[name]

    # Clean malformed empty arguments from the model.
    if arguments is None:
        arguments = {}

    if isinstance(arguments, dict):
        arguments = {
            key: value
            for key, value in arguments.items()
            if key
        }

    # Tool requires no arguments.
    if not arguments:
        return function()

    return function(**arguments)
