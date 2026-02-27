# Current Context

## Active Milestone

**Name**: Structure & Algorithm Framework
**Goal**: Create trading-concepts/ folder hierarchy and document 6 algorithm framework concepts generalized for any trading platform.

## Current Phase

**Phase**: execute
**Started**: 2026-02-26

## Key Decisions

- [AUTO] Using trading-concepts/ as parent folder with sub-folders per section (algorithm-framework/, indicators/, reality-modeling/, orders/, historical-data/, portfolio-and-securities/)
- [AUTO] Generalizing all content — removing LEAN/QuantConnect API references from body text, keeping source attribution
- [AUTO] Algorithm Framework docs: overview, universe-selection, alpha-model, portfolio-construction, execution-model, risk-management (6 docs)

## Blockers

(none)

## Plan Reference

### Steps

1. [ ] Create trading-concepts/ folder structure with all sub-folders
2. [ ] Write trading-concepts/README.md master index
3. [ ] Write algorithm-framework/overview.md
4. [ ] Write algorithm-framework/universe-selection.md
5. [ ] Write algorithm-framework/alpha-model.md
6. [ ] Write algorithm-framework/portfolio-construction.md
7. [ ] Write algorithm-framework/execution-model.md
8. [ ] Write algorithm-framework/risk-management.md

## Notes

- QuantConnect v2 docs use JavaScript rendering, WebFetch returns empty content
- Use WebSearch + v1 docs + domain knowledge as workaround (same as Goal 3)
