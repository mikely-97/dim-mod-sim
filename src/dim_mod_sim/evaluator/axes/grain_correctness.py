"""Grain correctness evaluation axis."""

from dim_mod_sim.evaluator.axes.base import EvaluationAxis
from dim_mod_sim.evaluator.result import AxisScore, Deduction, Severity
from dim_mod_sim.schema.models import SchemaSubmission


class GrainCorrectnessAxis(EvaluationAxis):
    """Evaluates grain declarations and consistency."""

    name = "grain_correctness"
    max_score = 100

    def evaluate(self, submission: SchemaSubmission) -> AxisScore:
        """Evaluate grain correctness."""
        deductions: list[Deduction] = []

        for fact in submission.fact_tables:
            # Check 1: Is grain explicitly declared?
            deductions.extend(self._check_grain_declaration(fact))

            # Check 2: Do grain columns match declaration?
            deductions.extend(self._check_grain_columns(fact))

            # Check 3: Detect fan-out risk
            deductions.extend(self._check_fan_out_risk(fact, submission))

            # Check 4: Mixed grain detection
            deductions.extend(self._check_mixed_grain(fact))

        score = max(0, self.max_score - sum(d.points for d in deductions))

        return AxisScore(
            axis_name=self.name,
            score=score,
            max_score=self.max_score,
            deductions=deductions,
            commentary=self._generate_commentary(deductions),
        )

    def _check_grain_declaration(self, fact) -> list[Deduction]:
        """Check if grain is properly declared."""
        deductions = []

        if not fact.grain_description or len(fact.grain_description.strip()) < 10:
            deductions.append(Deduction(
                points=10,
                reason=f"Fact table '{fact.name}' has no or insufficient grain description",
                severity=Severity.MODERATE,
                affected_elements=[fact.name],
            ))

        return deductions

    def _check_grain_columns(self, fact) -> list[Deduction]:
        """Check if grain columns are properly defined."""
        deductions = []

        grain_cols = fact.grain_columns
        dim_keys = fact.dimension_keys

        # Check that grain columns reference dimensions or are degenerate
        for gc in grain_cols:
            if gc.references_dimension:
                if gc.references_dimension not in dim_keys:
                    deductions.append(Deduction(
                        points=10,
                        reason=f"Grain column '{gc.name}' references '{gc.references_dimension}' which is not in dimension_keys",
                        severity=Severity.MODERATE,
                        affected_elements=[fact.name, gc.name],
                    ))
            elif not gc.is_degenerate:
                deductions.append(Deduction(
                    points=5,
                    reason=f"Grain column '{gc.name}' should reference a dimension or be marked as degenerate",
                    severity=Severity.MINOR,
                    affected_elements=[fact.name, gc.name],
                ))

        return deductions

    def _check_fan_out_risk(self, fact, submission: SchemaSubmission) -> list[Deduction]:
        """Detect fan-out risk from one-to-many joins."""
        deductions = []

        relationships = submission.get_relationships_for_fact(fact.name)

        for rel in relationships:
            if rel.cardinality == "many-to-many":
                # Many-to-many without bridge table is a fan-out risk
                has_bridge = any(
                    bt.fact_table == fact.name and bt.dimension_table == rel.dimension_table
                    for bt in submission.bridge_tables
                )
                if not has_bridge:
                    deductions.append(Deduction(
                        points=20,
                        reason=f"Many-to-many relationship between '{fact.name}' and '{rel.dimension_table}' without bridge table",
                        severity=Severity.MAJOR,
                        affected_elements=[fact.name, rel.dimension_table],
                    ))

        return deductions

    def _check_mixed_grain(self, fact) -> list[Deduction]:
        """Check for signs of mixed grain in a single fact table."""
        deductions = []

        grain_desc = fact.grain_description.lower()

        # Warning signs of mixed grain
        mixed_indicators = ["or", "sometimes", "depending", "either", "mixed"]
        for indicator in mixed_indicators:
            if indicator in grain_desc:
                deductions.append(Deduction(
                    points=25,
                    reason=f"Fact '{fact.name}' grain description suggests mixed grain (contains '{indicator}')",
                    severity=Severity.CRITICAL,
                    affected_elements=[fact.name],
                ))
                break

        # Check for multiple different grain-like patterns
        grain_patterns = ["transaction", "line item", "order", "event", "snapshot"]
        found_patterns = [p for p in grain_patterns if p in grain_desc]
        if len(found_patterns) > 1:
            deductions.append(Deduction(
                points=15,
                reason=f"Fact '{fact.name}' grain mentions multiple concepts: {found_patterns}",
                severity=Severity.MAJOR,
                affected_elements=[fact.name],
            ))

        return deductions
