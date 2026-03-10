# Databricks AI/BI (Genie + Dashboards) vs Power BI

## Key Research Links
- [Dashboards Dead? Killed by Agents - Pawel Potasinski](https://www.linkedin.com/pulse/dashboards-dead-killed-agents-pawel-potasinski-dlkcf/)
- [Databricks Apps vs Power BI & Tableau - Xorbix](https://xorbix.com/insights/are-power-bi-and-tableau-obsolete-why-databricks-apps-is-the-future-of-enterprise-bi/)
- [ElanWave - Databricks Dashboards vs PowerBI](https://www.elanwave.com/blog/databricks-dashboards-vs-powerbi-understanding-the-differences)
- [Bridging BI Tools: AI/BI Dashboards for Power BI Practitioners - Data+AI Summit 2025](https://www.databricks.com/dataaisummit/session/bridging-bi-tools-deep-dive-aibi-dashboards-power-bi-practitioners)
- [Unified Advanced Analytics: Integrating Power BI and Databricks Genie](https://www.databricks.com/dataaisummit/session/unified-advanced-analytics-integrating-power-bi-and-databricks-genie)

## Databricks AI/BI: Two Components

### 1. AI/BI Dashboards (GA)
- Redesigned dashboarding experience for regular reporting
- No per-user licensing costs - consumption-based pricing only
- Pay for compute + storage, regardless of user count
- Native to the lakehouse - no data movement or copy
- Legacy dashboards sunset January 12, 2026

### 2. AI/BI Genie (GA)
- Conversational/natural language analytics interface
- Users ask data questions in plain English
- Feedback mechanisms for quality rating
- Benchmarking tools for accuracy evaluation
- Knowledge stores with curated semantic definitions
- Cost transparency via serverless SQL warehouse allocation
- Serverless compute model

## The "One Platform" Value Proposition

### Cost Argument
| Aspect | Databricks AI/BI | Power BI + Fabric |
|--------|-----------------|-------------------|
| Licensing | No per-user licensing | Power BI Pro: ~$10/user/mo, Premium: ~$20/user/mo |
| Compute | Consumption-based (serverless SQL) | Fabric capacity units (F SKUs) |
| Data movement | None - native to lakehouse | Requires data copy/import or DirectQuery |
| Governance | Unity Catalog (already in platform) | Purview + additional config |
| AI/NL queries | Genie (included) | Copilot for Power BI (requires M365 Copilot license ~$30/user/mo) |

### Strengths of "All Databricks"
- **Zero data movement** - dashboards query lakehouse directly
- **Single governance model** - Unity Catalog covers data + analytics
- **No additional licensing** - massive cost savings at scale
- **Genie for ad-hoc** - users self-serve without building dashboards
- **Unified security** - row/column-level security in one place

### When Power BI Still Wins
- **Visualization richness** - Power BI has more chart types, custom visuals marketplace
- **Enterprise adoption** - deeply embedded in Microsoft 365 ecosystem
- **Existing investment** - orgs already have Power BI skills and reports
- **Pixel-perfect reporting** - paginated reports for finance/compliance
- **Broad data connectivity** - 200+ connectors beyond just Databricks

## Potasinski's Article: Key Takeaways

**Thesis**: Dashboards aren't dead - they coexist with AI agents

- Most business users are "up-to-two-clicks users" who need insights delivered immediately
- Conversational BI (Genie) is better for **ad-hoc exploration**
- Dashboards are better for **standardized, shared, persistent insights**
- Neither Genie nor other agentic BI tools offer out-of-the-box persistence/sharing of findings
- **The future**: Conversational BI helps BI teams identify which dashboard improvements matter most
- Genie feeds insights BACK into traditional dashboards, not replaces them

## Wegmans Interview Angle

### Why This Matters for Wegmans
- Moving to enterprise data platform = deciding on BI strategy
- If they adopt Databricks lakehouse, AI/BI is already included
- Avoids dual-licensing (Databricks + Power BI/Fabric) costs
- Small team (5 architects) benefits from single-platform simplicity

### Smart Questions to Ask
1. "What BI tools are your business users currently using? Are you considering Databricks' native AI/BI capabilities as part of the platform strategy?"
2. "How are you thinking about the cost model - full Databricks stack including AI/BI vs. Databricks for data + Power BI for visualization?"
3. "Are your analysts comfortable with self-service, or do they need curated dashboards? That affects whether Genie or traditional dashboards are the right fit."

### Architecture Recommendation Framework
- **For standardized operational dashboards** (store performance, daily sales): AI/BI Dashboards
- **For ad-hoc business questions** (why did sales drop in store X?): Genie
- **For pixel-perfect financial/compliance reports**: Power BI Paginated Reports (keep Power BI for this niche)
- **For executive consumption**: Either works, but Genie is the differentiator
