from __future__ import annotations

from pathlib import Path

import typer

from ibl_ai_agent.commands.common import fail
from ibl_ai_agent.report_publish import DEFAULT_REPORTS_REPO, publish_report_to_github, stage_report_site


PUBLIC_WARNING = (
    "This report will be public. I will avoid publishing obvious local paths, credentials, "
    "cache files, raw data, and private project artifacts, but you are responsible for checking "
    "that the report does not reveal identifying, sensitive, unpublished, or confidential information.\n"
    "How to check before confirming: open the rendered HTML report in a browser; review the title, "
    "text, figures, captions, tables, links, hover text, and appendices; use browser search for your "
    "name, username, computer name, institution, email addresses, local paths such as C:\\Users or "
    "/home, passwords, tokens, subject identifiers, and unpublished or private data; then review the "
    "files_to_publish manifest printed by this command."
)


def register(app: typer.Typer) -> None:
    @app.command("publish-report-to-github")
    def publish_report_to_github_command(
        report_path: Path = typer.Argument(
            ...,
            exists=True,
            readable=True,
            help="Quarto HTML report directory or HTML report file.",
        ),
        owner: str = typer.Option(
            ...,
            help="GitHub user or organization that will own the public Pages repository.",
        ),
        repo: str = typer.Option(
            DEFAULT_REPORTS_REPO,
            help="GitHub repository used for public report hosting.",
        ),
        slug: str | None = typer.Option(
            None,
            help="Public URL slug. Defaults to the project slug inferred from the report path.",
        ),
        title: str | None = typer.Option(
            None,
            help="Optional report title for the root report index.",
        ),
        publish_root: Path = typer.Option(
            Path(".ibl-ai-agent-publish"),
            help="Local workspace for the cloned report publishing repository.",
        ),
        overwrite: bool = typer.Option(
            False,
            "--overwrite",
            help="Replace an existing report with the same slug.",
        ),
        confirm_public: bool = typer.Option(
            False,
            "--confirm-public",
            help="Confirm that the report has been reviewed and may be published publicly.",
        ),
        allow_risky: bool = typer.Option(
            False,
            "--allow-risky",
            help="Allow publication despite privacy/security preflight blockers.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Stage and scan files without creating, committing, pushing, or enabling Pages.",
        ),
    ) -> None:
        """Publish a Quarto HTML report to a user-owned GitHub Pages repository."""
        typer.echo(PUBLIC_WARNING)
        if not dry_run and not confirm_public:
            try:
                preflight = publish_report_to_github(
                    report_path,
                    owner=owner,
                    repo=repo,
                    slug=slug,
                    title=title,
                    publish_root=publish_root / "_preflight",
                    overwrite=True,
                    confirm_public=False,
                    allow_risky=allow_risky,
                    dry_run=True,
                )
            except Exception as exc:
                fail(str(exc))
            _echo_staged_manifest(preflight.staged)
            if preflight.staged.has_blockers and not allow_risky:
                fail("Privacy/security preflight found blockers. Review the staged manifest above.")
            if not typer.confirm("Publish these files publicly on GitHub Pages?"):
                fail("Publication cancelled.")
            confirm_public = True

        try:
            result = publish_report_to_github(
                report_path,
                owner=owner,
                repo=repo,
                slug=slug,
                title=title,
                publish_root=publish_root,
                overwrite=overwrite,
                confirm_public=confirm_public,
                allow_risky=allow_risky,
                dry_run=dry_run,
            )
        except Exception as exc:
            fail(str(exc))

        _echo_staged_manifest(result.staged)
        mode = "dry_run" if dry_run else "published"
        typer.echo(f"mode={mode}")
        typer.echo(f"repo={result.repo_full_name}")
        typer.echo(f"local_repo={result.local_repo}")
        typer.echo(f"url={result.url}")

    @app.command("stage-report-site")
    def stage_report_site_command(
        report_path: Path = typer.Argument(
            ...,
            exists=True,
            readable=True,
            help="Quarto HTML report directory or HTML report file.",
        ),
        site_dir: Path = typer.Option(..., help="Local output directory for the static report site."),
        slug: str | None = typer.Option(None, help="URL slug for the staged report."),
        title: str | None = typer.Option(None, help="Optional report title for the root report index."),
        overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing staged report."),
        allow_risky: bool = typer.Option(
            False,
            "--allow-risky",
            help="Stage files despite privacy/security preflight blockers.",
        ),
    ) -> None:
        """Stage a report into a local static site directory without GitHub operations."""
        typer.echo(PUBLIC_WARNING)
        try:
            staged = stage_report_site(
                report_path,
                site_dir=site_dir,
                slug=slug,
                title=title,
                overwrite=overwrite,
                allow_risky=allow_risky,
            )
        except Exception as exc:
            fail(str(exc))
        _echo_staged_manifest(staged)
        if staged.has_blockers and not allow_risky:
            fail("Privacy/security preflight found blockers. Review the staged manifest above.")
        typer.echo(f"site_dir={staged.site_dir}")
        typer.echo(f"report_dir={staged.report_dir}")
        typer.echo(f"slug={staged.slug}")


def _echo_staged_manifest(staged: object) -> None:
    typer.echo("files_to_publish:")
    for path in getattr(staged, "files"):
        typer.echo(f"- {path}")
    findings = getattr(staged, "findings")
    if findings:
        typer.echo("preflight_findings:")
        for finding in findings:
            typer.echo(f"- {finding.severity}: {finding.path}: {finding.message}")
    else:
        typer.echo("preflight_findings: none")
