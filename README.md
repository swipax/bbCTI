# CTI Bulteni

Acik kaynak tehdit istihbarati feed'lerinden (ThreatFox, URLhaus) her 2 gunde
bir otomatik IOC ceken, Gemini ile ozetleyen ve statik bir sitede yayinlayan
kucuk bir otomasyon.

## Kurulum (tek seferlik)

1. **Bu dosyalari bir GitHub reposuna yukle.**
   Repo public olabilir (GitHub Pages'in ucretsiz calismasi icin public
   repo gerekir, private repo icin Pages ozelligi kisitli).

2. **Secrets ekle.**
   Repo -> Settings -> Secrets and variables -> Actions -> "New repository secret"
   - `ABUSECH_AUTH_KEY` -> https://auth.abuse.ch/ hesabindan aldigin key
   - `GEMINI_API_KEY` -> https://aistudio.google.com/apikey adresinden, kart gerekmeden aldigin key

   Bu degerler hicbir zaman kodda gorunmez, sadece Actions calisirken
   gecici olarak ortam degiskeni olarak enjekte edilir.

3. **GitHub Pages'i ac.**
   Repo -> Settings -> Pages -> "Build and deployment" -> Source: "Deploy from
   a branch" -> Branch: `main`, klasor: `/docs`. Kaydet.
   Birkac dakika icinde site `https://<kullanici-adin>.github.io/<repo-adi>/`
   adresinde yayinda olacak.

4. **Workflow'u ilk kez elle calistir.**
   Repo -> Actions sekmesi -> "Update CTI Bulletin" -> "Run workflow".
   Bu, `docs/data/latest.json` dosyasini ilk kez uretir ve otomatik commit'ler.
   Bundan sonra 2 gunde bir 06:00 UTC'de kendiliginden calisacak.

5. **Kontrol et.**
   Actions sekmesinde calismanin yesil (basarili) tamamlandigini gor,
   sonra siteyi ac ve IOC listesinin goruldugunu dogrula.

## Dosya yapisi

```
collector.py                    -> toplama + Gemini ile ozetleme scripti
requirements.txt                -> Python bagimliliklari
.github/workflows/update.yml    -> 2 gunde bir otomatik calistirma
docs/index.html                 -> site (filtreleme, arama, aktivite seridi ile)
docs/data/latest.json           -> workflow tarafindan otomatik uretilir
docs/data/seen_ids.json         -> daha once islenmis IOC'lerin kaydi (tekrar onler)
```

## Notlar

- `collector.py` icindeki `MAX_ITEMS_PER_RUN` degeri her calistirmada en fazla
  kac yeni IOC'nin AI'a gonderilecegini kontrol eder (varsayilan 20).
  Gemini'nin ucretsiz kotasi bu hacim icin fazlasiyla yeterli.
- Model olarak `gemini-3.5-flash-lite` (Gemini 3 ailesinin en hizli/ucuz
  modeli) kullaniliyor, `thinkingLevel: low` ile basit siniflandirma/ozet
  gorevleri icin optimize edilmis. Google modelleri zamanla emekliye
  ayirdigi icin ileride 404 alirsan aistudio.google.com/models uzerinden
  guncel model adini kontrol et.
- Zamanlama su an 2 gunde bir (`0 6 */2 * *`, UTC 06:00). Kucuk bir cron
  garipligi var: bu ifade "ayin 1, 3, 5, 7... gunleri" demek, yani ay
  sonundan ay basina gecişte (31 -> 1) bir gun ust uste gelebilir. Bu,
  toplama script'i zaten sadece yeni IOC'leri isledigi icin bir sorun
  yaratmaz; sikligi degistirmek istersen `.github/workflows/update.yml`
  icindeki cron satirini guncelle.
- Sitedeki "Son gunler" aktivite seridi, `first_seen` tarihine gore son
  14 gunu gruplayip severity renklerine gore gosterir - projenin canli
  calistigini ilk bakista kanitlayan gorsel bir kanit.
