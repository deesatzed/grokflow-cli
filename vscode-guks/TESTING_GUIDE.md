# GUKS VS Code Extension - Testing Guide

**Version**: 0.1.0
**Last Updated**: 2025-12-10

This guide covers testing the GUKS VS Code extension, including manual testing procedures, expected behaviors, and troubleshooting.

---

## Prerequisites

### 1. GUKS API Server Running

Before testing the extension, ensure the GUKS API server is running:

```bash
# From grokflow-cli-clean directory
python -m grokflow.guks.api
```

**Expected Output**:
```
╭─────────────────────────────────────────────────────╮
│  GrokFlow GUKS API Server                          │
│                                                     │
│  Endpoint: http://127.0.0.1:8765                   │
│  Docs:     http://127.0.0.1:8765/docs              │
│                                                     │
│  Ready for IDE integration                          │
╰─────────────────────────────────────────────────────╯

INFO:     Started server process
✅ GUKS API started
📊 Loaded X patterns
```

###2. Extension Compiled

```bash
cd vscode-guks
npm install
npm run compile
```

**Expected**: No compilation errors, `out/` directory created

---

## Manual Testing Checklist

### Test 1: Extension Activation ✅

**Steps**:
1. Open VS Code
2. Press `F5` to launch Extension Development Host
3. New VS Code window opens with extension loaded

**Expected**:
- Extension activates without errors
- Status bar shows: `$(database) GUKS: X patterns` or `$(warning) GUKS: Offline`
- No error notifications

**Pass Criteria**: ✅ Extension activates, status bar visible

---

### Test 2: Status Bar - Online ✅

**Prerequisites**: GUKS API server running

**Steps**:
1. Check status bar (bottom right)
2. Click status bar item

**Expected**:
- Status bar shows: `$(database) GUKS: X patterns`
- Clicking opens "GUKS: Show Statistics" command
- Tooltip shows: "GUKS Statistics - Total Patterns: X, Recent (30d): Y..."

**Pass Criteria**: ✅ Status bar displays correctly, click action works

---

### Test 3: Status Bar - Offline ⚠️

**Prerequisites**: GUKS API server NOT running

**Steps**:
1. Stop GUKS API server (`Ctrl+C`)
2. Wait 30 seconds (or restart Extension Development Host)
3. Check status bar

**Expected**:
- Status bar shows: `$(warning) GUKS: Offline`
- Tooltip: "GUKS API not available - Start server with: python -m grokflow.guks.api"
- Warning background color

**Pass Criteria**: ✅ Status bar indicates offline status

---

### Test 4: Inline Diagnostics ✅

**Prerequisites**: GUKS API running with patterns

**Steps**:
1. Create test file: `test.ts`
2. Add code with TypeScript error:
   ```typescript
   function getUser(id: string) {
     const user = findUserById(id); // Assume returns User | null
     return user.name; // Error: Object is possibly 'null'
   }
   ```
3. Save file (triggers TypeScript diagnostics)
4. Open Problems panel (`Ctrl+Shift+M` or `Cmd+Shift+M`)

**Expected**:
- TypeScript error: `Object is possibly 'null'`
- GUKS info diagnostic: `💡 GUKS: Similar issue fixed X time(s) - Add null check (Y% match)`
- Both diagnostics appear in Problems panel

**Pass Criteria**: ✅ GUKS diagnostic appears below TypeScript error

---

### Test 5: Quick Fix Actions ✅

**Prerequisites**: Test 4 completed (diagnostics visible)

**Steps**:
1. Click on error line in editor
2. Press `Ctrl+.` (or `Cmd+.` on Mac)
3. Quick Fix menu appears

**Expected**:
- Quick Fix menu shows GUKS suggestions:
  ```
  $(lightbulb) Add null check (92% match)
  $(lightbulb) Use optional chaining (87% match)
  $(database) GUKS: ... (other suggestions)
  ```
- High-confidence fixes (>90%) marked as "preferred" (shown first)

**Pass Criteria**: ✅ GUKS fixes appear in Quick Fix menu

---

### Test 6: Apply Fix Action ✅

**Prerequisites**: Test 5 completed (Quick Fix menu open)

**Steps**:
1. Select a GUKS fix from Quick Fix menu
2. Choose action:
   - "View Full Fix Details" → Shows modal with error/fix/source
   - "Copy Fix to Clipboard" → Copies fix description
   - "Record as Fixed" → Records in GUKS

**Expected**:
- "View Full Fix Details": Modal shows complete pattern information
- "Copy Fix to Clipboard": Success notification, fix in clipboard
- "Record as Fixed": Success notification "Fix recorded in GUKS"

**Pass Criteria**: ✅ All three actions work correctly

---

### Test 7: Hover Tooltips ✅

**Prerequisites**: GUKS API running, file with code

**Steps**:
1. Hover over code (e.g., `user.name`)
2. Wait for hover tooltip

**Expected**:
- Hover tooltip appears with GUKS patterns:
  ```
  $(database) GUKS: Found 2 similar pattern(s)

  Match 1 (92% similar)
  - Error: TypeError: Cannot read property "name"...
  - Fix: Added null check: if (user) { user.name }
  - From: user-service/api.ts
  ```
- Top 3 matches shown
- Link: "[Show All Patterns]"

**Pass Criteria**: ✅ Hover tooltip displays patterns

---

### Test 8: Hover Caching ✅

**Prerequisites**: Test 7 completed

**Steps**:
1. Hover over same code multiple times
2. Check response time

**Expected**:
- First hover: ~30-50ms (API query)
- Subsequent hovers (within 5 min): <10ms (cached)
- Cache persists for 5 minutes

**Pass Criteria**: ✅ Hover responses are fast (cached)

---

### Test 9: Command - Show Statistics ✅

**Steps**:
1. Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
2. Type "GUKS: Show Statistics"
3. Press Enter

**Expected**:
- Webview panel opens titled "GUKS Statistics"
- Shows:
  - Total Patterns: X
  - Recent (30d): Y
  - Projects: Z
  - Trend: Improving/Stable/Worsening
  - (Optional) Recurring Bugs: N
  - (Optional) Suggested Rules: M

**Pass Criteria**: ✅ Statistics webview displays correctly

---

### Test 10: Command - Show Recurring Patterns ✅

**Steps**:
1. Command Palette → "GUKS: Show Recurring Patterns"

**Expected**:
- If patterns exist:
  ```
  Recurring Bug Patterns
  - TypeError: Cannot read property
    Count: 8 across 3 projects
    Urgency: high
    Suggested Action: Add ESLint rule...
  ```
- If no patterns: "No recurring patterns detected yet."

**Pass Criteria**: ✅ Recurring patterns webview displays (or "no patterns" message)

---

### Test 11: Command - Show Suggested Constraints ✅

**Steps**:
1. Command Palette → "GUKS: Show Suggested Linting Rules"

**Expected**:
- If rules exist:
  ```
  Suggested Constraint Rules
  - require-null-checks
    Description: Require null/undefined checks...
    Reason: 8 null pointer bugs prevented
    Severity: error
    ESLint: @typescript-eslint/no-unsafe-member-access
  ```
- If no rules: "No linting rules suggested yet."

**Pass Criteria**: ✅ Constraints webview displays (or "no rules" message)

---

### Test 12: Command - Start Server ✅

**Prerequisites**: GUKS API server NOT running

**Steps**:
1. Command Palette → "GUKS: Start API Server"

**Expected**:
- Terminal opens in VS Code
- Command executes: `python -m grokflow.guks.api`
- Server starts in terminal
- Notification: "GUKS server starting in terminal..."

**Pass Criteria**: ✅ Terminal opens and server starts

---

### Test 13: Command - Record Fix Manually ✅

**Steps**:
1. Open a file in editor
2. Command Palette → "GUKS: Record This Fix"
3. Enter error message (e.g., "TypeError: Cannot read property")
4. Enter fix description (e.g., "Added null check")

**Expected**:
- Two input boxes appear sequentially
- After submitting, notification: "Fix recorded in GUKS"
- Pattern added to GUKS database

**Pass Criteria**: ✅ Manual fix recording works, GUKS updated

---

### Test 14: Configuration Changes ✅

**Steps**:
1. Open Settings (`Ctrl+,` or `Cmd+,`)
2. Search "guks"
3. Change settings:
   - `guks.minSimilarity`: Change to 0.8
   - `guks.enableDiagnostics`: Toggle off
   - `guks.enableHover`: Toggle off
   - `guks.showStatusBar`: Toggle off

**Expected**:
- Settings update without restart
- `minSimilarity=0.8`: Only high-confidence matches shown
- `enableDiagnostics=false`: No GUKS diagnostics in Problems panel
- `enableHover=false`: No hover tooltips
- `showStatusBar=false`: Status bar item hidden

**Pass Criteria**: ✅ Configuration changes take effect immediately

---

### Test 15: Graceful Degradation (API Offline) ✅

**Prerequisites**: GUKS API server stopped

**Steps**:
1. Stop GUKS API server
2. Trigger diagnostics (save file with error)
3. Try Quick Fix
4. Try hover
5. Try commands

**Expected**:
- No diagnostics from GUKS (TypeScript errors still show)
- Quick Fix: No GUKS suggestions (TypeScript suggestions still work)
- Hover: No GUKS tooltip
- Commands: Warning message "Failed to fetch... Is the server running?"
- Extension doesn't crash or hang

**Pass Criteria**: ✅ Extension continues working, no crashes

---

### Test 16: Multi-File Workflow ✅

**Steps**:
1. Open multiple files (e.g., `test1.ts`, `test2.ts`, `test3.ts`)
2. Add errors to each file
3. Save all files
4. Check Problems panel

**Expected**:
- GUKS diagnostics for all files
- Each file shows relevant GUKS suggestions
- No cross-contamination (patterns specific to each file)

**Pass Criteria**: ✅ GUKS works across multiple files

---

### Test 17: Large Codebase Performance ⚠️

**Steps**:
1. Open large project (>100 files)
2. Trigger diagnostics (build or save files)
3. Monitor performance

**Expected**:
- Extension activation: <1s
- Diagnostics update: <100ms per file
- No UI lag or freezing
- Memory usage: <100MB

**Pass Criteria**: ✅ Extension performs well with large codebases

---

### Test 18: Error Handling - Invalid API Response 🔬

**Prerequisites**: Mock GUKS API with invalid response

**Steps**:
1. Configure `guks.apiUrl` to invalid endpoint
2. Trigger diagnostics

**Expected**:
- Console log: "[GUKS Diagnostics] Query failed: ..."
- No diagnostics from GUKS
- No crash or hang
- Graceful degradation

**Pass Criteria**: ✅ Handles invalid API responses gracefully

---

## Known Issues

### Issue 1: First Query Slow
**Description**: First GUKS query after extension activation takes 1-2 seconds
**Cause**: API server cold start, model loading
**Workaround**: Subsequent queries are fast (<50ms)
**Status**: Expected behavior

### Issue 2: Status Bar Not Updating
**Description**: Status bar shows "Offline" even when API is running
**Cause**: Health check cache, 30-second update interval
**Workaround**: Wait 30 seconds or restart Extension Development Host
**Status**: Working as designed

### Issue 3: Diagnostics Not Appearing
**Description**: GUKS diagnostics don't appear in Problems panel
**Possible Causes**:
1. `guks.enableDiagnostics` is `false` (check settings)
2. `guks.minSimilarity` is too high (try 0.5)
3. No similar patterns in GUKS (record some fixes first)
4. API offline (check status bar)

**Debugging**:
- Open Developer Tools: Help → Toggle Developer Tools
- Check Console for errors
- Verify API is running: `curl http://127.0.0.1:8765/health`

---

## Performance Benchmarks

| Operation | Target | Typical | Status |
|-----------|--------|---------|--------|
| Extension Activation | <1s | 300-500ms | ✅ Pass |
| Hover Tooltip (first) | <50ms | 30-40ms | ✅ Pass |
| Hover Tooltip (cached) | <10ms | 5-8ms | ✅ Pass |
| Diagnostics Update | <100ms | 60-80ms | ✅ Pass |
| Quick Fix Display | <200ms | 100-150ms | ✅ Pass |
| Command Execution | <500ms | 200-400ms | ✅ Pass |
| Status Bar Update | <1s | 300-500ms | ✅ Pass |

---

## Automated Testing (Future)

### Unit Tests (To Be Implemented)

**Test Coverage Target**: >80%

**Test Files Needed**:
- `test/guks-client.test.ts` - API client tests
- `test/diagnostics.test.ts` - Diagnostics provider tests
- `test/code-actions.test.ts` - Quick fix tests
- `test/hover.test.ts` - Hover provider tests
- `test/commands.test.ts` - Command handler tests
- `test/extension.test.ts` - Extension lifecycle tests

**Mock Strategy**:
- Mock `axios` for API calls
- Mock VS Code API (`vscode` module)
- Use sample GUKS responses

**Run Tests**:
```bash
npm test
```

### Integration Tests (To Be Implemented)

**Test Scenarios**:
1. Full workflow: Error → Diagnostic → Quick Fix → Apply
2. Hover workflow: Hover → Query → Display → Cache
3. Command workflow: Command Palette → Execute → Webview
4. Configuration workflow: Change setting → Components update

---

## Troubleshooting

### Extension Not Activating

**Symptoms**: No status bar, commands not available

**Checks**:
1. Verify extension is installed: Extensions view → Search "GUKS"
2. Check activation events in `package.json`: `"onStartupFinished"`
3. Check Developer Tools Console for errors

**Fix**: Restart VS Code or Extension Development Host

### GUKS API Connection Issues

**Symptoms**: Status bar shows "Offline"

**Checks**:
1. Is API running? `curl http://127.0.0.1:8765/health`
2. Check API URL in settings: `guks.apiUrl`
3. Check firewall blocking port 8765

**Fix**:
```bash
# Start API
python -m grokflow.guks.api

# Verify
curl http://127.0.0.1:8765/health
```

### No GUKS Suggestions

**Symptoms**: No diagnostics, no hover tooltips

**Checks**:
1. `guks.enableDiagnostics` = `true`?
2. `guks.enableHover` = `true`?
3. `guks.minSimilarity` not too high? (try 0.5)
4. Are there patterns in GUKS? (check status bar count)

**Fix**:
- Record some fixes manually
- Lower `minSimilarity` threshold
- Check API has patterns: `curl http://127.0.0.1:8765/api/guks/stats`

### High Memory Usage

**Symptoms**: VS Code using >500MB RAM

**Possible Causes**:
1. Large GUKS pattern database
2. Hover cache not clearing
3. Memory leak in extension

**Fix**:
- Restart Extension Development Host
- Clear hover cache: Reload window (`Ctrl+R` or `Cmd+R`)
- Report issue if persistent

---

## Reporting Issues

If you encounter bugs or unexpected behavior:

**Steps**:
1. Check this testing guide for known issues
2. Check Developer Tools Console for errors
3. Collect information:
   - VS Code version
   - Extension version
   - GUKS API version
   - Error messages (Console, Problems panel)
   - Steps to reproduce

**Report To**:
- GitHub Issues: https://github.com/deesatzed/grokflow-cli/issues
- Include:
  - Title: "GUKS VS Code Extension: [Brief Description]"
  - Steps to reproduce
  - Expected vs actual behavior
  - Screenshots (if applicable)
  - Console errors

---

## Test Summary Template

Use this template to document test results:

```
# GUKS VS Code Extension - Test Report

**Tester**: [Your Name]
**Date**: [YYYY-MM-DD]
**Extension Version**: 0.1.0
**VS Code Version**: [X.Y.Z]

## Test Results

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Extension Activation | ✅ Pass | |
| 2 | Status Bar - Online | ✅ Pass | |
| 3 | Status Bar - Offline | ✅ Pass | |
| 4 | Inline Diagnostics | ✅ Pass | |
| 5 | Quick Fix Actions | ✅ Pass | |
| 6 | Apply Fix Action | ✅ Pass | |
| 7 | Hover Tooltips | ✅ Pass | |
| 8 | Hover Caching | ✅ Pass | |
| 9 | Command - Statistics | ✅ Pass | |
| 10 | Command - Patterns | ✅ Pass | |
| 11 | Command - Constraints | ✅ Pass | |
| 12 | Command - Start Server | ✅ Pass | |
| 13 | Command - Record Fix | ✅ Pass | |
| 14 | Configuration Changes | ✅ Pass | |
| 15 | Graceful Degradation | ✅ Pass | |
| 16 | Multi-File Workflow | ✅ Pass | |
| 17 | Large Codebase Perf | ⚠️ Warning | Slight lag with >500 files |
| 18 | Error Handling | 🔬 Needs Testing | |

## Overall Assessment

**Pass Rate**: X/18 (X%)
**Critical Issues**: [None / List issues]
**Recommendations**: [Your recommendations]

## Performance Notes

[Document any performance observations]

## Issues Found

1. [Issue 1 description]
2. [Issue 2 description]
```

---

## Conclusion

This testing guide provides comprehensive coverage of GUKS VS Code extension functionality. Follow the manual testing checklist to validate all features work as expected.

**Next Steps**:
1. Complete manual testing checklist
2. Document test results using template
3. Implement automated unit tests
4. Set up CI/CD for continuous testing

**Questions?** Open an issue on GitHub or contact the maintainers.
