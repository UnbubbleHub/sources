# Unbubble — Piano di progetto

## Panoramica

Dato un fatto o una notizia (es. "tensioni USA/Cuba, 1 Feb 2026"), il sistema recupera un insieme di articoli relativi, ciascuno annotato con metadati generati tramite AI (posizione rispetto al fatto, supporto del claim, prospettiva, tono, rilevanza, ...). Restituisce poi una lista ordinata che massimizza la diversita di prospettive, privilegiando le fonti di maggiore qualita.

## Metadati

Due categorie di metadati generati tramite AI:

1. **Metadati di prospettiva** — posizionano ciascun articolo in uno "spazio delle prospettive", in modo da selezionare un insieme il piu diversificato possibile.
2. **Metadati di qualita / rilevanza** — assegnano un punteggio a ciascun articolo, cosi che tra articoli con prospettive simili si possano preferire le fonti piu affidabili (es. dichiarazioni ufficiali di soggetti coinvolti > editoriali > rilanci di fonti secondarie).

## Pipeline

### Step 1 — Ricerca articoli

**Obiettivo:** dato un fatto/notizia, restituire un'ampia lista di articoli candidati per l'analisi successiva.

**Approccio iniziale:**
1. Generare piu query di ricerca a partire dall'evento in input (modelli/prompt diversi producono query diverse).
2. Deduplicare e raggruppare le query tramite similarita di embedding e clustering.
3. Eseguire le query su uno o piu motori di ricerca.
4. Aggregare i risultati e rimuovere articoli duplicati.

Principio di design: definire interfacce e wrapper API puliti, in modo che le strategie di generazione query e ricerca siano intercambiabili.

**Idee future:**
- Ricerca su liste di fonti curate.
- Utilizzo di piu motori di ricerca (Google, Bing, API di news specializzate).

### Step 2 — Estrazione metadati

Per ciascun articolo candidato, estrarre:

- **Metadati di prospettiva:** posizione, framing, dimensioni del punto di vista — usati per mappare gli articoli nello spazio delle prospettive.
- **Metadati di qualita / rilevanza:** autorita della fonte, immediatezza (fonte primaria vs. secondaria), supporto fattuale — usati per il ranking tra articoli con prospettive simili.

### Step 3 — Selezione e ordinamento

**Obiettivo:** restituire una lista finale di articoli che copra il ventaglio piu ampio possibile di prospettive, privilegiando la qualita.

**Approccio:**
1. **Metrica di diversita** — massimizzare la copertura nello spazio delle prospettive (es. volume del convex hull o simili).
2. **Ordinamento** — tra articoli con prospettive comparabili, ordinare per punteggio di rilevanza/qualita.

**Idea futura — ricerca iterativa:** dopo il primo round di selezione, identificare le prospettive sotto-rappresentate ed eseguire ricerche mirate per colmare i vuoti.

## Domande aperte

- Come definire e misurare concretamente lo "spazio delle prospettive".
- Quali segnali di qualita sono piu predittivi dell'affidabilita di una fonte.
- Come bilanciare diversita e qualita nel ranking finale.
