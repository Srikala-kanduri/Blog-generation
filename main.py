import streamlit as st
import google.generativeai as genai
import markdown
import re
import os


def get_gemini_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")



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

    faq_instruction       = f"Include a FAQ section with 5 detailed questions and answers related to {topic}." if generate_faq else ""
    cta_instruction       = "End with a strong call-to-action paragraph." if add_cta else ""
    takeaways_instruction = "Add a Key Takeaways section after the introduction with 4–5 bullet points." if add_key_takeaways else ""
    meta_instruction      = "At the top write:\nMETA: [meta description]\nKeep it 150–160 characters." if generate_meta else ""

    prompt = f"""
You are a professional SEO blog writer.

Write a complete publication-ready blog article.

TOPIC: {topic}
PRIMARY KEYWORD: {keyword}
TARGET AUDIENCE: {audience}
WRITING TONE: {tone}

REQUIREMENTS:
1. Write around {word_count} words.
2. {readability_map.get(readability)}
3. {density_map.get(keyword_usage)}
4. {secondary_kw_instruction}
5. Use exactly {num_sections} main sections with H2 headings.
6. Every section should contain detailed paragraphs.
7. Include practical examples.
8. Avoid repetition.
9. Write naturally like a human writer.
10. Use markdown headings.

{meta_instruction}

MANDATORY STRUCTURE:
# Blog Title
## Introduction
{takeaways_instruction}
## Main Sections
## Conclusion
{cta_instruction}
{faq_instruction}
"""

    with st.spinner(f"Generating ~{word_count} word SEO blog..."):

        try:
            api_key = get_gemini_api_key()
            if not api_key:
                st.error("Gemini API key is missing. Add GEMINI_API_KEY in Streamlit secrets before generating a blog.")
                st.stop()

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("models/gemini-2.5-flash")

            full_response = ""
            stream_box = preview_placeholder.empty()

            response = model.generate_content(prompt, stream=True)

            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    stream_box.markdown(
                        f'<div class="card"><div class="card-title"> Generated Blog Preview</div>'
                        f'<div class="card-underline"></div>'
                        f'<div class="blog-output">{markdown.markdown(full_response)}▌</div></div>',
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
            keyword_count = len(re.findall(re.escape(keyword.lower()), blog_body.lower()))
            density       = round((keyword_count / total_words) * 100, 2) if total_words > 0 else 0
            reading_time  = max(1, round(total_words / 200))
            faq_count     = len(re.findall(r'(?i)(## faq|Q\d[\.\)])', blog_body))

            st.success("✅ Blog generated successfully!")
            stream_box.markdown(
                f'<div class="card"><div class="card-title"> Generated Blog Preview</div>'
                f'<div class="card-underline"></div>'
                f'<div class="blog-output">{markdown.markdown(blog_body)}</div></div>',
                unsafe_allow_html=True
            )
            with metrics_placeholder.container():
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">📊 SEO Summary</div>
                    <div class="card-underline"></div>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#eff6ff">📄</div>
                                <span class="metric-label">Word Count</span>
                            </div>
                            <div class="metric-value">{total_words}</div>
                            <div class="metric-unit">words</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#f0fdf4">⏱️</div>
                                <span class="metric-label">Estimated Read Time</span>
                            </div>
                            <div class="metric-value">{reading_time}</div>
                            <div class="metric-unit">min</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#fff7ed">🎯</div>
                                <span class="metric-label">Keyword Density</span>
                            </div>
                            <div class="metric-value">{density}%</div>
                            <div class="metric-unit">&nbsp;</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon-row">
                                <div class="metric-icon" style="background:#faf5ff">❓</div>
                                <span class="metric-label">FAQ Count</span>
                            </div>
                            <div class="metric-value">{faq_count}</div>
                            <div class="metric-unit">&nbsp;</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            html_body_content = markdown.markdown(blog_body)
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{topic}</title>
<meta name="description" content="{effective_meta}">
<meta name="keywords" content="{keyword}">
<style>
body {{ font-family: Arial, sans-serif; background-color: #f9f9f9; color: #333; line-height: 1.8; margin: 0; padding: 0; }}
.container {{ max-width: 900px; margin: auto; padding: 50px; }}
h1 {{ color: #4F46E5; }} h2 {{ color: #6C63FF; }} h3 {{ color: #7C3AED; }}
p {{ margin-bottom: 18px; }}
</style>
</head>
<body>
<div class="container">{html_body_content}</div>
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
