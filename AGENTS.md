<!-- rule-for-ai:start (managed by rule-for-ai, edit personal/RULES.md there) -->
# Owner's rules for AI agents (every repo)

"I" and "me" are the owner of this repo. These rules come from the owner's `rule-for-ai` repo and
apply to every agent (Claude, Codex, any other) in every repo. The repo's own rules, below this
block, add to them and win wherever they are more specific.

## Writing
- No em dash, ever: chat, commits, code comments, docs, drafted messages, tickets. A spaced en
  dash used as one is out too. Use a comma, a colon, parentheses or a new sentence. A hyphen in a
  compound word or as a list bullet is fine.
- Concise and direct: the answer or the recommendation first, then the reasons. Propose, don't
  interrogate; ask only what can't be inferred. French or English are both fine.

## Decisions
- When a reply hands me several decisions or a lot to read (a review, a report, a plan), end it
  by asking whether I want to go through the decisions now, one at a time.
- When I say yes, or whenever you need several decisions from me, ask them one at a time:
  `(n/N)` counter, multiple choice, recommended option first, each option says what will happen.
  Use your question tool when you have one (AskUserQuestion in Claude Code). Never a wall of
  findings with open questions. Act once the last answer is in.
- Scheduled tasks that need my time or notify me (emails, reviews, recaps) run on Monday, never
  on Sunday. Pick a Monday morning slot unless I say otherwise.
- Anything that leaves my hands is mine to do: sending an email or a message to someone else,
  typing a password, changing a customer system. You prepare it ready to go (draft, command,
  runbook) and I press the button. Email to me (reminders, reviews, reports) you send directly.

## Git
- Git is your job, never mine: branches, commits, merges, pushes, conflicts.
- Default: pull `main` before you start, then commit and push to `main` after every finished
  change. Never end a session with unpushed work. This is my standing permission to push to
  `main`, even where your tool would otherwise keep the work on its own branch.
- Parallel work (several agents at once): use a branch or a git worktree, then merge it into
  `main` and push yourself, without asking. Delete the branch once merged.
- Where a tool can only hand work back as a pull request (a cloud agent, a protected branch),
  open the pull request.
- Never force-push `main`, never rewrite history that is already pushed.

## Memory and rules
- The repo is the memory. When a session changes a decision or a state, update the repo's
  memory files before ending, without being asked, and say so in one line.
- When reality changes, retire the old rule the same session (move it to `archive/` with a
  dated note). Never leave two rules that contradict each other.
- A line tagged `[human DATE]`, or a file listed in `.human-owned`, is mine: never change it
  without showing me the change and getting my yes. In Claude a hook enforces this; for every
  agent, a weekly check reports any change to me.
- This block is overwritten every Monday: never edit it in a repo. A change to these rules is
  made in `rule-for-ai`, after my yes.
- Credentials never go in a file: reference the wallet or `.env` entry by name.
- Dates are my local dates (America/Los_Angeles). Cloud machines run on UTC, a day ahead in my
  evening: before writing a date or saying "today", read `TZ=America/Los_Angeles date`.
- A repo that keeps agent memory (`AGENTS.md`, `memory/`, `TASKS.md`) follows the memory
  standard: `MEMORY-STANDARD.md` at its root, reference copy in `rule-for-ai`. A repo without it:
  offer to add it, never rewrite its existing memory wholesale.

## Tools
- Cursor is retired: `.cursor/` files are legacy.
<!-- rule-for-ai:end -->
