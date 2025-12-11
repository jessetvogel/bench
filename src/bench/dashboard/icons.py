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


def icon_done() -> Elem:
    return parse_svg(
        '<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="var(--green)" fill-rule="evenodd" d="M12 21a9 9 0 1 0 0-18a9 9 0 0 0 0 18m-.232-5.36l5-6l-1.536-1.28l-4.3 5.159l-2.225-2.226l-1.414 1.414l3 3l.774.774z" clip-rule="evenodd"/></svg>'  # noqa: E501
    )


def icon_loading() -> Elem:
    return SVG(
        SVGElem(
            "path",
            SVGElem(
                "animateTransform",
                **{
                    "attributeName": "transform",
                    "type": "rotate",
                    "from": "0 12 12",
                    "to": "360 12 12",
                    "dur": "1s",
                    "repeatCount": "indefinite",
                },
            ),
            fill="var(--blue)",
            d="M12 2.25c-5.384 0-9.75 4.366-9.75 9.75s4.366 9.75 9.75 9.75v-2.437A7.312 7.312 0 1 1 19.313 12h2.437c0-5.384-4.366-9.75-9.75-9.75",  # noqa: E501
        ),
        width="24",
        height="24",
        viewBox="0 0 24 24",
    )

    # return parse_svg(
    #     '<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
    #     '<path fill="currentColor" d="M12 2.25c-5.384 0-9.75 4.366-9.75 9.75s4.366 9.75 9.75 9.75v-2.437A7.312 7.312 0 1 1 19.313 12h2.437c0-5.384-4.366-9.75-9.75-9.75">'  # noqa: E501
    #     '<animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite" />'  # noqa: E501
    #     "</path>"
    #     "</svg>"
    # )


def icon_error() -> Elem:
    return parse_svg(
        '<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
        '<path fill="var(--red)" d="M12 17q.425 0 .713-.288T13 16t-.288-.712T12 15t-.712.288T11 16t.288.713T12 17m0-4q.425 0 .713-.288T13 12V8q0-.425-.288-.712T12 7t-.712.288T11 8v4q0 .425.288.713T12 13m0 9q-2.075 0-3.9-.788t-3.175-2.137T2.788 15.9T2 12t.788-3.9t2.137-3.175T8.1 2.788T12 2t3.9.788t3.175 2.137T21.213 8.1T22 12t-.788 3.9t-2.137 3.175t-3.175 2.138T12 22"/>'  # noqa: E501
        "</svg>"
    )
