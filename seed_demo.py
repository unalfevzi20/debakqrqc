"""
QRQC — Örnek Veri Oluşturma (v2 — baslangic_zamani / bitis_zamani destekli)
=============================================================================
"""

from datetime import date, datetime, timedelta

from models import Action, Issue, Meeting, SessionLocal, init_db


def seed_demo_data() -> None:
    """Veritabanina ornek kayitlar ekler."""

    init_db()
    session = SessionLocal()

    try:
        # ── Bitmiş Toplantı #1 (dün sabah, 25 dk sürmüş) ───────────────
        dun_baslangic = datetime(2026, 6, 30, 8, 0, 0)
        dun_bitis = datetime(2026, 6, 30, 8, 25, 0)

        toplanti_1 = Meeting(
            tarih=dun_baslangic,
            vardiya="Gunduz",
            katilimcilar="Ahmet Yilmaz, Elif Demir, Mehmet Kara, Zeynep Aksoy",
            baslangic_zamani=dun_baslangic,
            bitis_zamani=dun_bitis,
        )
        session.add(toplanti_1)
        session.flush()

        problem_1 = Issue(
            meeting_id=toplanti_1.id,
            problem_tanimi=(
                "Hat-3 cikisinda urun yuzeyinde cizik tespit edildi. "
                "Son 2 saatteki uretim partisi karantinaya alindi."
            ),
            tespit_yeri="Hat-3 / Son Kontrol Istasyonu",
            kategori="Kalite",
            acil_onlem_alindi_mi=True,
            durum="Acik",
            olusturma_tarihi=dun_baslangic,
        )
        session.add(problem_1)
        session.flush()

        aksiyon_1 = Action(
            issue_id=problem_1.id,
            aksiyon_tanimi="Hat-3 tasima bandini yenisiyle degistir.",
            sorumlu="Mehmet Kara",
            termin_tarihi=date.today() + timedelta(days=1),
            aksiyon_durumu="Devam Ediyor",
        )
        aksiyon_2 = Action(
            issue_id=problem_1.id,
            aksiyon_tanimi=(
                "PM planina bant degisim periyodunu ekle ve "
                "hatirlatma mekanizmasi kur."
            ),
            sorumlu="Zeynep Aksoy",
            termin_tarihi=date.today() + timedelta(days=7),
            aksiyon_durumu="Acik",
        )
        session.add_all([aksiyon_1, aksiyon_2])

        # ── Bitmiş Toplantı #2 (bugün sabah, 18 dk sürmüş) ─────────────
        bugun_baslangic = datetime(2026, 7, 1, 8, 0, 0)
        bugun_bitis = datetime(2026, 7, 1, 8, 18, 0)

        toplanti_2 = Meeting(
            tarih=bugun_baslangic,
            vardiya="Gunduz",
            katilimcilar="Ahmet Yilmaz, Elif Demir, Can Ozturk",
            baslangic_zamani=bugun_baslangic,
            bitis_zamani=bugun_bitis,
        )
        session.add(toplanti_2)
        session.flush()

        problem_2 = Issue(
            meeting_id=toplanti_2.id,
            problem_tanimi="Montaj hattinda vidalar yanlis tork ile sikiliyor.",
            tespit_yeri="Montaj Hatti / Istasyon-7",
            kategori="Kalite",
            acil_onlem_alindi_mi=True,
            durum="Acik",
            olusturma_tarihi=bugun_baslangic,
        )
        session.add(problem_2)
        session.flush()

        aksiyon_3 = Action(
            issue_id=problem_2.id,
            aksiyon_tanimi="Tork aleti kalibrasyonunu yaptir.",
            sorumlu="Can Ozturk",
            termin_tarihi=date.today(),
            aksiyon_durumu="Devam Ediyor",
        )
        session.add(aksiyon_3)

        session.commit()
        print("[OK] Ornek veriler basariyla eklendi (2 bitmis toplanti).")

    except Exception as exc:
        session.rollback()
        print(f"[HATA] {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_demo_data()
