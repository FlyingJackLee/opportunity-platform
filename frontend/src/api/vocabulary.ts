/** Mirrors app/core/vocabulary.py's SourceType/OrganizationType StrEnums (and
 * app/models/event_filter_rule.py's FilterRuleType) -- kept in sync by hand
 * since there's no shared codegen between the two. */

export const SOURCE_TYPES = [
  { value: "GOV_WEB", label: "政府网站" },
  { value: "TENDER_SITE", label: "招标网站" },
  { value: "NEWS_SITE", label: "新闻网站" },
  { value: "OTHER", label: "其他" },
] as const;

export const ORGANIZATION_TYPES = [
  { value: "GOV", label: "政府部门" },
  { value: "SOE", label: "国企" },
  { value: "INSTITUTION", label: "事业单位" },
  { value: "OTHER", label: "其他" },
] as const;

// Event.region/industry are validated server-side against these exact
// values (app/core/vocabulary.py's Region/Industry StrEnums) -- a free-text
// input would just 422. Extend both lists here in lockstep whenever a new
// value is added there.
export const REGIONS = ["重庆市"] as const;

export const INDUSTRIES = ["住建", "发改", "经信", "数据", "国资"] as const;
