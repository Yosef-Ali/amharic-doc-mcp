# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **Specify Framework** repository - a specification-driven development system that emphasizes structured planning, feature specification, and automated task management. The system is designed around constitutional principles and uses a workflow-based approach to feature development.

## Core Architecture

### Directory Structure
```
/here/                               # Main project directory
├── .claude/commands/               # Claude-specific slash commands
│   ├── constitution.md            # Constitution management
│   ├── specify.md                 # Feature specification workflow  
│   ├── plan.md                    # Implementation planning
│   ├── tasks.md                   # Task generation
│   ├── implement.md               # Task execution
│   ├── analyze.md                 # Cross-artifact analysis
│   └── clarify.md                 # Requirements clarification
├── .specify/                      # Framework core
│   ├── memory/constitution.md     # Project constitution (template)
│   ├── scripts/bash/             # Automation scripts
│   └── templates/                # Document templates
└── specs/                         # Feature specifications (generated)
    └── {###-feature-name}/       # Individual feature directories
        ├── spec.md               # Feature requirements
        ├── plan.md               # Implementation plan
        ├── tasks.md              # Task breakdown
        ├── research.md           # Technical research
        ├── data-model.md         # Data structures
        ├── quickstart.md         # Integration scenarios
        └── contracts/            # API specifications
```

### Workflow Commands

The system provides slash commands that execute structured workflows:

- `/specify` - Create feature specifications from user requirements
- `/clarify` - Resolve ambiguities in specifications  
- `/plan` - Generate implementation plans and technical design
- `/tasks` - Create detailed task breakdowns from plans
- `/implement` - Execute tasks following TDD principles
- `/analyze` - Validate consistency across artifacts
- `/constitution` - Manage project constitution and principles

## Development Commands

### Core Workflow
```bash
# 1. Start with feature specification
/specify "Add user authentication system"

# 2. Clarify any ambiguities (if needed)
/clarify

# 3. Generate implementation plan
/plan

# 4. Create task breakdown
/tasks

# 5. Execute implementation
/implement

# 6. Validate consistency
/analyze
```

### Bash Scripts
The framework includes automation scripts in `.specify/scripts/bash/`:

```bash
# Check prerequisites and get feature paths
./.specify/scripts/bash/check-prerequisites.sh --json

# Setup plan phase
./.specify/scripts/bash/setup-plan.sh --json

# Update agent-specific context files
./.specify/scripts/bash/update-agent-context.sh claude

# Create new feature branch/directory
./.specify/scripts/bash/create-new-feature.sh
```

## Key Principles

### Constitution-Based Development
- All features must comply with project constitution (`.specify/memory/constitution.md`)
- Constitution defines non-negotiable principles (Library-First, CLI Interface, Test-First, etc.)
- Constitutional violations must be explicitly justified in complexity tracking

### Specification-Driven Workflow
1. **Requirements First**: All features start with detailed specifications
2. **Clarification Gates**: Ambiguities must be resolved before proceeding
3. **Design Before Code**: Technical plans precede implementation
4. **Task Breakdown**: Complex features decomposed into manageable tasks
5. **TDD Enforcement**: Tests written before implementation

### Template-Based Consistency  
- All documents follow structured templates
- Templates ensure completeness and consistency
- Cross-artifact validation prevents misalignment

## Working with Features

### Feature Branch Naming
Features should be organized with numbered branches/directories:
```
001-user-authentication
002-payment-processing  
003-notification-system
```

### Document Flow
```
spec.md → plan.md → tasks.md → implementation
   ↓        ↓         ↓
research.md → data-model.md → contracts/
           → quickstart.md
```

### Constitutional Requirements
Before implementation, verify compliance with:
- Library-First principle (standalone, testable components)
- CLI Interface requirement (text in/out protocols)
- Test-First methodology (TDD cycle enforced)
- Integration testing for contracts and communication
- Observability and versioning standards

## File Operations

### Reading Artifacts
Always use absolute paths when working with feature artifacts:
```bash
# Get feature paths
eval $(./.specify/scripts/bash/check-prerequisites.sh --json | jq -r 'to_entries[] | "\(.key)=\(.value)"')

# Then access files using variables like:
# $FEATURE_SPEC, $IMPL_PLAN, $TASKS, etc.
```

### Template Processing
Templates contain placeholder tokens in `[BRACKETS]` that need replacement:
- `[PROJECT_NAME]` - Project identifier
- `[FEATURE_NAME]` - Current feature name  
- `[PRINCIPLE_X_NAME]` - Constitutional principles
- `[NEEDS CLARIFICATION]` - Unresolved requirements

## Error Handling

### Common Issues
- **Missing Prerequisites**: Run check-prerequisites.sh to verify setup
- **Constitutional Violations**: Document in complexity tracking or simplify approach
- **Ambiguous Requirements**: Use /clarify before proceeding with implementation
- **Template Errors**: Ensure all placeholder tokens are replaced

### Validation Gates
- Specification completeness (no [NEEDS CLARIFICATION] markers)
- Constitutional compliance (principles followed or violations justified)
- Cross-artifact consistency (requirements → plan → tasks alignment)
- Test coverage (TDD cycle maintained)

## Integration Notes

This is a meta-development framework focused on process and planning rather than specific technology implementation. The actual source code structure depends on the project type determined during planning (single/web/mobile).

The system emphasizes documentation-driven development with strong governance through constitutional principles and automated consistency checking.
