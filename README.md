# shakespeare_scanner

A simple Python program to demonstrate use of Textual to present a terminal-interface form, supporting keyword search against the Shakespeare play "Macbeth".

## Setup

Install dependencies using:

    pip install -r requirements.txt

## Running the program

### As a REPL

To run the search program as a REPL, open a terminal window, set default to the project directory, and run:

    python searcher.py
    
At the `>>>` prompt, enter one more more search terms. A list of matching lines will be given. (You can prefix a term with "+" or "-" to show preference or 
anti-preference for a term. Use "++" or "--" to indicate mandatory inclusion or exclusion of a term.)

To exit, enter "q" at the prompt.

### As a TUI

To run to program using the full TUI interface, open a terminal window, set default to the project directory, and run:

    python ./search/shakespeare_search.py

Like the REPL, you will be able to enter search terms in an input field at the top of the screen. Press ENTER to display the matching lines. If more lines match
than can be displayed, you can scroll to view the additional lines.

In addition, if you click on one of the matched search results, the display of the complete play in the bottom half of the screen will scroll to center itself at
the chosen line.

To exit, click the "Q" button in the footer.

## Implementation

- TUI interaction features are provided by the `textual` package (https://pypi.org/project/textual/).
- The CSV import and keyword search features are provided by the `littletable` package (https://pypi.org/project/littletable/).
