# ngjs-nested-components (Benchmark 5)

AngularJS component-based app with nested components and two-way bindings.

## Covers
- AngularJS .component() API
- Cross-file controller ↔ template wiring
- TemplateUrl resolution
- Two-way bindings (=) and callback bindings (&)
- Nested component communication

## Expected Migration Risks
- Two-way binding elimination (Angular inputs/outputs)
- Binding direction inference
- TemplateUrl → inline or component template mapping
- Component selector renaming

## Validation
- Unit test asserting child → parent interaction
- Snapshot of binding topology and state

## Failure Means
EVUA cannot correctly infer component boundaries or convert two-way bindings safely.
