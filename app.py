import streamlit as st
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import os
import re

st.set_page_config(page_title="Haber Podcast'a Çevir", page_icon="🎙️")

st.title("🎙️ Haber → Podcast Dönüştürücü")
st.markdown("Bir haber URL'si yapıştır, sana podcast formatında sesli içerik üreteyim!")

# --- Dil seçimi ---
dil = st.selectbox("Ses dili seç:", ["Türkçe", "İngilizce"])
dil_kodu = "tr" if dil == "Türkçe" else "en"

# --- URL girişi ---
url = st.text_input("🔗 Haber URL'sini buraya yapıştır:")

def metni_cek(url):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")

        # Gereksiz etiketleri temizle
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "button", "iframe", "img"]):
            tag.decompose()

        # Paragrafları topla
        paragraflar = soup.find_all("p")
        metin = " ".join(p.get_text(strip=True) for p in paragraflar)

        # Çok kısa sonuç olduysa tüm body'yi dene
        if len(metin) < 200:
            metin = soup.get_text(separator=" ", strip=True)

        # Fazla boşlukları temizle
        metin = re.sub(r"\s+", " ", metin).strip()

        return metin if metin else None
    except Exception as e:
        return None

def podcast_metni_hazirla(metin, baslik=""):
    """Metni podcast formatına uygun hale getirir."""
    # Çok uzunsa ilk 3000 karakteri al (gTTS için makul limit)
    if len(metin) > 3000:
        metin = metin[:3000] + "..."

    giris = (
        f"Merhaba, hoş geldiniz. Bugünkü haberimize geçiyoruz. {baslik} "
        if dil_kodu == "tr"
        else f"Hello and welcome. Here is today's news. {baslik} "
    )
    bitis = (
        " Haberi dinlediğiniz için teşekkür ederiz. İyi günler!"
        if dil_kodu == "tr"
        else " Thank you for listening. Have a great day!"
    )
    return giris + metin + bitis

def ses_olustur(metin, dil_kodu):
    try:
        tts = gTTS(text=metin, lang=dil_kodu, slow=False)
        dosya = "podcast.mp3"
        tts.save(dosya)
        return dosya
    except Exception as e:
        st.error(f"Ses oluşturulurken hata: {e}")
        return None

# --- Ana buton ---
if st.button("🚀 Podcast'a Dönüştür", type="primary"):
    if not url.strip():
        st.warning("Lütfen bir URL gir.")
    else:
        with st.spinner("Haber metni çekiliyor..."):
            metin = metni_cek(url)

        if not metin:
            st.error(
                "❌ Bu sayfadan metin çekemedim. "
                "Bazı siteler otomatik erişimi engelliyor olabilir. "
                "Farklı bir haber URL'si deneyin."
            )
        else:
            st.success(f"✅ Metin çekildi! ({len(metin)} karakter)")

            with st.expander("📄 Çekilen Metni Gör"):
                st.write(metin[:2000] + ("..." if len(metin) > 2000 else ""))

            with st.spinner("Podcast sesi oluşturuluyor..."):
                podcast_metni = podcast_metni_hazirla(metin)
                ses_dosyasi = ses_olustur(podcast_metni, dil_kodu)

            if ses_dosyasi and os.path.exists(ses_dosyasi):
                st.success("🎙️ Podcast hazır!")
                with open(ses_dosyasi, "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
                with open(ses_dosyasi, "rb") as f:
                    st.download_button(
                        label="⬇️ MP3 İndir",
                        data=f,
                        file_name="podcast.mp3",
                        mime="audio/mp3"
                    )

st.markdown("---")
st.caption("Ücretsiz araçlarla yapıldı: BeautifulSoup + gTTS")