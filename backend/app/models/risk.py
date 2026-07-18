"""
Guardian Risk Models

WebsiteSummary is the output contract of WebsiteAnalyzer and the input
website-side data for the Risk Engine's scoring in app/api/risk.py.
"""

from dataclasses import dataclass


# ==========================================================
# Website Summary (from Website Analyzer)
# ==========================================================

@dataclass
class WebsiteSummary:
    """
    Output from Website Analyzer.
    Input to Risk Engine.
    
    Fields are used by rule evaluator lambdas in risk_engine.py
    """

    website_score: int
    https: bool
    url_length: int
    suspicious_keywords: int
    special_characters: int
    uses_ip: bool
    suspicious_tld: bool
    domain_age_days: int
    redirect_count: int
    ssl_valid: bool
    brand_similarity: int
    virustotal_score: int
    safe_browsing: bool
    phishtank: bool
    suspicious: bool

    def to_dict(self) -> dict:
        return {
            "website_score": self.website_score,
            "https": self.https,
            "url_length": self.url_length,
            "suspicious_keywords": self.suspicious_keywords,
            "special_characters": self.special_characters,
            "uses_ip": self.uses_ip,
            "suspicious_tld": self.suspicious_tld,
            "domain_age_days": self.domain_age_days,
            "redirect_count": self.redirect_count,
            "ssl_valid": self.ssl_valid,
            "brand_similarity": self.brand_similarity,
            "virustotal_score": self.virustotal_score,
            "safe_browsing": self.safe_browsing,
            "phishtank": self.phishtank,
            "suspicious": self.suspicious
        }
