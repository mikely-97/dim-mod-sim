"""Schema analyzer for diagnostic explanations."""

from dim_mod_sim.evaluator.engine import SchemaEvaluator
from dim_mod_sim.events.models import EventLog
from dim_mod_sim.explain.models import ExplainResult
from dim_mod_sim.explain.scenarios import generate_all_scenarios
from dim_mod_sim.schema.models import SchemaSubmission
from dim_mod_sim.shop.config import ShopConfiguration


class SchemaAnalyzer:
    """Analyzes schemas and generates diagnostic explanations.

    This shows concrete examples of where the schema produces
    wrong answers, helping users understand WHY their model fails.
    """

    def __init__(
        self,
        config: ShopConfiguration,
        events: EventLog,
    ) -> None:
        self.config = config
        self.events = events
        self.evaluator = SchemaEvaluator(config, events)

    def analyze(self, schema: SchemaSubmission) -> ExplainResult:
        """Analyze a schema and generate explanation scenarios."""
        # First, run evaluation to understand the issues
        eval_result = self.evaluator.evaluate(schema)

        # Generate scenarios based on config and schema issues
        scenarios = generate_all_scenarios(self.config, schema, eval_result)

        # Count issues
        issues_found = len(scenarios)

        # Generate summary
        if issues_found == 0:
            summary = "No specific failure scenarios identified for this schema."
        elif issues_found == 1:
            summary = "Found 1 scenario where your model produces incorrect answers."
        else:
            summary = f"Found {issues_found} scenarios where your model produces incorrect answers."

        return ExplainResult(
            schema_issues_found=issues_found,
            query_scenarios=scenarios,
            summary=summary,
        )
