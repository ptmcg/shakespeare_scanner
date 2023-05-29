import itertools
import operator

import textual
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll, Grid
from textual.events import Event
from textual.widgets import Header, Footer, Input, Static, DataTable

from pathlib import Path

import littletable as lt


class InputSubmitEvent(Event):
    def __init__(self, input_value):
        super().__init__()
        self.value = input_value


class ShakespeareSearchApp(App):
    """
    A Textual app to search Shakespeare plays for given search terms.

    TODO:
    - add selector for different plays
    - add help popup
        . show how to add multiple search terms, with optional +, -, ++, and --
        . click on results to scroll the script to that line in the play
    - search multiple plays
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        script_loc = Path(__file__).parent

        # load play CSV and build search index
        self.play = lt.Table().csv_import(
            script_loc.parent / "csvs" / "1533-0.txt.csv",
            transforms={"file_lineno": int},
        )
        self.play.add_field(
            "act_scene_line",
            lambda rec: f"{rec.act}.{rec.scene.lower()}.{rec.scene_line}"
        )
        self.play.create_search_index("line")

        self.play_contents: list[str] = Path("gutenberg/1533-0.txt").read_text().splitlines()

        # find title line - first non-blank line after "cover"
        play_iter = iter(enumerate(self.play_contents))
        play_iter = itertools.dropwhile(lambda s: s[1].strip() != "cover", play_iter)
        next(play_iter)
        play_iter = itertools.dropwhile(lambda s: not s[1].strip(), play_iter)
        self.title_line_no = next(play_iter)[0]

        title_line = next(line for line in self.play_contents if line.startswith("Title:"))
        self.play_title: str = title_line.removeprefix("Title:").strip()

        # initialize instance vars that will be populated in event handlers
        self.search_results: lt.Table = None
        self.script_scroller: VerticalScroll = None
        self.search_results_table: DataTable = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        search_results_table = DataTable(id="search-results")
        search_results_table.add_columns(
            "Act.Scene.Line",
            "Role",
            "Line",
        )
        search_results_table.zebra_stripes = True

        yield Header(show_clock=True)
        self.title = "Shakespeare Keyword Search"
        self.sub_title = self.play_title

        yield Footer()
        with Container():
            yield Input(placeholder="Search terms...")
            with Grid():
                yield search_results_table
                with VerticalScroll() as vs:
                    self.script_scroller = vs
                    yield (script_view := Static(id="script-view"))

        self.script_scroller.styles.border = ("solid", "white")

        script_view.update('\n'.join(self.play_contents))
        self.search_results_table = search_results_table

    def on_mount(self, event):
        self.script_scroller.scroll_to(y=self.title_line_no)

    @textual.on(DataTable.CellSelected, "#search-results")
    def on_data_table_click(self, event):
        data = self.search_results[event.coordinate.row]
        self.script_scroller.scroll_to(
            y=data.file_lineno - self.script_scroller.size.height // 2,
            animate=False
        )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def on_key(self, event):
        if event.key == 'enter':
            input_widget = self.query_one(Input)
            self.on_enter(InputSubmitEvent(input_widget.value))

    def on_enter(self, event: InputSubmitEvent):
        search_results = self.play.search.line(event.value)

        # sort results in order by position in the script
        search_results.sort("file_lineno")

        # if a preference was given, then re-sort by search score (descending)
        if "+" in event.value.replace("++", "") or "-" in event.value.replace("--", ""):
            search_results.sort("line_search_score desc")

        results_table: DataTable = self.search_results_table

        # clear search results list
        results_table.clear()

        # populate search results list
        self.search_results = search_results
        record_extract = operator.attrgetter("act_scene_line", "role", "line")
        for result in search_results:
            results_table.add_row(*record_extract(result))


if __name__ == "__main__":
    app = ShakespeareSearchApp()
    app.run()
