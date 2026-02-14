# Dim-Mod-Sim: Textual TUI/Web Interface Plan

## Environment Setup

### Python Environment
```bash
# The serpens_novus conda environment is auto-activated via ~/.zshrc
# Poetry is installed in ~/.local/bin (also in PATH via ~/.zshrc)

# To run commands with proper environment:
source ~/anaconda3/etc/profile.d/conda.sh && conda activate serpens_novus && export PATH="$HOME/.local/bin:$PATH"

# Then use poetry:
poetry lock      # Regenerate lock file after pyproject.toml changes
poetry install   # Install dependencies

# Or install in editable mode directly:
pip install -e .
```

### Dependencies (in pyproject.toml)
```toml
# Core TUI dependency
"textual>=0.50.0",

# Optional web serving (install with: poetry install --extras web)
[project.optional-dependencies]
web = ["textual-web>=0.1.0"]
```

---

## Project Overview

Transform the current CLI-only interface into a rich TUI (Terminal User Interface) with optional web serving capability using Textual. The existing CLI commands remain for scripting/automation.

### Goals
1. **Visual progress tracking** - Dashboard showing improvement over time
2. **Integrated schema editing** - Edit JSON with live validation
3. **Interactive feedback** - Clickable, grouped violations with context
4. **Scenario library** - Browse, filter, and replay previous attempts
5. **Dual deployment** - Same codebase serves terminal and web

---

## Architecture

```
src/dim_mod_sim/
├── cli.py                    # Existing - keep for scripting
├── ui/                       # NEW - Textual interface
│   ├── __init__.py
│   ├── app.py                # Main DimModSimApp(App)
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── home.py           # Landing: new game / continue / progress
│   │   ├── scenario.py       # Briefing + trap display before play
│   │   ├── play.py           # Main play screen (editor + feedback)
│   │   ├── results.py        # Final evaluation with full breakdown
│   │   └── progress.py       # Historical dashboard
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── schema_editor.py  # JSON editor with syntax highlighting
│   │   ├── score_display.py  # 6-axis scores (bars/radar)
│   │   ├── feedback_tree.py  # Collapsible violation groups
│   │   ├── trap_grid.py      # Visual trap indicators
│   │   ├── attempt_list.py   # History sidebar
│   │   └── diff_view.py      # Compare schema versions
│   ├── modals/
│   │   ├── __init__.py
│   │   ├── new_game.py       # Difficulty + seed selection
│   │   ├── trap_help.py      # Detailed trap explanation
│   │   └── confirm.py        # Generic confirmation dialog
│   └── styles/
│       └── app.tcss          # Textual CSS styling
└── ... (existing modules unchanged)
```

---

## Screen Flow

```
┌──────────────────────────────────────────────────────────────┐
│                         HOME                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  New Game   │  │  Continue   │  │  Progress   │          │
│  │             │  │  (recent)   │  │  Dashboard  │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          ▼                │                ▼
┌──────────────────┐       │      ┌──────────────────┐
│  NEW GAME MODAL  │       │      │    PROGRESS      │
│  - Difficulty    │       │      │  - Attempt list  │
│  - Seed (opt)    │       │      │  - Score charts  │
│  - Traps preview │       │      │  - Best scores   │
└────────┬─────────┘       │      └──────────────────┘
         │                 │
         ▼                 │
┌──────────────────────────┴───────────────────────────────────┐
│                       SCENARIO                                │
│  ┌─────────────────────────┐  ┌────────────────────────────┐ │
│  │   Business Description  │  │   Enabled Traps Grid       │ │
│  │   (scrollable)          │  │   [x] Late-arriving dims   │ │
│  │                         │  │   [x] Multi-currency       │ │
│  │                         │  │   [ ] Promotions...        │ │
│  └─────────────────────────┘  └────────────────────────────┘ │
│                    [ Start Modeling ]                         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         PLAY                                  │
│  ┌────────────────────────┐  ┌─────────────────────────────┐ │
│  │    Schema Editor       │  │   Feedback Panel            │ │
│  │    (JSON + validation) │  │   ├─ Grain Violations (3)   │ │
│  │                        │  │   ├─ Temporal Issues (1)    │ │
│  │    {                   │  │   └─ Data Loss (2)          │ │
│  │      "facts": [...],   │  │                             │ │
│  │      "dimensions": []  │  │   ┌─────────────────────┐   │ │
│  │    }                   │  │   │ Score: 72/100       │   │ │
│  │                        │  │   │ ████████░░ 72%      │   │ │
│  └────────────────────────┘  └─────────────────────────────┘ │
│  [Evaluate] [Save] [Load Scaffold] [Submit Final] [Help]     │
└──────────────────────────────┬───────────────────────────────┘
                               │ (on Submit Final)
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       RESULTS                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Final Score: 85/100                                    │ │
│  │                                                         │ │
│  │  Event Preservation   ████████████████████  95          │ │
│  │  Grain Correctness    ████████████████░░░░  80          │ │
│  │  Temporal Correctness ██████████████████░░  90          │ │
│  │  Semantic Faithfulness████████████████░░░░  80          │ │
│  │  Structural Optimality████████████████████  100         │ │
│  │  Queryability         ███████████████░░░░░  75          │ │
│  └─────────────────────────────────────────────────────────┘ │
│  [Try Again] [New Scenario] [View Details] [Export Report]   │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Core App Shell) ✓ COMPLETE
- [x] Add Textual dependencies to pyproject.toml
- [x] Create `ui/app.py` with basic App class and screen routing
- [x] Create `ui/styles/app.tcss` with base styling
- [x] Add `ui` command to CLI: `dim-mod-sim ui` launches TUI
- [x] Implement HomeScreen with navigation buttons

**Deliverable:** App launches, shows home screen, can quit

### Phase 2: Scenario Flow ✓ COMPLETE
- [x] NewGameModal - difficulty selection, seed input, trap preview
- [x] ScenarioScreen - display business description + enabled traps
- [x] Wire up shop generation on "Start Modeling"
- [x] TrapGrid widget showing enabled/disabled traps

**Deliverable:** Can start a new game and see the scenario briefing

### Phase 3: Play Screen (Core Experience) ✓ COMPLETE
- [x] SchemaEditor widget (TextArea with JSON syntax highlighting)
- [x] JSON validation on edit (red squiggles / error footer)
- [x] ScoreDisplay widget (horizontal bars for 6 axes)
- [x] FeedbackTree widget (collapsible violation groups)
- [x] "Evaluate" button triggers evaluation, updates feedback
- [x] "Load Scaffold" populates editor with generated scaffold

**Deliverable:** Full edit-evaluate loop works in TUI

### Phase 4: Feedback & Help ✓ COMPLETE
- [x] TrapHelpModal - detailed explanation when clicking trap name
- [x] Violation details on click (example, consequence, fix hint)
- [x] Keyboard shortcuts (Ctrl+E evaluate, Ctrl+S save, etc.)
- [x] Footer help bar showing available shortcuts

**Deliverable:** Rich contextual help throughout

### Phase 5: Progress & History ✓ COMPLETE
- [x] ProgressScreen - list all attempts, filter by seed/difficulty
- [x] "Continue" from home loads last session
- [ ] AttemptList widget (sidebar in play screen) - deferred
- [ ] Score trend sparklines/charts - deferred
- [ ] DiffView widget - compare two schema versions - deferred

**Deliverable:** Full progress tracking with history (core features implemented)

### Phase 6: Results & Polish ✓ COMPLETE
- [x] ResultsScreen - final breakdown with export options
- [x] Export to Markdown report
- [x] Color themes (dark/light toggle)
- [ ] Animations (score counting up, progress bars) - deferred
- [ ] textual-web setup for browser access - deferred

**Deliverable:** Complete, polished experience (core features implemented)

---

## Key Widgets Detail

### SchemaEditor
```python
class SchemaEditor(TextArea):
    """JSON editor with live validation."""

    def on_text_area_changed(self, event):
        # Validate JSON structure
        # Validate against schema/models.py Pydantic models
        # Show errors in footer or gutter
```

### ScoreDisplay
```python
class ScoreDisplay(Static):
    """Six horizontal bars showing axis scores."""

    scores: reactive[dict[str, int]]

    # Color coding: red < 50, yellow < 75, green >= 75
    # Animate on change
```

### FeedbackTree
```python
class FeedbackTree(Tree):
    """Collapsible tree of violations grouped by category."""

    # Root nodes: violation categories
    # Leaves: individual violations with details
    # Click to expand/show fix hints
```

---

## CLI Integration

```python
# In cli.py, add:

@app.command()
def ui(
    web: bool = typer.Option(False, "--web", "-w", help="Serve as web app"),
    port: int = typer.Option(8080, "--port", "-p", help="Web server port"),
):
    """Launch the interactive TUI (or web interface with --web)."""
    from dim_mod_sim.ui.app import DimModSimApp

    if web:
        # Use textual-web to serve
        from textual_web import run_app
        run_app(DimModSimApp, port=port)
    else:
        app = DimModSimApp()
        app.run()
```

---

## File Structure After Implementation

```
src/dim_mod_sim/
├── __init__.py
├── cli.py                          # +ui command
├── ui/
│   ├── __init__.py
│   ├── app.py                      # ~150 lines
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── home.py                 # ~80 lines
│   │   ├── scenario.py             # ~120 lines
│   │   ├── play.py                 # ~250 lines (largest)
│   │   ├── results.py              # ~150 lines
│   │   └── progress.py             # ~180 lines
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── schema_editor.py        # ~200 lines
│   │   ├── score_display.py        # ~100 lines
│   │   ├── feedback_tree.py        # ~150 lines
│   │   ├── trap_grid.py            # ~80 lines
│   │   ├── attempt_list.py         # ~100 lines
│   │   └── diff_view.py            # ~120 lines
│   ├── modals/
│   │   ├── __init__.py
│   │   ├── new_game.py             # ~100 lines
│   │   ├── trap_help.py            # ~60 lines
│   │   └── confirm.py              # ~40 lines
│   └── styles/
│       └── app.tcss                # ~200 lines
├── shop/
├── events/
├── schema/
├── evaluator/
├── scaffold/
├── play/
├── explain/
├── progress/
├── description/
└── core/
```

**Estimated new code:** ~1,800 lines for full TUI

---

## Testing Strategy

1. **Unit tests** for widgets (mock data, check rendering)
2. **Snapshot tests** using Textual's pilot API
3. **Integration tests** for screen flows
4. **Manual testing** in both terminal and web modes

```python
# Example widget test
async def test_score_display_colors():
    async with ScoreDisplay().run_test() as pilot:
        pilot.app.query_one(ScoreDisplay).scores = {"grain": 45}
        assert "red" in pilot.app.query_one(".score-bar").classes
```

---

## Notes

- Keep existing CLI fully functional for CI/automation
- All business logic stays in existing modules; UI is pure presentation
- Use reactive properties for automatic UI updates
- Consider accessibility (screen readers, high contrast)
- Web mode uses same TCSS styling, no separate CSS needed
