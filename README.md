# Plan
Algoritmo che dato un fatto (o una notizia, e.g. tensione USA/Cuba 1 Feb 2026), estrae una lista di articoli relative al suddetto fatto, ciascuno con una serie di metadati che lo collegano al fatto (opinione rispetto al fatto, supporto del claim, prospettiva, tono, rilevanza...)

Metadati AI generated, due tipi:
- Alcuni per avere una nozione di posizione relativa tra gli articoli, per selezionare opinioni più varie possibili
- Alcuni per valutare la qualità della fonte - in modo da scegliere fonti di qualità maggiore (e.g. dichiarazioni ufficiali di elementi coinvolti direttamente dovrebbero avere qualità maggiore, opinioni di attori rilevanti ha qualità maggiore... Rilanci/fonti secondarie hanno valore minore)

Obiettivo: ritornare una lista di articoli, ordinata per rilevanza, che siano sufficientemente ortogonali tra loro (fornire più opinioni diverse)

To Do:
- Definire come cercare articoli rilevanti
- Definire metadati rilevanti e come misurare "rilevanza" o qualità di una fonte
- Definizione di metrica sui metadati e algoritmo per sorting

Idee aggiuntive:
- Ricerca iterativa per avere una prospettiva completa (e.g. se una volta fatto il sorting manca una prospettiva specifica, è possibile re-iterare e cercare quella specifica prospettiva mancante)
- ...

## Step 1: Algoritmo di ricerca
Obiettivo: dato un fatto/notizia, ritornare una lista di articoli candidati per ulteriore analisi (estrazione metadata). Gli articoli dovrebbero essere abbastanza vari da poter fornire una visione del fatto da prospettive multiple, una volta selezionati i più rilevanti.
How to: TBD
Idee:
- Ricerca su fonti specifiche
- Ricerca su google con varie queries
- ...
## Step 2: Estrazione metadati
### Definizione metadata
#### Prospettiva
Metadati usati per posizionare un articolo nello spazio delle prospettive.
#### Rilevanza
Metadati usati per sorting di notizie con prospettive simili.
### Estrazione
## Step 3: Algoritmo di scelta
Idea: prospettiva più "ampia" possibile (convex hull), fonti più rilevanti/attendibili possibile.
### Metrica - usa prospettiva
### Sorting - usa rilevanza
