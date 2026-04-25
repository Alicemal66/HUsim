# HÜsim — Hızlı Başlangıç

## Tek Adımda Başlatma

1. `start.bat` dosyasına çift tıkla
2. Tarayıcı otomatik açılacak
3. Tamam!

## Adım Adım (Manuel)

**Terminal 1 — Backend:**
```
cd "C:\Users\cemal\OneDrive\Desktop\HÜsim\husim\backend"
call venv\Scripts\activate.bat
uvicorn main:app --reload --port 8002
```

**Terminal 2 — Frontend (yeni terminal):**
```
cd "C:\Users\cemal\OneDrive\Desktop\HÜsim\husim\frontend"
npm run dev
```

Tarayıcıda: http://localhost:5173

## İlk Kullanım

1. Sol panelden hava koşullarını seç
2. Yük ve eğim parametrelerini ayarla (Yük Paneli)
3. "Parametreleri Optimize Et" butonuna tıkla
4. Senaryo listesinden bir senaryo seç (Faza E senaryoları için "Faza E" filtresini kullan)
5. "Simülasyonu Başlat" butonuna tıkla
6. Araçları izle — EGO hedefe ulaşmaya çalışır
7. Simülasyon bitince "Rapor Oluştur" ile sonuçları kaydet

## Faza E — Yeni Özellikler

- **Yük Sistemi**: Araç yük yüzdesini (0-100%) ve yol eğimini (-15% ile +15%) ayarla
- **10 Yeni Senaryo**: "Faza E" filtresiyle listele
- **Eğim Göstergesi**: Canvas sol alt köşesinde görünür
- **Akıllı Çarpışma Kaçınma**: Sarı (uyarı) / kırmızı (frenleme) halka ile görselleştirilir
