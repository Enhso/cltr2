# Context checks (17 Oct 2026): Anthropic Sept 2025 postmortem, Gemini CLI issue collapse

From the context-checks subagent (its report came back as a message; recorded here verbatim in substance). Raw page texts it saved: /tmp/claude-1000/-home-hatim-applications-cltr2/7732be64-f9d7-4a9e-9034-833768750cf0/scratchpad/gemini/ (session scratchpad, may not persist).

## Anthropic, "A postmortem of three recent issues" (established from the page text)

- URL: https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues . Published 17 Sep 2025.
- Opening line: "Between August and early September, three infrastructure bugs intermittently degraded Claude's response quality."
- Bug 1, context window routing error. Sonnet 4. Active from 5 Aug; fix deployed 4 Sep; rollouts finished 16 Sep (first-party, Vertex) and 18 Sep (Bedrock). Surfaces named: first-party API, Bedrock, Vertex, and Claude Code. Quote: "Approximately 30% of Claude Code users who made requests during this period had at least one message routed to the wrong server type, resulting in degraded responses."
- Bug 2, output corruption (Thai/Chinese characters in English answers, syntax errors in code). Opus 4.1 and Opus 4 on 25-28 Aug; Sonnet 4 on 25 Aug-2 Sep. Rolled back 2 Sep. First-party API only (Claude Code not named).
- Bug 3, approximate top-k XLA:TPU miscompilation. Confirmed on Haiku 3.5; possibly Sonnet 4 and Opus 3. Deployed 25 or 26 Aug (the post gives both). Rollbacks 4-12 Sep. First-party API only (Claude Code not named).
- Other quote: "We never reduce model quality due to demand, time of day, or server load. The problems our users reported were due to infrastructure bugs alone."
- Not the same as "An update on recent Claude Code quality reports", 23 Apr 2026 (https://www.anthropic.com/engineering/april-23-postmortem). Title and date checked only; body not read.

## Gemini CLI issue volume

- Counts confirmed (search API): Mar 2026 1,704; Apr 946; May 663; Jun 235; Jul 123; Aug 179; Sep 132. GraphQL differs slightly (Mar 1,711, Apr 957, May 668). Sep 2025-Feb 2026 averaged about 1,070 a month, so March 2026 is a spike and the fall starts in May.
- PRs fell about 65% and Discussions about 80% over the same period: the fall is across all channels, not a move to Discussions.
- Stated reason (established): on 19 May 2026 Google announced the move from Gemini CLI to Antigravity CLI (https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/). Quote: "On June 18, 2026, Gemini CLI and Gemini Code Assist IDE extensions will stop serving requests for Google AI Pro and Ultra, as well as those using it free of charge using Gemini Code Assist for individuals." The README now says Gemini CLI "was replaced by Antigravity CLI on June 18th, 2026." Enterprise and API-key users are unaffected; the repo still ships releases.
- Precursor: discussion #22970 (18 Mar 2026): free-tier users lose Pro models from 25 Mar.
- Inference (the subagent's, not a source's): the drop tracks the loss of individual users, the main bug reporters.
- Ruled out (no evidence found): issue creation restricted, move to Discussions, repo move. Interaction limits could not be checked (admin only).
- Absent issue numbers: 2,189 of 1-29,796 have no current issue or PR; the largest gap is Sep 2025 (689 of 2,748 numbers, 25%). The API does not say whether these were deleted, transferred or converted. This is a denominator caveat for Gemini CLI in late 2025.
