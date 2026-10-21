"""
Wix Lead Gen Tool - Online Version (Non-programmer friendly)
============================================================
Supports Google Gemini (recommended for you) + optional SerpAPI
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
from typing import Optional, Dict, List

# -------------------------------------------------
# PAGE SETUP
# -------------------------------------------------
st.set_page_config(
    page_title="Wix Lead Gen Tool",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Wix Lead Generation Tool")
st.caption("Enter City + Niche → Find Wix websites → Audit → Get ready-to-send pitches")

# -------------------------------------------------
# SIDEBAR - SIMPLE SETTINGS
# -------------------------------------------------
with st.sidebar:
    st.header("Your Settings")
    
    city = st.text_input("City", placeholder="e.g. Austin")
    niche = st.text_input("Niche", placeholder="e.g. dentist, restaurant, coach")
    
    st.divider()
    your_name = st.text_input("Your Name", value="Alex")
    agency_name = st.text_input("Agency Name", value="Your Wix Agency")
    
    st.divider()
    st.subheader("API Keys (required for full power)")
    
    gemini_key = st.text_input(
        "Gemini API Key (Recommended)",
        type="password",
        help="Get free key from https://aistudio.google.com/apikey"
    )
    
    serpapi_key = st.text_input(
        "SerpAPI Key (for finding businesses)",
        type="password",
        help="Free 250 searches/month → https://serpapi.com"
    )
    
    max_results = st.slider("How many websites to check", 5, 15, 8)
    
    run_button = st.button("🚀 Find Wix Leads", type="primary", use_container_width=True)

# -------------------------------------------------
# WIX DETECTION
# -------------------------------------------------
WIX_SIGNALS = [
    "static.wixstatic.com",
    "parastorage.com",
    "_wixCIDX",
    "Wix.com Website Builder",
    "viewer-app.wix.com",
    "wixstatic.com",
]

def is_wix_site(html: str) -> bool:
    if not html:
        return False
    lower = html.lower()
    return any(s.lower() in lower for s in WIX_SIGNALS)

# -------------------------------------------------
# FETCH PAGE
# -------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_html(url: str) -> Optional[str]:
    try:
        if not url.startswith("http"):
            url = "https://" + url
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        return None
    return None

# -------------------------------------------------
# BASIC AUDIT
# -------------------------------------------------
def basic_audit(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    findings = []
    score = 100

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not title or len(title) < 10:
        findings.append("Missing or very weak page title")
        score -= 15
    elif len(title) > 70:
        findings.append("Page title is too long")
        score -= 5

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if not meta_desc or not meta_desc.get("content", "").strip():
        findings.append("No meta description (bad for Google)")
        score -= 12

    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        findings.append("No clear H1 heading on homepage")
        score -= 10

    text = soup.get_text(" ", strip=True).lower()
    cta_words = ["book", "schedule", "contact", "call now", "get quote", 
                 "free consultation", "request", "get started", "learn more"]
    if not any(w in text for w in cta_words):
        findings.append("Weak or missing clear call-to-action")
        score -= 12

    if len(text) < 400:
        findings.append("Homepage has very little content")
        score -= 10

    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        findings.append("Missing mobile viewport tag")
        score -= 8

    if not findings:
        findings.append("No major technical issues found – design & conversion can still be improved")

    return {
        "findings": findings,
        "score": max(0, min(100, score)),
        "title": title,
        "url": url
    }

# -------------------------------------------------
# PITCH GENERATION (Gemini preferred)
# -------------------------------------------------
def generate_pitch_gemini(
    business_name: str,
    url: str,
    city: str,
    niche: str,
    findings: List[str],
    your_name: str,
    agency_name: str,
    api_key: str
) -> str:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        findings_text = "\n".join(f"- {f}" for f in findings)

        prompt = f"""You are an expert Wix website designer writing a short cold outreach email.

Business name: {business_name}
Website: {url}
City: {city}
Niche: {niche}

Website audit findings:
{findings_text}

Write a short, professional, friendly email (maximum 110 words).

Rules:
- Start with: Hi there,
- Say you looked at their Wix website
- Mention 2-3 specific issues from the audit in natural language
- Say you specialize in modern high-converting Wix sites for {niche} businesses
- End with this soft question: Would you be open to me sending a fresh homepage overview?
- Close with: Best regards, then the name and agency
- No pressure, no asking for a call, keep it email-friendly
- Do not invent problems that are not in the findings list
"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return generate_fallback_pitch(business_name, url, city, niche, findings, your_name, agency_name)

def generate_fallback_pitch(
    business_name: str,
    url: str,
    city: str,
    niche: str,
    findings: List[str],
    your_name: str,
    agency_name: str
) -> str:
    issues = findings[:3]
    return f"""Hi there,

I came across {business_name}'s Wix site while looking at {niche} businesses in {city}.

A few things stood out that are likely affecting results:
{chr(10).join('• ' + f for f in issues)}

I specialize in modern, high-converting Wix redesigns for {niche} businesses.

Would you be open to me sending a fresh homepage overview (no obligation) so you can see how it could look and convert better?

Best regards,
{your_name}
{agency_name}"""

# -------------------------------------------------
# SEARCH WITH SERPAPI
# -------------------------------------------------
def search_businesses(city: str, niche: str, api_key: str, num: int = 10) -> List[Dict]:
    try:
        params = {
            "engine": "google",
            "q": f"{niche} in {city}",
            "api_key": api_key,
            "num": num,
            "hl": "en"
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=20)
        data = resp.json()
        results = []
        for item in data.get("organic_results", [])[:num]:
            link = item.get("link")
            title = item.get("title", "")
            if link:
                results.append({
                    "name": title.split(" - ")[0].split(" | ")[0].strip(),
                    "website": link
                })
        return results
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

# -------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------
if run_button:
    if not city or not niche:
        st.error("Please enter both City and Niche")
        st.stop()

    if not serpapi_key:
        st.warning("⚠️ Please add a SerpAPI key in the sidebar to find real businesses. (Free tier available at serpapi.com)")
        st.info("You can still test the audit + pitch by using the manual test below.")
        
        st.subheader("Quick Test Any Website")
        test_url = st.text_input("Paste any website URL to audit")
        if test_url and st.button("Audit & Write Pitch"):
            with st.spinner("Analyzing..."):
                html = fetch_html(test_url)
                if not html:
                    st.error("Could not open this website")
                elif not is_wix_site(html):
                    st.warning("This does not look like a Wix website.")
                else:
                    audit = basic_audit(html, test_url)
                    st.success("This is a Wix site!")
                    st.write("**Audit findings:**")
                    for f in audit["findings"]:
                        st.write(f"• {f}")
                    
                    if gemini_key:
                        pitch = generate_pitch_gemini(
                            "this business", test_url, city, niche,
                            audit["findings"], your_name, agency_name, gemini_key
                        )
                    else:
                        pitch = generate_fallback_pitch(
                            "this business", test_url, city, niche,
                            audit["findings"], your_name, agency_name
                        )
                    
                    st.subheader("Your Ready Pitch")
                    st.code(pitch, language=None)
        st.stop()

    # Real search
    with st.spinner("Searching for businesses..."):
        leads = search_businesses(city, niche, serpapi_key, max_results)

    if not leads:
        st.error("No results found. Try a different city or niche.")
        st.stop()

    st.success(f"Found {len(leads)} websites. Now checking which ones are Wix...")

    wix_leads = []
    progress = st.progress(0)
    status = st.empty()

    for i, lead in enumerate(leads):
        status.text(f"Checking: {lead['name']} ({i+1}/{len(leads)})")
        progress.progress((i + 1) / len(leads))

        html = fetch_html(lead["website"])
        if html and is_wix_site(html):
            audit = basic_audit(html, lead["website"])

            if gemini_key:
                pitch = generate_pitch_gemini(
                    lead["name"], lead["website"], city, niche,
                    audit["findings"], your_name, agency_name, gemini_key
                )
            else:
                pitch = generate_fallback_pitch(
                    lead["name"], lead["website"], city, niche,
                    audit["findings"], your_name, agency_name
                )

            wix_leads.append({
                "name": lead["name"],
                "website": lead["website"],
                "score": audit["score"],
                "findings": audit["findings"],
                "pitch": pitch
            })

        time.sleep(0.7)

    progress.empty()
    status.empty()

    if not wix_leads:
        st.warning("No Wix websites found this time. Try another city or increase the number of results.")
    else:
        st.success(f"✅ Found {len(wix_leads)} Wix websites ready for you")

        for idx, lead in enumerate(wix_leads):
            with st.expander(f"📌 {lead['name']}   |   Score: {lead['score']}/100", expanded=(idx == 0)):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown(f"**Website:** [{lead['website']}]({lead['website']})")
                    st.markdown("**Problems found:**")
                    for f in lead["findings"]:
                        st.write(f"• {f}")

                with col2:
                    st.markdown("**Ready-to-send Pitch:**")
                    st.code(lead["pitch"], language=None)
                    st.download_button(
                        "⬇️ Download this pitch",
                        data=lead["pitch"],
                        file_name=f"pitch_{idx+1}.txt",
                        mime="text/plain",
                        key=f"dl_{idx}"
                    )

st.divider()
st.markdown("""
**How to get the free keys:**
1. **Gemini API Key** → Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API key
2. **SerpAPI Key** → Go to [serpapi.com](https://serpapi.com) → Sign up (250 free searches every month)
""")
