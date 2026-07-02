"""
QRQC — Streamlit Arayüzü  (v3 — Dinamik Sidebar Navigasyon)
==============================================================
Endüstriyel kalite yönetim paneli.
Çalıştırmak için:  streamlit run app.py
"""

from __future__ import annotations

import math
import os
import base64
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import plotly.express as px

# ── Models importu ─────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)

from models import (  # noqa: E402
    AKSIYON_DURUM,
    KATEGORI_SQCD,
    VARDIYA_SECENEKLERI,
    Action,
    Issue,
    Meeting,
    SessionLocal,
    User,
    init_db,
)

init_db()


# ═══════════════════════════════════════════════════════════════════════════
#  DB Session Yönetimi
# ═══════════════════════════════════════════════════════════════════════════
@contextmanager
def get_db():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()



# ═══════════════════════════════════════════════════════════════════════════
#  Session State — Sayfa Takibi
# ═══════════════════════════════════════════════════════════════════════════
PAGES = {
    "sabah_toplantisi": "📅  Sabah Toplantısı",
    "aksiyon_takip":    "📊  Aksiyon Takip Panosu",
    "kok_neden":        "🔍  Kök Neden Analizi",
    "geciken":          "⚠️  Geciken Aksiyonlar",
    "acik_problemler":  "🔴  Açık Problemler",
    "gorsel_analiz":    "📊  Görsel Analiz",
}

if "current_page" not in st.session_state:
    st.session_state.current_page = "sabah_toplantisi"
if "selected_meeting_id" not in st.session_state:
    st.session_state.selected_meeting_id = None
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None

if not st.session_state.is_logged_in:
    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    .main .block-container {
        max-width: 500px !important;
        padding-top: 4rem !important;
    }
    div[data-testid="stForm"] {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 12px; padding: 24px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div class="qrqc-header" style="text-align: center; margin-top: 30px; margin-bottom: 24px; padding: 24px 16px;">
            <h1 style="font-size: 1.6rem; margin-bottom: 6px;">DEBAK QRQC APP</h1>
            <p style="font-size: 0.85rem;">Kurumsal Kalite ve Hızlı Müdahale Yönetim Sistemi</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    tab_login, tab_register = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
    
    with tab_login:
        with st.form("login_form"):
            l_email = st.text_input("E-posta Adresi", placeholder="ad.soyad@debak.com.tr")
            l_password = st.text_input("Şifre", type="password", placeholder="••••••••")
            l_submit = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            
            if l_submit:
                if not l_email or not l_password:
                    st.error("Lütfen tüm alanları doldurun.")
                else:
                    login_success = False
                    user_data = None
                    with get_db() as db:
                        user = db.query(User).filter(User.eposta == l_email.strip(), User.sifre == l_password).first()
                        if user:
                            login_success = True
                            user_data = {
                                "id": user.id,
                                "ad_soyad": user.ad_soyad,
                                "eposta": user.eposta,
                                "bolum": user.bolum,
                                "gorev": user.gorev
                            }
                    if login_success:
                        st.session_state.is_logged_in = True
                        st.session_state.user_info = user_data
                        st.success(f"Hoş geldiniz, {user_data['ad_soyad']}!")
                        st.rerun()
                    else:
                        st.error("E-posta veya şifre hatalı!")
                            
    with tab_register:
        with st.form("register_form"):
            r_name = st.text_input("Ad Soyad", placeholder="Ahmet Yılmaz")
            r_email = st.text_input("E-posta Adresi", placeholder="ad.soyad@debak.com.tr")
            r_password = st.text_input("Şifre", type="password", placeholder="Minimum 6 karakter")
            
            r_bolum = st.selectbox("Bölüm", ["Üretim", "Kalite", "Bakım", "Metot", "Lojistik", "Yönetim", "Diğer"])
            r_gorev = st.selectbox("Görev", ["Operatör", "Takım Lideri", "Mühendis", "Müdür", "Yönetici", "Diğer"])
            
            r_submit = st.form_submit_button("Kayıt Ol", type="primary", use_container_width=True)
            
            if r_submit:
                if not r_name.strip() or not r_email.strip() or not r_password:
                    st.error("Lütfen tüm zorunlu alanları doldurun.")
                elif not r_email.strip().endswith("@debak.com.tr"):
                    st.error("Yalnızca @debak.com.tr uzantılı kurumsal e-posta adresleri kayıt olabilir.")
                else:
                    register_success = False
                    user_data = None
                    error_msg = None
                    with get_db() as db:
                        existing = db.query(User).filter(User.eposta == r_email.strip()).first()
                        if existing:
                            error_msg = "Bu e-posta adresiyle zaten kayıt yapılmış."
                        else:
                            new_user = User(
                                ad_soyad=r_name.strip(),
                                eposta=r_email.strip(),
                                sifre=r_password,
                                bolum=r_bolum,
                                gorev=r_gorev
                            )
                            db.add(new_user)
                            db.flush()
                            register_success = True
                            user_data = {
                                "id": new_user.id,
                                "ad_soyad": new_user.ad_soyad,
                                "eposta": new_user.eposta,
                                "bolum": new_user.bolum,
                                "gorev": new_user.gorev
                            }
                    if register_success:
                        st.session_state.is_logged_in = True
                        st.session_state.user_info = user_data
                        st.success("Kayıt başarılı! Giriş yapıldı.")
                        st.rerun()
                    elif error_msg:
                        st.error(error_msg)
    st.stop()


def navigate(page_key: str) -> None:
    """Sayfa değiştirmek için session state'i günceller."""
    st.session_state.current_page = page_key


# ═══════════════════════════════════════════════════════════════════════════
#  Sayfa Değiştirme
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
#  Sayfa Yapılandırması
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="QRQC Yönetim Paneli",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Sidebar ─────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
section[data-testid="stSidebar"] hr { border-color: #334155; }

/* ── Nav Kart Butonları (Sidebar) ────────────────────────────────────── */
section[data-testid="stSidebar"] div.stButton button[kind="secondary"] {
    width: 100% !important;
    background-color: #1E293B !important;
    color: #FFFFFF !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    min-height: 48px !important;
    padding: 10px 16px !important;
    text-align: left !important;
    display: flex !important;
    justify-content: flex-start !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
}
section[data-testid="stSidebar"] div.stButton button[kind="secondary"] p {
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    margin: 0 !important;
}
section[data-testid="stSidebar"] div.stButton button[kind="secondary"]:hover {
    border-color: #3B82F6 !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}
section[data-testid="stSidebar"] div.stButton button[kind="secondary"]:hover p {
    color: #FFFFFF !important;
}

/* Aktif nav kart (Primary) */
section[data-testid="stSidebar"] div.stButton button[kind="primary"] {
    width: 100% !important;
    background-color: #3B82F6 !important;
    color: #FFFFFF !important;
    border: 1px solid #3B82F6 !important;
    border-radius: 12px !important;
    min-height: 48px !important;
    padding: 10px 16px !important;
    text-align: left !important;
    display: flex !important;
    justify-content: flex-start !important;
    box-shadow: 0 4px 20px rgba(59,130,246,0.35) !important;
}
section[data-testid="stSidebar"] div.stButton button[kind="primary"] p {
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    margin: 0 !important;
}

/* Geciken (kırmızı) nav kart */
div.element-container:has(.marker-danger) + div.element-container button {
    border-color: #EF4444 !important;
}
div.element-container:has(.marker-danger) + div.element-container button:hover {
    border-color: #F87171 !important;
}

/* ── Gelişmiş KPI Kartları ───────────────────────────────────────────── */
.kpi-container {
    display: flex; gap: 24px; margin-bottom: 24px; flex-wrap: wrap;
}
.adv-kpi-card {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 24px;
    flex: 1;
    min-width: 220px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    border-left-width: 4px;
    border-left-style: solid;
}
.adv-kpi-card .kpi-title {
    color: #94A3B8; font-size: 0.95rem; font-weight: 500; margin-bottom: 12px;
}
.adv-kpi-card .kpi-value {
    color: #F8FAFC; font-family: 'JetBrains Mono', monospace;
    font-size: 2.8rem; font-weight: 800; line-height: 1; margin-bottom: 8px;
}
.adv-kpi-card .kpi-subtext {
    font-size: 0.85rem; font-weight: 600;
}

/* ── Sayfa Başlığı (Breadcrumb) ──────────────────────────────────────── */
.page-breadcrumb {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 20px; padding: 12px 0;
    border-bottom: 1px solid #e2e8f0;
}
.page-breadcrumb .crumb-home {
    color: #94a3b8; font-size: 0.85rem; font-weight: 500;
}
.page-breadcrumb .crumb-sep { color: #cbd5e1; font-size: 0.8rem; }
.page-breadcrumb .crumb-current {
    color: #1e40af; font-size: 0.95rem; font-weight: 700;
}

/* ── Üst Nav Pilleri ─────────────────────────────────────────────────── */
.top-nav { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
.top-nav-pill {
    display: inline-block; padding: 8px 18px; border-radius: 24px;
    font-size: 0.82rem; font-weight: 600; cursor: pointer;
    text-decoration: none; transition: all 0.2s ease;
    border: 1px solid #e2e8f0; color: #475569; background: #f8fafc;
}
.top-nav-pill:hover { background: #e2e8f0; color: #1e293b; }
.top-nav-pill-active {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    color: #fff !important; border-color: #3b82f6 !important;
    box-shadow: 0 2px 12px rgba(59,130,246,0.3);
}

/* ── Forms ────────────────────────────────────────────────────────────── */
div[data-testid="stForm"] {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 24px;
}
.block-container { padding-top: 2rem; }

/* ── Header ──────────────────────────────────────────────────────────── */
.qrqc-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #1e40af 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(15,23,42,0.35);
    position: relative; overflow: hidden;
}
.qrqc-header::before {
    content: ""; position: absolute; top: -40%; right: -10%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.qrqc-header h1 {
    color: #f8fafc; font-size: 1.75rem; font-weight: 800;
    margin: 0 0 4px 0; letter-spacing: -0.02em;
}
.qrqc-header p { color: #94a3b8; font-size: 0.9rem; margin: 0; }

/* ── Badges ──────────────────────────────────────────────────────────── */
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em;
}
.badge-open   { background: #fef3c7; color: #92400e; }
.badge-prog   { background: #dbeafe; color: #1e40af; }
.badge-verify { background: #ede9fe; color: #5b21b6; }
.badge-closed { background: #d1fae5; color: #065f46; }
.badge-late   { background: #fee2e2; color: #991b1b; }

/* ── Info Card ────────────────────────────────────────────────────────── */
.info-card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid #334155; border-radius: 12px;
    padding: 20px 24px; margin: 12px 0; color: #e2e8f0;
}
.info-card h4 {
    color: #60a5fa; margin: 0 0 8px 0; font-size: 0.85rem;
    text-transform: uppercase; letter-spacing: 0.05em;
}
.info-card p { color: #cbd5e1; margin: 4px 0; font-size: 0.9rem; }
.info-card .highlight { color: #f8fafc; font-weight: 700; }

/* ── Empty State ─────────────────────────────────────────────────────── */
.empty-state { text-align: center; padding: 48px 24px; color: #94a3b8; }
.empty-state .icon { font-size: 3rem; margin-bottom: 12px; }
.empty-state h3 { color: #64748b; font-weight: 600; margin-bottom: 8px; }
.empty-state p { color: #94a3b8; font-size: 0.9rem; }

/* ── Action Row Colors ───────────────────────────────────────────────── */
.overdue-row {
    background-color: #fee2e2 !important; border-left: 4px solid #ef4444;
    padding: 12px; border-radius: 8px; margin-bottom: 6px;
}
.normal-row {
    background-color: #f8fafc; border-left: 4px solid #3b82f6;
    padding: 12px; border-radius: 8px; margin-bottom: 6px;
}
.ontime-row {
    background-color: #f0fdf4; border-left: 4px solid #22c55e;
    padding: 12px; border-radius: 8px; margin-bottom: 6px;
}

/* ── Aktif Toplantı Banner ───────────────────────────────────────────── */
.active-banner {
    background: linear-gradient(135deg, #065f46 0%, #047857 50%, #059669 100%);
    border: 2px solid #34d399; border-radius: 16px;
    padding: 24px 32px; margin: 16px 0;
    box-shadow: 0 4px 24px rgba(5,150,105,0.3);
    position: relative; overflow: hidden;
}
.active-banner::after {
    content: ""; position: absolute; top: -30%; right: -5%;
    width: 180px; height: 180px;
    background: radial-gradient(circle, rgba(52,211,153,0.2) 0%, transparent 70%);
    border-radius: 50%;
}
.active-banner h3 { color: #ecfdf5; font-size: 1.1rem; font-weight: 700; margin: 0 0 8px 0; }
.active-banner p  { color: #a7f3d0; font-size: 0.95rem; margin: 3px 0; }
.active-banner .time-big { color: #fff; font-size: 1.5rem; font-weight: 800; }

/* ── Özet Tablosu ────────────────────────────────────────────────────── */
.summary-table {
    width: 100%; border-collapse: separate; border-spacing: 0;
    border-radius: 12px; overflow: hidden; border: 1px solid #334155;
}
.summary-table th {
    background: #1e293b; color: #94a3b8; padding: 10px 16px;
    font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; text-align: left;
}
.summary-table td {
    background: #0f172a; color: #e2e8f0; padding: 10px 16px;
    font-size: 0.88rem; border-top: 1px solid #1e293b;
}
.summary-table tr:hover td { background: #1e293b; }

/* ── Eski Metrik Kartları ─────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155; border-radius: 12px;
    padding: 16px 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}
div[data-testid="stMetric"] label {
    color: #94a3b8 !important; font-weight: 600;
    text-transform: uppercase; font-size: 0.7rem !important; letter-spacing: 0.08em;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #f8fafc !important; font-weight: 800; font-size: 2rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Yardımcı Fonksiyonlar
# ═══════════════════════════════════════════════════════════════════════════
def badge_html(text: str) -> str:
    css_map = {
        "Açık": "badge-open", "Devam Ediyor": "badge-prog",
        "Doğrulama": "badge-verify", "Kapandı": "badge-closed",
        "GECİKMİŞ": "badge-late",
    }
    return f'<span class="badge {css_map.get(text, "badge-open")}">{text}</span>'


def load_active_meeting() -> dict | None:
    with get_db() as db:
        m = (
            db.query(Meeting)
            .filter(Meeting.bitis_zamani.is_(None))
            .order_by(Meeting.baslangic_zamani.desc())
            .first()
        )
        if not m:
            return None
        issues = [
            {"id": i.id, "tespit_yeri": i.tespit_yeri, "kategori": i.kategori,
             "durum": i.durum, "problem_tanimi": i.problem_tanimi}
            for i in m.issues
        ]
        return {
            "id": m.id, "tarih": m.tarih, "vardiya": m.vardiya,
            "katilimcilar": m.katilimcilar or "",
            "baslangic_zamani": m.baslangic_zamani, "issues": issues,
        }


def load_last_completed_meetings(limit: int = 5) -> list[dict]:
    with get_db() as db:
        meetings = (
            db.query(Meeting)
            .filter(Meeting.bitis_zamani.isnot(None))
            .order_by(Meeting.bitis_zamani.desc())
            .limit(limit)
            .all()
        )
        return [
            {"id": m.id, "tarih": m.tarih, "vardiya": m.vardiya,
             "sure_dakika": m.sure_dakika, "problem_sayisi": len(m.issues)}
            for m in meetings
        ]


def load_open_issues() -> list[dict]:
    with get_db() as db:
        issues = (
            db.query(Issue).filter(Issue.durum == "Açık")
            .order_by(Issue.olusturma_tarihi.desc()).all()
        )
        return [
            {"id": i.id, "kategori": i.kategori, "tespit_yeri": i.tespit_yeri,
             "problem_tanimi": i.problem_tanimi,
             "kok_neden_5_why": i.kok_neden_5_why or "", "df_no": i.df_no or ""}
            for i in issues
        ]


def load_all_actions() -> list[dict]:
    with get_db() as db:
        actions = db.query(Action).order_by(Action.termin_tarihi.asc()).all()
        return [
            {"id": a.id, "issue_id": a.issue_id,
             "problem": f"[{a.issue.kategori}] {a.issue.tespit_yeri}" if a.issue else "—",
             "aksiyon_tanimi": a.aksiyon_tanimi, "sorumlu": a.sorumlu,
             "termin_tarihi": a.termin_tarihi, "aksiyon_durumu": a.aksiyon_durumu}
            for a in actions
        ]


def load_global_kpis() -> dict:
    """KPI değerlerini tek sorguda toplar."""
    with get_db() as db:
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            "toplam_toplanti": db.query(Meeting).count(),
            "toplanti_bu_hafta": db.query(Meeting).filter(Meeting.tarih >= start_of_week).count(),
            "acik_problem": db.query(Issue).filter(Issue.durum == "Açık").count(),
            "acik_aksiyon": db.query(Action).filter(
                Action.aksiyon_durumu.in_(["Açık", "Devam Ediyor"])
            ).count(),
            "geciken": db.query(Action).filter(
                Action.aksiyon_durumu.in_(["Açık", "Devam Ediyor"]),
                Action.termin_tarihi < date.today(),
            ).count(),
        }


def delete_action_by_id(action_id: int) -> bool:
    """Verilen ID'ye sahip aksiyonu veritabanından siler."""
    with get_db() as db:
        action_obj = db.query(Action).get(action_id)
        if action_obj:
            db.delete(action_obj)
            return True
    return False


def delete_meeting_by_id(meeting_id: int) -> bool:
    """Toplantıyı veritabanından kalıcı olarak siler. (İlişkili problemler ve aksiyonlar cascade kuralı ile silinir)"""
    with get_db() as db:
        meeting_obj = db.query(Meeting).get(meeting_id)
        if meeting_obj:
            db.delete(meeting_obj)
            return True
    return False


def load_all_users() -> list[dict]:
    """Tüm kayıtlı kullanıcıları veritabanından çeker."""
    with get_db() as db:
        users = db.query(User).order_by(User.ad_soyad.asc()).all()
        return [
            {
                "id": u.id,
                "ad_soyad": u.ad_soyad,
                "eposta": u.eposta,
                "bolum": u.bolum,
                "gorev": u.gorev,
            }
            for u in users
        ]


def render_action_table(actions: list[dict], today: date, page_prefix: str = "") -> None:
    """Aksiyon listesini renkli satırlarla render eder. Sil butonu dahil."""
    header_cols = st.columns([0.5, 2.2, 1.8, 1.3, 1.1, 1.1, 1.1, 0.5])
    header_cols[0].markdown("**#**")
    header_cols[1].markdown("**Problem**")
    header_cols[2].markdown("**Aksiyon**")
    header_cols[3].markdown("**Sorumlu**")
    header_cols[4].markdown("**Termin**")
    header_cols[5].markdown("**Durum**")
    header_cols[6].markdown("**Gecikme**")
    header_cols[7].markdown("")

    for a in actions:
        is_overdue = (
            a["aksiyon_durumu"] in ("Açık", "Devam Ediyor") and a["termin_tarihi"] < today
        )
        is_closed = a["aksiyon_durumu"] == "Kapandı"
        row_class = "overdue-row" if is_overdue else ("ontime-row" if is_closed else "normal-row")

        if is_overdue:
            gecikme_text = f"🔴 {(today - a['termin_tarihi']).days} gün"
        elif a["aksiyon_durumu"] in ("Açık", "Devam Ediyor"):
            gecikme_text = f"🟢 {(a['termin_tarihi'] - today).days} gün kaldı"
        else:
            gecikme_text = "—"

        st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)
        rc = st.columns([0.5, 2.2, 1.8, 1.3, 1.1, 1.1, 1.1, 0.5])
        rc[0].write(f"**{a['id']}**")
        rc[1].write(a["problem"])
        rc[2].write(a["aksiyon_tanimi"][:50] + ("…" if len(a["aksiyon_tanimi"]) > 50 else ""))
        rc[3].write(a["sorumlu"])
        rc[4].write(a["termin_tarihi"].strftime("%d.%m.%Y"))
        rc[5].markdown(badge_html(a["aksiyon_durumu"]), unsafe_allow_html=True)
        rc[6].write(gecikme_text)
        with rc[7]:
            if st.button("🗑️", key=f"{page_prefix}del_{a['id']}", help=f"Aksiyon #{a['id']} sil"):
                if delete_action_by_id(a["id"]):
                    st.toast(f"Aksiyon #{a['id']} silindi.", icon="✅")
                    st.rerun()
                else:
                    st.toast(f"Aksiyon #{a['id']} bulunamadı!", icon="❌")
        st.markdown("</div>", unsafe_allow_html=True)


def render_action_update_form(all_actions: list[dict]) -> None:
    """Aksiyon durumu güncelleme formu."""
    st.subheader("🔄 Aksiyon Durumu Güncelle")
    active_actions = [a for a in all_actions if a["aksiyon_durumu"] != "Kapandı"]
    if not active_actions:
        st.success("Tüm aksiyonlar kapatılmış. Harika! 🎉")
        return

    update_options = {
        f"#{a['id']} — {a['sorumlu']}: {a['aksiyon_tanimi'][:50]}": a["id"]
        for a in active_actions
    }
    with st.form("update_action_form"):
        cu1, cu2 = st.columns([3, 1])
        with cu1:
            selected_action_label = st.selectbox("Aksiyonu Seçin", list(update_options.keys()))
        with cu2:
            new_status = st.selectbox("Yeni Durum", AKSIYON_DURUM)
        update_btn = st.form_submit_button(
            "✅ Durumu Güncelle", use_container_width=True, type="primary",
        )
    if update_btn:
        action_id = update_options[selected_action_label]
        with get_db() as db:
            action_obj = db.query(Action).get(action_id)
            if action_obj:
                action_obj.aksiyon_durumu = new_status
        st.success(f"Aksiyon #{action_id} durumu → **{new_status}** olarak güncellendi.")
        st.rerun()


def render_action_dataframe(all_actions: list[dict], today: date) -> None:
    """Pandas DataFrame ile alternatif tablo görünümü."""
    df = pd.DataFrame(all_actions)
    if df.empty:
        return
    df = df.rename(columns={
        "id": "ID", "problem": "Problem", "aksiyon_tanimi": "Aksiyon",
        "sorumlu": "Sorumlu", "termin_tarihi": "Termin", "aksiyon_durumu": "Durum",
    }).drop(columns=["issue_id"], errors="ignore")

    def color_rows(row):
        if row["Durum"] in ("Açık", "Devam Ediyor") and row["Termin"] < today:
            return ["background-color: #fee2e2; color: #991b1b; font-weight: 600"] * len(row)
        if row["Durum"] == "Kapandı":
            return ["background-color: #d1fae5; color: #065f46"] * len(row)
        return [""] * len(row)

    st.dataframe(df.style.apply(color_rows, axis=1), use_container_width=True, hide_index=True)


def render_advanced_kpis(kpi: dict) -> None:
    """Gelişmiş KPI kartlarını (renkli sol barlı) ekrana basar."""
    st.markdown(f"""
<div class="kpi-container">
    <div class="adv-kpi-card" style="border-left-color: #3B82F6;">
        <div class="kpi-title">Toplam Toplantı</div>
        <div class="kpi-value">{kpi['toplam_toplanti']:02d}</div>
        <div class="kpi-subtext" style="color: #10B981;">+{kpi['toplanti_bu_hafta']} Bu hafta</div>
    </div>
    <div class="adv-kpi-card" style="border-left-color: #F59E0B;">
        <div class="kpi-title">Açık Problemler</div>
        <div class="kpi-value">{kpi['acik_problem']:02d}</div>
        <div class="kpi-subtext" style="color: #F59E0B;">Acil müdahale</div>
    </div>
    <div class="adv-kpi-card" style="border-left-color: #EF4444;">
        <div class="kpi-title">Geciken Aksiyonlar</div>
        <div class="kpi-value">{kpi['geciken']:02d}</div>
        <div class="kpi-subtext" style="color: #EF4444;">Eskalasyon gerekli</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Sidebar — Dinamik Navigasyon
# ═══════════════════════════════════════════════════════════════════════════
kpi = load_global_kpis()
current = st.session_state.current_page

with st.sidebar:
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<img src="data:image/png;base64,{encoded}" style="width: 100%; border-radius: 8px; margin-bottom: 20px;">',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="text-align: center; padding: 20px; background: #1E293B; border-radius: 8px; margin-bottom: 20px; color: #94A3B8;">'
            '🖼️ <b>DEBAK Logo Alanı</b><br><small>(Lütfen logonuzu <b>logo.png</b> adıyla qrqc klasörüne ekleyin)</small></div>',
            unsafe_allow_html=True
        )

    st.markdown("## 🏭 QRQC Panel")
    st.caption("Quick Response Quality Control")
    
    if st.session_state.get("user_info"):
        u = st.session_state.user_info
        st.markdown(
            f'<div style="background: #0F172A; padding: 12px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #334155;">'
            f'<small style="color: #94A3B8; text-transform: uppercase; font-size: 0.7rem; font-weight: 700;">Giriş Yapan Kullanıcı</small><br>'
            f'<b style="color: #F8FAFC; font-size: 0.95rem;">👤 {u["ad_soyad"]}</b><br>'
            f'<small style="color: #60A5FA;">💼 {u["bolum"]} / {u["gorev"]}</small>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.divider()

    # ── KPI Navigasyon Kartları ──────────────────────────────────────────

    # 1) Toplam Toplantı
    st.button(
        f"📅  {kpi['toplam_toplanti']}  ·  Toplam Toplantı",
        key="nav_toplanti",
        on_click=navigate,
        args=("sabah_toplantisi",),
        use_container_width=True,
        type="primary" if current == "sabah_toplantisi" else "secondary",
    )

    # 2) Açık Problemler
    st.button(
        f"🔴  {kpi['acik_problem']}  ·  Açık Problemler",
        key="nav_problem",
        on_click=navigate,
        args=("acik_problemler",),
        use_container_width=True,
        type="primary" if current == "acik_problemler" else "secondary",
    )

    # 3) Açık Aksiyonlar
    st.button(
        f"📊  {kpi['acik_aksiyon']}  ·  Açık Aksiyonlar",
        key="nav_aksiyon",
        on_click=navigate,
        args=("aksiyon_takip",),
        use_container_width=True,
        type="primary" if current == "aksiyon_takip" else "secondary",
    )

    # 4) Geciken Aksiyonlar
    if kpi["geciken"] > 0:
        st.markdown('<div class="marker-danger" style="display:none;"></div>', unsafe_allow_html=True)
    st.button(
        f"⚠️  {kpi['geciken']}  ·  Geciken Aksiyonlar",
        key="nav_geciken",
        on_click=navigate,
        args=("geciken",),
        use_container_width=True,
        type="primary" if current == "geciken" else "secondary",
    )

    st.divider()

    # ── Alt Navigasyon Linkleri ──────────────────────────────────────────
    st.button(
        "🔍  Kök Neden Analizi (5 Why)",
        key="nav_kok_neden",
        on_click=navigate,
        args=("kok_neden",),
        use_container_width=True,
        type="primary" if current == "kok_neden" else "secondary",
    )

    st.button(
        "📊  Görsel Analiz",
        key="nav_gorsel_analiz",
        on_click=navigate,
        args=("gorsel_analiz",),
        use_container_width=True,
        type="primary" if current == "gorsel_analiz" else "secondary",
    )

    st.divider()
    st.caption(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    st.caption("v3.0 — QRQC Yönetim Sistemi")
    
    st.divider()
    if st.button("🚪 Çıkış Yap", key="sidebar_logout_btn", use_container_width=True, type="secondary"):
        st.session_state.is_logged_in = False
        st.session_state.user_info = None
        st.session_state.selected_meeting_id = None
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  Ana Başlık
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(
    """
<div class="qrqc-header">
    <h1>DEBAK QRQC APP</h1>
    <p>Günlük üretim problemlerini tespit et · Kök neden analizi yap · Aksiyonları takip et</p>
</div>
""",
    unsafe_allow_html=True,
)

# Gelişmiş KPI barlarını başlığın hemen altında render et
render_advanced_kpis(kpi)

# ── Üst Navigasyon Pilleri ───────────────────────────────────────────────
nav_cols = st.columns(len(PAGES))
for idx, (page_key, page_label) in enumerate(PAGES.items()):
    with nav_cols[idx]:
        is_active = current == page_key
        st.button(
            page_label,
            key=f"topnav_{page_key}",
            on_click=navigate,
            args=(page_key,),
            use_container_width=True,
            type="primary" if is_active else "secondary",
        )

st.markdown("")  # spacer


# ═══════════════════════════════════════════════════════════════════════════
#  SAYFA: Sabah Toplantısı
# ═══════════════════════════════════════════════════════════════════════════
if current == "sabah_toplantisi":

    active_meeting = load_active_meeting()

    # ── AKTİF TOPLANTI VARSA ─────────────────────────────────────────────
    if active_meeting:
        elapsed_minutes = math.floor(
            (datetime.now() - active_meeting["baslangic_zamani"]).total_seconds() / 60
        )
        start_str = active_meeting["baslangic_zamani"].strftime("%H:%M")

        st.markdown(
            f"""
<div class="active-banner">
    <h3>🟢 Şu an aktif toplantı devam ediyor</h3>
    <p>🔧 Vardiya: <b>{active_meeting['vardiya']}</b>
        &nbsp;|&nbsp; 👥 {active_meeting['katilimcilar']}</p>
    <p>⏱️ Başlangıç: <span class="time-big">{start_str}</span>
        &nbsp;—&nbsp; Geçen süre: <span class="time-big">{elapsed_minutes} dk</span></p>
    <p>📝 Kayıtlı Problem: <b>{len(active_meeting['issues'])}</b></p>
</div>
""",
            unsafe_allow_html=True,
        )

        col_stop, _ = st.columns([1, 2])
        with col_stop:
            if st.button(
                "🛑  Toplantıyı Bitir",
                use_container_width=True, type="primary",
                key="finish_meeting_btn",
            ):
                now = datetime.now()
                with get_db() as db:
                    m = db.query(Meeting).get(active_meeting["id"])
                    if m:
                        m.bitis_zamani = now
                delta = now - active_meeting["baslangic_zamani"]
                sure = max(int(delta.total_seconds() / 60), 0)
                st.success(f"Toplantı başarıyla kapatıldı!  ⏱️ Süre: **{sure} dakika**")
                st.rerun()

        if active_meeting["issues"]:
            with st.expander(
                f"📝 Bu Toplantının Problemleri ({len(active_meeting['issues'])})",
                expanded=False,
            ):
                for issue in active_meeting["issues"]:
                    st.markdown(
                        f"**#{issue['id']}** — {issue['tespit_yeri']} | "
                        f"{badge_html(issue['durum'])} | "
                        f"<span class='badge badge-prog'>{issue['kategori']}</span><br>"
                        f"<small>{issue['problem_tanimi'][:120]}"
                        f"{'…' if len(issue['problem_tanimi']) > 120 else ''}</small>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("---")

        st.divider()
        st.subheader("🔴 Yeni Problem Ekle")

        with st.form("new_issue_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                tespit_yeri = st.text_input(
                    "Tespit Yeri (Hat / Makine / İstasyon)",
                    placeholder="Hat-3 / Son Kontrol İstasyonu",
                )
                kategori = st.selectbox("Kategori (SQCD)", KATEGORI_SQCD)
            with col_b:
                problem_tanimi = st.text_area(
                    "Problem Tanımı",
                    placeholder="Üretim hattında tespit edilen problemi detaylı açıklayın…",
                    height=120,
                )
                acil_onlem = st.checkbox("Acil önlem alındı mı?", value=False)
            submitted_issue = st.form_submit_button(
                "💾 Problemi Kaydet", use_container_width=True, type="primary",
            )

        if submitted_issue:
            if not tespit_yeri.strip() or not problem_tanimi.strip():
                st.warning("Tespit yeri ve problem tanımı zorunludur.")
            else:
                with get_db() as db:
                    db.add(Issue(
                        meeting_id=active_meeting["id"],
                        problem_tanimi=problem_tanimi.strip(),
                        tespit_yeri=tespit_yeri.strip(),
                        kategori=kategori,
                        acil_onlem_alindi_mi=acil_onlem,
                        durum="Açık", olusturma_tarihi=datetime.now(),
                    ))
                st.success("Problem başarıyla kaydedildi!")
                st.rerun()

        st.divider()
        st.subheader("⚡ Hızlı Geçici Aksiyon Ekle")
        open_issues_data = load_open_issues()
        if not open_issues_data:
            st.info("Aksiyon atamak için önce bir problem kaydedin.")
        else:
            issue_action_options = {
                f"#{i['id']} — [{i['kategori']}] {i['tespit_yeri']}: {i['problem_tanimi'][:60]}": i["id"]
                for i in open_issues_data
            }
            with st.form("quick_action_form", clear_on_submit=True):
                selected_issue_label = st.selectbox("Problemi Seçin", list(issue_action_options.keys()))
                cx, cy, cz = st.columns(3)
                with cx:
                    aksiyon_tanimi = st.text_area("Aksiyon Tanımı", placeholder="…", height=80)
                with cy:
                    users_list = load_all_users()
                    if users_list:
                        sorumlu_options = [u["ad_soyad"] for u in users_list]
                        default_idx = 0
                        logged_in_name = st.session_state.user_info.get("ad_soyad", "") if st.session_state.get("user_info") else ""
                        if logged_in_name in sorumlu_options:
                            default_idx = sorumlu_options.index(logged_in_name)
                        sorumlu = st.selectbox("Sorumlu Kişi", sorumlu_options, index=default_idx)
                    else:
                        sorumlu = st.text_input("Sorumlu Kişi", placeholder="Ad Soyad")
                with cz:
                    termin = st.date_input("Termin Tarihi", value=date.today() + timedelta(days=3), min_value=date.today())
                submitted_action = st.form_submit_button(
                    "⚡ Aksiyonu Kaydet", use_container_width=True, type="primary",
                )
            if submitted_action:
                if not aksiyon_tanimi.strip() or not sorumlu.strip():
                    st.warning("Aksiyon tanımı ve sorumlu kişi zorunludur.")
                else:
                    with get_db() as db:
                        db.add(Action(
                            issue_id=issue_action_options[selected_issue_label],
                            aksiyon_tanimi=aksiyon_tanimi.strip(),
                            sorumlu=sorumlu.strip(),
                            termin_tarihi=termin, aksiyon_durumu="Açık",
                        ))
                    st.success("Aksiyon başarıyla kaydedildi!")
                    st.rerun()

    # ── AKTİF TOPLANTI YOKSA ─────────────────────────────────────────────
    else:
        col_new, col_info = st.columns([1.3, 1.7])
        with col_new:
            st.subheader("➕ Yeni Toplantı Başlat")
            
            katilimcilar = st.text_area(
                "Katılımcılar", placeholder="Ahmet Yılmaz, Elif Demir …", height=100,
            )
            
            st.markdown("---")
            st.markdown("##### 📋 Kritik Kontrol Listesi")
            
            checklist_items = [
                {
                    "label": "1. İş Sağlığı & Güvenliği (Kaza/Ramak Kala)",
                    "category": "İş Sağlığı & Güvenliği",
                    "key": "isg"
                },
                {
                    "label": "2. Müşteri Kalite Vakası",
                    "category": "Müşteri Kalite Vakası",
                    "key": "musteri_kalite"
                },
                {
                    "label": "3. Tedarikçi Kalite Vakası",
                    "category": "Tedarikçi Kalite Vakası",
                    "key": "tedarikci_kalite"
                },
                {
                    "label": "4. İşletme İçi Kalite Vakası",
                    "category": "İşletme İçi Kalite Vakası",
                    "key": "isletme_kalite"
                },
                {
                    "label": "5. CSL1 Kontrol Durumu",
                    "category": "CSL1 Kontrol Durumu",
                    "key": "csl1"
                },
                {
                    "label": "6. Yeni Ürün Proje Takibi",
                    "category": "Yeni Ürün Proje Takibi",
                    "key": "yeni_urun"
                }
            ]
            
            checklist_values = {}
            for item in checklist_items:
                checked = st.checkbox(item["label"], value=False, key=f"chk_{item['key']}")
                desc = ""
                if checked:
                    desc = st.text_area(
                        f"↳ {item['category']} Açıklaması",
                        placeholder=f"{item['category']} detaylarını giriniz...",
                        key=f"desc_{item['key']}",
                        height=80
                    )
                checklist_values[item["key"]] = {"checked": checked, "desc": desc}
                
            submitted_meeting = st.button(
                "🚀 Toplantıyı Başlat", use_container_width=True, type="primary"
            )
            
            if submitted_meeting:
                if not katilimcilar.strip():
                    st.warning("Lütfen en az bir katılımcı girin.")
                else:
                    # Check if any checked items have empty descriptions
                    missing_fields = []
                    for item in checklist_items:
                        item_data = checklist_values.get(item["key"])
                        if item_data and item_data["checked"] and not item_data["desc"].strip():
                            missing_fields.append(item["category"])
                    
                    if missing_fields:
                        st.error(f"Lütfen işaretlediğiniz şu maddeler için açıklama giriniz: {', '.join(missing_fields)}")
                    else:
                        now = datetime.now()
                        # Automatically determine shift based on startup hour
                        hour = now.hour
                        if 8 <= hour < 16:
                            vardiya = "Gündüz"
                        elif 16 <= hour < 24:
                            vardiya = "Akşam"
                        else:
                            vardiya = "Gece"

                        with get_db() as db:
                            new_meeting = Meeting(
                                tarih=now,
                                vardiya=vardiya,
                                katilimcilar=katilimcilar.strip(),
                                baslangic_zamani=now,
                                bitis_zamani=None,
                            )
                            db.add(new_meeting)
                            db.flush()  # to get new_meeting.id
                            
                            # Automatically convert checked checklist items to Issues
                            for item in checklist_items:
                                item_data = checklist_values.get(item["key"])
                                if item_data and item_data["checked"]:
                                    desc_text = item_data["desc"].strip()
                                    db.add(Issue(
                                        meeting_id=new_meeting.id,
                                        problem_tanimi=desc_text,
                                        tespit_yeri="Sabah Toplantısı",
                                        kategori=item["category"],
                                        acil_onlem_alindi_mi=False,
                                        durum="Açık",
                                        olusturma_tarihi=now,
                                    ))
                        st.success("Toplantı başlatıldı ve kritik kontrol listesi maddeleri probleme dönüştürüldü! ⏱️ Süre sayacı çalışıyor…")
                        st.rerun()

        with col_info:
            st.subheader("📋 Durum")
            st.markdown(
                """
<div class="empty-state">
    <div class="icon">📅</div>
    <h3>Aktif toplantı yok</h3>
    <p>Soldaki formu kullanarak yeni bir toplantı başlatın.</p>
</div>""",
                unsafe_allow_html=True,
            )

    # ── GEÇMİŞ TOPLANTI ÖZETİ ───────────────────────────────────────────
    st.divider()
    st.subheader("📊 Son Kapatılan Toplantılar")
    completed = load_last_completed_meetings(5)
    if not completed:
        st.caption("Henüz kapatılmış toplantı bulunmuyor.")
    else:
        hc = st.columns([1, 2, 2, 1, 1, 2])
        hc[0].markdown("**#**")
        hc[1].markdown("**Tarih**")
        hc[2].markdown("**Vardiya**")
        hc[3].markdown("**Süre**")
        hc[4].markdown("**Problem**")
        hc[5].markdown("")

        for c in completed:
            tarih_str = c["tarih"].strftime("%d.%m.%Y %H:%M") if c["tarih"] else "—"
            sure_str = f"{c['sure_dakika']} dk" if c["sure_dakika"] is not None else "—"
            
            row_bg = "background-color: #1e3a5f; border-left: 4px solid #60a5fa;" if st.session_state.get("selected_meeting_id") == c["id"] else ""
            st.markdown(f'<div class="normal-row" style="{row_bg}">', unsafe_allow_html=True)
            rc = st.columns([1, 2, 2, 1, 1, 2])
            rc[0].write(f"**#{c['id']}**")
            rc[1].write(tarih_str)
            rc[2].write(c["vardiya"])
            rc[3].write(sure_str)
            rc[4].write(str(c["problem_sayisi"]))
            with rc[5]:
                b1, b2 = st.columns([2, 1])
                with b1:
                    if st.button("🔎 İncele", key=f"view_meeting_{c['id']}", use_container_width=True):
                        st.session_state.selected_meeting_id = c["id"]
                        st.rerun()
                with b2:
                    if st.button("🗑️", key=f"del_meeting_{c['id']}", help="Toplantıyı tamamen sil", use_container_width=True):
                        if delete_meeting_by_id(c["id"]):
                            st.toast(f"Toplantı #{c['id']} silindi.", icon="✅")
                            if st.session_state.get("selected_meeting_id") == c["id"]:
                                st.session_state.selected_meeting_id = None
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ── DİNAMİK DETAY PANELİ ─────────────────────────────────────────────
    if st.session_state.get("selected_meeting_id"):
        sm_id = st.session_state.selected_meeting_id
        st.markdown("---")
        
        with get_db() as db:
            m = db.query(Meeting).get(sm_id)
            if not m:
                st.error("Toplantı bulunamadı.")
            else:
                d1, d2 = st.columns([4, 1])
                d1.markdown(f"### 📋 Toplantı #{m.id} Detayları")
                with d2:
                    if st.button("❌ Özeti Kapat", use_container_width=True, type="primary"):
                        st.session_state.selected_meeting_id = None
                        st.rerun()
                
                t_str = m.tarih.strftime("%d.%m.%Y %H:%M") if m.tarih else "—"
                sure_str = f"{m.sure_dakika} dk" if m.sure_dakika is not None else "—"
                st.info(f"**Tarih:** {t_str} | **Vardiya:** {m.vardiya} | **Süre:** {sure_str} | **Katılımcılar:** {m.katilimcilar}")
                
                if not m.issues:
                    st.caption("Bu toplantıda kaydedilmiş problem yok.")
                else:
                    for issue in m.issues:
                        with st.expander(f"🔴 Problem: [{issue.kategori}] {issue.tespit_yeri} - {issue.durum}", expanded=True):
                            st.write(f"**Tanım:** {issue.problem_tanimi}")
                            if issue.kok_neden_5_why:
                                st.write(f"**5 Neden Analizi:** {issue.kok_neden_5_why}")
                            
                            if issue.actions:
                                st.write("**Aksiyonlar:**")
                                for a in issue.actions:
                                    termin_str = a.termin_tarihi.strftime("%d.%m.%Y") if a.termin_tarihi else "—"
                                    st.markdown(f"- {badge_html(a.aksiyon_durumu)} **{a.sorumlu}** ({termin_str}): {a.aksiyon_tanimi}", unsafe_allow_html=True)
                            else:
                                st.caption("Bu probleme bağlı aksiyon yok.")


# ═══════════════════════════════════════════════════════════════════════════
#  SAYFA: Aksiyon Takip Panosu
# ═══════════════════════════════════════════════════════════════════════════
elif current == "aksiyon_takip":

    actions_data = load_all_actions()

    if not actions_data:
        st.markdown(
            '<div class="empty-state"><div class="icon">📊</div>'
            '<h3>Henüz aksiyon kaydı yok</h3>'
            '<p>"Sabah Toplantısı" sekmesinden problem ve aksiyon ekleyerek başlayın.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        today = date.today()
        total = len(actions_data)
        open_count = sum(1 for a in actions_data if a["aksiyon_durumu"] in ("Açık", "Devam Ediyor"))
        overdue_count = sum(
            1 for a in actions_data
            if a["aksiyon_durumu"] in ("Açık", "Devam Ediyor") and a["termin_tarihi"] < today
        )
        closed_count = sum(1 for a in actions_data if a["aksiyon_durumu"] == "Kapandı")
        verify_count = sum(1 for a in actions_data if a["aksiyon_durumu"] == "Doğrulama")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Toplam Aksiyon", total)
        m2.metric("Açık / Devam Eden", open_count)
        m3.metric("⚠️ Gecikmiş", overdue_count)
        m4.metric("Doğrulamada", verify_count)
        m5.metric("✅ Kapanan", closed_count)
        st.divider()

        fc1, _ = st.columns([1, 3])
        with fc1:
            status_filter = st.multiselect(
                "Durum Filtresi", options=list(AKSIYON_DURUM),
                default=["Açık", "Devam Ediyor", "Doğrulama"],
            )

        st.subheader("📋 Aksiyon Listesi")
        filtered = [a for a in actions_data if a["aksiyon_durumu"] in status_filter]
        if not filtered:
            st.info("Seçili filtreye uygun aksiyon bulunamadı.")
        else:
            render_action_table(filtered, today, page_prefix="at_")

        st.divider()
        render_action_update_form(actions_data)

        with st.expander("📊 Tablo Görünümü (DataFrame)", expanded=False):
            render_action_dataframe(actions_data, today)

        with st.expander("⚠️ Gelişmiş: Kayıt Sil", expanded=False):
            st.caption("Hatalı veya yanlış girilmiş bir aksiyonu veritabanından kalıcı olarak silmek için kullanın.")
            del_options = {
                f"#{a['id']} — {a['sorumlu']}: {a['aksiyon_tanimi'][:60]}": a["id"]
                for a in actions_data
            }
            selected_del = st.selectbox(
                "Silinecek Aksiyonu Seçin", list(del_options.keys()), key="adv_del_select",
            )
            if st.button(
                "🗑️ Veritabanından Tamamen Sil",
                key="adv_del_btn",
                type="primary",
                use_container_width=True,
            ):
                aid = del_options[selected_del]
                if delete_action_by_id(aid):
                    st.success(f"Aksiyon #{aid} veritabanından tamamen silindi.")
                    st.rerun()
                else:
                    st.error(f"Aksiyon #{aid} bulunamadı!")


# ═══════════════════════════════════════════════════════════════════════════
#  SAYFA: Geciken Aksiyonlar (özel filtre)
# ═══════════════════════════════════════════════════════════════════════════
elif current == "geciken":

    st.subheader("⚠️ Geciken Aksiyonlar — Termin Tarihi Geçmiş Aksiyonlar")
    st.caption("Bu sayfa yalnızca durumu **Açık** veya **Devam Ediyor** olan ve termin tarihi geçmiş aksiyonları listeler.")

    actions_data = load_all_actions()
    today = date.today()
    overdue_actions = [
        a for a in actions_data
        if a["aksiyon_durumu"] in ("Açık", "Devam Ediyor") and a["termin_tarihi"] < today
    ]

    if not overdue_actions:
        st.success("🎉 Geciken aksiyon bulunmuyor! Tüm aksiyonlar zamanında.")
    else:
        st.error(f"**{len(overdue_actions)}** adet geciken aksiyon tespit edildi.")

        # Metrikler
        max_late = max((today - a["termin_tarihi"]).days for a in overdue_actions)
        avg_late = sum((today - a["termin_tarihi"]).days for a in overdue_actions) / len(overdue_actions)
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Geciken Aksiyon", len(overdue_actions))
        mc2.metric("En Fazla Gecikme", f"{max_late} gün")
        mc3.metric("Ortalama Gecikme", f"{avg_late:.0f} gün")
        st.divider()

        render_action_table(overdue_actions, today, page_prefix="gc_")

        st.divider()
        render_action_update_form(actions_data)

        with st.expander("⚠️ Gelişmiş: Kayıt Sil", expanded=False):
            st.caption("Geciken aksiyonlardan hatalı kaydı kalıcı olarak silmek için kullanın.")
            del_opts_gc = {
                f"#{a['id']} — {a['sorumlu']}: {a['aksiyon_tanimi'][:60]}": a["id"]
                for a in overdue_actions
            }
            selected_del_gc = st.selectbox(
                "Silinecek Aksiyonu Seçin", list(del_opts_gc.keys()), key="gc_del_select",
            )
            if st.button(
                "🗑️ Veritabanından Tamamen Sil",
                key="gc_del_btn",
                type="primary",
                use_container_width=True,
            ):
                aid_gc = del_opts_gc[selected_del_gc]
                if delete_action_by_id(aid_gc):
                    st.success(f"Aksiyon #{aid_gc} veritabanından tamamen silindi.")
                    st.rerun()
                else:
                    st.error(f"Aksiyon #{aid_gc} bulunamadı!")


# ═══════════════════════════════════════════════════════════════════════════
#  SAYFA: Açık Problemler
# ═══════════════════════════════════════════════════════════════════════════
elif current == "acik_problemler":

    st.subheader("🔴 Açık Problemler — Çözüm Bekleyen Uygunsuzluklar")
    open_issues = load_open_issues()

    if not open_issues:
        st.success("🎉 Açık problem bulunmuyor!")
    else:
        st.info(f"**{len(open_issues)}** adet açık problem mevcut.")

        for issue in open_issues:
            with st.container():
                st.markdown(
                    f"""
<div class="info-card">
    <h4>Problem #{issue['id']} — {issue['kategori']}</h4>
    <p>📍 Tespit Yeri: <span class="highlight">{issue['tespit_yeri']}</span></p>
    <p>📝 Tanım: <span class="highlight">{issue['problem_tanimi']}</span></p>
    <p>📄 DF No: <span class="highlight">{issue['df_no'] or '—'}</span></p>
</div>""",
                    unsafe_allow_html=True,
                )

        st.divider()
        st.caption("Kök neden analizi yapmak için sol menüden **🔍 Kök Neden Analizi** sayfasına gidin.")
        if st.button("🔍 Kök Neden Analizine Git", key="goto_kok_neden"):
            navigate("kok_neden")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  SAYFA: Kök Neden Analizi (5 Why / 4D)
# ═══════════════════════════════════════════════════════════════════════════
elif current == "kok_neden":

    rca_issues_data = load_open_issues()

    if not rca_issues_data:
        st.markdown(
            '<div class="empty-state"><div class="icon">🔍</div>'
            '<h3>Açık problem bulunamadı</h3>'
            '<p>"Sabah Toplantısı" sayfasından bir problem kaydedin.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        issue_rca_options = {
            f"#{d['id']} — [{d['kategori']}] {d['tespit_yeri']}: {d['problem_tanimi'][:80]}": idx
            for idx, d in enumerate(rca_issues_data)
        }
        selected_rca_label = st.selectbox(
            "Analiz Edilecek Problemi Seçin", list(issue_rca_options.keys()),
        )
        selected_rca = rca_issues_data[issue_rca_options[selected_rca_label]]

        st.markdown(
            f"""
<div class="info-card">
    <h4>Problem Detayı</h4>
    <p>📍 Tespit Yeri: <span class="highlight">{selected_rca['tespit_yeri']}</span></p>
    <p>🏷️ Kategori: <span class="highlight">{selected_rca['kategori']}</span></p>
    <p>📝 Tanım: <span class="highlight">{selected_rca['problem_tanimi']}</span></p>
</div>""",
            unsafe_allow_html=True,
        )
        st.divider()
        st.subheader("🔬 5 Neden Analizi (5 Why)")
        st.caption('Her adımda bir önceki cevabın nedenini sorun: "Neden böyle oldu?"')

        existing_whys = (
            selected_rca["kok_neden_5_why"].split("\n")
            if selected_rca["kok_neden_5_why"] else [""] * 5
        )
        while len(existing_whys) < 5:
            existing_whys.append("")

        with st.form("rca_form"):
            why_labels = [
                ("1️⃣", "Birinci Neden — Problem neden oluştu?"),
                ("2️⃣", "İkinci Neden — İlk neden neden gerçekleşti?"),
                ("3️⃣", "Üçüncü Neden — İkinci neden neden gerçekleşti?"),
                ("4️⃣", "Dördüncü Neden — Üçüncü neden neden gerçekleşti?"),
                ("5️⃣", "Beşinci Neden — Kök neden nedir?"),
            ]
            why_values = []
            for idx, (icon, label) in enumerate(why_labels):
                val = st.text_area(
                    f"{icon}  {label}",
                    value=existing_whys[idx] if idx < len(existing_whys) else "",
                    height=70, key=f"why_{idx}",
                )
                why_values.append(val)

            st.divider()
            cdf1, cdf2 = st.columns([2, 1])
            with cdf1:
                df_no_input = st.text_input(
                    "📄 Düzeltici Faaliyet No (DF / 4D Referans No)",
                    value=selected_rca["df_no"], placeholder="DF-2026-XXXX",
                )
            with cdf2:
                close_issue = st.checkbox("Problemi Kapat (analiz tamamlandı)", value=False)

            save_rca = st.form_submit_button(
                "💾 Analizi Kaydet", use_container_width=True, type="primary",
            )

        if save_rca:
            combined_why = "\n".join(w.strip() for w in why_values)
            with get_db() as db:
                issue_obj = db.query(Issue).get(selected_rca["id"])
                if issue_obj:
                    issue_obj.kok_neden_5_why = combined_why
                    issue_obj.df_no = df_no_input.strip() or None
                    if close_issue:
                        issue_obj.durum = "Kapandı"
            status_msg = " ve problem **kapatıldı**" if close_issue else ""
            st.success(f"Kök neden analizi kaydedildi{status_msg}!")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  SAYFA: Görsel Analiz (Dashboard)
# ═══════════════════════════════════════════════════════════════════════════
elif current == "gorsel_analiz":
    st.subheader("📊 Görsel Analiz Paneli")
    st.caption("Veritabanı kayıtlarının dağılım grafikleri ve KPI görselleştirmesi.")

    # 1) Donut Chart: Actions by status
    # 2) Pareto/Bar Chart: Issues by category
    # 3) Horizontal Bar Chart: Active actions workload per responsible person
    
    with get_db() as db:
        # Secure database calls using SQLAlchemy
        all_actions = db.query(Action).all()
        all_issues = db.query(Issue).all()
        active_actions = db.query(Action).filter(Action.aksiyon_durumu.in_(["Açık", "Devam Ediyor"])).all()

        # Extract data while session is active to prevent DetachedInstanceError
        actions_data = [{"aksiyon_durumu": a.aksiyon_durumu} for a in all_actions]
        issues_data = [{"kategori": i.kategori} for i in all_issues]
        active_data = [{"sorumlu": a.sorumlu, "aksiyon_durumu": a.aksiyon_durumu} for a in active_actions]

    # DataFrames
    df_actions = pd.DataFrame(actions_data)
    df_issues = pd.DataFrame(issues_data)
    df_active = pd.DataFrame(active_data)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### 🍩 Aksiyon Durumu Dağılımı")
        if df_actions.empty:
            st.info("Grafik için yeterli aksiyon verisi bulunmuyor.")
        else:
            df_status = df_actions['aksiyon_durumu'].value_counts().reset_index()
            df_status.columns = ['Aksiyon Durumu', 'Sayı']
            fig1 = px.pie(
                df_status, 
                names='Aksiyon Durumu', 
                values='Sayı', 
                hole=0.4, 
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig1.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                template="plotly_dark",
                margin=dict(l=20, r=20, t=20, b=20),
                height=350
            )
            st.plotly_chart(fig1, use_container_width=True)

    with col_g2:
        st.markdown("### 📊 Kategorilere Göre Problemler")
        if df_issues.empty:
            st.info("Grafik için yeterli problem verisi bulunmuyor.")
        else:
            df_kat = df_issues['kategori'].value_counts().reset_index()
            df_kat.columns = ['Kategori', 'Problem Sayısı']
            df_kat = df_kat.sort_values(by='Problem Sayısı', ascending=False)
            fig2 = px.bar(
                df_kat, 
                x='Kategori', 
                y='Problem Sayısı', 
                text='Problem Sayısı',
                color='Kategori',
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig2.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                template="plotly_dark",
                margin=dict(l=20, r=20, t=20, b=20),
                height=350,
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🏃 Sorumlulara Göre Aktif Aksiyon Yükü")
    if df_active.empty:
        st.info("Aktif aksiyon (Açık veya Devam Ediyor) bulunmuyor.")
    else:
        df_workload = df_active.groupby(['sorumlu', 'aksiyon_durumu']).size().reset_index(name='Aksiyon Sayısı')
        df_workload.columns = ['Sorumlu', 'Aksiyon Durumu', 'Aksiyon Sayısı']
        
        fig3 = px.bar(
            df_workload,
            y='Sorumlu',
            x='Aksiyon Sayısı',
            color='Aksiyon Durumu',
            orientation='h',
            color_discrete_map={"Açık": "#EF4444", "Devam Ediyor": "#3B82F6"}
        )
        fig3.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            template="plotly_dark",
            margin=dict(l=20, r=20, t=20, b=20),
            height=400,
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig3, use_container_width=True)

