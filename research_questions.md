# RESEARCH QUESTIONS & PROJECT STATE (EN)

## Project Flow & Architecture
The logical progression of the project is: 
1. Prove it works (**RQ1**) → 2. Prove people feel it (**RQ2**) → 3. Prove you can see it (**RQ3**) → 4. Prove you can predict it (**RQ4**) → 5. Prove you can optimize the inputs (**RQ5**).

* **RQ1 & RQ2:** Answered sufficiently to justify continued investment.
* **RQ3:** The open gap (requires further modeling).
* **RQ4:** The core engine of the application.
* **RQ5:** The roadmap for the next iteration of the playlist generator.

---

### RQ1 — Objective Stress Reduction
* **Primary Question:** Does music reduce stress objectively? (Does listening to a playlist actually speed up physiological recovery?)
* **Role in Project:** The foundation. Without a positive result here, downstream analysis is moot.
* **Current Status:** Inconclusive. Effect present but not statistically significant at this sample size.
* **Metrics & Findings:**
    * The recovery analysis finds a mean advantage of +46.9 min (reliable subset, n=6; p=0.094, not significant at α=0.05). All-valid subset: n=13, mean=+17.5 min, p=0.317.
    * Data loss is severe: only 17 of 74 sessions pass quality filters (r²>0.05); only 6 pass the full reliability criteria (pre_stress ≥ asymptote).
    * Per playlist (all-valid subset): ENERGY=+41 min, CALM=−10 min. CALM's negative advantage may reflect that calm pre-states need no recovery boost, or is noise at n=6.

### RQ2 — Subjective Mood Improvement
* **Primary Question:** Does physiological recovery translate into feeling better? (If the body recovers faster, does the person report a mood improvement?)
* **Role in Project:** The bridge between smartwatch biometrics and self-reported data.
* **Current Status:** Weakly correlated. This is the most honest finding in the project.
* **Metrics & Findings:**
    * Correlation between recovery advantage and mood delta is positive but not strong (r ≈ 0.3).
    * Users sometimes feel better without showing it physiologically, and vice versa.

### RQ3 — Biometric Classification
* **Primary Question:** Can we read back which playlist was used from the biometrics alone? (Does the body respond differently enough to Calm vs. Energy vs. Neutral that we could classify the input?)
* **Role in Project:** The inverse problem. Tests whether the biometric signal is clean and distinguishable.
* **Current Status:** The least explored area; currently an open gap.
* **Dependencies:** There is no dedicated notebook for this yet. It will likely require the LSTM architecture work (`lstm_arc.py`) to mature further.

### RQ4 — Mood Outcome Prediction
* **Primary Question:** Can we predict mood outcomes in advance? (Given an individual's current biometric state, which playlist will help them the most?)
* **Role in Project:** The actionable core and engine of the app.
* **Current Status:** Promising but exploratory.
* **Metrics & Findings:**
    * **Ridge Regression:** Yields numerical predictions (LOO-R² ≈ 0.32 for mood, 0.87 for stress).
    * **Bayesian Recommender:** Yields probabilistic recommendations with uncertainty intervals per participant.
    * **Key Signal:** Circadian baseline deviation is the strongest predictor.
    * **Limitation:** N=40 sessions is currently too small for confident, generalized conclusions.

### RQ5 — Unsupervised Playlist Optimization
* **Primary Question:** Can unsupervised clustering improve the playlists themselves? (Rather than hand-tuning BPM/energy cutoffs, can the data tell us how music naturally groups?)
* **Role in Project:** Zooms out from the individual session to the music library. Informs the next iteration of the playlist generator.
* **Current Status:** The manual trichotomy (Calm/Neutral/Energy) is artificial. We must transition to data-driven clusters as the song pool for playlist generation.
* **Metrics & Findings:**
    * GMM analysis shows the Bayesian Information Criterion (BIC) prefers k=9 over k=3 (BIC difference = −1,696 points). However, silhouette score at k=9 is −0.001 (no cluster separation), while k=3 silhouette = 0.101 (marginal separation).
    * Conclusion: The audio feature space is a continuous spectrum — no truly discrete categories exist. The manual three-category split approximates a gradient rather than partitioning natural clusters. For playlist generation, k=3 remains the practical choice.


---
# ONDERZOEKSVRAGEN & PROJECTSTATUS (NL)

## Projectflow & Architectuur
De logische opbouw van het project is: 
1. Bewijs dat het werkt (**RQ1**) → 2. Bewijs dat mensen het voelen (**RQ2**) → 3. Bewijs dat je het kunt meten (**RQ3**) → 4. Bewijs dat je het kunt voorspellen (**RQ4**) → 5. Bewijs dat je de input kunt optimaliseren (**RQ5**).

* **RQ1 & RQ2:** Voldoende beantwoord om verdere investeringen te verantwoorden.
* **RQ3:** De ontbrekende schakel (vereist verdere modellering).
* **RQ4:** De kernmotor van de applicatie.
* **RQ5:** De roadmap voor de volgende iteratie van de playlist-generator.

---

### RQ1 — Objectieve Stressreductie
* **Hoofdvraag:** Vermindert muziek stress objectief? (Zorgt het luisteren naar een playlist daadwerkelijk voor een sneller fysiologisch herstel?)
* **Rol in het Project:** Het fundament. Zonder een positief resultaat hier zijn alle verdere stappen zinloos.
* **Huidige Status:** Inconclusief. Effect aanwezig maar niet statistisch significant bij deze steekproefomvang.
* **Metrieken & Bevindingen:**
    * De herstelanalyse toont een gemiddeld voordeel van +46,9 min (betrouwbare subset, n=6; p=0,094, niet significant bij α=0,05). Alle geldige sessies: n=13, gemiddeld +17,5 min, p=0,317.
    * Het dataverlies is ernstig: slechts 17 van de 74 sessies doorstaan de kwaliteitsfilters (r²>0,05); slechts 6 sessies doorstaan alle betrouwbaarheidscriteria.
    * Per playlist (alle geldige sessies): ENERGY=+41 min, CALM=−10 min. Het negatieve voordeel van CALM kan erop wijzen dat rustige beginstaten geen herstelboost nodig hebben, of is ruis bij n=6.

### RQ2 — Subjectieve Stemmingsverbetering
* **Hoofdvraag:** Vertaalt fysiologisch herstel zich in een beter gevoel? (Als het lichaam sneller herstelt, rapporteert de persoon dan ook daadwerkelijk een verbetering van de stemming?)
* **Rol in het Project:** De brug tussen de biometrie van de smartwatch en de zelfgerapporteerde data.
* **Huidige Status:** Zwak gecorreleerd. Dit is de meest eerlijke bevinding in het volledige project.
* **Metrieken & Bevindingen:**
    * De correlatie tussen het herstelvoordeel en de verandering in stemming (delta) is positief, maar niet sterk (r ≈ 0.3).
    * Gebruikers voelen zich soms beter zonder dat dit fysiologisch zichtbaar is, en vice versa.

### RQ3 — Biometrische Classificatie
* **Hoofdvraag:** Kunnen we puur op basis van de biometrie aflezen welke playlist er is gebruikt? (Reageert het lichaam voldoende verschillend op Calm vs. Energy vs. Neutral zodat we de input kunnen classificeren?)
* **Rol in het Project:** Het inverse probleem. Dit test of het biometrische signaal zuiver en duidelijk te onderscheiden is.
* **Huidige Status:** Het minst onderzochte gebied; momenteel een open hiaat.
* **Afhankelijkheden:** Er is hiervoor nog geen specifieke notebook. Dit vereist waarschijnlijk dat het werk aan de LSTM-architectuur (`lstm_arc.py`) verder wordt ontwikkeld.

### RQ4 — Voorspelling van Stemmingsresultaat
* **Hoofdvraag:** Kunnen we de impact op de stemming vooraf voorspellen? (Gegeven de huidige biometrische staat van een individu, welke playlist zal hen het meest helpen?)
* **Rol in het Project:** De actiegerichte kern en de motor van de app.
* **Huidige Status:** Veelbelovend, maar nog in een verkennende fase.
* **Metrieken & Bevindingen:**
    * **Ridge Regressie:** Levert numerieke voorspellingen (LOO-R² ≈ 0.32 voor stemming, 0.87 voor stress).
    * **Bayesiaanse Recommender:** Geeft probabilistische aanbevelingen met onzekerheidsintervallen per deelnemer.
    * **Belangrijkste Signaal:** De afwijking van de circadiane baseline is de sterkste voorspeller.
    * **Beperking:** N=40 sessies is momenteel te klein om met zekerheid algemene conclusies te trekken.

### RQ5 — Unsupervised Playlist-optimalisatie
* **Hoofdvraag:** Kan 'unsupervised clustering' de playlists zelf verbeteren? (In plaats van handmatig BPM/energy-grenswaarden in te stellen, kan de data ons vertellen hoe muziek zich op een natuurlijke manier groepeert?)
* **Rol in het Project:** Zoomt uit van de individuele sessie naar de volledige muziekbibliotheek. Vormt de basis voor de volgende iteratie van de playlist-generator.
* **Huidige Status:** De handmatige driedeling (Calm/Neutral/Energy) is kunstmatig. We moeten overstappen op datagedreven clusters als poel voor het genereren van playlists.
* **Metrieken & Bevindingen:**
    * GMM-analyse toont aan dat het Bayesian Information Criterion (BIC) een voorkeur heeft voor k=9 boven k=3 (BIC-verschil = −1.696 punten). De silhouette-score bij k=9 is echter −0,001 (geen clusterscheiding), terwijl k=3 een silhouette van 0,101 heeft (marginale scheiding).
    * Conclusie: De *audio feature space* is een continu spectrum — er zijn geen werkelijk discrete categorieën. De handmatige driedeling benadert een gradiënt. Voor het genereren van playlists blijft k=3 de praktische keuze.