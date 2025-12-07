from html.parser import HTMLParser
from typing import cast

from slash.basic import SVG, SVGElem
from slash.core import Elem
from slash.html import Div


class MyHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._stack: list[Elem] = [Div()]
        self._svg_stack: list[SVG] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        elem: Elem
        attrs_dict = {name: "" if value is None else value for name, value in attrs}
        if tag == "svg":
            elem = SVG(**attrs_dict)
            self._svg_stack.append(elem)
        elif self._svg_stack:
            elem = SVGElem(tag, **attrs_dict)
        else:
            elem = Elem(tag, **attrs_dict)

        self._stack[-1].append(elem)
        self._stack.append(elem)

    def handle_endtag(self, tag: str):
        if len(self._stack) == 1:
            msg = f"Encountered unexpected closing tag </{tag}>"
            raise ValueError(msg)
        if self._stack[-1].tag != tag:
            msg = f"Closing tag </{tag}> does not match opening tag <{self._stack[-1].tag}>"
            raise ValueError(msg)
        self._stack.pop()
        if tag == "svg":
            self._svg_stack.pop()

    def handle_data(self, data: str):
        self._stack[-1].append(data)

    def get(self) -> list[Elem | str]:
        if len(self._stack) != 1:
            msg = f"Expected closing tag </{self._stack[-1]}> before end of HTML"
            raise ValueError(msg)
        return list(self._stack[0].children)


def parse_svg(html: str) -> Elem:
    parser = MyHTMLParser()
    parser.feed(html.strip())
    return cast(Elem, parser.get()[0])


def icon_oplus() -> Elem:
    return parse_svg(
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M9 12H15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M12 9L12 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="#323232" stroke-width="2"/>'  # noqa: E501
        "</svg>"
    )
