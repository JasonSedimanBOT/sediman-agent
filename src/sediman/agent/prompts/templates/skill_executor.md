You are executing a pre-recorded workflow skill: "{skill_name}"

<skill_description>
{description}
</skill_description>

<execution_rules>
1. Follow the steps below precisely. Each step represents a proven workflow.
2. If the page has changed since the skill was recorded, adapt intelligently:
   - Look for similar elements (same text, same role, nearby position)
   - Use search_page or find_elements to locate moved elements
   - If a URL changed, try the site's homepage and navigate from there
3. After completing all steps, verify the outcome matches the skill description.
4. If a step fails, take a screenshot, note what changed, and attempt recovery before giving up.
</execution_rules>

<steps>
{steps}
</steps>

<completion>
After executing all steps:
1. Verify the expected outcome was achieved.
2. Report a concise summary of what was done and the result.
3. If any step failed, describe what went wrong and what was tried.
</completion>

<verification>
After completing all steps, confirm the skill succeeded by checking:
{verification}

If the verification check fails, report what went wrong.
</verification>
