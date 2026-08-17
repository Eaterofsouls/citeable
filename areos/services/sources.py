# areos/services/sources.py
#
# Source Registry seed data and service functions.
#
# All 107 sources from AEO_GEO_Master_Knowledge_Base_v2.md §6 are defined here
# as structured Python data. Trust tiers are DETERMINISTIC from source type —
# no editorial judgment, per Bible §6.4 / ADR D5.
#
# Trust Tier Key:
#   T1 = Official platform documentation (OpenAI, Google, Perplexity speaking about their own systems)
#   T2 = Primary research / peer-reviewed (named authors, stated methodology, sample sizes)
#   T3 = Legal primary sources (court filings, actual ToS text)
#   T4 = Reputable named practitioners (verified SEO/GEO analysts with track records)
#   T5 = Industry media (Search Engine Land, Ars Technica — secondhand but edited)
#   T6 = Vendor research (useful but vendor-motivated framing — treat with caution)
#   T7 = Community / social signals (Reddit, Twitter — signals only, never claim backbone)

from __future__ import annotations
import sqlite3
from areos.db.context import write_as

# ---------------------------------------------------------------------------
# Seed data — one dict per source, ordered by tier then priority within tier.
# Fields: source_id, name, domain, url, trust_tier, source_type,
#         verified (1=yes), verified_date, notes
# ---------------------------------------------------------------------------

SOURCES: list[dict] = [

    # =========================================================================
    # T1 — Official Platform Documentation (15 sources)
    # =========================================================================
    {
        "source_id": "S001",
        "name": "OpenAI — Publishers and Developers FAQ",
        "domain": "help.openai.com",
        "url": "https://help.openai.com",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "OpenAI's own FAQ for publishers. Verified live during Research Update session.",
    },
    {
        "source_id": "S002",
        "name": "OpenAI — GPTBot Policy",
        "domain": "openai.com",
        "url": "https://openai.com/bot/",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "OpenAI's canonical bot policy page. Resolves CLM-023. Verified live 2026-07-28.",
    },
    {
        "source_id": "S003",
        "name": "Google Search Central — AI Features Documentation",
        "domain": "developers.google.com",
        "url": "https://developers.google.com/search/docs/appearance/ai-features",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 1,
        "verified_date": "2025-12-10",
        "notes": "Claude fetched this page directly (stamp: 2025-12-10). States no special schema needed for AI Overviews.",
    },
    {
        "source_id": "S004",
        "name": "Google Search Central — FAQPage Structured Data",
        "domain": "developers.google.com",
        "url": "https://developers.google.com/search/docs/appearance/structured-data/faqpage",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 1,
        "verified_date": "2026-05-08",
        "notes": "Primary source confirming FAQ rich-result removal (May 7 2026). 4/5 models confirm directly.",
    },
    {
        "source_id": "S005",
        "name": "Google Search Central — Updates Changelog",
        "domain": "developers.google.com",
        "url": "https://developers.google.com/search/updates",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Official changelog for all Google Search Central updates.",
    },
    {
        "source_id": "S006",
        "name": "Google Search Central Blog",
        "domain": "developers.google.com",
        "url": "https://developers.google.com/search/blog",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Google's own blog for product announcements. Gemini confirmed FAQ deprecation via blog post dated June 14, 2026.",
    },
    {
        "source_id": "S007",
        "name": "Google — Googlebot Documentation",
        "domain": "developers.google.com",
        "url": "https://developers.google.com/search/docs/crawling-indexing/googlebot",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Primary reference for Googlebot crawl behaviour.",
    },
    {
        "source_id": "S008",
        "name": "OpenAI — GPTBot IP Ranges",
        "domain": "openai.com",
        "url": "https://openai.com/gptbot.json",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Machine-readable GPTBot IP range file from OpenAI.",
    },
    {
        "source_id": "S009",
        "name": "OpenAI — API / Platform Docs",
        "domain": "platform.openai.com",
        "url": "https://platform.openai.com/docs",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "OpenAI's primary developer documentation hub.",
    },
    {
        "source_id": "S010",
        "name": "Anthropic — Does Anthropic Crawl Data from the Web",
        "domain": "support.claude.com",
        "url": "https://support.claude.com",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Anthropic's official crawler policy page.",
    },
    {
        "source_id": "S011",
        "name": "Perplexity — Crawler Documentation",
        "domain": "docs.perplexity.ai",
        "url": "https://docs.perplexity.ai/docs/resources/perplexity-crawlers",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Perplexity's official crawler policy and documentation.",
    },
    {
        "source_id": "S012",
        "name": "Cloudflare — AI Crawl Control Reference",
        "domain": "developers.cloudflare.com",
        "url": "https://developers.cloudflare.com/ai-crawl-control",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Cloudflare's authoritative reference for AI crawler blocking controls.",
    },
    {
        "source_id": "S013",
        "name": "Cloudflare — Radar / Bot Behaviour Reports",
        "domain": "blog.cloudflare.com",
        "url": "https://blog.cloudflare.com",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Includes the Aug 2025 Perplexity/Bytespider directive-evasion report. Corroborated C013.",
    },
    {
        "source_id": "S014",
        "name": "Apple — Applebot-Extended Support Page",
        "domain": "support.apple.com",
        "url": "https://support.apple.com",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Apple's official Applebot documentation.",
    },
    {
        "source_id": "S015",
        "name": "Meta — Web Crawlers Documentation",
        "domain": "developers.facebook.com",
        "url": "https://developers.facebook.com/docs/sharing/webmasters/web-crawlers",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Meta's official web crawler documentation.",
    },
    {
        "source_id": "S015b",
        "name": "Common Crawl — CCBot Documentation",
        "domain": "commoncrawl.org",
        "url": "https://commoncrawl.org/ccbot",
        "trust_tier": "T1",
        "source_type": "official-platform-doc",
        "verified": 0,
        "verified_date": None,
        "notes": "Common Crawl's official CCBot documentation.",
    },

    # =========================================================================
    # T2 — Primary Research / Peer-Reviewed (17 sources)
    # =========================================================================
    {
        "source_id": "S016",
        "name": "Ahrefs — Linehan & Guan Schema/AI-Citation Matched-Control Study",
        "domain": "ahrefs.com",
        "url": "https://ahrefs.com/blog",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Named authors (Louise Linehan, Xibeijia Guan). Matched-control methodology. Primary backing for CLM-007.",
    },
    {
        "source_id": "S017",
        "name": "Kurt Fischman — 'Does Schema Markup Predict AI Citation?' (SSRN)",
        "domain": "ssrn.com",
        "url": "https://ssrn.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Named researcher. SSRN preprint. Strongest single source for the schema/citation null finding.",
    },
    {
        "source_id": "S018",
        "name": "Aggarwal, Murahari et al. — 'GEO: Generative Engine Optimization' (Princeton/Georgia Tech/Allen AI, KDD)",
        "domain": "arxiv.org",
        "url": "https://arxiv.org",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Peer-reviewed conference paper (KDD). Foundational academic reference for GEO as a field.",
    },
    {
        "source_id": "S019",
        "name": "Vercel / MERJ — AI-Crawler JS-Rendering Analysis (500M+ Fetches)",
        "domain": "vercel.com",
        "url": "https://vercel.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Large-scale empirical study (500M+ fetches). Key source for C034 (JS non-rendering as stable fact).",
    },
    {
        "source_id": "S020",
        "name": "Writesonic — AI Citation Churn Tracking (23M Sources)",
        "domain": "writesonic.com",
        "url": "https://writesonic.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Large dataset (23M sources). Verified specific churn numbers that replaced Claude's imprecise C076 figures.",
    },
    {
        "source_id": "S021",
        "name": "SALT.agency — Backlink Correlation Study (5,825 URLs)",
        "domain": "salt.agency",
        "url": "https://salt.agency",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Named agency. Stated sample size (5,825 URLs). Backs CLM-054 backlink/DA correlation.",
    },
    {
        "source_id": "S022",
        "name": "Semrush — Authority Score / AI-Mention Correlation Study",
        "domain": "semrush.com",
        "url": "https://semrush.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Named study from Semrush research team. Treat as T2 for data; vendor framing still present.",
    },
    {
        "source_id": "S023",
        "name": "Kevin Indig — ChatGPT Citation-Position ('Ski-Ramp') Analysis",
        "domain": "growth-memo.com",
        "url": "https://growth-memo.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Named analyst. Original empirical analysis with named methodology. Verified session.",
    },
    {
        "source_id": "S024",
        "name": "Cyrus Shepard (Zyppy) — 23-Factor, 54-Study GEO Meta-Analysis",
        "domain": "zyppy.com",
        "url": "https://zyppy.com/blog",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Flagged during Research Update as highest-value single lead. Exists and verified; full content not yet fetched. NEEDS FOLLOW-UP.",
    },
    {
        "source_id": "S025",
        "name": "Moz — AI Mode Citation-Source Study (40,000-Query Analysis)",
        "domain": "moz.com",
        "url": "https://moz.com/blog",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Named study from Moz research team. 40,000-query scale gives reasonable statistical weight.",
    },
    {
        "source_id": "S026",
        "name": "Trustpilot — Brand Review-Profile vs. AI Citation-Rate Analysis",
        "domain": "trustpilot.com",
        "url": "https://trustpilot.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Named study from Trustpilot. Backs brand-review / AI-citation claims.",
    },
    {
        "source_id": "S027",
        "name": "WordLift — Recursive Language Models over Knowledge Graphs",
        "domain": "wordlift.io",
        "url": "https://wordlift.io",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Research paper from WordLift. Entity/knowledge-graph focus.",
    },
    {
        "source_id": "S028",
        "name": "SE Ranking — llms.txt Adoption Study",
        "domain": "seranking.com",
        "url": "https://seranking.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Named adoption study from SE Ranking research team.",
    },
    {
        "source_id": "S029",
        "name": "Bright Data / Daniel Shashko — Citation-Position Studies",
        "domain": "brightdata.com",
        "url": "https://brightdata.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Named researcher (Daniel Shashko). Backs citation-position claims.",
    },
    {
        "source_id": "S030",
        "name": "arXiv — GEO / LLM-Citation Preprint Corpus",
        "domain": "arxiv.org",
        "url": "https://arxiv.org",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Living index of peer-reviewed preprints. Search: 'generative engine optimization', 'LLM citation', 'answer engine'.",
    },
    {
        "source_id": "S031",
        "name": "Google Scholar — Peer-Reviewed GEO/AEO Work 2025–2026",
        "domain": "scholar.google.com",
        "url": "https://scholar.google.com",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 0,
        "verified_date": None,
        "notes": "Living index. Filter to 2025–2026 for current peer-reviewed GEO research.",
    },
    {
        "source_id": "S032",
        "name": "Ahrefs Blog — Data-Driven Research Team",
        "domain": "ahrefs.com",
        "url": "https://ahrefs.com/blog",
        "trust_tier": "T2",
        "source_type": "primary-research",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "General Ahrefs research output. Separate from the specific Linehan & Guan study (S016).",
    },

    # =========================================================================
    # T3 — Legal Primary Sources (7 sources)
    # =========================================================================
    {
        "source_id": "S033",
        "name": "CourtListener / PACER — SerpApi v. Google Docket",
        "domain": "courtlistener.com",
        "url": "https://courtlistener.com",
        "trust_tier": "T3",
        "source_type": "legal-primary",
        "verified": 0,
        "verified_date": None,
        "notes": "Primary court filings for SerpApi v. Google. NOT YET FETCHED. Required to confirm CLM-044 court order status.",
    },
    {
        "source_id": "S034",
        "name": "Google Consumer Terms of Service — Primary Text",
        "domain": "policies.google.com",
        "url": "https://policies.google.com/terms",
        "trust_tier": "T3",
        "source_type": "legal-primary",
        "verified": 0,
        "verified_date": None,
        "notes": "NOT YET FETCHED. Required to confirm CLM-044 scraping clause language directly.",
    },
    {
        "source_id": "S035",
        "name": "Gemini API Additional Terms of Service — Primary Text",
        "domain": "ai.google.dev",
        "url": "https://ai.google.dev/gemini-api/terms",
        "trust_tier": "T3",
        "source_type": "legal-primary",
        "verified": 0,
        "verified_date": None,
        "notes": "NOT YET FETCHED. Required to confirm CLM-045 Gemini API terms language directly.",
    },
    {
        "source_id": "S036",
        "name": "Proxyway — Scraping-Industry Legal News",
        "domain": "proxyway.com",
        "url": "https://proxyway.com",
        "trust_tier": "T3",
        "source_type": "legal-primary",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Specialist legal tracking for the scraping industry. Verified session.",
    },
    {
        "source_id": "S037",
        "name": "Search Engine Roundtable — SEO Legal Coverage (Barry Schwartz)",
        "domain": "seroundtable.com",
        "url": "https://seroundtable.com",
        "trust_tier": "T3",
        "source_type": "legal-primary",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "SEO-industry legal coverage. Verified session.",
    },
    {
        "source_id": "S038",
        "name": "IPWatchdog — IP-Law Analysis of Platform Lawsuits",
        "domain": "ipwatchdog.com",
        "url": "https://ipwatchdog.com",
        "trust_tier": "T3",
        "source_type": "legal-primary",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Specialist IP-law publication. Verified session.",
    },
    {
        "source_id": "S039",
        "name": "ScrapeBadger — Scraping Legal Case Tracking",
        "domain": "scrapebadger.com",
        "url": "https://scrapebadger.com",
        "trust_tier": "T3",
        "source_type": "legal-primary",
        "verified": 1,
        "verified_date": "2026-07-28",
        "notes": "Dedicated scraping legal case tracker. Verified session.",
    },

    # =========================================================================
    # T4 — Named Practitioners (30 sources)
    # =========================================================================
    {
        "source_id": "S040", "name": "Kevin Indig — Growth Memo",
        "domain": "growth-memo.com", "url": "https://growth-memo.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Independent growth/GEO analyst. Original research on citation-position patterns.",
    },
    {
        "source_id": "S041", "name": "Aleyda Solis",
        "domain": "aleydasolis.com", "url": "https://aleydasolis.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "International/multilingual GEO specialist.",
    },
    {
        "source_id": "S042", "name": "Lily Ray — Amsive",
        "domain": "amsive.com", "url": "https://amsive.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "E-E-A-T and GEO specialist. Active on LinkedIn/X.",
    },
    {
        "source_id": "S043", "name": "Mike King — iPullRank",
        "domain": "ipullrank.com", "url": "https://ipullrank.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Technical/engineering approach to GEO.",
    },
    {
        "source_id": "S044", "name": "Rand Fishkin — SparkToro",
        "domain": "sparktoro.com", "url": "https://sparktoro.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Zero-click and AI-answer research.",
    },
    {
        "source_id": "S045", "name": "Cyrus Shepard — Zyppy",
        "domain": "zyppy.com", "url": "https://zyppy.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Evidence-based GEO ranking research. Author of S024 meta-analysis.",
    },
    {
        "source_id": "S046", "name": "Andrea Volpini — WordLift",
        "domain": "wordlift.io", "url": "https://wordlift.io",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Entity/knowledge-graph strategy specialist.",
    },
    {
        "source_id": "S047", "name": "Chris Long — Go Fish Digital / Nectiv",
        "domain": "gofishdigital.com", "url": "https://gofishdigital.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Public GEO experiments and tooling.",
    },
    {
        "source_id": "S048", "name": "Dan Petrovic — DEJAN AI",
        "domain": "dejan.ai", "url": "https://dejan.ai",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Retrieval/ranking reverse-engineering.",
    },
    {
        "source_id": "S049", "name": "David Konitzny — Answer Engine Research",
        "domain": "davidkonitzny.com", "url": "https://davidkonitzny.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Answer-engine retrieval research.",
    },
    {
        "source_id": "S050", "name": "Olivier de Segonzac — Answer Engine Research",
        "domain": "linkedin.com", "url": "https://linkedin.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Answer-engine retrieval research.",
    },
    {
        "source_id": "S051", "name": "Crystal Carter — Wix",
        "domain": "wix.com", "url": "https://wix.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Active AEO commentary from Wix.",
    },
    {
        "source_id": "S052", "name": "Jason Barnard — Kalicube",
        "domain": "kalicube.com", "url": "https://kalicube.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Entity/knowledge-panel specialist.",
    },
    {
        "source_id": "S053", "name": "Metehan Yesilyurt — AEO Vision / metehan.ai",
        "domain": "metehan.ai", "url": "https://metehan.ai",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "AEO Vision co-founder. Independent AEO research.",
    },
    {
        "source_id": "S054", "name": "Ipek Isler — AEO Vision",
        "domain": "aeovision.io", "url": "https://aeovision.io",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "AEO Vision co-founder.",
    },
    {
        "source_id": "S055", "name": "Barry Schwartz — Search Engine Roundtable / Search Engine Land",
        "domain": "seroundtable.com", "url": "https://seroundtable.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Industry news and commentary. Highly prolific and reliable SEO reporter.",
    },
    {
        "source_id": "S056", "name": "John Mueller — Google Search Relations",
        "domain": "twitter.com", "url": "https://twitter.com/JohnMu",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Google Search Relations. Public statements on llms.txt/schema carry weight as semi-official.",
    },
    {
        "source_id": "S057", "name": "Danny Sullivan — Google Search Liaison",
        "domain": "twitter.com", "url": "https://twitter.com/dannysullivan",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Google Search Liaison. Official public search-policy communications.",
    },
    {
        "source_id": "S058", "name": "Fabrice Canel — Microsoft Bing",
        "domain": "linkedin.com", "url": "https://linkedin.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Official Microsoft Bing statements on schema and Copilot. Backs CLM-018/CLM-057.",
    },
    {
        "source_id": "S059", "name": "Marie Haynes — Google Algorithm Specialist",
        "domain": "mariehaynes.com", "url": "https://mariehaynes.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Google algorithm/E-E-A-T specialist.",
    },
    {
        "source_id": "S060", "name": "Glenn Gabe — GSQI",
        "domain": "gsqi.com", "url": "https://gsqi.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Technical SEO/algorithm-impact analyst.",
    },
    {
        "source_id": "S061", "name": "James Dooley — SEO/AI-Search Commentator",
        "domain": "jamesdooley.com", "url": "https://jamesdooley.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "SEO/AI-search commentator. Verified session.",
    },
    {
        "source_id": "S062", "name": "Julian Goldie — AI SEO Community",
        "domain": "juliangoldie.com", "url": "https://juliangoldie.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "AI SEO community/testing. Verified session.",
    },
    {
        "source_id": "S063", "name": "Gareth Hoyle — GEO Practitioner",
        "domain": "linkedin.com", "url": "https://linkedin.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "GEO practitioner. Verified session.",
    },
    {
        "source_id": "S064", "name": "Duane Forrester — Former Bing Exec",
        "domain": "linkedin.com", "url": "https://linkedin.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Former Bing exec, now independent AEO/GEO commentator.",
    },
    {
        "source_id": "S065", "name": "Wil Reynolds — Seer Interactive",
        "domain": "seerinteractive.com", "url": "https://seerinteractive.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Search-strategy commentary.",
    },
    {
        "source_id": "S066", "name": "Aja Frost — Content/AEO Commentary",
        "domain": "linkedin.com", "url": "https://linkedin.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Content-strategy/AEO commentary.",
    },
    {
        "source_id": "S067", "name": "Eli Schwartz — SEO Strategy",
        "domain": "elischwartz.co", "url": "https://elischwartz.co",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "SEO strategy, product-led growth crossover.",
    },
    {
        "source_id": "S068", "name": "Brodie Clark — Technical SEO / SERP Feature Tracking",
        "domain": "brodieseo.com", "url": "https://brodieseo.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Technical SEO, SERP-feature tracking.",
    },
    {
        "source_id": "S069", "name": "Patrick Stox — Ahrefs",
        "domain": "ahrefs.com", "url": "https://ahrefs.com",
        "trust_tier": "T4", "source_type": "named-practitioner",
        "verified": 0, "verified_date": None,
        "notes": "Technical SEO and schema commentary from Ahrefs team.",
    },

    # =========================================================================
    # T5 — Industry Media (11 sources)
    # =========================================================================
    {
        "source_id": "S070", "name": "Search Engine Land",
        "domain": "searchengineland.com", "url": "https://searchengineland.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Leading SEO/SEM industry publication.",
    },
    {
        "source_id": "S071", "name": "Search Engine Journal",
        "domain": "searchenginejournal.com", "url": "https://searchenginejournal.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "Major SEO industry publication.",
    },
    {
        "source_id": "S072", "name": "Search Engine Roundtable",
        "domain": "seroundtable.com", "url": "https://seroundtable.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 1, "verified_date": "2026-07-28", "notes": "SEO industry news. Barry Schwartz primary author.",
    },
    {
        "source_id": "S073", "name": "Moz Blog",
        "domain": "moz.com", "url": "https://moz.com/blog",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "Long-running SEO publication.",
    },
    {
        "source_id": "S074", "name": "Backlinko (Brian Dean)",
        "domain": "backlinko.com", "url": "https://backlinko.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "Data-driven SEO content.",
    },
    {
        "source_id": "S075", "name": "Ars Technica",
        "domain": "arstechnica.com", "url": "https://arstechnica.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "Tech-industry legal and platform coverage.",
    },
    {
        "source_id": "S076", "name": "Practical Ecommerce",
        "domain": "practicalecommerce.com", "url": "https://practicalecommerce.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "AEO/GEO for commerce coverage.",
    },
    {
        "source_id": "S077", "name": "SparkToro Blog",
        "domain": "sparktoro.com", "url": "https://sparktoro.com/blog",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Zero-click and AI-answer research blog.",
    },
    {
        "source_id": "S078", "name": "Growth Memo Newsletter",
        "domain": "growth-memo.com", "url": "https://growth-memo.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Kevin Indig's research newsletter.",
    },
    {
        "source_id": "S079", "name": "Zyppy Blog",
        "domain": "zyppy.com", "url": "https://zyppy.com/blog",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Cyrus Shepard's evidence-based GEO blog.",
    },
    {
        "source_id": "S079b", "name": "VKTR — AI Platform Business/Legal News",
        "domain": "vktr.com", "url": "https://vktr.com",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "AI-platform business and legal news.",
    },

    # =========================================================================
    # T6 — Vendor Research (11 sources)
    # =========================================================================
    {
        "source_id": "S080", "name": "BrightEdge — AI Visibility Research",
        "domain": "brightedge.com", "url": "https://brightedge.com",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None,
        "notes": "Vendor-motivated framing. Uplift percentages flagged as uncontrolled in CLM-015.",
    },
    {
        "source_id": "S081", "name": "SE Ranking — Technical Adoption Studies",
        "domain": "seranking.com", "url": "https://seranking.com",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None,
        "notes": "Useful adoption data. Vendor framing present.",
    },
    {
        "source_id": "S082", "name": "Profound — Enterprise AI Visibility Platform",
        "domain": "profound.com", "url": "https://profound.com",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Sponsors/publishes GEO explainers.",
    },
    {
        "source_id": "S083", "name": "Otterly.AI — Citation/Mention Monitoring",
        "domain": "otterly.ai", "url": "https://otterly.ai/blog",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None, "notes": "Vendor tool. Research blog present.",
    },
    {
        "source_id": "S084", "name": "AthenaHQ — Prompt-Level Visibility Benchmarking",
        "domain": "athenahq.ai", "url": "https://athenahq.ai",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None, "notes": "Vendor tool.",
    },
    {
        "source_id": "S085", "name": "Peec AI — Engine Visibility Monitoring",
        "domain": "peec.ai", "url": "https://peec.ai",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None, "notes": "Vendor tool.",
    },
    {
        "source_id": "S086", "name": "Scrunch AI — All-Engine Audit Tooling",
        "domain": "scrunch.ai", "url": "https://scrunch.ai",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None, "notes": "Vendor tool.",
    },
    {
        "source_id": "S087", "name": "Knowatoa — Brand-Description / Sentiment Monitoring",
        "domain": "knowatoa.com", "url": "https://knowatoa.com",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None, "notes": "Vendor tool.",
    },
    {
        "source_id": "S088", "name": "WordLift — Schema / Knowledge-Graph Tooling",
        "domain": "wordlift.io", "url": "https://wordlift.io",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 0, "verified_date": None, "notes": "Vendor tool with research output.",
    },
    {
        "source_id": "S089", "name": "Authoritytech / Machine Relations — Earned-Media Citation Analysis",
        "domain": "authoritytech.com", "url": "https://authoritytech.com",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Vendor research. Verified session.",
    },
    {
        "source_id": "S090", "name": "Mentiohunt — Backlink-vs-Mention Citation Analysis",
        "domain": "mentiohunt.com", "url": "https://mentiohunt.com",
        "trust_tier": "T6", "source_type": "vendor-research",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Vendor research. Verified session.",
    },

    # =========================================================================
    # T7 — Community / Social Signals (7 sources)
    # =========================================================================
    {
        "source_id": "S091", "name": "r/TechSEO (Reddit)",
        "domain": "reddit.com", "url": "https://reddit.com/r/TechSEO",
        "trust_tier": "T7", "source_type": "community",
        "verified": 0, "verified_date": None,
        "notes": "Practitioner debate. Signals only — never used as sole claim backbone.",
    },
    {
        "source_id": "S092", "name": "r/SEO (Reddit)",
        "domain": "reddit.com", "url": "https://reddit.com/r/SEO",
        "trust_tier": "T7", "source_type": "community",
        "verified": 0, "verified_date": None,
        "notes": "Community SEO discussion.",
    },
    {
        "source_id": "S093", "name": "WebmasterWorld Forums",
        "domain": "webmasterworld.com", "url": "https://webmasterworld.com",
        "trust_tier": "T7", "source_type": "community",
        "verified": 0, "verified_date": None,
        "notes": "Long-running technical SEO forum.",
    },
    {
        "source_id": "S094", "name": "X/Twitter — SEO Practitioner Threads",
        "domain": "twitter.com", "url": "https://twitter.com",
        "trust_tier": "T7", "source_type": "community",
        "verified": 0, "verified_date": None,
        "notes": "Threads often precede formal write-ups by days/weeks. Signal value only.",
    },
    {
        "source_id": "S095", "name": "LinkedIn — Enterprise SEO Practitioner Posts",
        "domain": "linkedin.com", "url": "https://linkedin.com",
        "trust_tier": "T7", "source_type": "community",
        "verified": 0, "verified_date": None,
        "notes": "Same dynamic as X, especially for senior/enterprise practitioners.",
    },
    {
        "source_id": "S096", "name": "Julian Goldie's AI SEO Community (Skool)",
        "domain": "skool.com", "url": "https://skool.com",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Active testing/discussion group. Verified session.",
    },
    {
        "source_id": "S097", "name": "Semantic Mastery — Hump Day Hangouts",
        "domain": "semanticmastery.com", "url": "https://semanticmastery.com",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28",
        "notes": "Ongoing AEO/GEO Q&A series. Verified session.",
    },

    # =========================================================================
    # YouTube / Video (9 sources) — treated as T5/T7 depending on source channel
    # =========================================================================
    {
        "source_id": "S098", "name": "YouTube — 'Complete Guide to AI Search Optimization'",
        "domain": "youtube.com", "url": "https://youtube.com/watch?v=nOk-kX8FndI",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Video resource. Verified session.",
    },
    {
        "source_id": "S099", "name": "YouTube — 'AI SEO Course for Beginners: Complete AEO Tutorial'",
        "domain": "youtube.com", "url": "https://youtube.com/watch?v=uza9GX0E2mw",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Video resource. Verified session.",
    },
    {
        "source_id": "S100", "name": "YouTube — 'GEO/AEO Strategy — Content & Technical Optimizations'",
        "domain": "youtube.com", "url": "https://youtube.com/watch?v=FPAMixpThBM",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Video resource. Verified session.",
    },
    {
        "source_id": "S101", "name": "YouTube — 'A Complete Guide to AI Search Optimisation for 2026'",
        "domain": "youtube.com", "url": "https://youtube.com/watch?v=qa47-quPcS0",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Video resource. Verified session.",
    },
    {
        "source_id": "S102", "name": "YouTube — 'Google AEO/GEO Guide: How to Rank in AI Mode'",
        "domain": "youtube.com", "url": "https://youtube.com/watch?v=mwYfX2w3Y_I",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Video resource. Verified session.",
    },
    {
        "source_id": "S103", "name": "YouTube — 'A Complete Guide to AI SEO in 2026 (AEO, GEO, LLMO)'",
        "domain": "youtube.com", "url": "https://youtube.com/watch?v=e9ccLnRmeo0",
        "trust_tier": "T7", "source_type": "community",
        "verified": 1, "verified_date": "2026-07-28", "notes": "Video resource. Verified session.",
    },
    {
        "source_id": "S104", "name": "Ahrefs — Official YouTube Channel",
        "domain": "youtube.com", "url": "https://youtube.com/@AhrefsTV",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "Data-driven SEO/GEO video explainers.",
    },
    {
        "source_id": "S105", "name": "Google Search Central — Official YouTube Channel",
        "domain": "youtube.com", "url": "https://youtube.com/@GoogleSearchCentral",
        "trust_tier": "T1", "source_type": "official-platform-doc",
        "verified": 0, "verified_date": None, "notes": "Google's own SEO Office Hours.",
    },
    {
        "source_id": "S106", "name": "Search Engine Journal — Official YouTube Channel",
        "domain": "youtube.com", "url": "https://youtube.com/@SearchEngineJournal",
        "trust_tier": "T5", "source_type": "industry-media",
        "verified": 0, "verified_date": None, "notes": "SEJ official video content.",
    },
]


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def load_all_sources(conn: sqlite3.Connection, actor: str = "genesis-loader") -> int:
    """
    Insert all seed sources into the `sources` table.
    Idempotent — uses INSERT OR IGNORE so re-running is safe.
    Returns the number of rows inserted.
    """
    inserted = 0
    for src in SOURCES:
        existing = conn.execute(
            "SELECT source_id FROM sources WHERE source_id = ?", (src["source_id"],)
        ).fetchone()
        if existing:
            continue
        with write_as(conn, actor=actor, reason=f"genesis load: source {src['source_id']}"):
            conn.execute(
                "INSERT INTO sources "
                "(source_id, name, domain, url, trust_tier, source_type, "
                " verified, verified_date, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    src["source_id"], src["name"], src["domain"], src["url"],
                    src["trust_tier"], src["source_type"],
                    src["verified"], src.get("verified_date"), src.get("notes"),
                ),
            )
        inserted += 1
    return inserted


def get_sources_for_claim(conn: sqlite3.Connection, claim_id: str) -> list[dict]:
    """
    Returns all sources linked to a claim, ordered by trust tier (T1 first).
    Used by the Citation Transparency UI feature.
    """
    rows = conn.execute(
        """
        SELECT s.source_id, s.name, s.domain, s.url, s.trust_tier,
               s.source_type, s.verified, s.verified_date, s.notes,
               cs.primary_source, cs.note AS link_note
        FROM claim_sources cs
        JOIN sources s ON cs.source_id = s.source_id
        WHERE cs.claim_id = ?
        ORDER BY s.trust_tier ASC, cs.primary_source DESC
        """,
        (claim_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_ranked_sources(conn: sqlite3.Connection,
                       tier_filter: str | None = None) -> list[dict]:
    """
    Returns all sources ranked by trust tier.
    Optionally filter to a specific tier (e.g. 'T1').
    """
    if tier_filter:
        rows = conn.execute(
            "SELECT * FROM sources WHERE trust_tier = ? ORDER BY trust_tier, verified DESC",
            (tier_filter,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sources ORDER BY trust_tier, verified DESC"
        ).fetchall()
    return [dict(r) for r in rows]
