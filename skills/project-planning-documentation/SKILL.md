---
name: project-planning-documentation
description: Use when planning, comparing or documenting software work — project proposals, architecture, README, API docs, implementation and testing plans.
version: 1.2.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Project Planning and Documentation

## Purpose

Plan and document software projects professionally — from initial idea through architecture,
implementation, testing, and deployment.

## When to Use

- Project proposals and pitches
- README files and project overviews
- Architecture documents
- API documentation
- Technical reports
- Implementation plans
- Testing plans
- Deployment plans
- Client-facing documents
- Technical specifications

## Parallel Work Pattern

For planning tasks, split into parallel workstreams:

```
Workstream 1: Feature and scope planning
Workstream 2: Architecture and tech stack
Workstream 3: Database / API / data flow design
Workstream 4: UI/UX planning (if applicable)
Workstream 5: Testing and deployment strategy
Workstream 6: Documentation drafting
```

## Workflow

1. **Identify goal** — What is the project trying to achieve?
2. **Define scope** — Features, boundaries, MVP vs future
3. **Design architecture** — Components, data flow, tech stack
4. **Plan implementation** — Phases, milestones, dependencies
5. **Plan testing** — How to verify it works
6. **Plan deployment** — How to ship it
7. **Document** — Produce clean, professional documentation

## Documentation Standards

### README
- Project name and one-line description
- Features list
- Quick start / install
- Usage examples
- Configuration
- Tech stack
- License

### Architecture Document
- System overview diagram (text-based)
- Component descriptions
- Data flow
- Tech stack decisions and rationale
- Security considerations
- Scalability notes

### API Documentation
- Endpoint list
- Request/response examples
- Authentication
- Error codes
- Rate limits

### Implementation Plan
- Phases and milestones
- Dependencies
- Estimated effort
- Risk areas
- Testing strategy

## Output Format

Deliver as:

1. Markdown file(s) in the project directory
2. Professional structure with clear headings
3. Tables for comparisons and specs
4. Code blocks for examples
5. Brief summary of what was produced

## Common Mistakes to Avoid

1. Over-planning without starting implementation
2. Missing tech stack rationale
3. Not considering deployment and operations
4. Ignoring security and error handling
5. Writing documentation that's too vague to be useful
6. Not including setup/install instructions
7. Skipping testing strategy
