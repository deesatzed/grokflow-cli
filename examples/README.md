# GrokFlow CLI - Real-World Examples

This directory contains documented real-world examples of GrokFlow CLI in action.

---

## Available Examples

### 1. [Podcast Briefing AI](./REAL_WORLD_EXAMPLE_PODCAST_AI.md)

**Project**: React + TypeScript + Google Gemini AI podcast generation app
**Status**: Production application (non-functional → working)
**Date**: 2025-12-09

**Summary**:
- 🐛 **11 critical bugs** identified in 2 files
- ⏱️ **103 seconds** total analysis time
- ✅ **9 production-ready fixes** applied
- 💾 **82% developer time saved** (~2 hours → 27 minutes)

**Key Issues Fixed**:
1. Wrong API request format (Gemini SDK)
2. Undefined response parsing (`response.text`)
3. JSON mode not working (wrong config key)
4. Missing error handling (no try-catch)
5. API key exposure vulnerability
6. Input validation gaps
7. UX bugs (search behavior)
8. Inconsistent visual feedback

**Before GrokFlow**:
```typescript
// ❌ Wrong format
const response = await ai.models.generateContent({
  model: 'gemini-2.5-flash',
  contents: prompt,  // String instead of array
});
return response.text;  // undefined
```

**After GrokFlow**:
```typescript
// ✅ Correct format
const response = await ai.models.generateContent({
  model: "gemini-1.5-flash",
  contents: [{ parts: [{ text: prompt }] }],
  generationConfig: { maxOutputTokens: 500 },
});
const text = extractText(response);  // Safe helper
return text || "Fallback message";
```

**Impact**:
- Script generation: ❌ Always fallback → ✅ Working
- Smart suggestions: ❌ JSON parse error → ✅ Returns AI suggestions
- Error messages: ❌ Generic → ✅ Specific (API key, network, etc.)
- Build: ✅ TypeScript passes → ✅ Runtime works

[**Read full example →**](./REAL_WORLD_EXAMPLE_PODCAST_AI.md)

---

## How to Use These Examples

### 1. Learn from Analysis Output

See how GrokFlow identifies bugs:

```bash
cd podcast-briefing-ai-example
cat grokflow-analysis-output.txt
```

**Example output**:
```
### Bug Analysis

#### Primary Issues
1. **Incorrect `contents` Format**:
   - The `generateContent` method expects `contents` to be an array
   - Currently, `contents: prompt` passes a plain string
   - **Impact**: Functions will fail with TypeError

2. **Inconsistent Response Parsing**:
   - Text responses assume `response.text` exists
   - The SDK returns `response.candidates[0].content.parts[0].text`
   - **Impact**: `response.text` is `undefined`
```

### 2. Apply Similar Fixes to Your Project

Use the fix patterns from examples:

**Pattern: SDK Response Parsing**
```typescript
// Generic helper (works for any nested response)
const extractText = (response: any): string | undefined => {
  return response.candidates?.[0]?.content?.parts?.[0]?.text;
};
```

**Pattern: Input Validation**
```typescript
// Always trim and validate user input
const validTopics = topics.filter((t) => t.trim());
if (validTopics.length === 0) return;
```

**Pattern: Error Categorization**
```typescript
// Specific error messages based on error type
if (error?.message?.includes("API key")) {
  return "API key error. Please check your configuration.";
} else if (error?.message?.includes("network")) {
  return "Network error. Please check your connection.";
}
```

### 3. Run GrokFlow on Your Own Project

```bash
# Install GrokFlow
git clone https://github.com/deesatzed/grokflow-cli
cd grokflow-cli
pip install -r requirements.txt

# Set API key
export XAI_API_KEY=xai-your-key-here

# Analyze your files
python grokflow_v2.py fix path/to/your/file.ts
```

---

## Example Statistics

| Example | Files | Bugs Found | Fixes Applied | Analysis Time | Time Saved |
|---------|-------|------------|---------------|---------------|------------|
| Podcast AI | 2 | 11 | 9 | 103s | ~2 hours |

---

## Contributing Examples

Have a great GrokFlow success story? Add it here!

### Requirements

1. **Real-world project** (not toy examples)
2. **Measurable impact** (before/after comparison)
3. **Reproducible** (include code snippets)
4. **Documented** (analysis output + fixes)

### Template

```markdown
# Project Name

**Summary**: Brief description
**Date**: YYYY-MM-DD
**Files**: Number of files analyzed
**Bugs**: Number found
**Impact**: What changed

## The Problem
[What wasn't working]

## GrokFlow Analysis
[What GrokFlow found]

## Fixes Applied
[Code before/after]

## Results
[Measurable improvements]
```

Submit via PR to https://github.com/deesatzed/grokflow-cli

---

## FAQ

### Q: Are these examples cherry-picked?

**A**: No. These are actual analyses from real projects. We include failures and limitations too.

### Q: Can I use GrokFlow on my proprietary code?

**A**: Yes. GrokFlow runs locally. Your code never leaves your machine (only sent to x.ai API for analysis, same as using ChatGPT).

### Q: What if GrokFlow suggests a wrong fix?

**A**: Always review suggestions. GrokFlow provides analysis and recommendations, not automatic code changes. You decide what to apply.

### Q: How much does it cost?

**A**: GrokFlow uses x.ai Grok models. See https://x.ai/api for current pricing. The podcast AI example cost ~$0.02 in API calls.

---

## Additional Resources

- [GrokFlow CLI README](../README.md)
- [Usage Guide](../CLI_USAGE_GUIDE.md)
- [MCP Integration Guide](../MCP_INTEGRATION_GUIDE.md)
- [API Test Results](../API_TEST_SUCCESS.md)

---

**GrokFlow CLI**: Autonomous code analysis powered by x.ai Grok models
**Repository**: https://github.com/deesatzed/grokflow-cli
**Version**: 1.4.0
