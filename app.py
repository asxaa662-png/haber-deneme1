import streamlit as st
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import os
import re
import json
from pydub import AudioSegment
import io

st.set_page_config(page_title="Haber Podcast'a Çevir", page_icon="🎙️")

st.title("🎙️ NotebookLM Tarzı Haber Podcast")
st.markdown("Haberi iki sunuculu, samimi sohbet formatında dinle!")

# --- Groq API Key ---
groq_api_key = st.text_input(
    "🔑 Groq API Anahtarı:",
    type="password",
    placeholder="gsk_xxxx...",
    help="console.groq.com adresinden ücretsiz alabilirsin"
)

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
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "button", "iframe", "img"]):
            tag.decompose()
        paragraflar = soup.find_all("p")
        metin = " ".join(p.get_text(strip=True) for p in paragraflar)
        if len(metin) < 200:
            metin = soup.get_text(separator=" ", strip=True)
        metin = re.sub(r"\s+", " ", metin).strip()
        return metin if metin else None
    except Exception as e:
        return None

def diyalog_olustur(metin, api_key):
    prompt = f"""Aşağıdaki haber metnini, iki podcast sunucusu arasında geçen samimi ve doğal bir Türkçe sohbete dönüştür.

Sunucular:
- AYŞEy: Meraklı, soru soran, zaman zaman şaşıran kadın sunucu
- MERT: Bilgili, açıklayan, zaman zaman espri yapan erkek sunucu

Kurallar:
- Toplam 8-12 konuşma satırı olsun
- Her satır şu formatta olsun: AYŞE: [metin] veya MERT: [metin]
- "Vay be!", "Gerçekten mi?", "Yani şunu mu diyorsun ki..." gibi doğal tepkiler ekle
- Haberi dramatize etme, ama ilgi çekici anlat
- Türkçe konuş, resmi değil samimi bir dil kullan
- Başında ve sonunda kısa giriş/kapanış ekle
- Sadece diyalog satırlarını yaz, başka hiçbir şey yazma

Haber metni:
{metin[:2500]}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "temperature": 0.8
    }
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        st.error(f"Groq API hatası: {e}")
        return None

def diyalogi_parcala(diyalog_metni):
    satirlar = []
    for satir in diyalog_metni.strip().split("\n"):
        satir = satir.strip()
        if not satir:
            continue
        if satir.upper().startswith("AYŞE:") or satir.upper().startswith("AYSE:"):
            metin = re.sub(r"^AYŞE:|^AYSE:", "", satir, flags=re.IGNORECASE).strip()
            satirlar.append(("ayse", metin))
        elif satir.upper().startswith("MERT:"):
            metin = re.sub(r"^MERT:", "", satir, flags=re.IGNORECASE).strip()
            satirlar.append(("mert", metin))
    return satirlar

def podcast_ses_olustur(satirlar):
    try:
        birlesik = AudioSegment.empty()
        sessizlik = AudioSegment.silent(duration=400)

        for konusmaci, metin in satirlar:
            if not metin.strip():
                continue
            # Mert için yavaş=True (biraz daha ağır tonu simüle eder)
            yavash = (konusmaci == "mert")
            tts = gTTS(text=metin, lang="tr", slow=yavash)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            seg = AudioSegment.from_mp3(buf)
            # Mert'i biraz daha bas yap (ses tonu farkı)
            if konusmaci == "mert":
                seg = seg - 2  # 2 dB kıs, daha derin algılanır
            birlesik += seg + sessizlik

        out = io.BytesIO()
        birlesik.export(out, format="mp3")
        out.seek(0)
        return out
    except Exception as e:
        st.error(f"Ses oluşturma hatası: {e}")
        return None

# --- Ana buton ---
if st.button("🚀 Podcast Oluştur", type="primary"):
    if not groq_api_key.strip():
        st.warning("Lütfen Groq API anahtarını gir.")
    elif not url.strip():
        st.warning("Lütfen bir URL gir.")
    else:
        with st.spinner("📰 Haber metni çekiliyor..."):
            metin = metni_cek(url)

        if not metin:
            st.error("❌ Bu sayfadan metin çekemedim. Farklı bir haber URL'si deneyin.")
        else:
            st.success(f"✅ Metin çekildi! ({len(metin)} karakter)")

            with st.expander("📄 Çekilen Metni Gör"):
                st.write(metin[:2000] + ("..." if len(metin) > 2000 else ""))

            with st.spinner("🤖 Diyalog oluşturuluyor (Groq/Llama3)..."):
                diyalog = diyalog_olustur(metin, groq_api_key)

            if not diyalog:
                st.error("❌ Diyalog oluşturulamadı.")
            else:
                st.success("✅ Diyalog hazır!")

                with st.expander("💬 Diyalogu Gör"):
                    st.text(diyalog)

                satirlar = diyalogi_parcala(diyalog)

                if not satirlar:
                    st.error("❌ Diyalog formatı anlaşılamadı. Tekrar deneyin.")
                else:
                    st.info(f"🎙️ {len(satirlar)} konuşma satırı bulundu. Sesler oluşturuluyor...")

                    with st.spinner("🔊 Podcast sesi birleştiriliyor..."):
                        ses = podcast_ses_olustur(satirlar)

                    if ses:
                        st.success("🎙️ Podcast hazır!")
                        st.audio(ses, format="audio/mp3")
                        st.download_button(
                            label="⬇️ MP3 İndir",
                            data=ses,
                            file_name="podcast.mp3",
                            mime="audio/mp3"
                        )

st.markdown("---")
st.caption("Groq (Llama3) + gTTS ile ücretsiz yapıldı")