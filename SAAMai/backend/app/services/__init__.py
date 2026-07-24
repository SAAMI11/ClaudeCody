"""Service layer: business logic that routers delegate to (LLM calls,
document parsing, export, plugins). Keeping this separate from the
routers makes each piece independently testable and reusable."""
