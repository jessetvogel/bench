import argparse

from slash import App
from slash.core import Elem, Session
from slash.html import Div
from slash.layout import Row

from bench.dashboard._sidebar import Sidebar


def main() -> None:
    # Parse arguments
    parser = argparse.ArgumentParser(prog="bench-dashboard", description="Launch the BENCH dashboard.")
    _ = parser.parse_args()

    # Launch app
    app = App()
    app.add_route("/", home)
    app.run()


def home() -> Elem:
    # Set document title
    Session.require().set_title("BENCH dashboard")

    # Create content and sidebar
    content = Div().style({"flex-grow": "1", "padding": "0px 8px 0px 16px"})

    def set_content(elem: Elem):
        content.clear()
        content.append(elem)

    sidebar = Sidebar(set_content)

    return Row(sidebar, content)
