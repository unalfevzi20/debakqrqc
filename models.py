"""
QRQC (Quick Response Quality Control) Veritabanı Modelleri
===========================================================
SQLAlchemy ORM ile tanımlanmış 3 ana tablo:
  - Meetings  : Günlük QRQC toplantı kayıtları
  - Issues    : Toplantılarda açılan problem/uygunsuzluk kayıtları
  - Actions   : Problemlere atanan aksiyon kalemleri
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# ── Ortak Sabitler ──────────────────────────────────────────────────────────
VARDIYA_SECENEKLERI = ("Gündüz", "Akşam", "Gece")
KATEGORI_SQCD = ("Güvenlik", "Kalite", "Teslimat", "Maliyet")
ISSUE_DURUM = ("Açık", "Kapandı")
AKSIYON_DURUM = ("Açık", "Devam Ediyor", "Doğrulama", "Kapandı")

# ── SQLAlchemy Temelleri ────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///qrqc.db"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════
#  1) Meetings — Toplantılar
# ═══════════════════════════════════════════════════════════════════════════
class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tarih = Column(DateTime, nullable=False, default=datetime.now)
    vardiya = Column(String(10), nullable=False)          # Gündüz / Akşam / Gece
    katilimcilar = Column(Text, nullable=True)            # Virgülle ayrılmış isimler
    baslangic_zamani = Column(DateTime, nullable=False, default=datetime.now)
    bitis_zamani = Column(DateTime, nullable=True)        # None → toplantı hâlâ aktif

    # İlişki: Bir toplantıda birden fazla problem açılabilir
    issues = relationship(
        "Issue",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def aktif(self) -> bool:
        """Toplantı henüz kapatılmadıysa aktiftir."""
        return self.bitis_zamani is None

    @property
    def sure_dakika(self) -> int | None:
        """Toplantı süresi (dakika). Henüz bitmemişse None döndürür."""
        if self.bitis_zamani is None or self.baslangic_zamani is None:
            return None
        delta = self.bitis_zamani - self.baslangic_zamani
        return max(int(delta.total_seconds() / 60), 0)

    def __repr__(self) -> str:
        return (
            f"<Meeting(id={self.id}, tarih={self.tarih:%Y-%m-%d}, "
            f"vardiya='{self.vardiya}')>"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  2) Issues — Problemler
# ═══════════════════════════════════════════════════════════════════════════
class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )

    problem_tanimi = Column(Text, nullable=False)
    tespit_yeri = Column(String(100), nullable=False)     # Hat / Makine / İstasyon adı
    kategori = Column(String(20), nullable=False)         # SQCD
    acil_onlem_alindi_mi = Column(Boolean, default=False)
    kok_neden_5_why = Column(Text, nullable=True)         # 5 Neden analizi notları
    df_no = Column(String(50), nullable=True)             # 4D / Düzeltici Faaliyet ref. no
    durum = Column(String(10), nullable=False, default="Açık")
    olusturma_tarihi = Column(DateTime, nullable=False, default=datetime.now)

    # İlişkiler
    meeting = relationship("Meeting", back_populates="issues")
    actions = relationship(
        "Action",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Issue(id={self.id}, kategori='{self.kategori}', "
            f"durum='{self.durum}')>"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  3) Actions — Aksiyonlar
# ═══════════════════════════════════════════════════════════════════════════
class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(
        Integer,
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )

    aksiyon_tanimi = Column(Text, nullable=False)
    sorumlu = Column(String(100), nullable=False)
    termin_tarihi = Column(Date, nullable=False)
    aksiyon_durumu = Column(String(20), nullable=False, default="Açık")

    # İlişki
    issue = relationship("Issue", back_populates="actions")

    def __repr__(self) -> str:
        return (
            f"<Action(id={self.id}, sorumlu='{self.sorumlu}', "
            f"durum='{self.aksiyon_durumu}')>"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  4) Users — Kullanıcılar
# ═══════════════════════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ad_soyad = Column(String(100), nullable=False)
    eposta = Column(String(100), nullable=False, unique=True)
    sifre = Column(String(100), nullable=False)
    bolum = Column(String(50), nullable=False)            # Üretim, Kalite, Bakım, Metot, Lojistik vb.
    gorev = Column(String(50), nullable=False)            # Mühendis, Takım Lideri, Operatör, Müdür vb.

    def __repr__(self) -> str:
        return f"<User(id={self.id}, ad_soyad='{self.ad_soyad}', eposta='{self.eposta}')>"


# ── Veritabanını Oluştur ────────────────────────────────────────────────────
def init_db() -> None:
    """Tüm tabloları oluşturur (varsa atlar)."""
    Base.metadata.create_all(bind=engine)
    print("[OK] Veritabani tablolari olusturuldu (qrqc.db)")

