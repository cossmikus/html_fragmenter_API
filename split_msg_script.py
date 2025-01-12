import click
from pathlib import Path
from msg_split import split_message, SplitMessageError

@click.command()
@click.argument("html_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--max-len", default=4096, help="Maximum length of each fragment")
def main(html_file: Path, max_len: int):
    """
    Reads `html_file`, splits into fragments each <= `max_len`,
    prints them to stdout with their raw length.
    """
    source = Path(html_file).read_text(encoding="utf-8")

    try:
        fragments = list(split_message(source, max_len))
        for i, fragment in enumerate(fragments, start=1):
            frag_len = len(fragment)
            click.echo(f"fragment #{i}: {frag_len} chars")
            click.echo(fragment)
            click.echo("-" * 80)
    except SplitMessageError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise click.Abort()

if __name__ == "__main__":
    main()
