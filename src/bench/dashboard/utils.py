from slash.core import Handler, Session
from slash.html import Button, Dialog, Div, Input, Span
from slash.layout import Column, Row

from bench.templates import Param

INPUT_TYPE: dict[type[int | float | str], str] = {
    bool: "number",
    int: "number",
    float: "number",
    str: "text",
}


def prompt(
    title: str,
    description: str,
    params: list[Param],
    handler: Handler[dict[str, int | float | str]],
) -> None:
    # Create inputs
    inputs: dict[str, Input] = {}
    for param in params:
        inputs[param.name] = (input := Input())
        input.type = INPUT_TYPE.get(param.type, "text")
        if param.default is not None:
            input.value = str(param.default)

    dialog: Dialog

    def submit() -> None:
        dialog.close()
        values: dict[str, int | float | str] = {}
        for param in params:
            value = inputs[param.name].value
            if param.type is bool:
                values[param.name] = bool(value)
            elif param.type is int:
                values[param.name] = int(value)
            elif param.type is float:
                values[param.name] = float(value)
            else:
                values[param.name] = value
        Session.require().call_handler(handler, values)

    dialog = Dialog(
        Column(
            Div(title).style({"font-size": "1.5rem", "font-weight": "bold"}),
            Div(description),
            Div(*[[Span(param.name), inputs[param.name]] for param in params]).style(
                {
                    "display": "grid",
                    "grid-template-columns": "repeat(2, auto)",
                    "align-items": "center",
                    "gap": "8px",
                }
            ),
            Row(
                Button("Submit").onclick(submit),
                Button("Cancel").onclick(lambda: dialog.close()),
            ).style({"justify-content": "center", "gap": "16px"}),
        ).style({"gap": "16px"})
    ).style({"max-width": "512px"})

    dialog.mount()
    dialog.show_modal()


class Form(Div):
    def __init__(self, params: list[Param]) -> None:
        super().__init__()
        self._params = {param.name: param for param in params}
        self._setup()

    def _setup(self) -> None:
        # Create inputs
        self._inputs: dict[str, Input] = {}
        for name, param in self._params.items():
            self._inputs[name] = (input := Input())
            input.type = INPUT_TYPE.get(param.type, "text")
            if param.default is not None:
                input.value = str(param.default)

        # Create grid of inputs
        self.append(
            Column(
                Div(*[[Span(name), self._inputs[name]] for name in self._params]).style(
                    {
                        "display": "grid",
                        "grid-template-columns": "repeat(2, auto)",
                        "align-items": "center",
                        "gap": "8px",
                    }
                ),
            ).style({"gap": "16px"})
        )

    def value(self, param: Param) -> int | float | str:
        value = self._inputs[param.name].value
        if param.type is int:
            return int(value)
        if param.type is float:
            return float(value)
        return str(value)
