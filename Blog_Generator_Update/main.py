import streamlit as st
from groq import Groq
import markdown
import re
import html
import requests
import random
import os


def get_secret(name):
    return st.secrets.get(name) or os.getenv(name, "")


GROQ_API_KEY = get_secret("GROQ_API_KEY")
PEXELS_API_KEY = get_secret("PEXELS_API_KEY")
FALLBACK_IMAGE_URL = "https://images.pexels.com/photos/11035380/pexels-photo-11035380.jpeg"
IMAGE_QUERY_VARIANTS = [
    "high quality editorial photography",
    "professional business technology photo",
    "modern technical concept photo",
    "clean corporate tech image",
    "realistic business interface visual"
]

@st.cache_data(show_spinner=False)
def get_image_urls(query, page=1):
    if not PEXELS_API_KEY:
        return [FALLBACK_IMAGE_URL]

    try:
        url = "https://api.pexels.com/v1/search"
        headers = {
            "Authorization": PEXELS_API_KEY
        }
        params = {
            "query": query,
            "per_page": 10,
            "page": page,
            "orientation": "landscape",
            "size": "large"
        }
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if data.get("photos"):
            image_urls = [
                image["src"].get("large2x") or image["src"].get("large") or image["src"].get("original")
                for image in data["photos"]
                if image.get("src")
            ]
            if any(image_urls):
                return [image_url for image_url in image_urls if image_url]
    except Exception:
        pass

    return [FALLBACK_IMAGE_URL]


def get_image_url(query, used_urls=None):
    used_urls = used_urls or set()
    image_urls = get_image_urls(query, page=random.randint(1, 3))
    available_urls = [url for url in image_urls if url not in used_urls]
    if available_urls:
        return random.choice(available_urls)

    # If all results are already used, try another page
    for page in random.sample(range(1, 4), 3):
        image_urls = get_image_urls(query, page=page)
        available_urls = [url for url in image_urls if url not in used_urls]
        if available_urls:
            return random.choice(available_urls)

    return random.choice(image_urls)

def clean_generated_blog(content):

    # Remove ```html
    content = re.sub(r"```html", "", content)

    # Remove ```markdown
    content = re.sub(r"```markdown", "", content)

    # Remove closing ```
    content = re.sub(r"```", "", content)

    return content.strip()
def fix_takeaways_format(content):
    pattern = re.compile(
        r"(?ims)^(?:##\s*)?(?:\*\*)?Key Takeaways(?:\*\*)?\s*:?\s*(.*?)(?=^##\s|\Z)"
    )

    def repl(match):
        section = match.group(1).strip()
        if not section:
            return "## Key Takeaways\n\n"

        bullet_lines = re.findall(
            r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+?)\s*$",
            section
        )
        inline_bullets = re.findall(
            r"(?:^|\s)\*\s+(.+?)(?=\s+\*\s+|$)",
            section.replace("\n", " ")
        )
        bullets = inline_bullets if len(inline_bullets) > len(bullet_lines) else bullet_lines
        if not bullets:
            bullets = [
                item.strip()
                for item in re.split(r"\s*[;|]\s*|\s+(?=\d+[.)]\s+)", section)
                if item.strip()
            ]

        if not bullets:
            return match.group(0)

        normalized_bullets = []
        for bullet in bullets:
            bullet = re.sub(r"^\d+[.)]\s*", "", bullet).strip(" -*\n\t")
            if bullet:
                normalized_bullets.append(f"- {bullet}")

        return "## Key Takeaways\n\n" + "\n".join(normalized_bullets) + "\n\n"

    return pattern.sub(repl, content)
def split_faq_section(markdown_text):
    faq_heading = re.search(
        r"(?im)^#{2,3}\s*(?:Frequently Asked Questions|FAQs Section|FAQ Section|FAQs|FAQ)(?:\s*\(FAQs?\))?\s*$",
        markdown_text
    )
    if not faq_heading:
        return markdown_text, []

    main_body = markdown_text[:faq_heading.start()].strip()
    faq_text = markdown_text[faq_heading.end():].strip()
    faq_text = re.split(
        r"(?im)^##\s+(?!(?:Frequently Asked Questions|FAQs Section|FAQ Section|FAQs|FAQ)(?:\s*\(FAQs?\))?\s*$).+$",
        faq_text,
        maxsplit=1
    )[0].strip()

    h3_faqs = re.findall(
        r"(?ms)^###\s+(.+?)\s*\n+(.+?)(?=^###\s+|\Z)",
        faq_text
    )
    h3_faqs = [
        (question.strip().strip("*"), answer.strip())
        for question, answer in h3_faqs
        if question.strip() and answer.strip()
    ]
    if h3_faqs:
        return main_body, h3_faqs

    question_pattern = re.compile(
        r"""
        ^\s*
        (?:[-*]\s+)?
        (?:\#{3,6}\s*)?
        (?:\d+[\.\)]\s*)?
        (?:\*\*)?
        (?:
            Q(?:uestion)?\s*\d*\s*[\.\):\-]\s*
        )?
        (.+?)
        (?:\*\*)?
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE
    )
    faqs = []
    current_question = None
    current_answer = []

    for line in faq_text.splitlines():
        clean_line = line.strip()
        match = question_pattern.match(clean_line)
        possible_question = False
        question_text = ""

        if match:
            question_text = match.group(1).strip()
            question_text = question_text.strip("*").strip()
            question_text = question_text.rstrip(":").strip()
            possible_question = (
                "?" in question_text
                or clean_line.startswith("#")
                or re.match(r"^(?:[-*]\s*)?(?:\d+[\.\)]\s*)?(?:\*\*)?Q(?:uestion)?\s*\d*\s*[\.\):\-]", clean_line, re.IGNORECASE)
            )

        if possible_question:
            if current_question:
                answer = "\n".join(current_answer).strip()
                faqs.append((current_question, answer))
            current_question = question_text
            current_answer = []
        elif current_question:
            current_answer.append(re.sub(r"^(?:A|Answer)\s*[:\-]\s*", "", line, flags=re.IGNORECASE))

    if current_question:
        answer = "\n".join(current_answer).strip()
        faqs.append((current_question, answer))

    faqs = [
        (question, answer)
        for question, answer in faqs
        if not re.fullmatch(r"(?i)(?:question\s*)?\d+\?", question.strip())
        and answer.strip()
        and not re.fullmatch(r"(?i)answer\s+text\.?", answer.strip())
    ]

    if not faqs:
        return markdown_text, []

    return main_body, faqs


def faq_dropdown_html(faqs):
    if not faqs:
        return ""

    items = []
    for question, answer in faqs:
        answer_html = markdown.markdown(answer.strip()) if answer.strip() else "<p>No answer generated.</p>"
        items.append(
            f'<details class="faq-item">'
            f'<summary>{html.escape(question)}</summary>'
            f'<div class="faq-answer">{answer_html}</div>'
            f'</details>'
        )

    return (
        '<div class="faq-section">'
        '<h2>Frequently Asked Questions</h2>'
        + "".join(items) +
        '</div>'
    )


def blog_preview_html(markdown_text, cursor=""):
    main_body, faqs = split_faq_section(markdown_text)
    return markdown.markdown(main_body) + faq_dropdown_html(faqs) + cursor


def replace_image_tags(content, used_urls=None):
    used_urls = set(used_urls or [])

    def repl(match):
        prompt = re.sub(r"\s+", " ", match.group(1)).strip()
        query = optimize_image_query(prompt)
        url = get_image_url(query, used_urls)
        used_urls.add(url)
        caption = image_caption(prompt)
        safe_url = html.escape(url, quote=True)
        safe_prompt = html.escape(prompt, quote=True)
        safe_caption = html.escape(caption)

        return f"""
<figure class="blog-figure">
<img src="{safe_url}" loading="lazy" alt="{safe_prompt}">
<figcaption>{safe_caption}</figcaption>
</figure>
"""

    return re.sub(r"\[IMAGE:\s*(.*?)\]", repl, content, flags=re.IGNORECASE | re.DOTALL)


def optimize_image_query(prompt):
    prompt = re.sub(r"\b(?:diagram|placeholder|image of|illustration about)\b", "", prompt, flags=re.IGNORECASE)
    prompt = re.sub(r"\s+", " ", prompt).strip(" ,.-")
    if not prompt:
        return "high quality technical concept image, modern digital interface"

    if re.search(
        r"\b(?:system log|error log|server log|application log|event log|console output|stack trace|terminal output|debug log|log file|log entry)\b",
        prompt,
        flags=re.IGNORECASE,
    ):
        return f"{prompt}, computer interface screenshot, terminal window, high resolution"

    if re.search(r"\b(?:diagram|flowchart|chart|graph|infographic|mockup|wireframe|architecture|architecture diagram)\b", prompt, flags=re.IGNORECASE):
        return f"{prompt}, clear technical diagram, infographic style"

    if re.search(r"\b(?:software|platform|cloud|ai|machine learning|data science|backend|frontend|devops|security|network|cybersecurity|code|api|database)\b", prompt, flags=re.IGNORECASE):
        return f"{prompt}, modern technical concept art, digital interface"

    style = random.choice(IMAGE_QUERY_VARIANTS)
    return f"{prompt}, {style}"


def image_caption(prompt):
    prompt = re.sub(r"^(?:detailed|high quality)\s+", "", prompt, flags=re.IGNORECASE)
    prompt = re.sub(r"\s+", " ", prompt).strip(" .")
    return prompt[:1].upper() + prompt[1:] if prompt else "Relevant blog image"


def section_image_prompt(heading, section):
    topic_terms = re.sub(r"\s+", " ", re.sub(r"[#*_`>\[\]]", "", section)).strip()
    topic_terms = " ".join(topic_terms.split()[:18])
    heading = heading.strip()
    query_subject = f"{heading} {topic_terms}".strip()
    if not query_subject:
        query_subject = f"technical illustration for {heading}"
    return (
        f"realistic editorial photography about {query_subject}; "
        f"visual context: {query_subject}"
    )


def auto_insert_section_images(content):
    section_pattern = re.compile(r"(?ms)^##\s+(.+?)\s*\n(.*?)(?=^##\s+|\Z)")
    content_section_index = 0

    def repl(match):
        nonlocal content_section_index
        heading = match.group(1).strip()
        body = match.group(2).rstrip()
        section = match.group(0)
        if re.search(r"\[IMAGE:\s*.*?\]", section, flags=re.IGNORECASE | re.DOTALL):
            content_section_index += 1
            return section.rstrip() + "\n\n"
        if re.fullmatch(r"(?i)frequently asked questions|faqs?|faq section|key takeaways", heading):
            return section.rstrip() + "\n\n"

        content_section_index += 1
        should_add_image = content_section_index <= 2 or content_section_index % 2 == 0
        if not should_add_image:
            return section.rstrip() + "\n\n"

        prompt = section_image_prompt(heading, body)
        if content_section_index % 2 == 0:
            first_block = re.match(r"(?s)(.+?\n\s*\n)(.+)", body)
            if first_block:
                before_image, after_image = first_block.groups()
                return (
                    f"## {heading}\n{before_image}\n"
                    f"[IMAGE: {prompt}]\n\n{after_image.rstrip()}\n\n"
                )

        return f"## {heading}\n{body}\n\n[IMAGE: {prompt}]\n\n"

    return section_pattern.sub(repl, content)


def sectionize_blog_html(content):
    blocks = re.split(r"(?=<h2(?:\s|>))", content)
    article_parts = []
    intro = blocks[0].strip()
    if intro:
        article_parts.append(f'<section class="article-intro">{intro}</section>')

    visual_section_index = 0
    special_headings = {"key takeaways", "frequently asked questions", "faqs", "faq section"}

    for block in blocks[1:]:
        clean_block = block.strip()
        if not clean_block:
            continue

        heading_match = re.match(r"(?is)<h2[^>]*>(.*?)</h2>", clean_block)
        heading_text = ""
        if heading_match:
            heading_text = re.sub(r"<[^>]+>", "", heading_match.group(1))
            heading_text = html.unescape(heading_text).strip().lower()

        classes = ["article-section", "flow-media"]
        has_figure = '<figure class="blog-figure">' in clean_block
        if has_figure and heading_text not in special_headings:
            classes = ["article-section"]
            if visual_section_index % 2 == 0:
                classes.extend(["split-media", "media-right"])
            else:
                classes.append("flow-media")
            if visual_section_index % 4 == 2:
                classes[-1] = "media-left"
            visual_section_index += 1

        article_parts.append(f'<section class="{" ".join(classes)}">{clean_block}</section>')

    return "".join(article_parts)


st.set_page_config(
    page_title="AI Blog Generator",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
<style>

header[data-testid="stHeader"] {
    background: transparent;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent;
}

/* App background */
.stApp {
    background-color: #f0f2f7 !important;
}

/* ---- SIDEBAR ---- */
/* Sidebar toggle button fix */
button[kind="header"] {
    background: transparent !important;
    color: #1a1a2e !important;
    border: none !important;
    box-shadow: none !important;
    top: 12px !important;
    left: 12px !important;
    z-index: 999999 !important;
}

button[kind="header"]:hover {
    background: transparent !important;
}
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e5e7eb !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 24px 18px !important;
}

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    background-color: #fafafa !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    color: #1a1a2e !important;
}
[data-testid="stSidebar"] .stTextInput input:focus,
[data-testid="stSidebar"] .stTextArea textarea:focus {
    border-color: #6C63FF !important;
    background: #fff !important;
    box-shadow: 0 0 0 2px rgba(108,99,255,0.08) !important;
}

[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #fafafa !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}

[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stTextArea label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stCheckbox label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #1a1a2e !important;
}

/* Checkbox color */
[data-testid="stSidebar"] .stCheckbox label[data-baseweb="checkbox"] {
    background-color: transparent !important;
}

[data-testid="stSidebar"] .stCheckbox label[data-baseweb="checkbox"] > div,
[data-testid="stSidebar"] .stCheckbox label[data-baseweb="checkbox"] > span {
    background-color: transparent !important;
}

[data-testid="stSidebar"] .stCheckbox label[data-baseweb="checkbox"] input[type="checkbox"] {
    accent-color: #0B0201 !important;
}

[data-testid="stSidebar"] .stCheckbox label[data-baseweb="checkbox"]:has(input[type="checkbox"]:checked) > span:first-child {
    background-color: #0B0201 !important;
    border-color: #0B0201 !important;
}

[data-testid="stSidebar"] .stCheckbox label[data-baseweb="checkbox"] > span:first-child {
    border-color: #0B0201 !important;
}

[data-testid="stSidebar"] .stCheckbox label[data-baseweb="checkbox"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
}

/* Generate button */
[data-testid="stSidebar"] .stButton > button {
    background: #402315 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    height: 52px !important;
    width: 100% !important;
    box-shadow: #522D17 !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #522D17 !important;
    box-shadow: #522D17!important;
}

/* ---- MAIN AREA ---- */
.block-container {
    padding: 28px 32px !important;
    max-width: 100% !important;
}

/* Card */
.card {
    background: #ffffff;
    border-radius: 14px;
    padding: 24px 26px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    margin-bottom: 22px;
}
.card-title {
    font-size: 18px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 6px;
}
.card-underline {
    height: 3px;
    width: 36px;
    background: #603A28;
    border-radius: 2px;
    margin-bottom: 18px;
}

/* Blog output */
.blog-output {
    background: #fff;
    padding: 4px 8px;
    border-radius: 8px;
    color: #1a1a2e;
    font-size: 14px;
    line-height: 1.8;
    max-height: 420px;
    overflow-y: auto;
}
.blog-output h1 { font-size: 20px; margin-bottom: 12px; color: #1a1a2e; }
.blog-output h2 { font-size: 16px; margin: 16px 0 8px; color: #2d2d5e; }
.blog-output h3 { font-size: 14px; margin: 12px 0 6px; color: #4338ca; }
.blog-output p  { margin-bottom: 10px; }
.faq-section {
    margin-top: 18px;
}
.faq-section h2 {
    color: #2d2d5e;
    font-size: 16px;
    margin-bottom: 12px;
}
.faq-item {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin-bottom: 10px;
    overflow: hidden;
    background: #ffffff;
}
.faq-item summary {
    cursor: pointer;
    list-style: none;
    padding: 13px 14px;
    font-size: 14px;
    font-weight: 600;
    color: #1a1a2e;
    background: #fafafa;
}
.faq-item summary::-webkit-details-marker {
    display: none;
}
.faq-item summary::after {
    content: "+";
    float: right;
    color: #0B0201;
    font-size: 18px;
    line-height: 1;
}
.faq-item[open] summary::after {
    content: "-";
}
.faq-answer {
    padding: 12px 14px 14px;
    border-top: 1px solid #e5e7eb;
}

/* Empty state */
.preview-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    color: #9ca3af;
    text-align: center;
    gap: 12px;
}
.preview-empty p    { font-size: 15px; font-weight: 500; color: #6b7280; }
.preview-empty span { font-size: 13px; color: #9ca3af; }

/* Metrics grid */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
}
.metric-card {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 18px 16px;
}
.metric-icon-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
}
.metric-icon {
    width: 30px;
    height: 30px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
}
.metric-label { font-size: 12px; color: #6b7280; font-weight: 500; line-height: 1.3; }
.metric-value { font-size: 28px; font-weight: 700; color: #1a1a2e; line-height: 1; }
.metric-unit  { font-size: 12px; color: #9ca3af; margin-top: 3px; }

/* HTML code block */
.html-code {
    background: #f8f9fa;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #374151;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
}

/* Download info */
.download-info {
    background: #eff6ff;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    color: #3b82f6;
    margin-bottom: 14px;
}

/* Download buttons */
.stDownloadButton > button {
    background: white !important;
    color: #1a1a2e !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    background: #f5f5f5 !important;
}

/* Tip box */
.tip-box {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
    color: #92400e;
    margin-top: 12px;
    line-height: 1.5;
}

/* Footer */
.footer-text {
    text-align: center;
    font-size: 12px;
    color: #9ca3af;
    margin-top: 8px;
    padding-bottom: 16px;
}
.footer-text a { color: #6C63FF; text-decoration: none; }
[data-testid="stTextInput"] small {
    display: none !important;
}
.featured-image img {
    width: 100%;
    border-radius: 14px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}

.blog-output img {
    width: 100%;
    border-radius: 12px;
}
.blog-output .article-section {
    margin-top: 18px;
}
.blog-output .article-section.split-media {
    display: flow-root;
}
.blog-output .article-section.split-media > h2 {
    margin-top: 0;
}
.blog-output .article-section.split-media > .blog-figure {
    float: right;
    margin: 2px 0 14px 18px;
    width: min(42%, 360px);
}
.blog-output .article-section.media-left > .blog-figure {
    float: left;
    margin: 2px 18px 14px 0;
}
.blog-output .blog-figure {
    margin: 16px 0;
}
.blog-output .blog-figure figcaption {
    color: #6b7280;
    font-size: 12px;
    font-style: italic;
    margin-top: 6px;
    text-align: center;
}
@media (max-width: 720px) {
    .blog-output .article-section.split-media {
        display: block;
    }
    .blog-output .article-section.split-media > .blog-figure {
        float: none;
        width: 100%;
        margin: 16px 0;
    }
}
</style>
""", unsafe_allow_html=True)


with st.sidebar:

    st.markdown("##  AI Blog Generator")
    st.caption("Create SEO optimized blogs in seconds.")
    st.divider()

    st.markdown("###  Blog Input")

    topic = st.text_input(
        "Blog Topic",
        placeholder="Example: Digital Marketing Strategies"
    )

    keyword = st.text_input(
        "Primary SEO Keyword",
        placeholder="Example: best digital marketing strategies"
    )

    secondary_keywords = st.text_input(
        "Secondary Keywords (comma separated)",
        placeholder="Example: online marketing, SEO tips, brand growth"
    )

    audience = st.selectbox(
        "Target Audience",
        [
            "General Audience",
            "Students",
            "Developers",
            "Businesses"
        ]
    )

    tone = st.selectbox(
        "Writing Tone",
        [
            "Professional",
            "Marketing",
            "Friendly",
            "Technical",
            "Conversational"
        ]
    )

    word_count = st.slider(
        "Target Word Count",
        min_value=300,
        max_value=3000,
        value=1000,
        step=100
    )

    st.divider()

    st.markdown("### SEO Settings")

    generate_faq = st.checkbox("Generate FAQ Section", value=True)
    generate_meta = st.checkbox("Auto-generate Meta Description", value=True)
    add_cta = st.checkbox("Add Call-To-Action", value=True)
    add_key_takeaways = st.checkbox("Add Key Takeaways Box", value=True)

    meta_description = ""
    if not generate_meta:
        meta_description = st.text_area(
            "Meta Description",
            placeholder="Short description for search engines..."
        )

    readability = st.selectbox(
        "Readability Level",
        [
            "Beginner",
            "Intermediate",
            "Expert"
        ]
    )

    keyword_usage = st.selectbox(
        "Keyword Density",
        [
            "Low (1–2%)",
            "Medium (2–3%)",
            "High (3–4%)"
        ]
    )

    num_sections = st.slider(
        "Number of Main Sections",
        min_value=3,
        max_value=8,
        value=5
    )

    st.divider()

    generate_blog = st.button(
        " Generate Blog",
        use_container_width=True
    )

    st.markdown(
        '<div class="tip-box"> <strong>Tip:</strong> Use a specific keyword and audience to get better results!</div>',
        unsafe_allow_html=True
    )


preview_placeholder  = st.empty()
metrics_placeholder  = st.empty()
html_placeholder     = st.empty()
download_placeholder = st.empty()

with preview_placeholder.container():
    st.markdown("""
    <div class="card">
        <div class="card-title"> Generated Blog Preview</div>
        <div class="card-underline"></div>
        <div class="preview-empty">
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none"
                 stroke="#d1d5db" stroke-width="1.2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <p>Your generated blog will appear here...</p>
            <span>Fill the inputs and click "Generate Blog" to get started.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with metrics_placeholder.container():
    st.markdown("""
    <div class="card">
        <div class="card-title"> SEO Summary</div>
        <div class="card-underline"></div>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-icon-row">
                    <div class="metric-icon" style="background:#eff6ff"></div>
                    <span class="metric-label">Word Count</span>
                </div>
                <div class="metric-value">0</div>
                <div class="metric-unit">words</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon-row">
                    <div class="metric-icon" style="background:#f0fdf4"></div>
                    <span class="metric-label">Estimated Read Time</span>
                </div>
                <div class="metric-value">0</div>
                <div class="metric-unit">min</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon-row">
                    <div class="metric-icon" style="background:#fff7ed"></div>
                    <span class="metric-label">Keyword Density</span>
                </div>
                <div class="metric-value">0%</div>
                <div class="metric-unit">&nbsp;</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon-row">
                    <div class="metric-icon" style="background:#faf5ff"></div>
                    <span class="metric-label">FAQ Count</span>
                </div>
                <div class="metric-value">0</div>
                <div class="metric-unit">&nbsp;</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with html_placeholder.container():
    st.markdown("""
    <div class="card">
        <div class="card-title"> Generated HTML Preview</div>
        <div class="card-underline"></div>
        <div class="html-code">&lt;html&gt;
    &lt;body&gt;
        &lt;h1&gt;Your HTML content will appear here...&lt;/h1&gt;
    &lt;/body&gt;
&lt;/html&gt;</div>
    </div>
    """, unsafe_allow_html=True)

with download_placeholder.container():
    st.markdown("""
    <div class="card">
        <div class="card-title"> Download HTML</div>
        <div class="card-underline"></div>
        <div class="download-info">After generating the blog, you can download it as an HTML file.</div>
    </div>
    """, unsafe_allow_html=True)

if generate_blog:

    if not topic.strip() or not keyword.strip():
        st.warning("Please enter both a Blog Topic and Primary SEO Keyword.")
        st.stop()

    # Prompt helpers (your original)
    readability_map = {
        "Beginner":     "Use simple language and explain concepts clearly.",
        "Intermediate": "Use clear language with moderate technical depth.",
        "Expert":       "Use advanced vocabulary and deep technical explanations."
    }

    density_map = {
        "Low (1–2%)":    f"Use the keyword '{keyword}' sparingly.",
        "Medium (2–3%)": f"Use the keyword '{keyword}' naturally throughout the article.",
        "High (3–4%)":   f"Use the keyword '{keyword}' frequently but naturally."
    }

    secondary_kw_instruction = ""
    if secondary_keywords.strip():
        secondary_kw_instruction = f"Also use these secondary keywords naturally: {secondary_keywords}"

    faq_instruction       = f"""Include a FAQ section with 5 detailed questions and answers related to {topic}.
Use this exact markdown format:
## Frequently Asked Questions

### Specific question ending with a question mark?

Detailed answer paragraph.

### Another specific question ending with a question mark?

Detailed answer paragraph.
Do not use placeholder headings like "Question 1?" or "Question 2?".""" if generate_faq else ""
    cta_instruction       = "End with a strong call-to-action paragraph." if add_cta else ""
    takeaways_instruction = "Add a Key Takeaways section after the introduction with 4–5 bullet points." if add_key_takeaways else ""
    meta_instruction      = "At the top write:\nMETA: [meta description]\nKeep it 150–160 characters." if generate_meta else ""

    prompt = f"""
You are an expert researcher, professional SEO strategist, and senior long-form content writer.

Your task is to write a highly informative, deeply researched, publication-quality blog article.

TOPIC: {topic}

PRIMARY SEO KEYWORD: {keyword}

SECONDARY KEYWORDS: {secondary_keywords}

TARGET AUDIENCE: {audience}

WRITING TONE: {tone}

TARGET WORD COUNT: {word_count}

READABILITY LEVEL:
{readability_map.get(readability)}

KEYWORD USAGE:
{density_map.get(keyword_usage)}

--------------------------------------------------
IMPORTANT WRITING RULES
--------------------------------------------------

1. Write like a human expert, not an AI assistant.

2. Avoid:
- fluff
- generic statements
- repetitive explanations
- unnecessary introductions
- motivational filler
- robotic transitions

3. Do NOT use phrases like:
- "In today's digital world"
- "It is important to note"
- "In conclusion"
- "This comprehensive guide"
- "Nowadays"
- "Unlock the power of"
- "Delve into"

4. Every paragraph must provide useful information.

5. Every section should teach something valuable.

6. Focus on:
- practical insights
- real-world applications
- examples
- case studies
- statistics
- comparisons
- expert explanations
- implementation strategies

7. Explain:
- WHAT
- WHY
- HOW
- BENEFITS
- CHALLENGES
- BEST PRACTICES

8. Make the article educational and genuinely useful.

9. Avoid repeating the same ideas in different sections.

10. Maintain natural readability and conversational flow.

11.Write a detailed long-form article with substantial depth and practical insights.
Aim naturally for around {word_count} words without forcing exact length.
--------------------------------------------------
CONTENT DEPTH REQUIREMENTS
--------------------------------------------------

For EVERY major section:

- Provide detailed explanations
- Add practical examples
- Include real-world use cases
- Mention advantages and disadvantages where relevant
- Include industry insights
- Explain common mistakes
- Add actionable tips

--------------------------------------------------
BLOG STRUCTURE
--------------------------------------------------

Use EXACTLY {num_sections} subject-focused main H2 sections after the introduction.

Use this structure:

# Blog Title

Write 2 or 3 opening paragraphs immediately below the title. Do not add an
"Introduction" heading. The opening paragraphs must clearly explain:
- what the topic is
- why it matters
- what readers will learn

{takeaways_instruction}

## First Main Section

Then continue with the remaining main H2 sections. Each main section must:
- be unique
- contain detailed information
- contain practical value
- avoid repetition

Use:
- H2 headings
- H3 subheadings where needed
- bullet points
- numbered lists
- markdown tables where useful

Include comparison tables wherever applicable.

Example:

| Feature | Option A | Option B |
|---|---|---|

--------------------------------------------------
IMAGE REQUIREMENTS
--------------------------------------------------

Insert relevant images naturally throughout the article.

IMPORTANT:
- Use images only where they clarify the topic or give the article visual rhythm
- Add 3-5 images for long blogs and fewer images for short blogs
- Put some image prompts after an explanatory paragraph and some between sections
- Do not add images inside Key Takeaways or FAQ answers
- Use realistic image prompts
- Image prompts should visually explain the section

Use EXACTLY this format:

[IMAGE: realistic editorial style image about AI automation in healthcare]

--------------------------------------------------
SEO REQUIREMENTS
--------------------------------------------------

- Use the primary keyword naturally
- Use secondary keywords naturally
- Avoid keyword stuffing
- Optimize headings for SEO
- Write SEO-friendly subheadings
- Maintain readability

--------------------------------------------------
SPECIAL SECTIONS
--------------------------------------------------

Include these sections naturally if relevant:

- Practical Applications
- Common Mistakes
- Best Practices
- Future Trends
- Expert Tips

--------------------------------------------------
FAQ SECTION
--------------------------------------------------

{faq_instruction}

--------------------------------------------------
CALL TO ACTION
--------------------------------------------------

{cta_instruction}

--------------------------------------------------
FINAL QUALITY RULES
--------------------------------------------------

Before finishing, ensure:

- The blog feels written by an expert
- The content is information-rich
- The article is engaging
- The explanations are practical
- The sections are not repetitive
- The writing sounds natural
- The article provides real value

Generate the complete blog now.
"""

    with st.spinner(f"Generating ~{word_count} word SEO blog..."):

        try:
            if not GROQ_API_KEY:
                st.error("Set the GROQ_API_KEY environment variable before generating a blog.")
                st.stop()

            stream_box = preview_placeholder
            full_response = ""
            client = Groq(api_key=GROQ_API_KEY)

            response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
            {
            "role": "user",
            "content": prompt
           }
           ],
           temperature=0.5,
           stream=True,
           max_tokens=6000
         )
            for chunk in response:
                content = chunk.choices[0].delta.content or ""

                if content:
                    full_response += content
                stream_box.markdown(
                        f'<div class="card"><div class="card-title"> Generated Blog Preview</div>'
                        f'<div class="card-underline"></div>'
                        f'<div class="blog-output">{blog_preview_html(full_response, "▌")}</div></div>',
                        unsafe_allow_html=True
                    )
            auto_meta = ""
            blog_body = full_response

            if generate_meta:
                meta_match = re.search(r"META:\s*(.+)", full_response)
                if meta_match:
                    auto_meta = meta_match.group(1).strip()
                    blog_body = re.sub(r"META:\s*.+\n?", "", full_response).strip()

            effective_meta = (
                auto_meta if generate_meta and auto_meta
                else meta_description if meta_description.strip()
                else f"A detailed guide about {topic}."
            )
            total_words   = len(blog_body.split())
            total_words = len(blog_body.split())
            keyword_count = len(re.findall(re.escape(keyword.lower()), blog_body.lower()))
            density       = round((keyword_count / total_words) * 100, 2) if total_words > 0 else 0
            reading_time  = max(1, round(total_words / 200))
            blog_without_faq, faq_items = split_faq_section(blog_body)
            faq_count     = len(faq_items) if faq_items else len(re.findall(r'(?i)(## faq|Q\d[\.\)])', blog_body))
            
            with metrics_placeholder.container():
                st.markdown(f"""
                <div class="card">
                    <div class="card-title"> SEO Summary</div>
                    <div class="card-underline"></div>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#eff6ff"></div>
                                <span class="metric-label">Word Count</span>
                            </div>
                            <div class="metric-value">{total_words}</div>
                            <div class="metric-unit">words</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#f0fdf4"></div>
                                <span class="metric-label">Estimated Read Time</span>
                            </div>
                            <div class="metric-value">{reading_time}</div>
                            <div class="metric-unit">min</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#fff7ed"></div>
                                <span class="metric-label">Keyword Density</span>
                            </div>
                            <div class="metric-value">{density}%</div>
                            <div class="metric-unit">&nbsp;</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#faf5ff"></div>
                                <span class="metric-label">FAQ Count</span>
                            </div>
                            <div class="metric-value">{faq_count}</div>
                            <div class="metric-unit">&nbsp;</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            blog_without_faq = clean_generated_blog(blog_without_faq)
            blog_without_faq = fix_takeaways_format(blog_without_faq)
            blog_without_faq = auto_insert_section_images(blog_without_faq)
            blog_without_faq = replace_image_tags(blog_without_faq)
            html_blog = markdown.markdown(
            blog_without_faq,
            extensions=["extra", "md_in_html"],
            output_format="html5"
           )
            html_blog = sectionize_blog_html(html_blog)
            st.success(" Blog generated successfully!")
            stream_box.markdown(
                f'<div class="card"><div class="card-title"> Generated Blog Preview</div>'
                f'<div class="card-underline"></div>'
                f'<div class="blog-output">{html_blog}{faq_dropdown_html(faq_items)}</div></div>',
                unsafe_allow_html=True
            )
            html_body_content = html_blog + faq_dropdown_html(faq_items)
            html_content = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="assets/media/logo.png">
<title>{html.escape(topic)}</title>
<meta name="description" content="{html.escape(effective_meta, quote=True)}">
<meta name="keywords" content="{html.escape(keyword, quote=True)}">
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
<link rel="stylesheet" href="assets/css/style.css">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background-image: url('assets/media/background_2.jpg'); }}
.generated-blog {{ color: #263142; font-size: 15px; line-height: 1.68; }}
.generated-blog h1 {{ color: rgb(153, 27, 27); font-size: 32px; font-weight: 750; line-height: 1.2; letter-spacing: 0; margin: 0 0 18px; text-align: center; }}
.generated-blog h2 {{ color: rgb(153, 27, 27); font-size: 23px; font-weight: 720; line-height: 1.32; letter-spacing: 0; margin: 32px 0 14px; }}
.generated-blog h3 {{ color: rgb(153, 27, 27); font-size: 19px; font-weight: 680; line-height: 1.38; letter-spacing: 0; margin: 22px 0 10px; }}
.generated-blog p {{ color: #263142; font-size: 15px; font-weight: 400; letter-spacing: 0; margin: 0 0 12px; text-align: justify; }}
.generated-blog li {{ color: #263142; font-size: 15px; font-weight: 400; letter-spacing: 0; margin: 0 0 12px; }}
.generated-blog ul, .generated-blog ol {{ padding-left: 24px; margin-bottom: 16px; }}
.generated-blog a {{ color: #d97706; }}
.generated-blog img {{ max-width: 100%; height: auto; }}
.article-intro {{ width: 100%; }}
.article-intro p {{ font-size: 16px; }}
.article-section {{ margin-top: 24px; }}
.article-section.split-media {{ display: flow-root; }}
.article-section.split-media > h2 {{ margin-top: 10px; }}
.article-section.split-media > .blog-figure {{ float: right; margin: 2px 0 14px clamp(18px, 3vw, 34px); width: min(42%, 420px); }}
.article-section.media-left > .blog-figure {{ float: left; margin: 2px clamp(18px, 3vw, 34px) 14px 0; }}
.blog-figure {{ margin: 20px 0; }}
.blog-figure img {{ display: block; width: 100%; max-height: 460px; object-fit: cover; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.12); }}
.blog-figure figcaption {{ color: #6b7280; font-size: 12px; font-style: italic; margin-top: 7px; text-align: center; }}
.generated-blog table {{ width: 100%; border-collapse: collapse; display: block; overflow-x: auto; margin: 28px 0; border: 1px solid #e5e7eb; border-radius: 12px; }}
.generated-blog th, .generated-blog td {{ padding: 12px 14px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
.generated-blog th {{ background: #fef3c7; color: #78350f; font-weight: 700; }}
.generated-blog tr:last-child td {{ border-bottom: 0; }}
.generated-blog blockquote {{ border-left: 4px solid #f59e0b; color: #4b5563; margin: 28px 0; padding: 8px 0 8px 18px; }}
.faq-section {{ margin-top: 42px; }}
.faq-item {{ border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 12px; overflow: hidden; background: #fff; }}
.faq-item summary {{ cursor: pointer; list-style: none; padding: 15px 18px; font-weight: 700; color: #1a1a2e; background: #fafafa; }}
.faq-item summary::-webkit-details-marker {{ display: none; }}
.faq-answer {{ padding: 16px 18px; border-top: 1px solid #e5e7eb; }}
@media (max-width: 640px) {{
    .generated-blog {{ line-height: 1.65; }}
    .generated-blog h1 {{ font-size: 27px; margin-bottom: 16px; }}
    .generated-blog h2 {{ font-size: 21px; }}
    .generated-blog h3 {{ font-size: 18px; }}
    .generated-blog p, .generated-blog li, .article-intro p {{ font-size: 15px; }}
    .article-section.split-media {{ display: block; }}
    .article-section.split-media > .blog-figure {{ float: none; width: 100%; margin: 20px 0; }}
    .generated-blog table {{ font-size: 14px; }}
}}
</style>
</head>
<body style="background-image: url('assets/media/background_2.jpg');">
<div class="bg-[#1c2328] px-4 py-3 top_header">
    <div class="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center">
        <p class="text-sm text-white mb-2 sm:mb-0">
            <span class="text-white font-thin">We Help You Grow Your Business</span>
        </p>
        <div class="flex gap-5 text-white text-sm">
            <a href="https://www.youtube.com/@SynthoQuest_Official" aria-label="YouTube"><i class="fab fa-youtube"></i></a>
            <a href="https://www.facebook.com/people/SynthoQuest-official/61559656813295/?mibextid=qi2Omg&rdid=cDx3M8k2tayhmeQ4&share_url=https%3A%2F%2Fwww.facebook.com%2Fshare%2FPGyPqzPyT5hE3deS%2F%3Fmibextid%3Dqi2Omg" aria-label="Facebook"><i class="fab fa-facebook-f"></i></a>
            <a href="https://twitter.com/SynthoQuest" aria-label="Twitter"><i class="fab fa-twitter"></i></a>
            <a href="https://www.instagram.com/synthoquest_official/?next=%2F" aria-label="Instagram"><i class="fab fa-instagram"></i></a>
            <a href="https://www.linkedin.com/in/synthoquest-official-4684812b6/" aria-label="LinkedIn"><i class="fab fa-linkedin-in"></i></a>
        </div>
    </div>
</div>

<nav id="navbar" class="sticky top-0 left-0 w-full backdrop-blur-sm z-50">
    <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
        <div class="flex items-center space-x-3">
            <a href="index.html"><img src="assets/media/logo.png" alt="Logo" class="h-20 w-auto" /></a>
        </div>

        <div class="space-x-6 font-semibold uppercase text-sm custom-nav z-50">
            <a href="index.html">Home</a>
            <a href="about_us.html">About Us</a>
            <a href="services.html">Services</a>
            <a href="products.html">Products</a>
            <a href="events_news.html">Events & News</a>
            <a href="apply_now.html">Apply Now</a>
            <a href="blog.html" class="text-amber-500">Blog</a>
            <a href="courses.html">Courses</a>
            <a href="contact_us.html">Contact Us</a>
        </div>

        <button id="menu-toggle" class="text-3xl text-black custom-hamburger z-50 relative">
            <i id="menu-icon" class="fas fa-bars"></i>
        </button>

        <div id="mobile-menu" class="absolute left-0 top-[100%] w-full bg-white text-black px-4 py-6 space-y-4 font-semibold uppercase text-sm text-center z-40 transition-all duration-200 ease-in-out transform scale-y-0 origin-top opacity-0 overflow-hidden">
            <a href="index.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[20ms]">Home</a>
            <a href="about_us.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[40ms]">About Us</a>
            <a href="services.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[60ms]">Services</a>
            <a href="products.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[60ms]">Products</a>
            <a href="events_news.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[80ms]">Events & News</a>
            <a href="apply_now.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[100ms]">Apply Now</a>
            <a href="blog.html" class="block text-amber-500 transform opacity-0 -translate-y-4 transition duration-200 delay-[120ms]">Blog</a>
            <a href="courses.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[140ms]">Courses</a>
            <a href="contact_us.html" class="block transform opacity-0 -translate-y-4 transition duration-200 delay-[160ms]">Contact Us</a>
        </div>
    </div>
</nav>

<section class="bg-fixed bg-cover bg-center min-h-screen px-2 sm:px-4 py-12 courses" id="course-card" style="background-image: url('assets/media/background_2.jpg');">
    <div class="p-2 sm:p-4 lg:p-6 rounded-xl max-w-7xl mx-auto mt-20">
        <div class="grid grid-cols-1 gap-6">
            <div class="bg-gray-100 rounded-lg shadow-md overflow-hidden">
                <article class="generated-blog p-5 sm:p-8 lg:p-10">
                    {html_body_content}
                    <div class="clear-both"></div>
                </article>
            </div>
        </div>
    </div>

    <footer>
        <hr class="mt-7 border-gray-700">
        <p class="text-white tracking-wider uppercase font-semibold text-sm text-center py-5">Copyright © 2024 <a href="index.html" class="text-amber-500"> SYNTHOQUEST PVT.LTD</a> All Rights Reserved.</p>
    </footer>
</section>

<script src="assets/js/menu.js"></script>
</body>
</html>"""
            html_snippet = html_content[:900] + ("\n..." if len(html_content) > 900 else "")
            with html_placeholder.container():
                st.markdown(f"""
                <div class="card">
                    <div class="card-title"> Generated HTML Preview</div>
                    <div class="card-underline"></div>
                    <div class="html-code">{html_snippet.replace('<','&lt;').replace('>','&gt;')}</div>
                </div>
                """, unsafe_allow_html=True)
            with download_placeholder.container():
                st.markdown("""
                <div class="card">
                    <div class="card-title"> Download HTML</div>
                    <div class="card-underline"></div>
                    <div class="download-info">Your blog is ready! Click below to download.</div>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label=" Download HTML",
                        data=html_content,
                        file_name=f"{topic}.html",
                        mime="text/html",
                        use_container_width=True
                    )
                with col2:
                    st.download_button(
                        label=" Download Markdown",
                        data=blog_body,
                        file_name=f"{topic}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

        except Exception as e:
            st.error(f" Error: {str(e)}")
