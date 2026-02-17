<!--
Sync Impact Report
==================
Version change: NONE → 1.0.0
Modified principles: N/A (initial creation)
Added sections: All (initial creation)
Removed sections: None
Templates requiring updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section compatible
  ✅ .specify/templates/spec-template.md - Requirements alignment compatible
  ✅ .specify/templates/tasks-template.md - Task categorization compatible
Follow-up TODOs: None
-->

# Mini Agent Constitution

## Core Principles

### I. Simplicity First

Mini Agent MUST maintain a minimal yet professional codebase. Every feature addition requires justification against the complexity it introduces.

- Start simple, grow only when justified by real use cases
- No speculative generalization or premature abstraction
- Clear, readable code over clever tricks
- One way to do things, not multiple alternatives

**Rationale**: A minimal codebase is easier to understand, debug, and extend. Complexity should be added only when concrete needs arise, not anticipated.

### II. Tool Extensibility

The tool system MUST be modular and extensible. New tools inherit from the `Tool` base class and integrate seamlessly.

- All tools implement: `name`, `description`, `parameters`, `execute()`
- Tools return `ToolResult` with standardized output format
- MCP tools load dynamically from configuration
- Claude Skills integrate via progressive disclosure

**Rationale**: A unified tool interface enables consistent LLM interaction, simplifies testing, and allows third-party extensions without core modifications.

### III. Test Coverage (NON-NEGOTIABLE)

Testing MUST accompany all core functionality. The project maintains comprehensive test coverage across unit, functional, and integration tests.

- Unit tests for tool classes and LLM client
- Functional tests for session persistence and MCP loading
- Integration tests for end-to-end agent execution
- New features MUST include corresponding tests

**Rationale**: Reliable agent behavior requires verified tool execution and response handling. Tests prevent regressions and document expected behavior.

### IV. Intelligent Context Management

The agent MUST handle long conversations gracefully through automatic summarization and token management.

- History summarization when approaching token limits
- Key information preservation across sessions via SessionNoteTool
- Configurable token thresholds for context limits
- No loss of critical state during summarization

**Rationale**: Extended tasks require maintaining context across many turns. Without intelligent management, token limits would cap task complexity.

### V. API Compatibility

The LLM layer MUST support multiple providers through a unified interface.

- Anthropic-compatible API as primary interface
- OpenAI-compatible API as secondary interface
- Unified `LLMClient` wrapper with retry mechanisms
- Configuration-driven provider selection

**Rationale**: API flexibility enables users to choose their preferred provider while maintaining consistent agent behavior across backends.

## Technology Standards

### Language & Runtime

- **Language**: Python 3.11+
- **Package Manager**: uv (recommended), pip (fallback)
- **Primary Dependencies**: httpx, pydantic, tiktoken, prompt-toolkit, mcp
- **Testing**: pytest with async support

### Code Quality

- Type hints required for public interfaces
- Pydantic models for data validation
- Async-first design for I/O operations
- Structured logging for observability

## Development Workflow

### Configuration Hierarchy

Configuration MUST follow priority order (highest to lowest):

1. `mini_agent/config/config.yaml` (development mode)
2. `~/.mini-agent/config/config.yaml` (user configuration)
3. Package directory configuration (installed mode)

### Adding New Tools

1. Create file in `mini_agent/tools/`
2. Inherit from `Tool` base class
3. Implement required interface
4. Register in `cli.py` initialization

### Commit Standards

- Commits MUST reference related issues when applicable
- Breaking changes MUST be documented in commit message
- Tests MUST pass before merge

## Governance

### Amendment Procedure

1. Propose amendment via issue or pull request
2. Document rationale and impact analysis
3. Update version according to semantic versioning:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or materially expanded guidance
   - PATCH: Clarifications, typo fixes, non-semantic refinements
4. Propagate changes to dependent templates and documentation
5. Update `LAST_AMENDED_DATE` to amendment date

### Compliance Review

All pull requests MUST:
- Pass existing test suite
- Maintain or improve code coverage
- Follow principle guidelines (no unnecessary complexity)
- Update documentation if behavior changes

### Runtime Guidance

For day-to-day development guidance, refer to `CLAUDE.md` which provides context-specific instructions for AI-assisted development within this repository.

**Version**: 1.0.0 | **Ratified**: 2026-02-17 | **Last Amended**: 2026-02-17
