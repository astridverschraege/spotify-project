# Project R.E.M. — Handleiding voor niet-experts

**R.E.M.** staat voor *Regulation of Emotion through Music*. Het project onderzoekt of gepersonaliseerde muziek aantoonbaar stress kan verminderen — gemeten via een smartwatch, niet alleen via zelfrapportage. Acht deelnemers luisterden tijdens het onderzoek naar drie soorten afspeellijsten (kalm, neutraal, energie), samengesteld uit hun eigen Spotify-bibliotheek. Na elke sessie vulden ze een korte check-in in over hoe ze zich voelden.

De basis is het **ISO-principe** uit de muziektherapie: in plaats van direct naar een doelstemming te springen, laat je de muziek geleidelijk meebewegen met de huidige toestand van de luisteraar en daarna langzaam verschuiven naar het doel.

Deelnemers zijn geanonimiseerd met fruitcodenamen: *bosbes, kiwi, kokosnoot, limoen, peer, watermeloen*, enzovoort. In deze handleiding gebruiken we **Peer** als doorlopend voorbeeld.

---

## Volledig stroomschema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GEGEVENSVERZAMELING                          │
│  Spotify-bibliotheek  +  Garmin smartwatch  +  Check-in enquête     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       AFSPEELLIJSTEN                                │
│  ISO-principe → filter op BPM/energie → sorteren → valideren        │
│  Output: kalm / neutraal / energie playlist per deelnemer           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PIJPLIJN 1 — EXTRACTIE                            │
│  Ruwe Garmin-export → minuut-voor-minuut tabellen + activiteitslabel│
│  Output: stress / hartslag / body battery per minuut                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PIJPLIJN 2 — BASISLIJNEN                          │
│  Niet-sessiedagen → "wat is normaal voor Peer om 7u?"               │
│  Output: uurlijks referentieprofiel + persoonlijke herstelcurves    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PIJPLIJN 3 — SESSIE-ANALYSE                       │
│  Sessiedata vs. basislijn → hielp de muziek? hoeveel?              │
│  Output: voordeel per sessie + stemmingsdelta + significantietests  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ML-ANALYSE (notebooks)                         │
│  Welke playlist werkt het best? Kunnen we het voorspellen?          │
│  Clusteren songs van nature in drie groepen?                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        EINDRESULTAAT                                │
│  recommendations.json — per deelnemer: beste playlist + zekerheid  │
│  Streamlit-app (gepland): gepersonaliseerde samenvatting            │
└─────────────────────────────────────────────────────────────────────┘
```

| Stap | Invoer | Wat het doet | Uitvoer |
|------|--------|--------------|---------|
| Gegevensverzameling | Spotify-export, Garmin-download, Google Forms | Drie databronnen verzamelen | Ruwe bestanden per deelnemer |
| Afspeellijsten | Liked songs + audiofeatures | ISO-sortering + validatie | `calm_playlist.csv`, `energy_playlist.csv`, `neutral_playlist.csv` |
| Extractie | Garmin GDPR-export (ZIP) | Ruwe data → gestructureerde minuuttabellen | `garmin_minute_stress.csv`, `classified_minutes.csv` |
| Basislijnen | Minuutdata (niet-sessiedagen) | Referentieprofiel per uur + herstelcurves | `hourly_baseline.csv`, `recovery_baselines.csv` |
| Sessie-analyse | Sessiedata + basislijn + check-in | Effect van muziek meten + statistiek | `session_effects.csv`, `significance_tests.csv` |
| ML-analyse | Sessiekenmerken + stemmingsscores | Modelleren, voorspellen, clusteren | `recommendations.json`, modelplots |

---

## Stap 1 — Gegevensverzameling

Het onderzoek combineert drie databronnen per deelnemer.

**Spotify-bibliotheek (via Exportify)**
Elke deelnemer exporteert alle nummers die hij of zij ooit heeft geliked. Spotify koppelt aan elk nummer automatisch audiofeatures: tempo (BPM), energie (0–1), valentie (positief/negatief gevoel), dansbaarheid, akoestisch karakter en volume. Die kenmerken zijn de basis voor de afspeellijsten en de muziekclassificatie.

*Peer: ~10.000 gelikede nummers.*

**Garmin smartwatch**
De smartwatch meet continu — elke minuut — drie signalen:
- **Stress (0–100):** berekend door Garmin op basis van hartslagvariabiliteit; 0 = volledig ontspannen, 100 = hoge stress
- **Hartslag (BPM):** slagen per minuut
- **Body battery (0–100):** Garmins maat voor energiereserve; daalt bij inspanning, stijgt bij slaap

Deelnemers downloaden hun volledige datageschiedenis via een GDPR-export bij Garmin Connect.

*Peer: ~450.000 minuutmetingen, van januari t/m mei 2026.*

**Check-in enquête (Google Forms)**
Vóór én na elke luistersessie vult de deelnemer een korte enquête in:
- Welke playlist luisterde je?
- Wanneer begon en eindigde de sessie?
- Hoe voelde je je — welke emotie (gestrest, moe, neutraal, blij, …) en hoe intens (1–10)?

Die stemmingsscores zijn de subjectieve meting naast de objectieve smartwatchdata.

*Peer: 31 sessies, verspreid over het onderzoek.*

---

## Stap 2 — Afspeellijsten maken

**Scriptlocatie:** `scripts/playlists/`

**Vraag:** *"Welke nummers uit Peer's eigen bibliotheek passen het best bij elk playlisttype?"*

### Het ISO-principe

Muziektherapie leert dat een abrupte overgang van "gestrest" naar "kalme muziek" averechts werkt. Het ISO-principe lost dit op: de muziek begint bij de huidige toestand van de luisteraar en verschuift geleidelijk naar het doel.

- **Kalme playlist** — begint op middelhoog tempo, daalt richting langzame nummers → bedoeld voor ontspanning en stressreductie
- **Neutrale playlist** — stabiel middentempo, geen richting → controlesessie, meting zonder verwacht effect
- **Energie-playlist** — begint op middelhoog tempo, stijgt naar hogere BPM → bedoeld voor alertheid en activering

### Hoe de afspeellijsten worden samengesteld

1. Filter op BPM-bereik en energieniveau (bijv. kalm: 50–95 BPM, energie < 0,9)
2. Sorteer in de juiste richting (dalend BPM voor kalm, stijgend voor energie)
3. Valideer: minstens 15 BPM verschil tussen kalm en energie, duur ≥ 25 minuten, minimaal 10 nummers

*Peer — energie-playlist: start op ~120 BPM, eindigt op ~175 BPM, 12 nummers, ~30 minuten.*

---

## Stap 3 — Pijplijn 1: Extractie

**Scriptlocatie:** `scripts/extraction/`

**Vraag:** *"Wat deed de smartwatch elke minuut gedurende het hele onderzoek?"*

De ruwe Garmin-export bestaat uit meerdere bestandsformaten die moeilijk direct leesbaar zijn. Deze pijplijn vertaalt alles naar gestructureerde CSV-tabellen.

### 3a. Garmin-extractie (`garmin_pipeline.py`)

Leest twee soorten bestanden uit de Garmin-export:
- **JSON-bestanden** — dagelijkse aggregaten (slaap, stappen, gemiddelde stress)
- **FIT-bestanden** — binaire bestanden met minuut-voor-minuut metingen van hartslag, stress en body battery

Een extra complicatie: de FIT-bestanden zijn opgeslagen in UTC-tijd, terwijl de check-in enquêtes in Belgische tijd (CET/CEST) zijn ingevuld. De extractie lijnt die tijdstempels uit.

*Output per deelnemer: `garmin_minute_stress.csv`, `garmin_minute_hr.csv`, `garmin_daily.csv`, en een aparte trace-CSV per sessie in `session_traces/`.*

### 3b. FIT-extractor (`fit_extractor.py`)

De FIT-bestanden bevatten ook stappentelling en activiteitsintensiteit (Garmins eigen classificatie van hoe zwaar een minuut was). Dit onderdeel voegt die kolommen toe aan de minuuttabellen.

### 3c. Activiteitsclassificatie (`activity_classifier.py`)

Kent aan elke minuut een activiteitslabel toe: **Slapen / Rust / Licht / Matig / Zwaar**.

De classificatie gebruikt een combinatie van signalen:
- Hartslagdrempels (bijv. hartslag > 100 → minstens Matig)
- Garmins intensiteitslabel
- Tijdstip van de dag (nachturen krijgen voorkeur voor Slapen)
- Verloop van de body battery (daalt snel → actief)

Dit label is later cruciaal: de herstelsnelheid van stress verschilt sterk per activiteitsniveau. Iemand die van het sporten komt, herstelt anders dan iemand die aan het bureau zit.

*Peer: `classified_minutes.csv` — 450.000 rijen, elke rij is één minuut met timestamp, stress, hartslag, body battery en activiteitslabel.*

---

## Stap 4 — Pijplijn 2: Basislijnen

**Scriptlocatie:** `scripts/baseline/`

**Vraag:** *"Wat is normaal voor Peer op dit tijdstip van de dag?"*

Om te meten of muziek stress verlaagde, moet je weten wat de stress *zou zijn geweest* zonder muziek. Dat is de basislijn.

### 4a. Circadiaans basislijn (`circadian_baseline.py`)

Ieder mens heeft een dagritme (circadiaans ritme): stress en hartslag variëren systematisch per uur van de dag. Peer's stress om 7u 's ochtends is gemiddeld anders dan om 14u.

Dit onderdeel berekent voor elk uur van de dag (0–23) het gemiddelde stressniveau en de gemiddelde hartslag — maar **uitsluitend op niet-sessiedagen**. Sessiedagen worden bewust uitgesloten: als die meegeteld zouden worden, zou het effect van de muziek de referentie zelf beïnvloeden.

Naast dit algemene dagprofiel berekent het ook een **pre-studie basislijn**: alleen de dagen vóór de allereerste sessie. Die vaste referentie wordt gebruikt om langetermijntrends te detecteren (verandert Peers stressniveau over de maanden van het onderzoek?).

*Peer: om 7u 's ochtends is zijn gemiddelde stress **42 ± 19**. Dat is de referentie voor alle ochtendsessies.*

*Output: `hourly_baseline.csv` (24 rijen, één per uur) en `feature_matrix.csv` (31 rijen, één per sessie, 28 kenmerken).*

### 4b. Persoonlijke herstelbasislijn (`baselines.py`)

Stress daalt niet altijd even snel. Na een zware workout duurt herstel langer dan na een rustige wandeling. Dit onderdeel past per activiteitsniveau een **exponentiële herstelcurve**: een wiskundig model dat beschrijft hoe snel Peer's stress normaal gesproken daalt na dat activiteitsniveau, *zonder muziek*.

Die curve wordt later het ijkpunt: hoe snel daalde de stress *met* muziek vergeleken met wat dit model voorspelt?

*Output: `recovery_baselines.csv` — curve-parameters (snelheid, startpunt, asymptoot) per activiteitsniveau.*

---

## Stap 5 — Pijplijn 3: Sessie-analyse

**Scriptlocatie:** `scripts/sessions/`

**Vraag:** *"Hielp de muziek echt? En hoeveel?"*

Nu alle referentiedata beschikbaar is, kunnen de 31 sessies van Peer één voor één worden geanalyseerd.

### 5a. Sessie-effecten (`session_effect.py`)

Per sessie worden vier dingen berekend:
- **Stress vóór** — gemiddelde stress in de 30 minuten vóór de sessie
- **Verwachte herstelsnelheid** — hoe snel zou stress gedaald zijn *zonder muziek*, gebaseerd op Peers activiteitsniveau en herstelcurve
- **Werkelijke herstelsnelheid** — hoe snel daalde de stress *tijdens* de sessie
- **Voordeel** = verwacht − werkelijk (positief = muziek hielp, stress daalde sneller dan verwacht)

*Voorbeeld Peer, sessie 28 januari:*
- Playlist: Energie
- Stress vóór: 67
- Stress daalde 9,5 punten tijdens de sessie
- Voordeel: **+35 minuten** (herstel verliep 35 minuten sneller dan verwacht)
- Stemming: +1 (licht verbeterd)

### 5b. Sessiefeaturesmatrix (`session_features.py`)

Combineert alle sessiekenmerken tot één platte tabel die direct bruikbaar is voor machine learning: 19 kolommen met onder andere deelnemer, datum, playlisttype, activiteitsstatus voor de sessie, stressmetrieken, hartslagmetrieken, body battery, het berekende voordeel en de stemmingsdelta.

*Output: `session_features.csv` (31 rijen voor Peer).*

### 5c. Sessie-booganalyse (`session_arc_analysis.py`)

**Vraag:** *"Heeft de stress een ander verloop — een andere boogvorm — met muziek dan zonder?"*

Kijkt niet alleen naar het gemiddelde, maar naar de *vorm* van het stresstraject: hoe ziet de stresscurve eruit in de vensters vóór / tijdens / na de sessie? Verschilt die boog per playlisttype?

Bekijkt ook de **langetermijntrend**: neemt het voordeel toe naarmate Peer meer sessies heeft gedaan, of slijt het effect weg?

*Output: `arc_deviations.csv`, `long_term_trends.csv`.*

### 5d. Significantietests (`circadian_significance.py`)

**Vraag:** *"Is het gemeten effect statistisch betrouwbaar, of kan het puur toeval zijn?"*

Voert per deelnemer twee soorten statistische tests uit:
- **Wilcoxon signed-rank test** — vergelijkt stress vóór vs. na per playlisttype (een niet-parametrische test, geschikt voor kleine steekproeven)
- **OLS-trendtest** — kijkt of de basislijnafwijking systematisch verandert over de sessievolgorde

*Output: `significance_tests.csv` — p-waarden en effectgroottes per deelnemer per playlisttype.*

### 5e. Herstelanalyse (`recovery_analysis.py`)

Niet elke sessie levert een betrouwbare herstelcurve op: als de stress tijdens de sessie te grillig verloopt, past de exponentiële curve slecht (lage R²). Dit onderdeel filtert sessies die voldoende betrouwbaar zijn (R² > 0,2) en extraheert verfijnde herstelkenmerken: tijd tot halvering van de stress, uiteindelijk herstelplateau, en of herstel symmetrisch verloopt.

*Output: `recovery_features.csv` + grafieken.*

---

## Stap 6 — Machine Learning

**Notebooklocatie:** `notebooks/ml/`

De pijplijnen produceren data. De ML-notebooks stellen de wetenschappelijke vragen.

### Bayesiaans aanbevelingsmodel (`bayesian_recommender.ipynb`)

**Vraag:** *"Welke playlist werkt het best voor Peer — en hoe zeker zijn we daarvan?"*

Met slechts 31 sessies per persoon is het risico op toeval groot. Een hiërarchisch Bayesiaans model lost dit op: het leert tegelijkertijd van alle deelnemers samen én van Peer afzonderlijk. Deelnemers die sterk afwijken van de groep worden iets teruggetrokken richting het groepsgemiddelde (shrinkage) — dit geeft eerlijkere schattingen bij weinig data.

Het resultaat is per deelnemer een **posterieure verdeling** per playlisttype: niet één getal, maar een kansverdeling die ook de onzekerheid uitdrukt.

*Peer: Kalm-playlist → gemiddeld +4 minuten voordeel (betrouwbaarheidsinterval [3,5–4,4]).*

### Circadiaans ML-model (`circadian_ml.ipynb`)

**Vraag:** *"Kunnen we op basis van de omstandigheden vóór een sessie voorspellen hoeveel stemming of stress zal verbeteren?"*

Traint drie modellen (Ridge regressie, Random Forest, Gradient Boosting) op de 28 kenmerken uit de featuresmatrix. Evalueert via leave-one-out kruisvalidatie (elk model wordt getest op een sessie die het nog niet gezien heeft). SHAP-waarden laten zien welke kenmerken — tijdstip, activiteitsstatus, basislijnafwijking — het meeste bijdragen aan de voorspelling.

### Muziekclassificatie op drempelwaarden (`music_class_thresholds.ipynb`)

**Vraag:** *"Waar liggen de optimale grenzen voor BPM en energie om songs te labelen als kalm of energie?"*

Berekent per nummer een gewogen "arousal score" op basis van de Spotify-audiofeatures. Zoekt dan de drempelwaarden die het beste onderscheid maken tussen kalm, energie en de rest. Die drempelwaarden kunnen de standaardparameters van de playlist-CLI verbeteren.

### Ongesuperviseerde muziekclassificatie (`music_class_unsupervised.ipynb`)

**Vraag:** *"Clusteren songs vanzelf in groepen die overeenkomen met de drie playlisttypen?"*

Gebruikt een Gaussian Mixture Model (GMM) om songs te groeperen op basis van hun audiofeatures, zonder vooraf te weten welk label erbij hoort. Vergelijkt het resultaat met k=3 (drie clusters, zoals de drie playlisttypen) en het statistisch optimale aantal clusters (BIC-selectie). KMeans dient als validatievergelijking.

---

## Stap 7 — Visualisaties

**Notebooklocatie:** `notebooks/visualisation/`

De visualisatienotebooks laden de modelresultaten en maken ze begrijpelijk — geen modeltraining, alleen grafieken en interpretatie.

| Notebook | Wat je ziet | Waarom relevant |
|----------|-------------|-----------------|
| `bayesian_recommender_viz.ipynb` | Posterieure verdelingen per persoon per playlist; groepseffect (forest plot); shrinkage-effect | Hoe zeker is het model over de aanbeveling? Hoe sterk wijkt Peer af van de groep? |
| `circadian_ml_viz.ipynb` | Modelcomparatie (R²); SHAP-belang per kenmerk; voorspelling vs. werkelijkheid | Welke kenmerken voorspellen stemmingsverandering het best? Welk model presteert? |
| `music_class_thresholds_viz.ipynb` | Scatter tempo vs. energie met drempellijnen; classificatienauwkeurigheid | Hoe goed passen de BPM-grenzen bij de werkelijke songs? |
| `music_class_unsupervised_viz.ipynb` | GMM-clusters in PCA-ruimte; BIC-curve; per-cluster statistieken | Bestaan er van nature drie muziekgroepen in de bibliotheken van deelnemers? |
| `recovery_analysis.ipynb` | Herstelcurves per deelnemer; kwaliteitsfilter; tijd-tot-halvering per playlist | Hoe snel herstelt stress, en verschilt dat per playlisttype? |

---

## Eindresultaat

Het project levert drie soorten output:

**Per deelnemer:**
- Sessie-voor-sessie overzicht: welke playlist, hoeveel voordeel, hoe veranderde de stemming
- Significantietests: is het effect betrouwbaar voor deze persoon?
- Posterieure aanbeveling: welke playlist werkt statistisch het best

**Gecombineerd (alle deelnemers samen):**
- Vergelijking tussen deelnemers: zijn er patronen in wie het meeste baat heeft bij welk playlisttype?
- ML-modelresultaten: hoe goed kunnen we het effect voorspellen?

**Centrale uitvoer:** `recommendations.json` — per deelnemer de beste playlist met betrouwbaarheidsinterval, klaar voor gebruik in de app.

**Gepland: Shiny**
