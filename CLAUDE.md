# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Skills

This project includes a set of composable skills in `skills/`. Use them as follows:

| Skill | When to use |
|-------|-------------|
| `brainstorming` | Before any feature work — explore requirements, propose approaches, get approval |
| `writing-plans` | After brainstorming — create a step-by-step implementation plan |
| `executing-plans` | When you have a written plan to implement |
| `test-driven-development` | When implementing any feature or bugfix |
| `systematic-debugging` | Before proposing any fix — find root cause first |
| `verification-before-completion` | Before claiming work is done — run verification, show evidence |
| `requesting-code-review` | After completing a task or feature |
| `receiving-code-review` | When processing review feedback |
| `finishing-a-development-branch` | When implementation is complete and ready to integrate |
| `using-superpowers` | At session start — establishes how to find and invoke skills |
| `understand` | Analyze codebase → build interactive knowledge graph |
| `understand-chat` | Ask questions about the codebase using the knowledge graph |
| `understand-dashboard` | Open web dashboard to visualize the knowledge graph |
| `understand-diff` | Analyze git diff/PR impact — what changed and what's affected |
| `understand-domain` | Extract business domain knowledge and flow graph |
| `understand-explain` | Deep-dive into a specific file, function, or module |
| `understand-knowledge` | Analyze a Karpathy-pattern LLM wiki knowledge base |
| `understand-onboard` | Generate an onboarding guide for new team members |
| `handoff` | Resume the most recent session — "where were we" / "pick up where we left off" |
| `recall` | Search past sessions and learnings about a topic |
| `recap` | Summarize last N sessions / today / this week |
| `remember` | Explicitly save an insight or decision to long-term memory |
| `forget` | Delete specific observations or sessions for privacy |
| `session-history` | Show what happened in recent past sessions |
| `commit-context` | Trace a file/function back to the agent session that produced its commit |
| `commit-history` | List recent commits linked to agent sessions |

### Skill Priority

1. User's explicit instructions (this file, direct requests) — highest priority
2. Skills — override default behavior where they conflict
3. Default system behavior — lowest priority
