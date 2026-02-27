# Lessons Learned

## Milestone: Project Structure & Strategy Index (2026-02-26)

### What Worked
- URL discovery: strategy detail pages follow a clean slug pattern at /learning/articles/investment-strategy-library/<slug>, no need for numeric ID discovery
- Flat category structure keeps things simple for 83 items across 10 categories

### What Didn't Work
- Initial WebFetch of the index page didn't extract individual strategy URLs (client-side rendered) — web search was needed to discover the URL pattern

### Patterns to Reuse
- Use WebSearch to discover QuantConnect URL patterns before attempting WebFetch on individual pages
- Strategy slug = kebab-case of the strategy name as it appears on the index page

### Patterns to Avoid
- Don't rely on HTML scraping for QuantConnect pages — they use client-side rendering for links
