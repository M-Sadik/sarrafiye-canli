# Sarrafiye Canlı

Altınkaynak, Hakan Altın ve Harem Altın sarrafiye fiyatlarını yan yana gösterir, 5 saniyede bir yeniler.

## Yerelde çalıştırma

```
pip install -r requirements.txt
python app.py
```

Tarayıcıda http://localhost:8000 adresini açın.

## Veri kaynakları

| Dövizci | Kaynak |
|---|---|
| Altınkaynak | `https://static.altinkaynak.com/public/Gold` (JSON) |
| Hakan Altın | `https://api.hakanaltin.net/api/history/latest` (JSON) |
| Harem Altın | `wss://hrmsocketonly.haremaltin.com` socket.io, `price_changed` olayı |

Sunucu bu kaynakları arka planda çeker, sayfa `/api/prices` uç noktasını 5 saniyede bir okur.
Ürün eşleştirmeleri `app.py` içindeki `PRODUCTS` listesindedir.

## Render.com'a yükleme (ücretsiz)

1. Bu klasörü bir GitHub deposuna yükleyin.
2. Render.com → New → Blueprint → depoyu seçin (`render.yaml` otomatik okunur).
3. Verilen `https://sarrafiye-canli-xxxx.onrender.com` linkini paylaşın.

Not: Ücretsiz planda 15 dakika kimse girmezse uygulama uyur; ilk açılış ~30-50 sn sürebilir.

## YouTube canlı yayın (OBS)

Yayın için hazırlanmış 1920×1080 ekran: `http://localhost:8000/yayin.html`

1. `baslat.bat` ile sunucuyu açın (çökerse kendini yeniden başlatır).
2. OBS → Kaynaklar → + → **Tarayıcı**: URL `http://localhost:8000/yayin.html`, Genişlik 1920, Yükseklik 1080.
3. OBS → Ayarlar → Video: 1920×1080, 30 FPS. Çıkış: bit hızı ~3000 Kbps.
4. OBS → Ayarlar → Yayın: Hizmet YouTube, "Hesabı bağla" ya da YouTube Studio'daki yayın anahtarı.
5. Yayını Başlat.
