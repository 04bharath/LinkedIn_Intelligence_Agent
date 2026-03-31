"""
app.py  –  LinkedIn Intelligence & Job Scraper
Dashboard UI matching the reference design:
  Sidebar nav | Pipeline flow | Job table | Skill match | Activity log
"""

import streamlit as st
import pandas as pd
import datetime

st.set_page_config(
    page_title="LinkedIn Intelligence & Job Scraper",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-sizing: border-box;
}

/* ── hide streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] > div { padding: 0 !important; }

/* ── sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e8edf2;
    min-width: 200px !important;
    max-width: 200px !important;
}

/* ── main content padding ── */
.main .block-container { padding: 0 !important; }

/* ── buttons ── */
.stButton > button {
    background: #2563eb !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 1.2rem !important;
    width: 100% !important;
    transition: background 0.2s !important;
}
.stButton > button:hover { background: #1d4ed8 !important; }

/* ── inputs ── */
.stTextInput > div > div > input {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 0.8rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}

/* ── dataframe ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* ── progress ── */
.stProgress > div > div { background: #2563eb !important; }

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 2px solid #e8edf2; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 500 !important;
    color: #64748b !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 0.5rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
    background: #eff6ff !important;
}
</style>
""", unsafe_allow_html=True)

# ── imports ───────────────────────────────────────────────────────────────────
from fetch     import fetch_jobs
from lyzr      import extract_data
from qdrant_db import init_collection, is_duplicate, store_job, search_jobs, collection_count, get_all_jobs
from sheets    import ensure_headers, save_to_sheet, get_sheet_url

# ── session state ─────────────────────────────────────────────────────────────
for k, v in {
    "activity_log": [],
    "fetched_jobs": [],
    "stats": {"fetched": 0, "saved": 0, "dupes": 0},
    "pipeline_stage": None,
    "page": "Dashboard",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── init DB ───────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def setup():
    init_collection()
    try:
        ensure_headers()
    except Exception:
        pass

setup()

# ── helpers ───────────────────────────────────────────────────────────────────
def log(msg, kind="success"):
    icons = {"success": "✅", "dupe": "🔁", "info": "ℹ️", "warn": "⚠️"}
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.activity_log.insert(0, {"msg": msg, "kind": kind, "ts": ts})
    if len(st.session_state.activity_log) > 20:
        st.session_state.activity_log = st.session_state.activity_log[:20]

def time_ago(i):
    mins = i * 2
    if mins == 0: return "just now"
    return f"{mins} min ago"

def qdrant_status():
    try:
        from config import QDRANT_URL
        if "memory" in QDRANT_URL or not QDRANT_URL:
            return False
        return True
    except Exception:
        return False

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 16px 12px;border-bottom:1px solid #e8edf2">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:36px;height:36px;background:#2563eb;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    color:#fff;font-size:1rem;font-weight:800">in</div>
        <div>
          <div style="font-weight:700;font-size:0.9rem;color:#0f172a;line-height:1.2">LinkedIn</div>
          <div style="font-size:0.68rem;color:#64748b;line-height:1.2">Intelligence & Job Scraper</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    nav_items = [
        ("📊", "Dashboard"),
        ("🔍", "Fetch Jobs"),
        ("🧠", "Skill Matching"),
        ("📋", "Stored Jobs"),
        ("⚙️", "Settings"),
    ]

    st.markdown('<div style="padding:12px 8px 0">', unsafe_allow_html=True)
    for icon, label in nav_items:
        active = st.session_state.page == label
        bg     = "#eff6ff" if active else "transparent"
        color  = "#2563eb" if active else "#475569"
        weight = "700" if active else "500"
        if st.button(f"{icon}  {label}", key=f"nav_{label}"):
            st.session_state.page = label
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # system status
    st.markdown("""<div style="height:1px;background:#e8edf2;margin:16px 0"></div>""", unsafe_allow_html=True)
    q_ok = qdrant_status()
    g_ok = False
    try:
        import os; g_ok = os.path.exists("creds.json")
    except Exception: pass

    st.markdown(f"""
    <div style="padding:0 16px 16px">
      <div style="font-size:0.72rem;font-weight:700;color:#94a3b8;
                  text-transform:uppercase;letter-spacing:1px;margin-bottom:10px">System Status</div>
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
        <div style="width:8px;height:8px;border-radius:50%;
                    background:{'#22c55e' if q_ok else '#f59e0b'}"></div>
        <span style="font-size:0.78rem;color:#475569">
          Qdrant: {'Connected' if q_ok else 'In-Memory'}
        </span>
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        <div style="width:8px;height:8px;border-radius:50%;
                    background:{'#22c55e' if g_ok else '#94a3b8'}"></div>
        <span style="font-size:0.78rem;color:#475569">
          Google Sheets: {'Connected' if g_ok else 'Not configured'}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Google Sheets open button
    if g_ok:
        try:
            _sheet_url = get_sheet_url()
            if _sheet_url:
                st.markdown(
                    f'''<div style="padding:0 16px 8px">
                      <a href="{_sheet_url}" target="_blank" style="
                        display:block;text-align:center;
                        background:#16a34a;color:#fff;
                        border-radius:8px;padding:8px 12px;
                        font-size:0.78rem;font-weight:700;
                        text-decoration:none;">
                        📊 Open Google Sheets
                      </a>
                    </div>''',
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

# ── main area ─────────────────────────────────────────────────────────────────
page = st.session_state.page

st.markdown(f"""
<div style="padding:24px 32px 0;border-bottom:1px solid #e8edf2;background:#fff">
  <div style="font-size:1.4rem;font-weight:800;color:#0f172a">LinkedIn Intelligence & Job Scraper</div>
  <div style="font-size:0.82rem;color:#64748b;margin-top:2px;padding-bottom:16px">
    Scrape LinkedIn jobs, deduplicate, match skills, and save to Google Sheets
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD / FETCH JOBS PAGE
# ══════════════════════════════════════════════════════════════════════════════
if page in ("Dashboard", "Fetch Jobs"):

    st.markdown('<div style="padding:24px 32px">', unsafe_allow_html=True)

    # ── Section 1: keyword input + stat cards ─────────────────────────────────
    st.markdown("""
    <div style="font-size:0.95rem;font-weight:700;color:#0f172a;margin-bottom:14px">
      1. Enter Job Role / Keyword
    </div>
    """, unsafe_allow_html=True)

    col_input, col_limit, col_btn, col_sp, col_c1, col_c2, col_c3 = st.columns([2.2, 0.8, 0.9, 0.1, 0.8, 0.8, 0.8])

    with col_input:
        keyword = st.text_input("keyword", label_visibility="collapsed",
                                placeholder="e.g. Data Scientist, ML Engineer")
    with col_limit:
        job_limit = st.selectbox("Jobs", [5, 10, 20, 50], index=1,
                                  label_visibility="collapsed")
    with col_btn:
        st.markdown("<div style='margin-top:2px'>", unsafe_allow_html=True)
        fetch_btn = st.button("🔍 Fetch Jobs")
        st.markdown("</div>", unsafe_allow_html=True)

    s = st.session_state.stats

    def stat_card(val, label, color, icon):
        return f"""
        <div style="background:{color};border-radius:12px;padding:14px 16px;text-align:center">
          <div style="font-size:0.65rem;font-weight:600;color:rgba(255,255,255,0.8);
                      text-transform:uppercase;letter-spacing:0.8px">{icon} {label}</div>
          <div style="font-size:1.6rem;font-weight:800;color:#fff;line-height:1.3">{val}</div>
        </div>"""

    with col_c1:
        st.markdown(stat_card(s["fetched"], "Fetched", "#2563eb", "⬇"), unsafe_allow_html=True)
    with col_c2:
        st.markdown(stat_card(s["saved"], "Saved", "#059669", "✅"), unsafe_allow_html=True)
    with col_c3:
        st.markdown(stat_card(s["dupes"], "Duplicates", "#d97706", "🔁"), unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Section 2: Pipeline flow ───────────────────────────────────────────────
    stage = st.session_state.pipeline_stage
    stages = ["Fetching", "AI Extraction", "Deduplication", "Storing", "Saving"]
    stage_icons = ["🌐", "🤖", "✅", "🗄️", "💾"]

    def stage_dot(s_name, current, done):
        if done:
            c, tc = "#22c55e", "#fff"
        elif s_name == current:
            c, tc = "#2563eb", "#fff"
        else:
            c, tc = "#e2e8f0", "#94a3b8"
        return f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
          <div style="width:36px;height:36px;border-radius:50%;background:{c};
                      display:flex;align-items:center;justify-content:center;
                      font-size:1rem">{stage_icons[stages.index(s_name)]}</div>
          <span style="font-size:0.7rem;font-weight:600;color:{tc if done or s_name==current else '#94a3b8'}">{s_name}</span>
        </div>"""

    completed = stage == "done"
    pipeline_html = '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 24px;margin-bottom:24px">'
    pipeline_html += '<div style="display:flex;align-items:center;justify-content:space-between">'
    pipeline_html += '<div style="font-size:0.85rem;font-weight:700;color:#0f172a">2. Fetch &amp; Process Jobs</div>'
    if completed:
        pipeline_html += '<div style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block"></span><span style="font-size:0.78rem;color:#22c55e;font-weight:600">Completed ✓</span></div>'
    pipeline_html += '</div>'
    pipeline_html += '<div style="display:flex;align-items:center;justify-content:center;gap:0;margin-top:14px">'
    for i, s_name in enumerate(stages):
        done_stage = completed or (stage and stages.index(s_name) < (stages.index(stage) if stage and stage != "done" else 5))
        pipeline_html += stage_dot(s_name, stage, done_stage)
        if i < len(stages) - 1:
            pipeline_html += '<div style="flex:1;height:2px;background:#e2e8f0;margin:0 4px;margin-bottom:16px"></div>'
    pipeline_html += '</div></div>'
    st.markdown(pipeline_html, unsafe_allow_html=True)

    # ── Fetch logic ────────────────────────────────────────────────────────────
    if fetch_btn and keyword.strip():
        st.session_state.pipeline_stage = "Fetching"
        progress_bar  = st.progress(0)
        status_text   = st.empty()

        status_text.markdown("⏳ Fetching jobs from LinkedIn...")
        posts = fetch_jobs(keyword.strip())
        st.session_state.stats["fetched"] = len(posts)

        if not posts:
            st.error("No posts returned. Check your RapidAPI key.")
        else:
            new_jobs  = []
            new_count = 0
            dup_count = 0

            for idx, post in enumerate(posts):
                pct = (idx + 1) / len(posts)

                if pct < 0.25:
                    st.session_state.pipeline_stage = "AI Extraction"
                elif pct < 0.5:
                    st.session_state.pipeline_stage = "Deduplication"
                elif pct < 0.75:
                    st.session_state.pipeline_stage = "Storing"
                else:
                    st.session_state.pipeline_stage = "Saving"

                status_text.markdown(f"🤖 Processing post **{idx+1} / {len(posts)}**…")
                job = extract_data(str(post), keyword.strip(), idx)

                if is_duplicate(job["post_id"]):
                    dup_count += 1
                else:
                    store_job(job)
                    try:
                        save_to_sheet(job)
                    except Exception:
                        pass
                    new_count += 1
                    new_jobs.append(job)

                progress_bar.progress(pct)

            st.session_state.stats["saved"] = new_count
            st.session_state.stats["dupes"] = dup_count
            st.session_state.fetched_jobs   = new_jobs
            st.session_state.pipeline_stage = "done"

            log(f"{new_count} new jobs saved", "success")
            if dup_count:
                log(f"{dup_count} duplicates removed", "dupe")
            log("Qdrant database updated", "info")

            status_text.empty()
            progress_bar.empty()
            st.rerun()

    elif fetch_btn:
        st.warning("Please enter a keyword.")

    # ── Section 3: Job results table ───────────────────────────────────────────
    jobs_to_show = st.session_state.fetched_jobs
    if jobs_to_show:
        st.markdown(f"""
        <div style="font-size:0.95rem;font-weight:700;color:#0f172a;margin-bottom:12px">
          3. Job Results &nbsp;<span style="font-size:0.8rem;font-weight:500;color:#22c55e">
          {len(jobs_to_show)} New Jobs Saved</span>
        </div>
        """, unsafe_allow_html=True)

        col_table, col_side = st.columns([1.8, 1])

        with col_table:
            # Build display rows
            rows = []
            for j in jobs_to_show[:10]:
                skills = j.get("primary_skills", [])
                skills_str = ", ".join(s for s in skills[:3] if s != "Not specified")
                rows.append({
                    "Role":       j.get("role", "—"),
                    "Company":    j.get("company_name", "—"),
                    "Location":   j.get("location", "—")[:18],
                    "Skills":     skills_str,
                    "Experience": j.get("years_of_experience", "—"),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True, height=280)

        with col_side:
            # Section 4: Skill matching
            st.markdown("""
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px">
              <div style="font-size:0.88rem;font-weight:700;color:#0f172a;margin-bottom:4px">
                4. Find Matching Jobs
              </div>
              <div style="font-size:0.75rem;color:#64748b;margin-bottom:12px">
                Find jobs matching your skills
              </div>
            """, unsafe_allow_html=True)

            skill_input = st.text_input("skills", label_visibility="collapsed",
                                        placeholder="Python, SQL, ML",
                                        key="skill_input_main")
            match_btn = st.button("🎯 Match Jobs", key="match_main")

            if match_btn and skill_input.strip():
                skills = [s.strip() for s in skill_input.split(",") if s.strip()]
                hits   = search_jobs(skills, top_k=5)
                if hits:
                    for h in hits[:3]:
                        p     = h.payload
                        score = round(h.score * 100, 1)
                        st.markdown(f"""
                        <div style="border:1px solid #e2e8f0;border-radius:8px;
                                    padding:10px 12px;margin-top:8px">
                          <div style="font-size:0.8rem;font-weight:700;color:#0f172a">{p.get('role','—')}</div>
                          <div style="font-size:0.72rem;color:#64748b">{p.get('company_name','—')} · {p.get('location','—')[:20]}</div>
                          <div style="margin-top:6px;background:#e2e8f0;border-radius:4px;height:4px">
                            <div style="width:{score}%;background:#2563eb;height:4px;border-radius:4px"></div>
                          </div>
                          <div style="font-size:0.68rem;color:#2563eb;margin-top:2px">{score}% match</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No matches yet. Fetch jobs first!")

            st.markdown("</div>", unsafe_allow_html=True)

        # ── Section 5: Sample extracted job ───────────────────────────────────
        if jobs_to_show:
            sample = jobs_to_show[0]
            st.markdown("""
            <div style="font-size:0.95rem;font-weight:700;color:#0f172a;
                        margin-top:24px;margin-bottom:12px">
              5. Sample Extracted Job (18 Fields)
            </div>
            """, unsafe_allow_html=True)

            skills_chips = "".join(
                f'<span style="background:#dbeafe;color:#1d4ed8;border-radius:20px;'
                f'padding:2px 10px;font-size:0.72rem;margin-right:4px">{s}</span>'
                for s in (sample.get("primary_skills") or [])[:4]
                if s != "Not specified"
            )

            st.markdown(f"""
            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
              <table style="width:100%;border-collapse:collapse">
                <thead>
                  <tr style="background:#f8fafc">
                    <th style="padding:10px 16px;text-align:left;font-size:0.75rem;
                               color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0">Post ID</th>
                    <th style="padding:10px 16px;text-align:left;font-size:0.75rem;
                               color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0">Role</th>
                    <th style="padding:10px 16px;text-align:left;font-size:0.75rem;
                               color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0">Location</th>
                    <th style="padding:10px 16px;text-align:left;font-size:0.75rem;
                               color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0">Skills</th>
                    <th style="padding:10px 16px;text-align:left;font-size:0.75rem;
                               color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0">Experience</th>
                    <th style="padding:10px 16px;text-align:left;font-size:0.75rem;
                               color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0">Posted</th>
                    <th style="padding:10px 16px;text-align:left;font-size:0.75rem;
                               color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0">Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style="padding:12px 16px;font-size:0.78rem;color:#0f172a;
                               font-family:monospace">{sample.get('post_id','—')[:12]}</td>
                    <td style="padding:12px 16px;font-size:0.78rem;color:#0f172a;
                               font-weight:600">{sample.get('role','—')}</td>
                    <td style="padding:12px 16px;font-size:0.78rem;color:#475569">
                      {sample.get('location','—')[:15]}</td>
                    <td style="padding:12px 16px">{skills_chips}</td>
                    <td style="padding:12px 16px;font-size:0.78rem;color:#475569">
                      {sample.get('years_of_experience','—')}</td>
                    <td style="padding:12px 16px;font-size:0.78rem;color:#475569">
                      {sample.get('date_posted','—')[:10]}</td>
                    <td style="padding:12px 16px">
                      <a href="{sample.get('post_url','#')}" target="_blank"
                         style="background:#eff6ff;color:#2563eb;border-radius:6px;
                                padding:4px 12px;font-size:0.75rem;font-weight:600;
                                text-decoration:none">View</a>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            """, unsafe_allow_html=True)

    # ── Activity Log ───────────────────────────────────────────────────────────
    if st.session_state.activity_log:
        st.markdown("""
        <div style="font-size:0.95rem;font-weight:700;color:#0f172a;
                    margin-top:28px;margin-bottom:12px">⚡ Activity Log</div>
        """, unsafe_allow_html=True)

        log_html = '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:8px 16px">'
        icons = {"success": ("✅", "#22c55e"), "dupe": ("🔁", "#f59e0b"),
                 "info": ("ℹ️", "#2563eb"), "warn": ("⚠️", "#ef4444")}
        for entry in st.session_state.activity_log[:6]:
            ico, col = icons.get(entry["kind"], ("•", "#64748b"))
            log_html += f"""
            <div style="display:flex;align-items:center;justify-content:space-between;
                        padding:8px 0;border-bottom:1px solid #e8edf2">
              <div style="display:flex;align-items:center;gap:8px">
                <span>{ico}</span>
                <span style="font-size:0.8rem;color:#0f172a;font-weight:500">{entry['msg']}</span>
              </div>
              <span style="font-size:0.72rem;color:#94a3b8">{entry['ts']}</span>
            </div>"""
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)

        # ── Google Sheets button after activity log ──────────────────────────
        try:
            import os
            if os.path.exists("creds.json"):
                _url = get_sheet_url()
                if _url:
                    st.markdown(
                        f'''<div style="margin-top:16px">
                          <a href="{_url}" target="_blank" style="
                            display:inline-flex;align-items:center;gap:8px;
                            background:#16a34a;color:#fff;
                            border-radius:10px;padding:10px 20px;
                            font-size:0.85rem;font-weight:700;
                            text-decoration:none;box-shadow:0 2px 8px rgba(22,163,74,0.3)">
                            📊 View Data in Google Sheets ↗
                          </a>
                        </div>''',
                        unsafe_allow_html=True,
                    )
        except Exception:
            pass

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SKILL MATCHING PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Skill Matching":
    st.markdown('<div style="padding:24px 32px">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.95rem;font-weight:700;color:#0f172a;margin-bottom:16px">
      🧠 Semantic Skill Matching
    </div>
    """, unsafe_allow_html=True)

    skill_input = st.text_input("Your skills (comma separated)",
                                placeholder="Python, Machine Learning, SQL, TensorFlow")
    top_k = st.slider("Number of results", 1, 20, 5)
    match_btn = st.button("🎯 Find Matching Jobs")

    if match_btn and skill_input.strip():
        skills = [s.strip() for s in skill_input.split(",") if s.strip()]
        with st.spinner("Running vector similarity search…"):
            hits = search_jobs(skills, top_k=top_k)

        if not hits:
            st.info("No matches found. Fetch some jobs first!")
        else:
            for h in hits:
                p     = h.payload
                score = round(h.score * 100, 1)
                skills_html = "".join(
                    f'<span style="background:#dbeafe;color:#1d4ed8;border-radius:20px;'
                    f'padding:2px 8px;font-size:0.72rem;margin-right:3px">{s}</span>'
                    for s in (p.get("primary_skills") or [])[:4]
                    if s != "Not specified"
                )
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;
                            padding:16px 20px;margin-bottom:12px">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-size:0.9rem;font-weight:700;color:#0f172a">
                        {p.get('role','—')} @ {p.get('company_name','—')}</div>
                      <div style="font-size:0.78rem;color:#64748b;margin-top:2px">
                        📍 {p.get('location','—')} &nbsp;·&nbsp; 💼 {p.get('years_of_experience','—')}</div>
                    </div>
                    <div style="text-align:right">
                      <div style="font-size:1.1rem;font-weight:800;color:#2563eb">{score}%</div>
                      <div style="font-size:0.68rem;color:#94a3b8">match</div>
                    </div>
                  </div>
                  <div style="background:#e2e8f0;border-radius:4px;height:5px;margin:10px 0 8px">
                    <div style="width:{score}%;background:linear-gradient(90deg,#2563eb,#7c3aed);
                                height:5px;border-radius:4px"></div>
                  </div>
                  <div>{skills_html}</div>
                </div>
                """, unsafe_allow_html=True)
    elif match_btn:
        st.warning("Enter at least one skill.")
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STORED JOBS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Stored Jobs":
    st.markdown('<div style="padding:24px 32px">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.95rem;font-weight:700;color:#0f172a;margin-bottom:16px">
      📋 All Stored Jobs
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Refresh"):
        st.rerun()

    try:
        jobs = get_all_jobs(limit=500)
    except Exception:
        jobs = []

    if not jobs:
        st.info("No jobs stored yet. Go to Dashboard and fetch some jobs first!")
    else:
        df = pd.DataFrame(jobs)
        for col in ("primary_skills", "secondary_skills", "must_to_have"):
            if col in df.columns:
                df[col] = df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        st.dataframe(df, use_container_width=True, height=500)
        st.caption(f"Showing {len(df)} stored jobs.")
        csv = df.to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", data=csv,
                           file_name="linkedin_jobs.csv", mime="text/csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Settings":
    st.markdown('<div style="padding:24px 32px">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.95rem;font-weight:700;color:#0f172a;margin-bottom:16px">
      ⚙️ Settings
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### API Configuration")
    st.code("""# config.py
RAPIDAPI_KEY    = "your_key_here"
OPENAI_API_KEY  = "your_key_here"
QDRANT_URL      = "https://your-cluster.qdrant.io"
QDRANT_API_KEY  = "your_key_here"
GOOGLE_CREDS_FILE = "creds.json"
GOOGLE_SHEET_NAME = "LinkedIn Jobs"
""", language="python")

    st.markdown("#### Reset Database")
    if st.button("🗑️ Reset Qdrant Collection (delete all jobs)"):
        try:
            init_collection(force_recreate=True)
            st.session_state.fetched_jobs = []
            st.session_state.stats = {"fetched": 0, "saved": 0, "dupes": 0}
            st.session_state.activity_log = []
            st.success("✅ Collection reset successfully.")
        except Exception as e:
            st.error(f"Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)