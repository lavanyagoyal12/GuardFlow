"""
Guardian Website Analyzer

Collects website intelligence.

This module NEVER decides fraud.

It only extracts website security features
for the Risk Engine.
"""

from urllib.parse import urlparse
import ipaddress
import re

from app.models.risk import WebsiteSummary


PHISHING_WORDS = [
    "login",
    "signin",
    "verify",
    "verification",
    "secure",
    "security",
    "account",
    "update",
    "confirm",
    "payment",
    "wallet",
    "bank",
    "credit",
    "debit",
    "otp",
    "password",
    "recover",
    "unlock",
    "kyc",
    "gift",
    "reward",
    "prize",
    "bonus",
    "cashback",
    "refund",
    "invoice",
    "support",
    "customer-care"
]


SUSPICIOUS_TLDS = [
    "xyz",
    "top",
    "click",
    "zip",
    "work",
    "country",
    "live",
    "shop",
    "site",
    "online",
    "gq",
    "tk",
    "cf",
    "ml",
    "ga"
]


class WebsiteAnalyzer:

    def analyze(self, url: str) -> WebsiteSummary:

        # Android's accessibility-scan payloads often report a bare domain
        # ("amazon.in") with no scheme. urlparse() treats an unprefixed
        # string as a relative path, not a netloc, so hostname/tld end up
        # empty and every hostname-based check below silently no-ops.
        # Parse a scheme-normalized copy for hostname/tld extraction while
        # keeping length/keyword/special-char checks against the original
        # string exactly as reported.
        parse_target = url if "://" in url else f"//{url}"
        parsed = urlparse(parse_target)
        hostname = (parsed.hostname or "").lower()
        scheme = urlparse(url).scheme
        score = 0

        # -------------------------
        # HTTPS
        # -------------------------

        https = scheme == "https"
        if not https:
            score += 20

        # -------------------------
        # URL Length
        # -------------------------

        url_length = len(url)
        if url_length > 75:
            score += 10

        # -------------------------
        # Phishing Keywords
        # -------------------------

        keyword_count = sum(
            word in url.lower()
            for word in PHISHING_WORDS
        )
        score += keyword_count * 5

        # -------------------------
        # Special Characters
        # -------------------------

        special_chars = len(
            re.findall(
                r"[@#$%^&*=+]",
                url
            )
        )
        if special_chars > 10:
            score += 10

        # -------------------------
        # IP Address
        # -------------------------

        try:
            ipaddress.ip_address(hostname)
            uses_ip = True
            score += 20
        except:
            uses_ip = False

        # -------------------------
        # TLD
        # -------------------------

        tld = hostname.split(".")[-1]
        suspicious_tld = tld in SUSPICIOUS_TLDS
        if suspicious_tld:
            score += 10

        # -------------------------
        # Placeholder Values
        # These will later be replaced with real APIs
        # -------------------------

        domain_age = 365
        redirects = 0
        ssl_valid = True
        brand_similarity = 0
        virustotal_score = 0
        safe_browsing = True
        phishtank = False

        score = min(score, 100)

        return WebsiteSummary(
            website_score=score,
            https=https,
            url_length=url_length,
            suspicious_keywords=keyword_count,
            special_characters=special_chars,
            uses_ip=uses_ip,
            suspicious_tld=suspicious_tld,
            domain_age_days=domain_age,
            redirect_count=redirects,
            ssl_valid=ssl_valid,
            brand_similarity=brand_similarity,
            virustotal_score=virustotal_score,
            safe_browsing=safe_browsing,
            phishtank=phishtank,
            suspicious=score >= 60
        )