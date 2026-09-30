---
name: research
description: Use when comparing tools, services or APIs, checking pricing or quotas, or needing current facts and sources for a decision.
version: 1.2.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Research

## Purpose

Research tools, services, platforms, APIs, products, pricing, and technical topics efficiently with
parallel source gathering and clear, actionable recommendations.

## When to Use

- Software and tool comparisons
- API documentation and capabilities
- Pricing and quota information
- Platform limitations and edge cases
- Technical troubleshooting
- Market research
- Current information and news
- Tool and service recommendations
- Best practices and conventions

## Parallel Work Pattern

For research tasks, split into parallel tracks:

```
Track 1: Official documentation and primary sources
Track 2: Pricing, limits, and quotas
Track 3: Community reports and practical experiences
Track 4: Alternatives and comparisons
Track 5: Final synthesis and recommendation
```

## Workflow

1. **Define** — What exactly are we researching? What question needs answering?
2. **Gather official sources** — Docs, official sites, API references
3. **Gather practical sources** — Community reports, real-world usage
4. **Compare findings** — Cross-reference, identify conflicts
5. **Identify uncertainty** — What's unclear or unverified?
6. **Produce recommendation** — Actionable, practical conclusion

## Output Format

```markdown
## Research: [Topic]

### Summary
[One-paragraph overview of findings]

### Key Findings
- Finding 1
- Finding 2
- Finding 3

### Comparison Table (when useful)
| Feature | Option A | Option B |
|---------|----------|----------|
| Price   | $X      | $Y      |
| Limit   | N       | M       |

### Recommendation
[What to do, what to choose, what to avoid]

### Sources
- [Official docs](url)
- [Community report](url)

### Uncertainty Notes
- What couldn't be verified
- What may have changed since research
```

## Rules

- Start with official sources first
- Cross-reference multiple sources
- Note uncertainty clearly — don't guess about pricing, limits, or policies
- Prefer current information (check dates)
- Be practical — what actually matters for the decision at hand
- Include links to sources when available

## Common Mistakes to Avoid

1. Relying on a single source
2. Not checking dates on information
3. Guessing about pricing or limits
4. Ignoring official docs in favor of community sources
5. Not noting uncertainty
6. Over-recommending without comparing alternatives
7. Missing platform-specific limitations
