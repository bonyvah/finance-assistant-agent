from app.tools.tools import TOOLS


def openai_tools():
    specs = []
    for t in TOOLS:
        tool = TOOLS[t]
        schema = tool.args_model.model_json_schema()
        spec = {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "strict": False,
            "parameters": schema,
        }
        specs.append(spec)
    return specs
