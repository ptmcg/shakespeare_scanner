import itertools
import operator
from pathlib import Path
import sys

import textual
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll, Grid
from textual.events import Mount
from textual.widgets import Header, Footer, Input, Static, DataTable

import littletable as lt


# capture location of this script
script_loc = Path(__file__).parent

play_name_table = lt.Table()
play_name_table.create_index("slug", unique=True)
play_name_table.create_index("title", unique=True)


def get_list_of_plays():
    play_name_table.csv_import(
        script_loc.parent / 'scraped.csv'
    )


def read_file_contents(fpath: Path):
    raw_source = fpath.read_bytes()
    try:
        file_text = raw_source.decode("utf-8")
    except UnicodeDecodeError:
        file_text = raw_source.decode("cp1252")
    return file_text


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

        # initialize play contents and search data
        self.play_lines: lt.Table = None
        self.play_contents: list[str] = []
        self.play_title = ""
        self.title_line_no = -1

        # initialize instance vars that will be populated in compose and event handlers
        self.search_results: lt.Table = None
        self.script_scroller: VerticalScroll = None
        self.search_results_data_table: DataTable = None

    def load_play_content(self, play_ref: str):

        # lookup play by slug or title in play_name_table
        # and get its base filename
        try:
            play_rec = play_name_table.by.slug[play_ref]
        except KeyError:
            try:
                play_rec = play_name_table.by.title[play_ref]
            except KeyError:
                raise

        play_file_name = play_rec.file_name

        # load play CSV and build search index
        self.play_lines = lt.csv_import(
            script_loc.parent / "csvs" / f"{play_file_name}.csv",
            transforms={"file_lineno": int},
        )
        self.play_lines.add_field(
            "act_scene_line",
            lambda rec: f"{rec.act}.{rec.scene.lower()}.{rec.scene_line}"
        )
        self.play_lines.create_search_index("line")

        play_text = read_file_contents(script_loc.parent / "gutenberg" / play_file_name)
        self.play_contents = play_text.splitlines()
        self.get_play_metadata_from_contents()

    def get_play_metadata_from_contents(self):
        """
        Scan through the play contents to get some useful values for display
        and navigation.
        """
        # find title line - first non-blank line after "cover"
        play_iter = iter(enumerate(self.play_contents))
        play_iter = itertools.dropwhile(lambda s: not s[1].startswith("*** START"), play_iter)
        next(play_iter)
        play_iter = itertools.dropwhile(lambda s: s[1].strip() in ("cover", ""), play_iter)
        self.title_line_no, title_line = next(play_iter)

        self.play_title: str = title_line.removeprefix("Title:").strip().title()

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
            yield Input(
                id="search-term-input",
                placeholder="Search terms...",
            )
            with Grid():
                yield search_results_table
                with VerticalScroll() as vs:
                    self.script_scroller = vs
                    yield (script_view := Static(id="script-view"))

        self.script_scroller.styles.border = ("solid", "white")

        script_view.update('\n'.join(self.play_contents))
        self.search_results_data_table = search_results_table

    def on_mount(self, event: Mount):
        # scroll the play script to the line bearing the title of the play
        self.script_scroller.scroll_to(y=self.title_line_no)

    @textual.on(Input.Submitted, "#search-term-input")
    def on_input_enter(self, event: Input.Submitted):
        """
        Event handler that runs when the user presses ENTER in the input
        field. As a result:
        - a new full-text search is run using the keywords provided in the event
        - the returned search results get sorted for display
        - the search results DataTable is cleared
        - the search results DataTable gets populated with data from
          the sorted search results
        - the search results are saved for future navigation from the DataTable
          to the scrollable play script
        """
        # perform full-text search against search index on line,
        # using search terms from event
        search_results = self.play_lines.search.line(event.value)

        # sort results in order by position in the script
        search_results.sort("file_lineno")

        # if a preference was given (indicated by a single '+' or single '-'),
        # then re-sort by search score (descending)
        if ("+" in event.value.replace("++", "")
                or "-" in event.value.replace("--", "")
        ):
            search_results.sort("line_search_score desc")

        # clear search results DataTable and populate with new search results
        self.search_results_data_table.clear()
        record_extract = operator.attrgetter("act_scene_line", "role", "line")
        self.search_results_data_table.add_rows(
            record_extract(result) for result in search_results
        )

        # save search_results table for navigation to play script lines
        self.search_results = search_results

    @textual.on(DataTable.CellSelected, "#search-results")
    def on_search_results_table_click(self, event: DataTable.CellSelected):
        """
        Event handler that runs when user selects a row of the search results DataTable.
        As a result:
        - the corresponding record is retrieved from the search_results table
        - the file_lineno field of that record is used to scroll the script contents
          to that line
        """
        data = self.search_results[event.coordinate.row]
        self.script_scroller.scroll_to(
            y=data.file_lineno - self.script_scroller.size.height // 2,
            animate=False
        )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    get_list_of_plays()

    try:
        play_reference = sys.argv[1]
    except IndexError:
        play_reference = "macbeth"

    # if no selection, pick Macbeth to start
    play_name_references = {
        *play_name_table.all.slug,
        *play_name_table.all.title,
    }

    if play_reference not in play_name_references:
        print(f"unknown play reference {play_reference!r}")
        sys.exit(1)

    app = ShakespeareSearchApp()
    app.load_play_content(play_reference)
    app.run()
