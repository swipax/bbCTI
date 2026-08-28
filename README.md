# CTI Bulteni

Acik kaynak tehdit istihbarati feed'lerinden (ThreatFox, URLhaus) her gun
otomatik IOC ceken, Grok (xAI) ile ozetleyen ve statik bir sitede yayinlayan
kucuk bir otomasyon.

## Kurulum (tek seferlik)

1. **Bu dosyalari bir GitHub reposuna yukle.**
   Repo public olabilir (GitHub Pages'in ucretsiz calismasi icin public
   repo gerekir, private repo icin Pages ozelligi kisitli).

2. **Secrets ekle.**
   Repo -> Settings -> Secrets and variables -> Actions -> "New repository secret"
   - `ABUSECH_AUTH_KEY` -> https://auth.abuse.ch/ hesabindan aldigin key
   - `XAI_API_KEY` -> https://console.x.ai hesabindan aldigin key

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
   Bundan sonra her gun 06:00 UTC'de kendiliginden calisacak (cron ayari
   `.github/workflows/update.yml` icinde, istersen saati degistirebilirsin).

5. **Kontrol et.**
   Actions sekmesinde calismanin yesil (basarili) tamamlandigini gor,
   sonra siteyi ac ve IOC listesinin goruldugunu dogrula.

## Dosya yapisi

```
collector.py              -> toplama + Grok ile ozetleme scripti
requirements.txt          -> Python bagimliliklari
.github/workflows/update.yml -> gunluk otomatik calistirma
docs/index.html           -> site (su an cok basit bir taslak)
docs/data/latest.json     -> workflow tarafindan otomatik uretilir
docs/data/seen_ids.json   -> daha once islenmis IOC'lerin kaydi (tekrar onler)
```

## Notlar

- `docs/index.html` su anda sadece pipeline'in ucdan uca calistigini
  dogrulamak icin cok sade bir taslak. Bir sonraki adimda gercek tasarimi
  yapacagiz.
- `collector.py` icindeki `MAX_ITEMS_PER_RUN` degeri gunde en fazla kac yeni
  IOC'nin AI'a gonderilecegini kontrol eder (varsayilan 20). Grok maliyetini
  yonetmek icin bu sayiyi degistirebilirsin.
- Model adi (`grok-4-fast`) zamanla degisebilir, console.x.ai uzerinden
  guncel/en ucuz model adini kontrol et.
