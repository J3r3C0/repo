import asyncio, json, sys, click
from typing import Any, Dict, List, Sequence
from .client import SheratanClient

@click.group()
def cli():
    pass

def _normalize_rows(data: Any) -> Sequence[Dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, dict):
        # If dict of dicts (e.g. keyed by id), turn into list of dicts
        if all(isinstance(v, dict) for v in data.values()):
            rows: List[Dict[str, Any]] = []
            for key, value in data.items():
                row = {"key": key}
                row.update(value)
                rows.append(row)
            return rows
        return [data]
    if isinstance(data, (list, tuple)):
        rows: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                rows.append(item)
            else:
                rows.append({"value": item})
        return rows
    return [{"value": data}]


def _render_table(data: Any) -> str:
    rows = list(_normalize_rows(data))
    if not rows:
        return "(no data)"
    headers: List[str] = sorted({key for row in rows for key in row.keys()})
    widths = {header: max(len(header), *(len(str(row.get(header, ""))) for row in rows)) for header in headers}
    sep = " | "
    header_line = sep.join(f"{header:{widths[header]}}" for header in headers)
    divider = "-+-".join("-" * widths[header] for header in headers)
    body_lines = [
        sep.join(f"{str(row.get(header, '')):{widths[header]}}" for header in headers)
        for row in rows
    ]
    return "\n".join([header_line, divider, *body_lines])


def _echo(data: Any, output: str) -> None:
    if output == "json":
        click.echo(json.dumps(data, indent=2, sort_keys=True))
    else:
        click.echo(_render_table(data))


def _async_run(coro):
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        click.echo("Aborted.", err=True)
        sys.exit(1)


@cli.command()
@click.option("--model", default="gpt-4o-mini", show_default=True)
@click.option("--prompt", required=True)
@click.option("--max_tokens", default=128, show_default=True, type=int)
@click.option("--output", type=click.Choice(["table", "json"]), default="table", show_default=True)
def complete(model, prompt, max_tokens, output):
    """LLM-Complete via Sheratan Core"""

    async def _run():
        c = SheratanClient()
        res = await c.complete(model=model, prompt=prompt, max_tokens=max_tokens)
        _echo(res, output)

    _async_run(_run())


@cli.group()
def jobs():
    """Job-Management"""


@jobs.command("submit")
@click.option("--model", default="gpt-4o-mini", show_default=True)
@click.option("--prompt", required=True)
@click.option("--max_tokens", default=128, show_default=True, type=int)
@click.option("--output", type=click.Choice(["table", "json"]), default="table", show_default=True)
def jobs_submit(model, prompt, max_tokens, output):
    """LLM-Job asynchron einreichen"""

    async def _run():
        c = SheratanClient()
        res = await c.submit_job(model=model, prompt=prompt, max_tokens=max_tokens)
        _echo(res, output)

    _async_run(_run())


@jobs.command("watch")
@click.argument("job_id")
@click.option("--interval", default=2.0, show_default=True, type=float)
@click.option("--output", type=click.Choice(["table", "json"]), default="table", show_default=True)
def jobs_watch(job_id, interval, output):
    """Job-Status beobachten"""

    async def _run():
        c = SheratanClient()
        res = await c.watch_job(job_id=job_id, interval=interval)
        _echo(res, output)

    _async_run(_run())


@cli.group()
def router():
    """Router-Operationen"""


@router.command("health")
@click.option("--output", type=click.Choice(["table", "json"]), default="table", show_default=True)
def router_health(output):
    """Health-Status des Routers abrufen"""

    async def _run():
        c = SheratanClient()
        res = await c.router_health()
        _echo(res, output)

    _async_run(_run())


@cli.group()
def models():
    """Model-Verwaltung"""


@models.command("list")
@click.option("--output", type=click.Choice(["table", "json"]), default="table", show_default=True)
def models_list(output):
    """Verfügbare Modelle anzeigen"""

    async def _run():
        c = SheratanClient()
        res = await c.list_models()
        if isinstance(res, dict) and "data" in res:
            payload = res["data"]
        else:
            payload = res
        _echo(payload, output)

    _async_run(_run())

if __name__ == "__main__":
    cli()
