import typer

app = typer.Typer()
__version__ = "0.1.0"

def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Output software version")):
    pass


if __name__ == "__main__":
    app()