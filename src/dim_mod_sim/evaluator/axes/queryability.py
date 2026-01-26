"""Queryability evaluation axis (bonus)."""

from dim_mod_sim.evaluator.axes.base import EvaluationAxis
from dim_mod_sim.evaluator.result import AxisScore, Deduction, Severity
from dim_mod_sim.schema.models import SchemaSubmission


class QueryabilityAxis(EvaluationAxis):
    """Evaluates how queryable the model is for common analytics."""

    name = "queryability"
    max_score = 100  # This is a bonus axis

    def evaluate(self, submission: SchemaSubmission) -> AxisScore:
        """Evaluate queryability bonuses."""
        # Start at 0 and add bonuses instead of deducting
        bonuses: list[Deduction] = []

        # Check for good practices that make querying easier
        bonuses.extend(self._check_date_dimension(submission))
        bonuses.extend(self._check_conformed_dimensions(submission))
        bonuses.extend(self._check_aggregate_tables(submission))
        bonuses.extend(self._check_naming_conventions(submission))

        # Calculate score as sum of bonuses
        score = min(self.max_score, sum(b.points for b in bonuses))

        return AxisScore(
            axis_name=self.name,
            score=score,
            max_score=self.max_score,
            deductions=bonuses,  # These are actually bonuses with positive points
            commentary=self._generate_bonus_commentary(bonuses, score),
        )

    def _check_date_dimension(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for a well-designed date dimension."""
        bonuses = []

        date_dims = [
            dt for dt in submission.dimension_tables
            if "date" in dt.name.lower() or "time" in dt.name.lower()
        ]

        if date_dims:
            bonuses.append(Deduction(
                points=15,
                reason="Date/time dimension present for time-based analysis",
                severity=Severity.MINOR,
                affected_elements=[d.name for d in date_dims],
            ))

            # Check for rich date attributes
            for dim in date_dims:
                date_attrs = [a.name.lower() for a in dim.attributes]
                rich_attrs = ["year", "quarter", "month", "week", "day", "fiscal"]
                found_rich = sum(1 for attr in rich_attrs if any(attr in da for da in date_attrs))

                if found_rich >= 3:
                    bonuses.append(Deduction(
                        points=10,
                        reason=f"Date dimension '{dim.name}' has rich time hierarchy attributes",
                        severity=Severity.MINOR,
                        affected_elements=[dim.name],
                    ))

        return bonuses

    def _check_conformed_dimensions(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for conformed dimensions used across facts."""
        bonuses = []

        # Count how many facts each dimension is connected to
        dim_usage: dict[str, int] = {}
        for rel in submission.relationships:
            dim_name = rel.dimension_table
            dim_usage[dim_name] = dim_usage.get(dim_name, 0) + 1

        # Bonus for dimensions used across multiple facts
        conformed = [name for name, count in dim_usage.items() if count >= 2]
        if conformed:
            bonuses.append(Deduction(
                points=15,
                reason=f"Conformed dimensions used across multiple facts: {conformed}",
                severity=Severity.MINOR,
                affected_elements=conformed,
            ))

        return bonuses

    def _check_aggregate_tables(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for pre-aggregated summary tables."""
        bonuses = []

        # Look for aggregate/summary facts
        agg_patterns = ["summary", "aggregate", "daily", "monthly", "snapshot"]
        agg_facts = [
            ft for ft in submission.fact_tables
            if any(p in ft.name.lower() for p in agg_patterns)
        ]

        if agg_facts:
            bonuses.append(Deduction(
                points=10,
                reason=f"Pre-aggregated tables may improve query performance: {[f.name for f in agg_facts]}",
                severity=Severity.MINOR,
                affected_elements=[f.name for f in agg_facts],
            ))

        return bonuses

    def _check_naming_conventions(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for consistent naming conventions."""
        bonuses = []

        # Check fact naming
        fact_prefixes = [ft.name.split("_")[0].lower() for ft in submission.fact_tables]
        if all(p == "fact" or p == "fct" for p in fact_prefixes):
            bonuses.append(Deduction(
                points=5,
                reason="Consistent fact table naming convention",
                severity=Severity.MINOR,
                affected_elements=["naming"],
            ))

        # Check dimension naming
        dim_prefixes = [dt.name.split("_")[0].lower() for dt in submission.dimension_tables]
        if all(p == "dim" or p == "dimension" for p in dim_prefixes):
            bonuses.append(Deduction(
                points=5,
                reason="Consistent dimension table naming convention",
                severity=Severity.MINOR,
                affected_elements=["naming"],
            ))

        # Check surrogate key naming
        sk_patterns = [dt.surrogate_key.lower() for dt in submission.dimension_tables]
        consistent_sk = all(
            sk.endswith("_key") or sk.endswith("_sk") or sk.endswith("_id")
            for sk in sk_patterns
        )
        if consistent_sk:
            bonuses.append(Deduction(
                points=5,
                reason="Consistent surrogate key naming convention",
                severity=Severity.MINOR,
                affected_elements=["naming"],
            ))

        return bonuses

    def _generate_bonus_commentary(self, bonuses: list[Deduction], score: int) -> str:
        """Generate commentary for bonuses."""
        if score >= 40:
            return "Good queryability with multiple best practices implemented."
        elif score >= 20:
            return "Decent queryability with some best practices."
        elif score > 0:
            return "Basic queryability; consider adding more analytical conveniences."
        else:
            return "No specific queryability bonuses detected."
