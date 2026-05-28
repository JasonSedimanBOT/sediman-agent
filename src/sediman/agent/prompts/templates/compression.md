<input>
You will receive a conversation between a user and a browser automation agent.
</input>

<instructions>
Summarize the conversation into a structured format. Be concise but preserve ALL critical details.

Include:
- Goal: What the user is trying to accomplish
- Progress: What was completed and what is in progress
- Key Decisions: Important technical decisions made
- Critical Context: Specific values, URLs, configuration details, data found

Rules:
- Preserve exact URLs, numbers, names, and technical values
- Note any errors encountered and how they were resolved
- Keep the summary under 500 words
</instructions>

<output_format>
## Goal
[What the user is trying to accomplish]

## Progress
### Done
[Completed work]
### In Progress
[Work currently underway]

## Key Decisions
[Important technical decisions]

## Critical Context
[Specific values, URLs, configuration details]
</output_format>
