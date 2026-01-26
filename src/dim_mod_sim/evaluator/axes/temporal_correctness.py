"""Temporal correctness evaluation axis."""

from dim_mod_sim.evaluator.axes.base import EvaluationAxis
from dim_mod_sim.evaluator.result import AxisScore, Deduction, Severity
from dim_mod_sim.schema.models import DimensionTable, SCDType, SchemaSubmission


class TemporalCorrectnessAxis(EvaluationAxis):
    """Evaluates temporal handling and SCD strategies."""

    name = "temporal_correctness"
    max_score = 100

    def evaluate(self, submission: SchemaSubmission) -> AxisScore:
        """Evaluate temporal correctness."""
        deductions: list[Deduction] = []

        # Check 1: Do dimensions with changes use appropriate SCD?
        for dim in submission.dimension_tables:
            deductions.extend(self._check_scd_choice(dim))

        # Check 2: Can historical queries be answered?
        deductions.extend(self._check_historical_query_support(submission))

        # Check 3: Late-arriving event handling
        if self.context.config.time.late_arriving_events:
            deductions.extend(self._check_late_arriving_support(submission))

        # Check 4: Backdated correction handling
        if self.context.config.time.backdated_corrections:
            deductions.extend(self._check_backdated_support(submission))

        score = max(0, self.max_score - sum(d.points for d in deductions))

        return AxisScore(
            axis_name=self.name,
            score=score,
            max_score=self.max_score,
            deductions=deductions,
            commentary=self._generate_commentary(deductions),
        )

    def _check_scd_choice(self, dim: DimensionTable) -> list[Deduction]:
        """Check if SCD choice is appropriate for this dimension."""
        deductions = []

        requires_history = self.context.requires_scd(dim.name)

        if requires_history:
            if dim.scd_strategy in (SCDType.TYPE_1, SCDType.NONE, SCDType.TYPE_0):
                deductions.append(Deduction(
                    points=20,
                    reason=f"Dimension '{dim.name}' has changing attributes but uses {dim.scd_strategy.value} (no history)",
                    severity=Severity.MAJOR,
                    affected_elements=[dim.name],
                ))
        else:
            # Check for unnecessary complexity
            if dim.scd_strategy == SCDType.TYPE_2:
                deductions.append(Deduction(
                    points=5,
                    reason=f"Dimension '{dim.name}' uses Type 2 SCD but may not require history tracking",
                    severity=Severity.MINOR,
                    affected_elements=[dim.name],
                ))

        # Check for tracked attributes matching SCD type
        if dim.scd_strategy in (SCDType.TYPE_2, SCDType.TYPE_6):
            tracked_attrs = [a for a in dim.attributes if a.scd_tracked]
            if not tracked_attrs:
                deductions.append(Deduction(
                    points=10,
                    reason=f"Dimension '{dim.name}' uses {dim.scd_strategy.value} but no attributes are marked as SCD tracked",
                    severity=Severity.MODERATE,
                    affected_elements=[dim.name],
                ))

        return deductions

    def _check_historical_query_support(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check if historical queries can be answered correctly."""
        deductions = []

        # For each fact table, check if related dimensions support point-in-time lookup
        for fact in submission.fact_tables:
            dims = submission.get_dimensions_for_fact(fact.name)

            for dim in dims:
                if self.context.requires_scd(dim.name):
                    if dim.scd_strategy in (SCDType.TYPE_1, SCDType.NONE, SCDType.TYPE_0):
                        deductions.append(Deduction(
                            points=15,
                            reason=f"Historical queries on '{fact.name}' may be incorrect due to '{dim.name}' lacking history",
                            severity=Severity.MAJOR,
                            affected_elements=[fact.name, dim.name],
                        ))

        return deductions

    def _check_late_arriving_support(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check if late-arriving events can be handled."""
        deductions = []

        # Late-arriving facts need dimension records to exist
        # Type 2 dimensions with surrogate keys can handle this
        problem_dims = []

        for dim in submission.dimension_tables:
            # Dimensions using natural keys only may have issues
            if not dim.surrogate_key:
                problem_dims.append(dim.name)

        if problem_dims:
            deductions.append(Deduction(
                points=10,
                reason=f"Late-arriving events may cause issues with dimensions lacking surrogate keys: {problem_dims}",
                severity=Severity.MODERATE,
                affected_elements=problem_dims,
            ))

        return deductions

    def _check_backdated_support(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check if backdated corrections can be represented."""
        deductions = []

        # Need to distinguish event_timestamp from business_effective_date
        for fact in submission.fact_tables:
            all_columns = (
                [gc.name.lower() for gc in fact.grain_columns]
                + [m.name.lower() for m in fact.measures]
                + [dk.lower() for dk in fact.dimension_keys]
            )

            has_event_timestamp = any(
                "event" in col and ("time" in col or "date" in col or "ts" in col)
                for col in all_columns
            )
            has_business_date = any(
                "business" in col or "effective" in col
                for col in all_columns
            )

            if not (has_event_timestamp or has_business_date):
                deductions.append(Deduction(
                    points=10,
                    reason=f"Fact '{fact.name}' may not distinguish event time from business effective date",
                    severity=Severity.MODERATE,
                    affected_elements=[fact.name],
                ))

        return deductions
