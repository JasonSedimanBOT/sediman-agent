# Sediman Roadmap

Features planned to close the gap with Hermes Agent and beyond.

---

## Completed

- [x] **Agent loop** — think-act-observe-reflect cycle
- [x] **Browser Use integration** — real Chromium via Playwright
- [x] **Skill engine** — create, patch, delete, version, rollback, dedup, usage tracking
- [x] **Skill executor** — run skills with auto-healing on failure
- [x] **Skill learner** — Hermes-style 3-question eval, auto-extract from traces
- [x] **Skill auditor** — staleness review, auto-archive/delete unused skills
- [x] **Skill healer** — LLM-based repair when page layouts change
- [x] **Skill validator** — name format, injection/exfiltration/destructive detection, trust levels
- [x] **Skills Hub** — browse, search, install, validate, publish community skills
- [x] **CLI + TUI** — Click CLI, prompt_toolkit TUI with slash commands
- [x] **Cron scheduler** — APScheduler-based 24/7 task scheduling
- [x] **Persistent memory** — dual-file bounded storage, background LLM review
- [x] **Memory security** — prompt injection, exfiltration, invisible unicode scanning
- [x] **Session storage** — SQLite + FTS5 full-text search
- [x] **Subagent orchestration** — parallel delegation with semaphore
- [x] **Context compression** — LLM-based conversation compaction
- [x] **Screen recording** — JS-injected cursor tracking, FPS capture, trace-to-skill conversion
- [x] **REST + WebSocket API** — FastAPI server with streaming
- [x] **`clarify` tool** — ask user questions with multiple-choice support
- [x] **`todo` tool** — session-scoped task list with status tracking
- [x] **`terminal` tool** — shell execution with per-command approval, dangerous pattern blocking, and session-level override

---

## In Progress

### File Tools

Filesystem interaction is the single biggest capability gap. The agent currently cannot read, write, search, or edit files locally.

- [x] **`read_file`** — Read files with line numbers and pagination (offset/limit)
- [x] **`write_file`** — Write content to files, create parent directories automatically
- [x] **`patch`** — Targeted find-and-replace edits with fuzzy matching. Auto-run syntax checks after editing
- [x] **`search_files`** — Ripgrep-backed file search by content (regex) and by name (glob). Faster than shelling out to grep/find

### Web Tools

- [ ] **`web_extract`** — Extract web page and PDF content to markdown. Current `web_search` is a stub that delegates to the browser subagent. Need a real implementation using HTTP fetch + HTML-to-markdown conversion. Pages under 5K chars return full markdown; larger pages get LLM-summarized

---

## Planned — Tier 1: Core Agent Capabilities

### Code Execution

- [ ] **`execute_code`** — Run Python scripts that can call agent tools programmatically. Use when 3+ tool calls with processing logic between them are needed, or for filtering/reducing large outputs before they enter context. Collapses multi-step pipelines into zero-context-cost turns

### Session Search Tool

- [ ] **`session_search`** — Expose the existing FTS5 session database as a callable tool. Three modes: discovery (pass `query`), scroll (pass `session_id` + `around_message_id`), browse (no args). No LLM calls — pure DB retrieval

### Granular Browser Tools

Sediman currently uses BrowserUse as a monolithic black box. Exposing individual browser operations as tools gives the LLM finer control and reduces context waste.

- [ ] **`browser_navigate`** — Go to URL
- [ ] **`browser_snapshot`** — Accessibility tree snapshot with element ref IDs
- [ ] **`browser_click`** — Click element by ref ID from snapshot
- [ ] **`browser_type`** — Type text into input field by ref ID
- [ ] **`browser_scroll`** — Scroll page in a direction
- [ ] **`browser_press`** — Press keyboard key
- [ ] **`browser_back`** — Navigate back in history
- [ ] **`browser_vision`** — Screenshot + vision AI analysis
- [ ] **`browser_console`** — Get browser console output and JS errors
- [ ] **`browser_get_images`** — List all images on current page

---

## Planned — Tier 2: Memory & Scheduling as Tools

These subsystems exist internally but are not exposed as callable tools. The agent should be able to manage memory and schedules mid-conversation.

- [ ] **`memory` tool** — Add/replace/remove entries in persistent memory via tool calls. Currently only done post-task via the memory manager. Exposing it lets the agent save important facts mid-task
- [ ] **`cronjob` tool** — Full CRUD for scheduled tasks from within a session (create, list, update, pause, resume, run, remove). Currently scheduling only happens via CLI or manager plan

---

## Planned — Tier 3: Media & Generation

- [ ] **`vision_analyze`** — Image analysis via vision-capable models. On vision models, pass raw pixels as multimodal tool result. On text-only models, fall back to auxiliary vision model
- [ ] **`image_generate`** — Text-to-image generation via FAL.ai (or pluggable backend)
- [ ] **`text_to_speech`** — TTS audio generation for voice delivery on messaging platforms
- [ ] **`video_analyze`** — Video content analysis (captions, scene breakdowns, key timestamps)
- [ ] **`video_generate`** — Text-to-video via plugin-registered backends

---

## Planned — Tier 4: Integrations & Platforms

### Messaging Gateway

- [ ] **`send_message`** — Cross-platform messaging delivery (Telegram, Discord, Slack, WhatsApp, Signal)
- [ ] Telegram adapter
- [ ] Discord adapter
- [ ] Slack adapter

### MCP Integration

- [ ] **MCP server support** — Load tools dynamically from MCP servers. Each configured server generates a `mcp-<server>` toolset at runtime. Support `command`-based and `url`-based MCP servers

### External Providers

- [ ] **`mixture_of_agents`** — Multi-model consensus via Mixture of Agents (route hard problems through multiple frontier LLMs)
- [ ] **Anthropic provider** — Native Anthropic/Claude support alongside OpenAI and Ollama
- [ ] **Google Gemini provider** — Native Gemini support

### Desktop Control

- [ ] **`computer_use`** — macOS/Linux desktop control (screenshots, click, drag, scroll, type). Does not steal cursor/focus

---

## Planned — Tier 5: Infrastructure

### Terminal Backends

The terminal tool currently runs commands locally. Add sandboxed execution environments:

- [ ] **Docker backend** — Isolated containers with persistent workspace
- [ ] **SSH backend** — Remote execution (keeps agent away from its own code)
- [ ] **Modal backend** — Serverless cloud execution
- [ ] **Daytona backend** — Persistent remote dev environments

### Background Process Management

- [ ] **`process` tool** — Manage background processes started with `terminal(background=true)`. Actions: list, poll, wait, kill, write (send stdin), log (full output with pagination)

### Web Dashboard

- [ ] Browser panel + chat panel UI
- [ ] Live viewport streaming
- [ ] Session history browser

### Advanced

- [ ] **Embedding-based skill dedup** — Replace word-overlap similarity with vector embeddings
- [ ] **Multi-user auth** — API key or OAuth-based authentication
- [ ] **Anti-captcha browser binary** — Custom Chromium build for CAPTCHA resistance
- [ ] **Toolsets system** — Named bundles of tools configurable per platform (like Hermes toolsets)
- [ ] **Plugin system** — Load third-party tool providers at runtime
- [ ] **Honcho memory provider** — Dialectic user modeling for cross-session personality

---

## Priority Order

1. ~~**File tools** (read/write/patch/search)~~ ✅ Done
2. **Web extract** — unlocks research and data extraction
3. **Session search tool** — low effort, high value (DB already exists)
4. **Granular browser tools** — finer control, less context waste
5. **Code execution** — programmatic tool chaining
6. **Memory + cronjob tools** — expose existing subsystems
7. **Media tools** (vision, image gen, TTS)
8. **Messaging gateway + MCP**
9. **Terminal backends + process management**
10. **Web dashboard + advanced features**
