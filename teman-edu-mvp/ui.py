from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


I18N = {
    "en": {
        "app_title": "TemanEDU - Readiness & Pathway Advisor",
        "subtitle": "Deterministic guidance for SPM and Diploma students.",
        "start": "Start",
        "next": "Next",
        "back": "Back",
        "reset": "Start Over",
        "student_mode": "Student",
        "counselor_mode": "Counselor",
        "admin_mode": "Admin",
        "language": "Language",
        "consent": "I consent to save my session data for future access.",
        "disclaimer_visa": "This is general guidance only and not legal visa advice.",
        "disclaimer_scholarship": "Scholarships are never guaranteed.",
        "disclaimer_general": "TemanEDU provides readiness guidance, not placement guarantees.",
        "no_match": "No direct matches yet - here is your Readiness Recovery Plan.",
        "download_pdf": "Download PDF Report",
        "download_json": "Download JSON Summary",
        "save": "Save Results",
        "explainability": "Explainability",
        "gaps": "Readiness Gaps",
        "actions_7": "Next 7-Day Actions",
        "actions_30": "30-Day Plan",
    },
    "bm": {
        "app_title": "TemanEDU - Penasihat Kesiapsiagaan & Laluan",
        "subtitle": "Panduan deterministik untuk pelajar SPM dan Diploma.",
        "start": "Mula",
        "next": "Seterusnya",
        "back": "Kembali",
        "reset": "Mula Semula",
        "student_mode": "Pelajar",
        "counselor_mode": "Kaunselor",
        "admin_mode": "Admin",
        "language": "Bahasa",
        "consent": "Saya setuju untuk simpan data sesi saya bagi akses masa depan.",
        "disclaimer_visa": "Ini hanya panduan umum dan bukan nasihat visa undang-undang.",
        "disclaimer_scholarship": "Biasiswa tidak pernah dijamin.",
        "disclaimer_general": "TemanEDU beri panduan kesiapsiagaan, bukan jaminan penempatan.",
        "no_match": "Tiada padanan terus buat masa ini - ini Pelan Pemulihan Kesiapsiagaan anda.",
        "download_pdf": "Muat Turun Laporan PDF",
        "download_json": "Muat Turun Ringkasan JSON",
        "save": "Simpan Keputusan",
        "explainability": "Kebolehjelasan",
        "gaps": "Jurang Kesiapsiagaan",
        "actions_7": "Tindakan 7 Hari",
        "actions_30": "Pelan 30 Hari",
    },
}


@st.cache_data
def get_i18n(language: str) -> dict[str, str]:
    return I18N.get(language, I18N["en"])


def t(language: str, key: str) -> str:
    return get_i18n(language).get(key, key)


def inject_mobile_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --primary-blue: #0D47A1;
                --primary-orange: #FF7A00;
                --primary-purple: #8B5CF6;
                --accent-yellow: #F59E0B;
                --accent-pink: #EC4899;
                --gradient-hero: linear-gradient(132deg, #0D47A1 0%, #1E5CCB 54%, #FF7A00 100%);
                --gradient-card: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
                --trust-anchor: #0D47A1;
                --growth-path: #FF7A00;
                --neutral-ground: #f4f8ff;
                --warm-support: #8B5CF6;
                --anxiety-buffer: #eef4ff;
                --gentle-caution: #F59E0B;
                --text-main: #1b2f4b;
                --text-muted: #4d6581;
                --surface: #ffffff;
                --surface-soft: #f5f9ff;
                --border: #d1def1;
                --sidebar-bg: #0D47A1;
                --primary-color: #FF7A00;
            }

            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at 88% 2%, rgba(255, 122, 0, 0.11), transparent 28%),
                    radial-gradient(circle at 12% 14%, rgba(30, 92, 203, 0.1), transparent 36%),
                    linear-gradient(180deg, #ffffff 0%, var(--neutral-ground) 100%);
                color: var(--text-main);
            }
            [data-testid="stHeader"] {
                background: transparent;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #1e40af, var(--sidebar-bg));
                border-right: 1px solid #3b82f6;
            }
            [data-testid="stSidebar"] * {
                color: #eaf3ff !important;
            }
            [data-testid="stSidebar"] [data-baseweb="select"] > div,
            [data-testid="stSidebar"] [data-baseweb="input"] > div {
                background: #f6f8fb !important;
                border: 1px solid #54749b !important;
                border-radius: 10px !important;
            }
            [data-testid="stSidebar"] [data-baseweb="select"] *:not(label),
            [data-testid="stSidebar"] [data-baseweb="input"] *:not(label) {
                color: #1d3349 !important;
            }
            [data-testid="stSidebar"] [data-baseweb="select"] svg {
                fill: #1d3349 !important;
            }
            [data-testid="stSidebar"] .stSelectbox label,
            [data-testid="stSidebar"] .stRadio label {
                color: #dbe8f7 !important;
            }
            [data-testid="stSidebar"] [role="radiogroup"] [data-checked="true"] p {
                color: #ffffff !important;
            }

            .app-container {
                width: 100%;
                max-width: min(1560px, 98vw);
                margin: 0 auto;
                padding: 0 0.25rem;
            }
            .top-nav {
                position: sticky;
                top: 0;
                z-index: 30;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1.1rem;
                border: 1px solid #c9daf5;
                border-radius: 16px;
                background: linear-gradient(180deg, #ffffff, #f9fbff);
                padding: 0.82rem 1rem;
                box-shadow: 0 10px 24px rgba(13, 71, 161, 0.1);
                margin-bottom: 1rem;
            }
            .nav-logo {
                font-size: 1.1rem;
                font-weight: 800;
                white-space: nowrap;
                min-width: 230px;
            }
            .nav-logo-box {
                display: flex;
                align-items: center;
                justify-content: flex-start;
            }
            .nav-brand {
                display: inline-flex;
                align-items: center;
                gap: 0;
                text-decoration: none !important;
            }
            .nav-logo-link {
                border: none;
                border-radius: 0;
                padding: 0;
                background: transparent;
            }
            .nav-logo-link:hover {
                opacity: 0.95;
            }
            .top-logo-img {
                width: 92px;
                height: 92px;
                object-fit: contain;
                border-radius: 10px;
            }
            .nav-logo-fallback-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 62px;
                height: 62px;
                border-radius: 14px;
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                color: #1e40af;
                font-size: 2rem;
            }
            .top-logo-wordmark {
                font-size: 2.15rem;
                font-weight: 900;
                line-height: 1;
            }
            .nav-links {
                display: flex;
                flex-wrap: wrap;
                justify-content: flex-end;
                gap: 0.48rem;
                overflow-x: visible;
                padding-bottom: 0.1rem;
            }
            .nav-link {
                border-radius: 999px;
                border: 1px solid #cfe1fb;
                background: #f7fbff;
                color: #1e3a8a;
                padding: 0.32rem 0.74rem;
                font-size: 0.82rem;
                font-weight: 600;
                text-decoration: none !important;
                white-space: nowrap;
            }
            .nav-link:hover {
                border-color: #93c5fd;
                background: #eff6ff;
            }
            .nav-link.active {
                border-color: #1E40AF;
                background: #dbeafe;
                color: #1E40AF;
            }
            .main-content {
                width: 100%;
            }
            .sidebar {
                border: 1px solid #d6e4f8;
                border-radius: 14px;
                background: linear-gradient(180deg, #1E40AF, #1d4ed8);
                color: #eff6ff;
                padding: 0.78rem;
                min-height: 0;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                height: fit-content;
                position: sticky;
                top: 4.9rem;
            }
            .sidebar-header {
                font-size: 1rem;
                font-weight: 800;
                margin-bottom: 0.65rem;
            }
            .sidebar-menu {
                display: flex;
                flex-direction: column;
                gap: 0.48rem;
            }
            .menu-item {
                display: block;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                padding: 0.45rem 0.56rem;
                color: #e2e8f0 !important;
                text-decoration: none !important;
                font-size: 0.84rem;
                font-weight: 600;
                background: rgba(255, 255, 255, 0.08);
            }
            .menu-item.active {
                background: rgba(249, 115, 22, 0.95);
                border-color: #fdba74;
                color: #ffffff !important;
            }
            .sidebar-footer {
                margin-top: 0.9rem;
                border-top: 1px solid rgba(255, 255, 255, 0.2);
                padding-top: 0.62rem;
            }
            .user-status {
                font-size: 0.75rem;
                color: #dbeafe;
            }
            .chat-container {
                border: 1px solid #dbe8f7;
                border-radius: 14px;
                background: #ffffff;
                min-height: 0;
                padding: 0.92rem;
                box-shadow: 0 10px 20px rgba(30, 64, 175, 0.05);
            }
            .chat-shell-header {
                border-bottom: 1px solid #dbe7f8;
                padding-bottom: 0.62rem;
                margin-bottom: 0.6rem;
                font-size: 1.06rem;
                font-weight: 800;
                color: #0D47A1;
                text-align: center;
                letter-spacing: 0.01em;
            }
            .chat-header {
                border: 1px solid #dbeafe;
                border-radius: 10px;
                background: #eff6ff;
                color: #1e3a8a;
                padding: 0.55rem 0.68rem;
                margin-bottom: 0.58rem;
                font-weight: 700;
            }
            .chat-messages {
                border: 1px solid #d8e6f8;
                border-radius: 14px;
                background: linear-gradient(180deg, #fbfdff, #f7fbff);
                padding: 0.7rem;
                margin-bottom: 0.7rem;
                max-width: 860px;
                margin-left: auto;
                margin-right: auto;
            }
            
            /* Chat Progress Bar */
            .chat-progress-container {
                margin: 1.5rem 0;
                padding: 1rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
            }
            
            .progress-bar-wrapper {
                width: 100%;
                height: 8px;
                background: rgba(255,255,255,0.3);
                border-radius: 10px;
                overflow: hidden;
            }
            
            .progress-bar {
                height: 100%;
                background: white;
                border-radius: 10px;
                transition: width 0.6s ease;
            }
            
            .progress-text {
                color: white;
                font-weight: 600;
                margin-top: 0.5rem;
                text-align: center;
            }
            
            /* Chat Messages Container */
            .chat-messages-container {
                max-width: 800px;
                margin: 2rem auto;
                padding: 0 1rem;
            }
            
            .message {
                display: flex;
                gap: 1rem;
                margin-bottom: 1.5rem;
                align-items: flex-start;
            }
            
            .assistant-message {
                flex-direction: row;
            }
            
            .user-message {
                flex-direction: row-reverse;
            }
            
            .message-avatar {
                font-size: 2rem;
                min-width: 48px;
                text-align: center;
            }
            
            .message-content {
                flex: 1;
                background: white;
                padding: 1rem 1.25rem;
                border-radius: 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }
            
            .assistant-message .message-content {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .user-message .message-content {
                background: #f0f2f5;
                color: #1c1e21;
            }
            
            .message-author {
                font-weight: 600;
                font-size: 0.85rem;
                margin-bottom: 0.35rem;
                opacity: 0.9;
            }
            
            .message-text {
                line-height: 1.6;
            }
            
            /* Transition Messages */
            .transition-message {
                margin: 1rem auto;
                padding: 0.75rem 1.25rem;
                background: #fff3cd;
                color: #856404;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
                font-style: italic;
                max-width: 700px;
            }
            
            /* Input Panel */
            .chat-input-panel {
                background: white;
                border: 2px solid #667eea;
                border-radius: 12px;
                padding: 1.25rem;
                margin: 1.5rem 0;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
            }
            
            .panel-header {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                color: #667eea;
                font-size: 1.1rem;
                margin-bottom: 0.5rem;
            }
            
            .panel-icon {
                font-size: 1.5rem;
            }
            
            .panel-help {
                color: #6c757d;
                font-size: 0.95rem;
                line-height: 1.5;
            }
            
            .privacy-note {
                background: #e7f3ff;
                border-left: 3px solid #2196f3;
                padding: 0.75rem 1rem;
                border-radius: 6px;
                font-size: 0.9rem;
                color: #0d47a1;
                margin: 1rem 0;
            }
            
            /* Input Area */
            .input-area {
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 12px;
                margin: 1.5rem 0;
            }
            
            /* Completion Banner */
            .completion-banner {
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                color: white;
                padding: 2rem;
                border-radius: 16px;
                text-align: center;
                font-size: 1.3rem;
                font-weight: 600;
                margin: 2rem 0;
                box-shadow: 0 8px 24px rgba(17, 153, 142, 0.3);
            }
            
            .banner-subtext {
                display: block;
                font-size: 0.95rem;
                font-weight: 400;
                margin-top: 0.5rem;
                opacity: 0.95;
            }
            
            /* Navigation Buttons */
            .nav-buttons {
                margin: 2rem 0 1rem;
            }
            
            /* Fade-in Animation */
            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .fade-in {
                animation: fadeIn 0.5s ease-out;
            }
            
            .chat-question-panel {
                max-width: 860px;
                margin: 0 auto 0.35rem;
                border-radius: 12px;
                border: 1px solid #cfe0f6;
                background: linear-gradient(180deg, #ffffff, #f3f8ff);
                padding: 0.55rem 0.7rem;
                color: #2b4769;
                font-size: 0.84rem;
            }
            .teman-role-footer {
                border-top: 1px solid #dbe7f8;
                margin-top: 1rem;
                padding-top: 0.5rem;
            }
            .chat-input {
                border-top: 1px solid #e2e8f0;
                padding-top: 0.5rem;
                margin-top: 0.25rem;
            }
            .message-input {
                width: 100%;
            }
            .send-button {
                width: 100%;
            }
            .chat-page-card {
                border: 1px solid #dbe6f9;
                border-radius: 12px;
                background: #f8fbff;
                padding: 0.75rem;
                color: #334155;
            }
            .chat-page-card h3 {
                margin-top: 0;
                color: #1e3a8a;
            }

            .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label {
                color: var(--text-main);
            }
            .stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea, .stApp select {
                font-family: "Nunito", "Poppins", "Avenir Next", "Segoe UI", sans-serif !important;
            }
            .stApp [data-testid="stMarkdownContainer"] p,
            .stApp [data-testid="stText"] p {
                color: var(--text-main);
            }
            .stApp [data-testid="stCaptionContainer"] p {
                color: var(--text-muted);
            }
            .stApp [role="radiogroup"] label p,
            .stApp [data-testid="stMultiSelect"] label p {
                color: #28466f !important;
            }
            .block-container {
                max-width: min(1560px, 98vw) !important;
                padding-top: 0.7rem;
                padding-bottom: 3rem;
            }

            @media (max-width: 1200px) {
                .sidebar {
                    position: relative;
                    top: auto;
                }
                .top-nav {
                    position: relative;
                }
                .nav-links {
                    justify-content: flex-start;
                }
            }
            
            /* Mobile Responsive for Chat */
            @media (max-width: 768px) {
                .message-avatar {
                    font-size: 1.5rem;
                    min-width: 40px;
                }
                
                .message-content {
                    padding: 0.875rem 1rem;
                }
                
                .chat-input-panel {
                    padding: 1rem;
                }
                
                .completion-banner {
                    font-size: 1.1rem;
                    padding: 1.5rem;
                }
                
                .chat-progress-container {
                    margin: 1rem 0;
                    padding: 0.75rem;
                }
                
                .chat-messages-container {
                    padding: 0 0.5rem;
                }
            }

            .stApp [data-baseweb="select"] > div,
            .stApp [data-baseweb="input"] > div,
            .stApp [data-baseweb="textarea"] > div {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 12px;
            }
            .stApp [data-baseweb="input"] input,
            .stApp [data-baseweb="textarea"] textarea,
            .stApp [data-baseweb="select"] input {
                color: var(--text-main) !important;
                -webkit-text-fill-color: var(--text-main) !important;
            }
            .stApp [data-baseweb="input"] input::placeholder,
            .stApp [data-baseweb="textarea"] textarea::placeholder,
            .stApp [data-baseweb="select"] input::placeholder {
                color: #8aa0b6 !important;
                opacity: 1 !important;
            }
            .stApp [data-baseweb="select"] > div:hover,
            .stApp [data-baseweb="input"] > div:hover,
            .stApp [data-baseweb="textarea"] > div:hover {
                border-color: #9ab5d9;
            }
            .stApp [role="radiogroup"] [data-checked="true"] div[role="radio"] {
                background-color: var(--trust-anchor) !important;
                border-color: var(--trust-anchor) !important;
            }
            .stApp input,
            .stApp button,
            .stApp textarea,
            .stApp select {
                accent-color: var(--trust-anchor) !important;
            }
            .stApp input[type="radio"],
            .stApp input[type="checkbox"] {
                accent-color: var(--trust-anchor) !important;
            }

            /* ── Metric widget text visibility fix ── */
            [data-testid="stMetric"] {
                color: var(--text-main) !important;
            }
            [data-testid="stMetric"] [data-testid="stMetricLabel"] {
                color: var(--text-main) !important;
            }
            [data-testid="stMetric"] [data-testid="stMetricLabel"] label,
            [data-testid="stMetric"] [data-testid="stMetricLabel"] p {
                color: var(--text-main) !important;
                -webkit-text-fill-color: var(--text-main) !important;
                font-weight: 600 !important;
            }
            [data-testid="stMetric"] [data-testid="stMetricValue"] {
                color: var(--trust-anchor) !important;
                -webkit-text-fill-color: var(--trust-anchor) !important;
                font-weight: 800 !important;
                font-size: 1.8rem !important;
            }
            [data-testid="stMetric"] [data-testid="stMetricDelta"] {
                color: var(--text-main) !important;
                -webkit-text-fill-color: var(--text-main) !important;
            }
            /* Also ensure st.caption under metrics is readable */
            [data-testid="stCaptionContainer"] {
                color: var(--text-muted) !important;
            }
            [data-testid="stCaptionContainer"] p {
                color: var(--text-muted) !important;
                -webkit-text-fill-color: var(--text-muted) !important;
            }

            .teman-hero {
                border-radius: 16px;
                padding: 1rem 1rem 0.8rem;
                margin-bottom: 0.8rem;
                background:
                    radial-gradient(circle at top right, rgba(16, 185, 129, 0.2), transparent 35%),
                    linear-gradient(160deg, var(--surface), var(--surface-soft));
                border: 1px solid var(--border);
                box-shadow: 0 2px 16px rgba(37, 99, 235, 0.08);
            }
            .teman-stepper {
                display: flex;
                gap: 0.32rem;
                flex-wrap: wrap;
                margin-bottom: 0.5rem;
            }
            .teman-step {
                padding: 0.18rem 0.58rem;
                border-radius: 999px;
                border: 1px solid var(--border);
                color: #5a6f83;
                font-size: 0.74rem;
                background: var(--surface);
            }
            .teman-step.active {
                border-color: var(--trust-anchor);
                background: var(--trust-anchor);
                color: #ffffff;
            }
            .teman-step.done {
                border-color: #a6c4ea;
                background: #eaf2ff;
                color: #2f5f9e;
            }
            .teman-card {
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 1rem;
                margin-bottom: 1rem;
                background: linear-gradient(160deg, var(--surface), #f5f8ff);
                box-shadow: 0 6px 20px rgba(59, 130, 246, 0.05);
            }
            .teman-outcome-window {
                border: 1px solid #c7d9f4;
                border-radius: 16px;
                padding: 1rem;
                margin-bottom: 1rem;
                background:
                    radial-gradient(circle at top right, rgba(16, 185, 129, 0.15), transparent 34%),
                    linear-gradient(150deg, #ffffff, #eef4ff);
                box-shadow: 0 8px 24px rgba(35, 70, 106, 0.08);
            }
            .teman-outcome-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: #24486f;
                margin-bottom: 0.4rem;
            }
            .teman-outcome-muted {
                color: #4f6882;
                font-size: 0.86rem;
                margin-bottom: 0.55rem;
            }
            .teman-outcome-item {
                border: 1px solid #d6e4f5;
                background: #ffffff;
                border-radius: 12px;
                padding: 0.62rem 0.72rem;
                margin-top: 0.45rem;
            }
            .teman-outcome-item-head {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.45rem;
            }
            .teman-rank-badge {
                display: inline-block;
                border-radius: 999px;
                padding: 0.08rem 0.5rem;
                background: #ede9fe;
                color: #5b21b6;
                font-size: 0.78rem;
                font-weight: 700;
            }
            .teman-outcome-name {
                font-weight: 650;
                color: #203d5d;
                font-size: 0.95rem;
            }
            .teman-outcome-meta {
                margin-top: 0.25rem;
                color: #4f6882;
                font-size: 0.82rem;
            }
            .teman-chip {
                display: inline-block;
                padding: 0.2rem 0.6rem;
                border-radius: 999px;
                background: #e8f0ff;
                margin-right: 0.4rem;
                margin-bottom: 0.3rem;
                font-size: 0.8rem;
                color: #325c90;
            }
            .teman-chat {
                border-left: 4px solid var(--trust-anchor);
                padding: 0.75rem 1rem;
                background: #eff6ff;
                border-radius: 10px;
                margin-bottom: 0.8rem;
                color: #254564;
            }
            .teman-summary {
                border-radius: 12px;
                border: 1px dashed #c9daf0;
                background: var(--surface);
                padding: 0.65rem 0.75rem;
                margin: 0.5rem 0 0.8rem;
            }
            .teman-muted {
                color: var(--text-muted);
                font-size: 0.86rem;
            }
            .teman-trust {
                border: 1px solid #cbd9ee;
                border-radius: 14px;
                padding: 1rem;
                margin-bottom: 0.9rem;
                background: linear-gradient(145deg, #ffffff, #f2f7ff);
            }
            .teman-trust-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: #23466a;
                margin-bottom: 0.4rem;
            }
            .teman-landing-hero {
                border: 1px solid #93c5fd;
                border-radius: 18px;
                padding: 1.15rem 1.05rem;
                margin-bottom: 0.9rem;
                background: var(--gradient-hero);
                box-shadow: 0 14px 32px rgba(30, 64, 175, 0.24);
            }
            .teman-landing-hero-v2 {
                position: relative;
                overflow: hidden;
            }
            .teman-landing-hero-v2::after {
                content: "";
                position: absolute;
                right: -40px;
                top: -36px;
                width: 140px;
                height: 140px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.16);
            }
            .teman-hero-eyebrow {
                color: #dbeafe;
                font-size: 0.8rem;
                font-weight: 600;
                letter-spacing: 0.01em;
                margin-bottom: 0.45rem;
            }
            .teman-landing-brand {
                display: flex;
                flex-direction: column;
                gap: 0.8rem;
                align-items: center;
                justify-content: center;
                height: 100%;
            }
            .teman-logo-frame {
                width: 100%;
                max-width: 240px;
                border: 1px solid #93c5fd;
                border-radius: 18px;
                background: linear-gradient(170deg, #ffffff, #f1f5ff);
                box-shadow: 0 10px 20px rgba(30, 64, 175, 0.12);
                padding: 0.6rem;
            }
            .teman-logo-fallback {
                border: 1px solid #93c5fd;
                border-radius: 18px;
                background: linear-gradient(170deg, #ffffff, #f1f5ff);
                box-shadow: 0 10px 20px rgba(30, 64, 175, 0.12);
                padding: 1rem 0.9rem;
                text-align: center;
                font-size: 2rem;
                font-weight: 800;
                color: #2563eb;
            }
            .teman-logo-fallback span {
                color: #F97316;
            }
            .teman-landing-title {
                font-size: 1.45rem;
                font-weight: 800;
                line-height: 1.2;
                color: #ffffff;
                margin-bottom: 0.4rem;
            }
            .teman-landing-subtitle {
                color: #e2e8f0;
                font-size: 0.95rem;
                margin-bottom: 0.7rem;
            }
            .teman-landing-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.42rem;
            }
            .teman-landing-chip {
                display: inline-block;
                border-radius: 999px;
                padding: 0.25rem 0.62rem;
                font-size: 0.79rem;
                color: #ffffff;
                background: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                backdrop-filter: blur(2px);
            }
            .teman-landing-card {
                border: 1px solid #d6e3f5;
                border-radius: 14px;
                background: var(--gradient-card);
                padding: 0.85rem 0.88rem;
                height: 100%;
                box-shadow: 0 8px 18px rgba(30, 41, 59, 0.06);
            }
            .teman-landing-card-title {
                font-size: 0.91rem;
                font-weight: 700;
                color: #1e3a8a;
                margin-bottom: 0.28rem;
            }
            .teman-landing-card-copy {
                color: #475569;
                font-size: 0.84rem;
            }
            .teman-landing-step {
                border: 1px dashed #bfdbfe;
                border-radius: 12px;
                padding: 0.65rem 0.7rem;
                background: #f8fbff;
                margin-bottom: 0.45rem;
            }
            .teman-landing-step-title {
                color: #1d4ed8;
                font-size: 0.86rem;
                font-weight: 700;
                margin-bottom: 0.2rem;
            }
            .teman-landing-step-copy {
                color: #64748b;
                font-size: 0.82rem;
            }
            .teman-hero-cta-wrap {
                border: 1px solid #c7d8f5;
                border-radius: 14px;
                padding: 0.75rem;
                margin-top: 0.75rem;
                margin-bottom: 0.85rem;
                background: #ffffff;
                box-shadow: 0 8px 16px rgba(30, 64, 175, 0.08);
            }
            .teman-trust-badges {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-top: 0.25rem;
            }
            .teman-trust-badge {
                border-radius: 999px;
                border: 1px solid #c7d2fe;
                background: #eef2ff;
                color: #3730a3;
                padding: 0.2rem 0.58rem;
                font-size: 0.76rem;
                font-weight: 600;
            }
            .teman-journey-panel {
                width: 100%;
                border: 1px solid #d5e2f7;
                border-radius: 14px;
                background: #ffffff;
                padding: 0.7rem 0.75rem;
            }
            .teman-journey-title {
                color: #1e3a8a;
                font-size: 0.84rem;
                font-weight: 700;
                margin-bottom: 0.4rem;
            }
            .teman-journey-item {
                color: #475569;
                font-size: 0.79rem;
                margin-bottom: 0.2rem;
            }
            .teman-value-banner {
                border: 1px solid #bfdbfe;
                border-radius: 12px;
                background: #eff6ff;
                color: #1e3a8a;
                padding: 0.62rem 0.75rem;
                margin-top: 0.4rem;
                margin-bottom: 0.9rem;
                font-size: 0.9rem;
            }
            .teman-social-title {
                margin-top: 0.2rem;
                margin-bottom: 0.45rem;
                color: #1e3a8a;
                font-size: 1rem;
                font-weight: 700;
            }
            .teman-proof-strip {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-bottom: 0.75rem;
            }
            .teman-proof-pill {
                border-radius: 999px;
                padding: 0.28rem 0.62rem;
                border: 1px solid #bfdbfe;
                background: #f0f9ff;
                color: #1e40af;
                font-size: 0.78rem;
                font-weight: 600;
            }
            .teman-testimonial {
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                background: #ffffff;
                padding: 0.75rem;
                color: #334155;
                font-size: 0.84rem;
                margin-bottom: 0.7rem;
                box-shadow: 0 6px 14px rgba(15, 23, 42, 0.05);
            }
            .teman-testimonial-meta {
                margin-top: 0.35rem;
                color: #64748b;
                font-size: 0.76rem;
                font-weight: 600;
            }

            .hero-section,
            .problem-solution-section,
            .how-it-works-section,
            .features-section,
            .social-proof-section,
            .cta-section {
                border: 1px solid #dbe7fb;
                border-radius: 18px;
                background: #ffffff;
                box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
                padding: 1rem;
                margin-bottom: 0.95rem;
            }
            .hero-section {
                background:
                    radial-gradient(circle at 92% 18%, rgba(249, 115, 22, 0.18), transparent 35%),
                    linear-gradient(145deg, #ffffff, #f8fbff);
            }
            .hero-topline {
                display: inline-block;
                border-radius: 999px;
                padding: 0.28rem 0.7rem;
                background: #e0ebff;
                color: #1e3a8a;
                font-size: 0.78rem;
                font-weight: 700;
                margin-bottom: 0.55rem;
            }
            .hero-headline {
                margin: 0;
                font-size: clamp(1.4rem, 3.2vw, 2rem);
                line-height: 1.15;
                color: #0f2b79;
                margin-bottom: 0.35rem;
            }
            .brand-teman { color: #1E40AF; }
            .brand-edu { color: #F97316; }
            .hero-subline {
                margin: 0;
                color: #42536d;
                max-width: 760px;
                font-size: 0.96rem;
            }
            .hero-mascot {
                border: 1px solid #d9e6fd;
                border-radius: 18px;
                padding: 0.4rem;
                background: #ffffff;
                box-shadow: 0 8px 18px rgba(30, 64, 175, 0.12);
            }
            .hero-panel {
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                background: #f8fbff;
                padding: 0.72rem 0.75rem;
                height: 100%;
            }
            .panel-title {
                color: #1e3a8a;
                font-size: 0.87rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }
            .panel-item {
                color: #475569;
                font-size: 0.81rem;
                margin-bottom: 0.16rem;
            }
            .section-heading {
                color: #0f2f88;
                font-size: 1.1rem;
                font-weight: 800;
                margin-bottom: 0.6rem;
            }
            .problem-solution-grid,
            .steps-grid,
            .feature-grid,
            .testimonial-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.65rem;
            }
            .steps-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
            .feature-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
            .testimonial-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .problem-card,
            .solution-card,
            .feature-card,
            .step-card,
            .testimonial-card {
                border: 1px solid #d8e4f5;
                border-radius: 12px;
                background: #ffffff;
                padding: 0.7rem 0.75rem;
            }
            .card-kicker {
                color: #1e3a8a;
                font-weight: 700;
                font-size: 0.84rem;
                margin-bottom: 0.3rem;
            }
            .problem-card ul,
            .solution-card ul {
                margin: 0;
                padding-left: 1rem;
                color: #475569;
                font-size: 0.83rem;
            }
            .step-card {
                display: flex;
                gap: 0.55rem;
                align-items: flex-start;
                color: #334155;
                font-size: 0.83rem;
            }
            .step-num {
                min-width: 24px;
                height: 24px;
                border-radius: 999px;
                background: #1e40af;
                color: #ffffff;
                font-size: 0.78rem;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
            }
            .plan-visual {
                border: 1px solid #d9e7fb;
                border-radius: 12px;
                background: #f8fbff;
                padding: 0.62rem 0.7rem;
                margin-top: 0.65rem;
            }
            .plan-title {
                color: #1e3a8a;
                font-weight: 700;
                font-size: 0.82rem;
                margin-bottom: 0.3rem;
            }
            .plan-track {
                display: flex;
                justify-content: space-between;
                color: #64748b;
                font-size: 0.72rem;
                margin-bottom: 0.22rem;
            }
            .plan-bar {
                height: 8px;
                border-radius: 999px;
                background: #dbeafe;
                overflow: hidden;
            }
            .plan-fill {
                width: 72%;
                height: 100%;
                background: linear-gradient(90deg, #1e40af, #f97316);
            }
            .feature-card {
                color: #475569;
                font-size: 0.83rem;
                line-height: 1.45;
            }
            .trust-banner {
                border-radius: 999px;
                background: #1e40af;
                color: #ffffff;
                display: inline-block;
                padding: 0.3rem 0.72rem;
                font-size: 0.8rem;
                font-weight: 700;
                margin-bottom: 0.55rem;
            }
            .testimonial-person {
                display: flex;
                align-items: center;
                gap: 0.45rem;
                margin-bottom: 0.38rem;
            }
            .testimonial-photo {
                width: 42px;
                height: 42px;
                border-radius: 999px;
                border: 2px solid #e2e8f0;
                object-fit: cover;
            }
            .testimonial-name {
                color: #1e3a8a;
                font-weight: 700;
                font-size: 0.82rem;
            }
            .testimonial-role {
                color: #64748b;
                font-size: 0.74rem;
            }
            .testimonial-card p {
                margin: 0;
                color: #475569;
                font-size: 0.81rem;
            }
            .partner-strip-title {
                color: #1e3a8a;
                font-size: 0.86rem;
                font-weight: 700;
                margin-top: 0.65rem;
                margin-bottom: 0.35rem;
            }
            .partner-strip {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
            }
            .partner-logo {
                border-radius: 999px;
                border: 1px solid #c7d2fe;
                padding: 0.24rem 0.56rem;
                background: #eef2ff;
                color: #1e3a8a;
                font-size: 0.75rem;
                font-weight: 600;
            }
            .privacy-box {
                margin-top: 0.65rem;
                border: 1px solid #fed7aa;
                background: #fff7ed;
                color: #9a3412;
                border-radius: 10px;
                padding: 0.55rem 0.65rem;
                font-size: 0.8rem;
            }
            .cta-section {
                position: relative;
                background: linear-gradient(140deg, #ffffff, #f8fafc);
            }
            .landing-centered {
                max-width: 1080px;
                margin: 0 auto;
                text-align: center;
            }
            .landing-centered .hero-subline {
                margin-left: auto;
                margin-right: auto;
            }
            .landing-centered .teman-trust-badges {
                justify-content: center;
            }
            .landing-centered .steps-grid {
                justify-content: center;
            }
            .landing-centered .step-card {
                justify-content: center;
                text-align: center;
            }
            .landing-centered .privacy-box {
                text-align: center;
            }
            .cta-copy {
                margin: 0;
                color: #475569;
                font-size: 0.9rem;
                margin-bottom: 0.35rem;
            }
            .cta-next {
                color: #0f766e;
                font-weight: 700;
                font-size: 0.78rem;
                margin-bottom: 0.55rem;
            }
            [data-testid="stButton"] button {
                border-radius: 999px;
                padding: 0.52rem 1rem;
                border: 1px solid transparent;
                background: linear-gradient(145deg, #ff8c1a, var(--growth-path));
                color: #ffffff !important;
                font-weight: 600;
            }
            [data-testid="stButton"] button p,
            [data-testid="stDownloadButton"] button p {
                color: inherit !important;
            }
            [data-testid="stButton"] button:hover {
                background: linear-gradient(145deg, #ff7a00, #ea5f00);
                color: #ffffff !important;
            }
            [data-testid="stButton"] button[kind="secondary"],
            [data-testid="stButton"] button[data-testid="baseButton-secondary"] {
                background: #eff5ff !important;
                color: #254a77 !important;
                border: 1px solid #b7cef0 !important;
            }
            [data-testid="stButton"] button[kind="secondary"]:hover,
            [data-testid="stButton"] button[data-testid="baseButton-secondary"]:hover {
                background: #e4efff !important;
                color: #1d426c !important;
                border: 1px solid #98b7e5 !important;
            }
            [data-testid="stButton"] button[kind="primary"],
            [data-testid="stButton"] button[data-testid="baseButton-primary"] {
                background: linear-gradient(145deg, #ff8c1a, var(--growth-path)) !important;
                color: #ffffff !important;
                border: 1px solid #de6800 !important;
            }
            [data-testid="stButton"] button[kind="primary"]:hover,
            [data-testid="stButton"] button[data-testid="baseButton-primary"]:hover {
                background: linear-gradient(145deg, #ff7a00, #d95f00) !important;
                color: #ffffff !important;
                border: 1px solid #b95000 !important;
            }
            [data-testid="stButton"] button:focus,
            [data-testid="stButton"] button:focus-visible,
            [data-testid="stButton"] button:active {
                outline: none !important;
                border-color: var(--trust-anchor) !important;
                box-shadow: 0 0 0 3px rgba(10, 62, 168, 0.28) !important;
            }
            [data-testid="stButton"] button:disabled {
                background: #e8edf5 !important;
                color: #778aa2 !important;
                border: 1px solid #d1dbe7 !important;
                opacity: 1 !important;
            }
            .teman-breathe {
                animation: temanBreathe 2.2s ease-in-out infinite !important;
                box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.45);
            }
            .teman-primary-glow {
                box-shadow: 0 8px 18px rgba(255, 122, 0, 0.25) !important;
            }
            @keyframes temanMessageIn {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            @keyframes temanBreathe {
                0% {transform: scale(1); box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.45);}
                70% {transform: scale(1.02); box-shadow: 0 0 0 10px rgba(249, 115, 22, 0);}
                100% {transform: scale(1); box-shadow: 0 0 0 0 rgba(249, 115, 22, 0);}
            }
            .stDownloadButton > button {
                border-radius: 10px !important;
                color: #ffffff !important;
            }
            .teman-quick-title {
                margin-top: 0.2rem;
                margin-bottom: 0.4rem;
                color: #2f4f72;
                font-weight: 600;
            }
            .teman-meter {
                margin-top: 0.4rem;
                margin-bottom: 0.45rem;
            }
            .teman-meter-head {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.88rem;
                color: #45627e;
                margin-bottom: 0.2rem;
            }
            .teman-meter-track {
                width: 100%;
                height: 11px;
                border-radius: 999px;
                background: #dbe5f2;
                overflow: hidden;
                border: 1px solid #c4d4e9;
            }
            .teman-meter-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--trust-anchor), var(--growth-path));
            }
            .teman-privacy {
                margin-top: 0.45rem;
                margin-bottom: 0.2rem;
                color: #51667c;
                font-size: 0.85rem;
            }
            @media (max-width: 768px) {
                .block-container {
                    max-width: 100% !important;
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                }
                .top-nav {
                    flex-direction: column;
                    align-items: flex-start;
                }
                .top-logo-wordmark {
                    font-size: 1.75rem;
                }
                .top-logo-img {
                    width: 72px;
                    height: 72px;
                }
                .nav-logo-fallback-icon {
                    width: 52px;
                    height: 52px;
                    font-size: 1.5rem;
                }
                .nav-links {
                    width: 100%;
                    justify-content: flex-start;
                }
                .sidebar {
                    min-height: auto;
                }
                .chat-container {
                    min-height: auto;
                }
                .teman-landing-title {font-size: 1.2rem;}
                .teman-landing-subtitle {font-size: 0.88rem;}
                .teman-hero-cta-wrap {padding: 0.62rem;}
                .teman-proof-pill {font-size: 0.74rem;}
                .teman-testimonial {font-size: 0.8rem;}
                .teman-value-banner {font-size: 0.84rem;}
                .problem-solution-grid,
                .steps-grid,
                .feature-grid,
                .testimonial-grid {
                    grid-template-columns: 1fr;
                }
                .hero-headline {font-size: 1.38rem;}
                .section-heading {font-size: 1rem;}
                .cta-section [data-testid="stButton"] button {
                    min-height: 50px;
                    font-size: 1rem;
                }
            }

            [data-testid="stSidebar"] [role="radiogroup"] label p {
                color: #eaf3ff !important;
                opacity: 1 !important;
            }
            [data-testid="stSidebar"] [role="radiogroup"] [data-checked="true"] + div p {
                color: #ffffff !important;
                font-weight: 600;
            }

            /* Final visibility and centering overrides */
            .block-container {
                max-width: min(1180px, 94vw) !important;
                margin: 0 auto !important;
                padding-top: 0.8rem !important;
                padding-bottom: 2.5rem !important;
            }
            .top-nav {
                max-width: min(1180px, 94vw);
                margin: 0 auto 1rem;
            }
            .top-logo-wordmark {
                font-size: clamp(1.65rem, 2vw, 2rem);
            }
            .chat-shell-header {
                font-size: clamp(1.3rem, 2.1vw, 1.7rem);
                color: #123e86;
                margin-bottom: 0.9rem;
            }
            .chat-page-card {
                max-width: 980px;
                margin: 0 auto 1rem;
                border: 1px solid #cadcf3;
                border-radius: 16px;
                background: linear-gradient(150deg, #ffffff 0%, #f7fbff 100%);
                box-shadow: 0 10px 24px rgba(30, 64, 175, 0.1);
                padding: 1.15rem 1.2rem;
                position: relative;
                overflow: hidden;
            }
            .chat-page-card::before {
                content: "";
                position: absolute;
                top: -68px;
                right: -48px;
                width: 190px;
                height: 190px;
                border-radius: 999px;
                background: radial-gradient(circle, rgba(249, 115, 22, 0.2) 0%, rgba(249, 115, 22, 0) 70%);
                pointer-events: none;
            }
            .chat-page-card::after {
                content: "";
                position: absolute;
                bottom: -78px;
                left: -50px;
                width: 210px;
                height: 210px;
                border-radius: 999px;
                background: radial-gradient(circle, rgba(30, 64, 175, 0.16) 0%, rgba(30, 64, 175, 0) 72%);
                pointer-events: none;
            }
            .chat-page-card h3 {
                font-size: 1.9rem;
                color: #123e86;
                margin-bottom: 0.45rem;
                text-align: center;
                position: relative;
                z-index: 1;
            }
            .chat-page-card p {
                font-size: 1.03rem;
                color: #355575;
                line-height: 1.55;
                margin-bottom: 0;
                text-align: center;
                position: relative;
                z-index: 1;
            }
            .student-chat-hero-logo {
                width: min(210px, 44vw);
                margin: 0 auto 0.45rem;
                display: block;
                filter: drop-shadow(0 10px 20px rgba(13, 71, 161, 0.18));
                animation: studentLogoFloat 3.8s ease-in-out infinite;
                position: relative;
                z-index: 1;
            }
            .chat-messages-container {
                max-width: 980px;
                margin: 1rem auto;
                padding: 0;
            }
            .chat-messages {
                max-width: 980px;
                margin: 0 auto;
                padding: 0.95rem;
                border: 1px solid #d2e1f5;
                background: linear-gradient(180deg, #ffffff, #f8fbff);
            }
            .chat-progress-container {
                max-width: 980px;
                margin: 1rem auto 1.2rem;
                border-radius: 14px;
                padding: 0.95rem 1rem;
                background: linear-gradient(135deg, #1E40AF 0%, #1D4ED8 58%, #F97316 100%);
                box-shadow: 0 10px 26px rgba(30, 64, 175, 0.2);
            }
            .progress-bar-wrapper {
                height: 10px;
                background: rgba(255, 255, 255, 0.34);
            }
            .progress-bar {
                background: #ffffff;
            }
            .progress-text {
                margin-top: 0.56rem;
                font-size: 1.02rem;
                font-weight: 700;
                color: #ffffff;
            }
            .message {
                margin-bottom: 1rem;
            }
            .message-avatar {
                font-size: 1.72rem;
                min-width: 40px;
            }
            .message-content {
                border-radius: 14px;
                padding: 0.9rem 1rem;
                box-shadow: 0 6px 16px rgba(30, 64, 175, 0.09);
            }
            .assistant-message .message-content {
                background: linear-gradient(130deg, #1E40AF 0%, #1D4ED8 100%);
                color: #ffffff;
            }
            .user-message .message-content {
                border: 1px solid #c6d7f1;
                background: #eef5ff;
                color: #1f3b56;
            }
            .message-author {
                font-size: 0.92rem;
                font-weight: 700;
                margin-bottom: 0.38rem;
            }
            .message-text {
                font-size: 1.02rem;
                line-height: 1.52;
            }
            .transition-message {
                max-width: 980px;
                margin: 0.9rem auto;
                border-left: 4px solid #f97316;
                background: #fff7ed;
                color: #9a3412;
                font-size: 0.95rem;
                font-style: normal;
            }
            .chat-input-panel {
                max-width: 980px;
                margin: 1rem auto;
                border: 1px solid #9ebef0;
                box-shadow: 0 6px 16px rgba(30, 64, 175, 0.08);
                background: #ffffff;
            }
            .panel-header {
                font-size: 1.05rem;
                color: #1E40AF;
            }
            .panel-help {
                color: #3a546f;
                font-size: 0.98rem;
                line-height: 1.5;
            }
            .privacy-note {
                max-width: 980px;
                margin: 0.7rem auto 0;
                border-left: 4px solid #1E40AF;
                border-radius: 8px;
                background: #ecf4ff;
                color: #1f496f;
                font-size: 0.93rem;
            }
            .input-area {
                max-width: 980px;
                margin: 0 auto 1rem;
                padding: 1rem;
                border: 1px solid #cfdef3;
                background: #f8fbff;
            }
            .nav-buttons {
                max-width: 980px;
                margin: 1rem auto 0.5rem;
            }
            .stApp [data-testid="stCaptionContainer"] p {
                color: #42607f !important;
                font-size: 0.94rem !important;
                opacity: 1 !important;
            }
            .stApp [data-testid="stMarkdownContainer"] p,
            .stApp [data-testid="stText"] p {
                font-size: 1rem;
                line-height: 1.55;
            }
            .stApp [data-testid="stMultiSelect"] label p,
            .stApp [data-testid="stSelectbox"] label p,
            .stApp [data-testid="stNumberInput"] label p,
            .stApp [data-testid="stSlider"] label p {
                font-size: 1rem !important;
                color: #1f3f66 !important;
                font-weight: 700 !important;
                opacity: 1 !important;
            }
            .stApp [data-testid="stMultiSelect"] [data-baseweb="tag"] {
                background: #e8f1ff !important;
                border: 1px solid #b9cfee !important;
                color: #1c4371 !important;
            }
            .stApp [data-testid="stMultiSelect"] [data-baseweb="tag"] span {
                color: #1c4371 !important;
                font-size: 0.9rem !important;
            }
            .stApp [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
            .stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div {
                min-height: 48px !important;
                border-radius: 12px !important;
                border: 1px solid #bcd1ee !important;
                background: #ffffff !important;
                opacity: 1 !important;
            }
            .stApp [data-testid="stMultiSelect"] input,
            .stApp [data-testid="stSelectbox"] input {
                color: #1f3f66 !important;
                -webkit-text-fill-color: #1f3f66 !important;
                font-size: 0.96rem !important;
            }
            .stApp [data-testid="stSelectbox"] [data-baseweb="select"] *,
            .stApp [data-testid="stMultiSelect"] [data-baseweb="select"] * {
                color: #111827 !important;
                -webkit-text-fill-color: #111827 !important;
                opacity: 1 !important;
            }
            .stApp [data-baseweb="input"] input,
            .stApp [data-baseweb="textarea"] textarea,
            .stApp [data-baseweb="select"] input,
            .stApp input[type="text"],
            .stApp input[type="number"],
            .stApp [role="spinbutton"] {
                color: #111827 !important;
                -webkit-text-fill-color: #111827 !important;
                caret-color: #111827 !important;
            }
            .stApp [data-baseweb="input"] input::placeholder,
            .stApp [data-baseweb="textarea"] textarea::placeholder,
            .stApp [data-baseweb="select"] input::placeholder,
            .stApp input[type="text"]::placeholder,
            .stApp input[type="number"]::placeholder {
                color: #6b7280 !important;
                -webkit-text-fill-color: #6b7280 !important;
                opacity: 1 !important;
            }
            .stApp [data-baseweb="popover"] *,
            .stApp [role="listbox"] *,
            .stApp [data-baseweb="menu"] * {
                color: #111827 !important;
                -webkit-text-fill-color: #111827 !important;
            }
            .stApp [data-testid="stMultiSelect"] input::placeholder,
            .stApp [data-testid="stSelectbox"] input::placeholder {
                color: #6c86a5 !important;
                opacity: 1 !important;
            }
            [data-testid="stButton"] button {
                min-height: 46px;
                font-size: 0.98rem;
                font-weight: 700;
            }
            @keyframes studentLogoFloat {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-7px); }
                100% { transform: translateY(0px); }
            }
            @media (max-width: 768px) {
                .block-container {
                    max-width: 100% !important;
                    padding-left: 0.82rem !important;
                    padding-right: 0.82rem !important;
                }
                .chat-page-card {
                    padding: 0.9rem 0.9rem;
                }
                .chat-page-card h3 {
                    font-size: 1.45rem;
                }
                .chat-page-card p {
                    font-size: 0.96rem;
                }
                .student-chat-hero-logo {
                    width: min(170px, 52vw);
                }
                .message-text {
                    font-size: 0.96rem;
                }
                .progress-text {
                    font-size: 0.94rem;
                }
                [data-testid="stButton"] button {
                    min-height: 44px;
                    font-size: 0.94rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_progress(step: int, total: int) -> None:
    chips = []
    for i in range(1, total + 1):
        klass = "teman-step"
        if i < step:
            klass += " done"
        elif i == step:
            klass += " active"
        chips.append(f"<span class='{klass}'>Step {i}</span>")
    st.markdown(f"<div class='teman-stepper'>{''.join(chips)}</div>", unsafe_allow_html=True)
    pct = max(0.0, min(1.0, step / max(1, total)))
    render_meter("Step progress", pct, f"Step {step}/{total}")


def render_meter(label: str, pct: float, value_text: str | None = None) -> None:
    pct = max(0.0, min(1.0, pct))
    pct_text = value_text or f"{int(round(pct * 100))}%"
    st.markdown(
        f"""
        <div class="teman-meter">
            <div class="teman-meter-head">
                <span>{label}</span>
                <span>{pct_text}</span>
            </div>
            <div class="teman-meter-track">
                <div class="teman-meter-fill" style="width: {pct * 100:.1f}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_disclaimers(language: str, custom_snippets: dict[str, str] | None = None) -> None:
    snippets = custom_snippets or {}
    st.caption(snippets.get("disclaimer_general", t(language, "disclaimer_general")))
    st.caption(snippets.get("disclaimer_visa", t(language, "disclaimer_visa")))
    st.caption(snippets.get("disclaimer_scholarship", t(language, "disclaimer_scholarship")))


def render_outcome_window(recommendations: list[dict[str, Any]]) -> None:
    st.markdown('<div class="teman-outcome-window">', unsafe_allow_html=True)
    st.markdown('<div class="teman-outcome-title">Outcome Window: Top 3 Most Suitable Pathways</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="teman-outcome-muted">A focused short-list so you can decide faster without information overload.</div>',
        unsafe_allow_html=True,
    )
    for idx, rec in enumerate(recommendations[:3], start=1):
        title = escape(rec.get("pathway_title", "Pathway"))
        fit_score = int(rec.get("fit_score", 0))
        readiness_score = int(rec.get("readiness_score", 0))
        cost_text = escape(rec.get("cost_estimate_text", "Cost estimate unavailable"))
        uni_options = rec.get("university_options", [])
        top_uni = ""
        if uni_options:
            top_item = uni_options[0]
            top_uni = f" | {escape(top_item.get('program_name', 'Program'))} @ {escape(top_item.get('university_name', 'University'))}"
        st.markdown(
            f"""
            <div class="teman-outcome-item">
                <div class="teman-outcome-item-head">
                    <span class="teman-rank-badge">Top {idx}</span>
                    <span class="teman-outcome-name">{title}</span>
                </div>
                <div class="teman-outcome-meta">Fit {fit_score} | Readiness {readiness_score} | {cost_text}{top_uni}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_pathway_card(recommendation: dict[str, Any], language: str) -> None:
    st.markdown('<div class="teman-card">', unsafe_allow_html=True)
    st.subheader(recommendation["pathway_title"])
    st.write(recommendation["pathway_summary"])

    st.markdown(
        f"""
        <span class='teman-chip'>Fit {recommendation['fit_score']}</span>
        <span class='teman-chip'>Readiness {recommendation['readiness_score']}</span>
        <span class='teman-chip'>Scholarship {recommendation['scholarship_likelihood']}</span>
        <span class='teman-chip'>{recommendation['cost_estimate_text']}</span>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(t(language, "explainability")):
        exp = recommendation["explanation"]
        st.markdown("**Matched conditions**")
        for item in exp["matched_conditions"][:8]:
            st.write(f"- {item}")

        st.markdown("**Borderline conditions**")
        for item in exp["borderline_conditions"][:6]:
            st.write(f"- {item}")

        st.markdown("**Missing conditions**")
        for item in exp["missing_conditions"][:6]:
            st.write(f"- {item}")

        st.caption(exp["ranking_reason"])

    st.markdown(f"**{t(language, 'gaps')}**")
    for gap in recommendation.get("readiness_gaps", []):
        st.checkbox(gap, value=False, key=f"gap_{recommendation['rule_id']}_{gap}")

    university_options = recommendation.get("university_options", [])
    if university_options:
        st.markdown("**Specific university options you can apply to**")
        for option in university_options:
            title = f"{option.get('program_name', 'Program')} - {option.get('university_name', 'University')} ({option.get('country', '-')})"
            with st.expander(title):
                st.write(f"Match score: {option.get('match_score', 0)}")
                st.write(f"Tuition: {option.get('tuition_yearly_text', '-')}")
                st.write(f"Intakes: {', '.join(option.get('intake_terms', [])) or '-'}")
                st.write(f"Application timeline: {option.get('application_deadline_text') or '-'}")
                st.write(f"PTPTN eligible: {'Yes' if option.get('ptptn_eligible') else 'No'}")
                st.write(f"MOHE listed: {'Yes' if option.get('mohe_listed') else 'No'}")
                qs_rank = option.get("qs_overall_rank")
                st.write(f"QS overall rank (snapshot): {qs_rank if qs_rank else 'Check source for latest'}")
                for reason in option.get("fit_reasons", []):
                    st.write(f"- {reason}")
                if option.get("cautions"):
                    st.caption("Watch-outs")
                    for item in option.get("cautions", []):
                        st.write(f"- {item}")
                if option.get("application_url"):
                    st.markdown(f"[Apply / Program page]({escape(option['application_url'])})")
                if option.get("contact_email"):
                    st.write(f"Admissions contact: {option.get('contact_email')}")
                source_trace = option.get("source_trace", [])
                if source_trace:
                    st.caption("Source trace")
                    for src in source_trace:
                        label = src.get("source", "Source")
                        url = src.get("url", "")
                        if url:
                            st.markdown(f"- {label}: [{url}]({url})")
                        else:
                            st.write(f"- {label}")

    st.info(recommendation["visa_note"])
    st.write(f"Next steps: {recommendation['next_steps']}")
    st.markdown("</div>", unsafe_allow_html=True)


def inject_interaction_js() -> None:
    return
