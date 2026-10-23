# AI Co-authorship

For every commit where you used an AI tool (for generating boilerplate, writing tests, debugging, etc.), add the AI as a co-author. At the end of the commit message, add two empty lines followed by a `Co-authored-by` trailer naming the AI tool.

Example commit message:

```text
feat: Implement user registration endpoint

Used an AI assistant to generate the initial boilerplate for the
controller and service, then manually added validation logic.


Co-authored-by: AI Tool Name <AI@users.noreply.github.com>
```

# README Documentation

The `README.md` file must include a detailed section titled **My AI Usage**. In that section, describe:

- Which AI tools you used (for example, GitHub Copilot, ChatGPT, or Gemini).
- How you used each tool, with concrete examples of the work it helped with.
- Your reflection on how AI affected your workflow.

Do not overwrite or remove existing AI usage entries. Add each new tool or use case to the section while preserving the earlier entries.

# AI Chat Records

Keep a `PROMPTS.md` file at the repository root containing raw, unedited AI chat logs or links to public AI chats. Do not substitute AI-generated summaries for the original conversations.

# Test-Driven Development (TDD)

Write tests before implementing functionality. Make the Red-Green-Refactor pattern clear in the commit history, especially for backend logic. Aim for high test coverage with meaningful test cases.

Use `$tdd-red-green-refactor` from `.agents/skills/tdd-red-green-refactor/` when implementing application features or bug fixes.
