"""Structural optimality evaluation axis."""

from dim_mod_sim.evaluator.axes.base import EvaluationAxis
from dim_mod_sim.evaluator.feedback import ViolationType
from dim_mod_sim.evaluator.result import AxisScore, Deduction, Severity
from dim_mod_sim.schema.models import SchemaSubmission


class StructuralOptimalityAxis(EvaluationAxis):
    """Evaluates structural efficiency of the model."""

    name = "structural_optimality"
    max_score = 100

    def evaluate(self, submission: SchemaSubmission) -> AxisScore:
        """Evaluate structural optimality."""
        deductions: list[Deduction] = []

        # Check 1: Unnecessary snowflaking
        deductions.extend(self._check_snowflaking(submission))

        # Check 2: Redundant dimensions
        deductions.extend(self._check_redundant_dimensions(submission))

        # Check 3: Unnecessary fact tables
        deductions.extend(self._check_unnecessary_facts(submission))

        # Check 4: Over-engineering
        deductions.extend(self._check_over_engineering(submission))

        score = max(0, self.max_score - sum(d.points for d in deductions))

        return AxisScore(
            axis_name=self.name,
            score=score,
            max_score=self.max_score,
            deductions=deductions,
            commentary=self._generate_commentary(deductions),
        )

    def _check_snowflaking(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for unnecessary snowflake structures."""
        deductions = []

        # Count dimensions with parent dimensions (snowflake)
        snowflaked = [
            dim for dim in submission.dimension_tables
            if dim.parent_dimension is not None
        ]

        # Snowflaking is usually unnecessary for small dimensions
        for dim in snowflaked:
            parent = submission.get_dimension_table(dim.parent_dimension)
            if parent:
                # Check if parent has few attributes (could be denormalized)
                if len(parent.attributes) <= 3:
                    deductions.append(Deduction(
                        points=5,
                        reason=f"Dimension '{dim.name}' snowflakes to '{parent.name}' which has few attributes",
                        severity=Severity.MINOR,
                        affected_elements=[dim.name, parent.name],
                    ))

        # Warn if excessive snowflaking
        if len(snowflaked) > len(submission.dimension_tables) // 2:
            deductions.append(Deduction(
                points=10,
                reason="Excessive snowflaking may complicate queries unnecessarily",
                severity=Severity.MODERATE,
                affected_elements=[d.name for d in snowflaked],
            ))

        return deductions

    def _check_redundant_dimensions(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for redundant or duplicate dimensions."""
        deductions = []

        # Check for dimensions that might be combined
        dim_names = [dt.name.lower() for dt in submission.dimension_tables]

        # Common patterns that suggest redundancy
        redundancy_patterns = [
            ("date", "time"),  # Often combined into date dimension
            ("product", "item"),  # Usually the same thing
            ("store", "location"),  # Usually the same thing
        ]

        for pat1, pat2 in redundancy_patterns:
            has_pat1 = any(pat1 in name for name in dim_names)
            has_pat2 = any(pat2 in name for name in dim_names)

            if has_pat1 and has_pat2:
                deductions.append(Deduction(
                    points=5,
                    reason=f"Dimensions with '{pat1}' and '{pat2}' might be redundant",
                    severity=Severity.MINOR,
                    affected_elements=[pat1, pat2],
                ))

        return deductions

    def _check_unnecessary_facts(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for unnecessary fact tables."""
        deductions = []

        # Check for facts with no measures
        for fact in submission.fact_tables:
            if not fact.measures:
                deductions.append(Deduction(
                    points=10,
                    reason=f"Fact table '{fact.name}' has no measures (factless fact should be intentional)",
                    severity=Severity.MODERATE,
                    affected_elements=[fact.name],
                ))

            # Check for facts with very similar grain
            for other in submission.fact_tables:
                if fact.name != other.name:
                    if fact.grain_description.lower() == other.grain_description.lower():
                        deductions.append(Deduction(
                            points=15,
                            reason=f"Fact tables '{fact.name}' and '{other.name}' have identical grain - consider consolidating",
                            severity=Severity.MAJOR,
                            affected_elements=[fact.name, other.name],
                        ))
                        break

        return deductions

    def _check_over_engineering(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check for over-engineering based on shop complexity."""
        deductions = []

        # Count entities
        num_facts = len(submission.fact_tables)
        num_dims = len(submission.dimension_tables)
        num_bridges = len(submission.bridge_tables)

        # Estimate expected complexity based on config
        expected_facts = 1  # At least sales
        if self.context.config.returns.reference_policy.value != "never":
            expected_facts += 1
        if self.context.config.inventory.tracked:
            expected_facts += 1

        expected_dims = 4  # date, product, store, customer (base)
        if self.context.config.promotions.basket_level_promotions:
            expected_dims += 1

        # Check for significantly more than expected
        if num_facts > expected_facts * 2:
            deductions.append(Deduction(
                points=10,
                reason=f"Schema has {num_facts} fact tables; {expected_facts}-{expected_facts + 2} may be sufficient",
                severity=Severity.MODERATE,
                affected_elements=["fact_tables"],
                violation_type=ViolationType.OVER_MODELING,
                concrete_example=f"Created {num_facts} facts for a shop that needs {expected_facts}-{expected_facts + 2}",
                consequence="Increased complexity, maintenance burden, and query confusion",
                fix_hint="Review if some fact tables can be consolidated or removed",
            ))

        if num_dims > expected_dims * 2:
            deductions.append(Deduction(
                points=5,
                reason=f"Schema has {num_dims} dimensions; {expected_dims}-{expected_dims + 3} may be sufficient",
                severity=Severity.MINOR,
                affected_elements=["dimension_tables"],
            ))

        return deductions
