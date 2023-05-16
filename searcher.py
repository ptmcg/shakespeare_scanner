import littletable as lt

play = lt.Table().csv_import(
    "csvs/1533-0.txt.csv",
    transforms={}.fromkeys("scene_line file_lineno".split(), int)
)

play.add_field("act.scene.line", lambda rec: f"{rec.act}.{rec.scene.lower()}.{rec.scene_line}")
play.create_search_index("line")

while True:
    search_terms = input("\n>>> ")
    if search_terms == "q":
        break
    search_terms = search_terms.strip()
    if not search_terms:
        continue

    match_lines = play.search.line(search_terms)
    if not match_lines:
        print("no matching lines found\n")
        continue

    if "+" not in search_terms:
        match_lines.sort("file_lineno")

    match_lines.select("act.scene.line role line").present()
