# IBL AI Agent

**IBL AI Agent** helps you use a coding agent such as [**OpenAI Codex**](https://openai.com/codex/) to analyze [**International Brain Laboratory (IBL)**](https://www.internationalbrainlab.com/) data.

You run the coding agent inside this repository and ask it a **scientific question
about IBL data**. The repository gives the agent the instructions, IBL context,
and data-loading guidance it needs to write analysis code, make plots, and save
a report.

**You stay involved** so you can inspect, correct, and rerun the work.

## What This Is

- A **work in progress**.
- A repository designed for agentic coding workflows, mostly tested with
  OpenAI Codex and **requiring access to an agentic coding subscription or
  equivalent tool**.
- A **scientist-in-the-loop** workflow, not a one-shot answer generator.
- A way to ask focused questions about IBL data and get inspectable analysis
  projects under `projects/<project_slug>/`.
- A set of **derived Brain Wide Map (BWM) datasets** and instructions that make common
  BWM analyses easier for agents to load, audit, and reproduce.
- A public invitation for feedback, issues, pull requests, and collaborators.

Other coding agents, such as Claude, may work with the repository's instructions
and skills, but that path is less tested and may require modifications.

## What This Is Not

- It does not guarantee correct scientific answers.
- It does not replace your judgment. You still need to inspect the code, plots,
  statistics, and assumptions.
- It is not meant to run unattended. The best workflow is interactive: ask,
  review, correct, and continue.
- It is not a raw Neuropixels or SpikeGLX preprocessing pipeline.
- **It requires access to a coding-agent tool**, such as OpenAI Codex. That access
  usually requires a paid subscription or paid API usage.
- **You are responsible for your own agent**, API, compute, storage, and download
  costs.
- **Be careful with pay-as-you-go plans.** Long agent sessions, repeated retries,
  large analyses, or accidental loops can lead to high charges.
- The IBL AI Agent maintainers are not responsible for costs incurred while using
  this repository.
- It can run commands and edit files through your coding agent. Use sandboxing
  and permissions carefully.

## Brain Wide Map Derived Datasets

The main current scientific use case is the **IBL Brain Wide Map (BWM)**, a large
collaborative dataset mapping neural activity across the mouse brain during a
decision-making task. The flagship paper is
[A brain-wide map of neural activity during complex behaviour](https://www.nature.com/articles/s41586-025-09235-0)
in *Nature*.

This repository uses **local derived BWM datasets** because the original data
surfaces are powerful but not always agent-friendly. The derived datasets make
common analyses faster, more local, and easier to inspect. IBL AI Agent
automatically downloads these datasets upon installation.

- `bwm_ephys`: spikes from good units, units, insertions, channels, trials,
  task and passive events, and derived neural-response feature tables.
- `bwm_behavior`: trials, task events, wheel traces and features, movement and
  quiescence epochs, event-aligned behavior summaries, and camera pose summaries
  where available.

See [docs/bwm/README.md](docs/bwm/README.md) for current dataset contents,
sizes, and versions, and [docs/data_locations.md](docs/data_locations.md) for
local data setup.

## Install

The expected user path is to work from your own fork:

1. **Fork** this repository on GitHub.
2. **Clone** your fork.
3. **Install a coding agent** such as Codex.
4. **Start the coding agent from the cloned repository.**
5. **Ask the agent to install the project.**
6. **Ask a scientific question about IBL data.**

Using your own fork gives you a place to commit and publish your reports, chat
logs, and analysis projects without needing write access to the main repository.

### Step 1: Fork This Repository

Do this on **GitHub in your web browser**:

1. Go to the main IBL AI Agent repository page.
2. Click the **Fork** button near the top-right of the page.
3. Choose your GitHub account as the destination.
4. Click **Create fork**.

After this step, you should be on a page like:

```text
https://github.com/<your-github-user>/ibl-ai-agent
```

If you are new to forks, see GitHub's guide:
[Fork a repository](https://docs.github.com/en/get-started/quickstart/fork-a-repo).

### Step 2: Clone Your Fork

Type this in your **terminal**:

```bash
git clone https://github.com/<your-github-user>/ibl-ai-agent.git
cd ibl-ai-agent
```

### Step 3: Start Codex

Type this in your **terminal**, from inside the `ibl-ai-agent` directory:

```bash
codex
```

### Step 4: Ask Codex To Install

Type this in **Codex**:

```text
install
```

Codex should inspect the checkout, detect missing setup, and lead you through
anything required for the task. This can include creating the Python
environment, checking IBL data access, checking Quarto for report rendering, and
checking GitHub tools if you choose to publish a report.

### Step 5: Ask A Scientific Question

After installation finishes, type your question in **Codex**:

```text
Do mice respond faster on high-contrast trials than on low-contrast trials?
```

More setup details are in [docs/data_locations.md](docs/data_locations.md).

For manual or developer setup, use Python 3.10 or newer and
[`uv`](https://docs.astral.sh/uv/). `uv` creates a local `.venv` and installs
dependencies from [pyproject.toml](pyproject.toml), including the Git-sourced
`brainwidemap` dependency. Plain `pip install -e .` is not the recommended setup
path for this repository.

```bash
UV_CACHE_DIR=.uv-cache uv sync --extra ibl --extra notebook
UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent doctor
```

For development tools:

```bash
UV_CACHE_DIR=.uv-cache uv sync --extra ibl --extra notebook --extra dev
```

You can activate the environment in your shell:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Report rendering requires Quarto. Public report publishing requires Git, the
GitHub CLI, and an authenticated GitHub session. Codex should check these only
when they are needed and guide installation or authentication at that point.

## Workflow

IBL AI Agent is designed for interactive scientific work:

1. Ask one focused scientific question.
2. Review the project plan and question summary the agent writes.
3. Let the agent start small on a subset of cells, sessions, probes, or other
   units.
4. Inspect exploratory plots and metric-definition diagnostics.
5. Refine the question, metric, data scope, and statistical unit.
6. Lock the confirmatory plan.
7. Run the confirmatory analysis.
8. Review the final report, generated code, artifacts, caveats, and statistics.

Good prompts are focused. Name the region, metric, comparison, data scope, or
event alignment you care about. Avoid bundling several unrelated scientific
questions into one prompt.

See [docs/workflow.md](docs/workflow.md) for the detailed scientific workflow,
project directory layout, and Codex interaction pattern.

## Publishing Reports

After Codex writes a final HTML report, it can help you publish the report to a
user-owned GitHub Pages repository. Publishing is always opt-in. Reports should
be published to your own repository, not to the upstream `ibl-ai-agent` repository.

The default public report repository is:

```text
ibl-ai-agent-reports
```

The default public URL is:

```text
https://<github_owner>.github.io/ibl-ai-agent-reports/<project_slug>/
```

The v1 publisher uses the GitHub CLI. Install it from
<https://cli.github.com/> and authenticate once with:

```bash
gh auth login
```

To publish manually:

```bash
UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent publish-report-to-github \
  projects/<project_slug>/report \
  --owner <github_owner> \
  --repo ibl-ai-agent-reports \
  --slug <project_slug> \
  --confirm-public
```

The command creates or reuses `<github_owner>/ibl-ai-agent-reports`, enables
GitHub Pages from `main` branch `/docs`, stages the rendered report at
`docs/<project_slug>/`, commits it, pushes it, and prints the public URL.

Before publishing, the command scans the staged files for obvious privacy and
security risks such as credentials, raw data tables, notebooks, local paths,
usernames, and computer names. This scan is best effort only. You are
responsible for checking that the report does not reveal identifying, sensitive,
unpublished, or confidential information before making it public. To check,
open the rendered HTML report in a browser, review the visible text, figures,
captions, tables, links, hover text, and appendices, search for names,
usernames, computer names, institutions, email addresses, local paths such as
`C:\Users` or `/home`, passwords, tokens, subject identifiers, and unpublished
or private data, and review the `files_to_publish` manifest printed by the
publishing command.

## Example Reports And Chat Logs

Work in progress. This section will link to reviewed reports and associated chat
logs once they have been reviewed for public release.

Planned examples include:

- Positive controls that recover known or expected effects.
- Analyses that expose useful BWM dataset structure.
- Negative examples and false-positive failure modes.

## Lessons Learned So Far

Work in progress. This section will be filled after the public examples are
selected and reviewed.

Expected themes include dataset surfaces for agents, ambiguity in scientific
metrics, the value of exploratory plots, and caution around false positives.

## Related Work

- [A brain-wide map of neural activity during complex behaviour](https://www.nature.com/articles/s41586-025-09235-0)
- Haussler group work on agentic or AI-assisted scientific analysis. Full
  citation to be added.

## Future Work

Work in progress. Current candidate directions:

- A compressed LFP dataset.
- A compact `bwm_neurobehavior` query layer for broad questions about where
  task, movement, pose, and behavioral-state information is represented in the
  brain.
- Laptop-sized brain-behavior correlation and ephys-feature datasets.
- More reviewed public reports and chat logs.
- Stronger examples of negative controls and false-positive failure modes.

## Contribute

Feedback, issues, pull requests, and collaborators are welcome.

- Open an issue for bugs, confusing docs, missing examples, or questionable
  scientific behavior.
- Open a pull request for documentation, skills, data-loading improvements,
  tests, or examples.
- See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for development setup and
  quality gates.

## FAQs

**Do I need Codex?**

Codex is the best-tested interface. Other coding agents may work, but expect
rough edges.

**Is this safe to run unattended?**

No. The workflow is designed for interactive review of plans, code, plots,
statistics, and caveats.

**Where do outputs go?**

Scientific outputs should go under `projects/<project_slug>/`. See
[docs/workflow.md](docs/workflow.md).

**Does it download data?**

It can. For public BWM analyses, agents may offer to download derived datasets
if no local data location is configured. See
[docs/data_locations.md](docs/data_locations.md).

**How much disk space do the public BWM derived datasets need?**

Less than 10 GB for all spikes from good units and behavior data from the BWM.

See [docs/bwm/README.md](docs/bwm/README.md) for more details. You
will also need working space for generated artifacts.

**Can it use private IBL data?**

The repository includes IBL access tooling, but public BWM local datasets are
the default path for public examples. See [docs/data_locations.md](docs/data_locations.md)
for access checks.

**How do I know whether a result is trustworthy?**

Inspect the question definition, data split, metric diagnostics, code,
exploratory plots, confirmatory statistics, caveats, and report. Treat generated
results as scientific claims requiring review, not as final authority.

## Credits

IBL AI Agent builds on data, tools, and scientific work from the International
Brain Laboratory community.

Funding acknowledgements to be added before public release.
