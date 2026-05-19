from __future__ import annotations

from dataclasses import dataclass

from ibl_ai_agent.ask.domain import AnalysisResultPayload, AskExecutionContext, AskManifest, AskPlanningContext, AskRunResult, AskStructuredPlan

from .io import path_str, write_text, write_yaml_object


@dataclass(frozen=True)
class RunArtifactsStore:
    planning_context: AskPlanningContext
    execution_context: AskExecutionContext
    planner_source: str

    def persist_failed_manifest(self, *, plan: AskStructuredPlan, errors: list[str]) -> None:
        manifest = AskManifest(
            run_id=self.execution_context.artifacts.run_id,
            question=self.planning_context.question,
            manifest_path=path_str(self.execution_context.manifest_path_in),
            snapshot_id=self.execution_context.snapshot_id,
            plan_source=self.execution_context.plan_source,
            planner_source=self.planner_source,
            question_interpretation=plan.question_interpretation,
            skills_used=plan.skills_used,
            phase_status=self.execution_context.phase_status,
            errors=errors,
            runtime_mode=self.execution_context.runtime_mode,
            live_one_required=self.execution_context.live_one_required,
            live_one_ok=self.execution_context.live_one_ok,
            auth_mode=self.execution_context.auth_mode if self.execution_context.auth_mode in {"public", "private"} else None,
            failure_reason=self.execution_context.failure_reason or (errors[0] if errors else None),
        )
        write_yaml_object(
            self.execution_context.artifacts.manifest_path_out,
            manifest.model_dump(mode="python"),
        )

    def persist_success_artifacts(self, *, plan: AskStructuredPlan, result_payload: AnalysisResultPayload) -> AskRunResult:
        paths = self.execution_context.artifacts
        manifest = AskManifest(
            run_id=paths.run_id,
            question=self.planning_context.question,
            manifest_path=path_str(self.execution_context.manifest_path_in),
            snapshot_id=self.execution_context.snapshot_id,
            plan_source=self.execution_context.plan_source,
            planner_source=self.planner_source,
            question_interpretation=plan.question_interpretation,
            skills_used=plan.skills_used,
            notebook_ipynb_path=path_str(paths.notebook_ipynb),
            notebook_edit_url=paths.notebook_edit_url,
            notebook_html_path=path_str(paths.notebook_html),
            figure_path=path_str(paths.notebook_png),
            result_json_path=path_str(paths.result_json_path),
            answer_md_path=path_str(paths.answer_md),
            phase_status=self.execution_context.phase_status,
            execution_backend=self.execution_context.execution_backend,
            execute_notebook=self.execution_context.execute_notebook,
            runtime_mode=self.execution_context.runtime_mode,
            live_one_required=self.execution_context.live_one_required,
            live_one_ok=self.execution_context.live_one_ok,
            auth_mode=self.execution_context.auth_mode if self.execution_context.auth_mode in {"public", "private"} else None,
            failure_reason=self.execution_context.failure_reason or None,
            errors=[],
        )
        write_yaml_object(paths.manifest_path_out, manifest.model_dump(mode="python"))
        write_yaml_object(paths.run_dir / "plan.yaml", plan.model_dump(mode="python", exclude={"analysis_code"}))
        write_yaml_object(paths.run_dir / "plan_full.yaml", plan.model_dump(mode="python"))
        write_text(paths.run_dir / "analysis_code.py", plan.analysis_code + "\n")
        write_yaml_object(paths.run_dir / "outputs.yaml", {"outputs": result_payload.evidence})
        write_text(paths.run_dir / "question.txt", self.planning_context.question.strip() + "\n")

        return AskRunResult(
            run_id=paths.run_id,
            run_dir=paths.run_dir,
            notebook_ipynb_path=paths.notebook_ipynb,
            notebook_html_path=paths.notebook_html,
            notebook_edit_url=paths.notebook_edit_url,
            answer_md_path=paths.answer_md,
            manifest_path=paths.manifest_path_out,
        )
