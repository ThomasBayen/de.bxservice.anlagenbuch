---
title: "Anlagenbuch"
subtitle: "Vorstellung des neuen Wartungs- und Fehlerberichts-Systems"
author: "Jakob Bayen KG"
institute: "\\includegraphics[height=1.4cm]{logo.png}"
date: "Mai 2026"
aspectratio: 169
fontsize: 11pt
---

# Worum geht es?

**Das Problem, das wir alle kennen:**

- Ein Fahrer meldet einen Mangel — irgendwo, irgendwem.
- Im Büro weiß ein paar Tage später keiner mehr Bescheid.
- Der LKW geht zum TÜV, die Ladeklappe bleibt kaputt.
- Zwei Personen fahren zweimal 25 km.

**Das wollen wir abstellen.**

\vspace{0.5em}

Ziel: Eine zentrale, elektronische **Akte pro Fahrzeug, Stapler oder Anlage**.
Wer was wann festgestellt hat. Was offen ist. Was als nächstes ansteht.

\topimage[5cm]{truck.png}

# Vier zentrale Begriffe

\begin{tabular}{p{3.5cm}p{10.5cm}}
\textbf{Anlage / Asset} & Ein verwaltetes Objekt — LKW, PKW, Stapler, Rolltor, Feuerlöscher, Sackkarre, Dach. Hat eine Akte. \\[0.6em]
\textbf{Fehlerbericht} & Eine Notiz, dass etwas nicht in Ordnung ist. Wer hat was wann an welcher Anlage festgestellt. Mit Priorität. \\[0.6em]
\textbf{Werkstattauftrag} & Sammelt mehrere Fehlerberichte, die gemeinsam in einer Werkstatt erledigt werden. Mit Werkstatt, Datum, Kosten, Rechnung. \\[0.6em]
\textbf{Wartungstermin} & TÜV, SP, UVV, Garantie-Ablauf. Pro Anlage. Pflicht oder Kür. \\
\end{tabular}

# Wie sieht das im Alltag aus?

**1. Jemand stellt etwas fest** → Fehlerbericht anlegen (Disponentin tippt sie nach mündlicher Meldung ein, später per App durch den Fahrer selbst).

**2. Es sammeln sich Fehlerberichte an der Anlage.**

**3. Wenn ein Werkstatttermin ansteht** (z. B. TÜV), legt die Disponentin einen Werkstattauftrag an und hängt die offenen Fehlerberichte rein, die mit erledigt werden sollen.

**4. Auto fährt zur Werkstatt mit der gedruckten Werkstattmappe.**

**5. Bei Rückkehr** wird der Auftrag geschlossen — Fehlerberichte, die behoben wurden, sind damit automatisch erledigt. Was nicht ging, bleibt offen für nächstes Mal.

# Eingabe: Fehlerbericht

\begingroup\tiny

```
+-----------------------------------------------------------------+
|  Fehlerbericht FEH-2026-00184                    [Speichern]    |
+-----------------------------------------------------------------+
|  Anlage:        [KR-JB 2078         v]  Mercedes Actros         |
|  Festgestellt:  [08.05.2026]  durch  [Müller, F.    v]          |
|  Priorität:     ( ) niedrig (•) mittel ( ) hoch                 |
|                                                                 |
|  Kurzbeschreibung: [Ladeklappe rechts klemmt              ]     |
|                                                                 |
|  Beschreibung (Details):                                        |
|  +-----------------------------------------------------------+  |
|  | Rechte Ladeklappe öffnet nicht. Mechanik klemmt,          |  |
|  | hörbar beim Versuch zu öffnen.                            |  |
|  +-----------------------------------------------------------+  |
|                                                                 |
|  km-Stand:        [   324 850]                                  |
|  Kostenschätzung: [   ca. 250 EUR]                              |
|                                                                 |
|  Status:          [Offen             v]                         |
+-----------------------------------------------------------------+
```

\endgroup

**Pflichtfelder:** Anlage, Datum, Kurzbeschreibung, Priorität. Alles andere kann nachgepflegt werden.

\backimage[5cm]{tow_truck.png}

# Sonderfall: Statusbericht — wofür?

Manchmal will man einfach nur **festhalten, wie eine Anlage an einem
Tag aussah** — ohne dass etwas kaputt ist. Zum Beispiel:

- bei der **Erstaufnahme** des Bestands (km-Stand, allgemeiner Eindruck, „läuft");
- bei einer **regelmäßigen Sichtung** durch die Disponentin oder den Werkstattmeister;
- nach einer **Übergabe** zwischen Fahrern;
- nach einer **Vorführung** beim Sachverständigen, dem TÜV, der Berufsgenossenschaft.

\vspace{0.5em}

Dafür gibt es am Anlage-Fenster den Detail-Tab **„Statusbericht"** — eine
schlanke Variante der Fehlerbericht-Maske, in der nur Datum, Erfasser,
Kurzbeschreibung und km-Stand erfasst werden. Wird direkt als erledigt
gespeichert, kein Werkstattauftrag.

# Sonderfall: Statusbericht — was bringt das?

\textbf{Drei konkrete Vorteile:}

1. **Lückenlose Historie pro Anlage.** In der Akte stehen Fehlerberichte,
   Wartungstermine *und* Statusmomente nebeneinander — immer mit Datum,
   Erfasser und km-Stand. Wer fragt „wie sah der LKW im März aus?",
   bekommt eine Antwort.

2. **Sauberer Einstieg ins System.** Wenn wir das Anlagenbuch neu
   einführen, sind viele Fahrzeuge weder kaputt noch fällig — sie
   *funktionieren*. Mit einem Statusbericht je Anlage haben wir trotzdem
   sofort einen dokumentierten Anfangsstand für jede.

3. **Grundlage für die Übersicht.** Der Report **„Anlagenübersicht /
   Status"** zeigt pro Anlage den letzten Statusbericht plus offene
   Fehler/Termine. Wer ihn morgens öffnet, sieht den aktuellen Zustand
   des kompletten Fuhrparks auf einer Seite.

# Eingabe: Werkstattauftrag

\begingroup\tiny

```
+-----------------------------------------------------------------+
|  Werkstattauftrag WAU-2026-00031                [Schließen]     |
+-----------------------------------------------------------------+
|  Anlage:       KR-JB 2078                                       |
|  Kurzbeschreibung: [TÜV + Klappe + Reifen                 ]     |
|  Werkstatt:    [Nutzfahrzeuge Schmidt GmbH      v]              |
|  Geplant:      [12.05.2026]   Rückgabe: [____________]          |
|  km bei Rückgabe: [_______]                                     |
|                                                                 |
|                  [Offene Einträge übernehmen]                   |
|                                                                 |
|  +-----------------------------------------------------------+  |
|  | erl? | Typ        | Nr             | Bezeichnung          |  |
|  | [x]  | Termin     | TER-2026-00412 | TÜV                  |  |
|  | [x]  | Termin     | TER-2026-00413 | Sicherheitsprüfung   |  |
|  | [x]  | Fehlerb.   | FEH-2026-00184 | Ladeklappe rechts    |  |
|  | [x]  | Fehlerb.   | FEH-2026-00190 | Reifen vorn links    |  |
|  | [ ]  | Fehlerb.   | FEH-2026-00191 | Innenraum-Lüfter     |  |
|  +-----------------------------------------------------------+  |
|                                                                 |
|  Geschätzte Kosten: [ 850 EUR]   Tatsächlich: [____ EUR]        |
|  Rechnung:          [..................................]        |
+-----------------------------------------------------------------+
```

\endgroup

\footnotesize

**„Offene Einträge übernehmen"** trägt offene Fehlerberichte und Wartungstermine automatisch ein — überflüssige werden gelöscht oder das Häkchen entfernt.

Beim **Schließen** werden abgehakte Positionen erledigt; Wartungstermine bekommen automatisch einen Folgetermin als Vorschlag. Nicht abgehakte Punkte (z. B. der Ventilator) bleiben offen für nächstes Mal.

\backimage[4cm]{mechanic.png}

# Eingabe: Wartungstermin

\begingroup\tiny

```
+-----------------------------------------------------------------+
|  Wartungstermin TER-2026-00412                  [Erledigt]      |
+-----------------------------------------------------------------+
|  Anlage:        KR-JB 2078                                      |
|  Termin-Typ:    [TÜV               v]   (Pflicht: ja)           |
|  Fällig am:     [15.06.2026]                                    |
|                                                                 |
|  Status:        [Geplant           v]                           |
|  Erledigt am:   [____________]                                  |
|  Erledigt durch Werkstattauftrag: [WAU-...        v]            |
|                                                                 |
|  Notiz:                                                         |
|  +-----------------------------------------------------------+  |
|  |                                                           |  |
|  +-----------------------------------------------------------+  |
+-----------------------------------------------------------------+
```

\endgroup

**Beim Klick auf „Erledigt"** wird automatisch ein **neuer TÜV-Termin** vorgeschlagen — vom Erledigungsdatum aus 12 Monate weitergerechnet (auf den Monatsersten gerundet, weil die TÜV-Plakette monatsgenau ist). Datum kann angepasst und gespeichert werden — fertig.

Pflicht/Kür wird nicht am Termin selbst gepflegt, sondern hängt am Termin-Typ — TÜV ist immer Pflicht, eine Garantie-Erinnerung immer Kür.

# Druckansicht: Anlagenakte

\begingroup\tiny

```
================================================================
   ANLAGENAKTE — KR-JB 2078                   Stand: 08.05.2026
================================================================
Mercedes Actros 1845, Bj. 2019, FIN WDB9...
km-Stand:        324.850 (08.05.2026)

Anstehende Termine
----------------------------------------------------------------
  15.06.2026   TÜV                            (Pflicht)
  15.06.2026   Sicherheitsprüfung SP          (Pflicht)
  04.09.2026   Tachograph-Prüfung             (Pflicht)
  31.12.2026   Garantie Aufbau                (Hinweis)

Offene Fehlerberichte
----------------------------------------------------------------
  FEH-2026-00184  hoch     Ladeklappe rechts klemmt
  FEH-2026-00190  mittel   Reifen vorn links: Flankenriss
  FEH-2026-00191  niedrig  Innenraum-Ventilator brummt

Letzte Sichtung
----------------------------------------------------------------
  STA-2026-00057  04.05.2026  Sichtkontrolle Disposition,
                              km 324.620, sichtbar in Ordnung

Letzte Werkstattbesuche
----------------------------------------------------------------
  12.03.2026  Schmidt GmbH      Inspektion          412,80 EUR
  04.11.2025  Aufbau Hellweg    Plane reparieren    218,50 EUR
================================================================
```

\endgroup

Das ist der Ausdruck, der **mit ins Auto** geht oder zur Lagebesprechung.

\rightimage[4cm]{binders.png}

# Druckansicht: Werkstattmappe

\begingroup\tiny

```
================================================================
   WERKSTATTAUFTRAG WAU-2026-00031        12.05.2026
   KR-JB 2078  Mercedes Actros 1845
   Werkstatt: Nutzfahrzeuge Schmidt GmbH
================================================================
km bei Abgabe:  324.850

Bitte folgende Punkte prüfen / beheben:

  1. FEH-2026-00184  Ladeklappe rechts klemmt
     Festgestellt 08.05.2026 von F. Müller
     Rechte Ladeklappe öffnet nicht. Mechanik klemmt,
     hörbar beim Versuch zu öffnen.

  2. FEH-2026-00190  Reifen vorn links: Flankenriss
     Festgestellt 06.05.2026 von H. Weber
     ...

  3. FEH-2026-00191  Innenraum-Ventilator brummt
     Festgestellt 04.05.2026 von F. Müller
     ...

Anstehende Wartung in diesem Auftrag:
  - TÜV (fällig 15.06.2026)
  - Sicherheitsprüfung SP (fällig 15.06.2026)
================================================================
```

\endgroup

Eine Seite pro Auftrag. Geht mit zur Werkstatt — bei Rückgabe fragt die Disponentin Position für Position ab.

\rightimage[4cm]{sign.png}

# Werkstattmappe — Beispiel

\begin{center}
\shadowimage[page=1,height=0.75\textheight]{Werkstattmappe_de.pdf}

\vspace{0.4em}
{\footnotesize Auftragskopf, Positionen und Quittierfeld der Werkstatt — automatisch generiert aus dem Werkstattauftrag.}
\end{center}

# Anlagenakte — Beispiel

\begin{center}
\shadowimage[page=1,height=0.75\textheight]{Anlagenakte_de.pdf}

\vspace{0.4em}
{\footnotesize Vollständige Akte einer Anlage: Stammdaten, anstehende Termine, offene Fehlerberichte, Status-Historie, Werkstattbesuche.}
\end{center}

# Anlagenübersicht — Beispiel

\begin{center}
\shadowimage[page=1,height=0.75\textheight]{Anlagenuebersicht_Status_de.pdf}

\vspace{0.4em}
{\footnotesize Eine Seite für den ganzen Fuhrpark: pro Anlage der letzte Statusbericht plus offene Themen. Speist sich aus den Statusberichten.}
\end{center}

# Welche Anlagen wollen wir abdecken?

**Sofort:**

- LKW
- PKW
- Stapler

**Bald:**

- Rolltore
- Feuerlöscher
- Kehrmaschinen, Sackkarren, weitere technische Anlagen

**Wenn wir Lust haben:**

- Immobilien (Dach, Heizung, …)
- IT-Geräte (Inventar)

\vspace{0.5em}

*Das System ist von Anfang an so gebaut, dass alle diese Klassen reinpassen — wir entscheiden Stück für Stück, was wir aktiv pflegen.*

# Was machen wir (noch) nicht?

- **Keine Fahrer-App** in der ersten Version. Fehlerberichte melden die Fahrer wie bisher mündlich oder per Telefon — die Disponentin tippt sie ein. *(Die App kommt später.)*

- **Keine Statistiken / Kennzahlen** am Anfang. Wenn wir ein paar Monate Daten haben, können wir Auswertungen ergänzen.

# Zeitplan und nächste Schritte

\textbf{Kurzfristig (in dieser Form):}

1. **Heute:** Konzept mit Euch durchsprechen, Eure Anmerkungen einsammeln.
2. **Nächste Wochen:** Konzept anpassen, im ERP einrichten (Tabellen, Eingabemasken, Druckberichte).
3. **Bestand erfassen:** alle vorhandenen LKW einmalig als Anlage anlegen, mit aktuellen offenen Themen und Terminen.
4. **Pilotbetrieb:** ein paar Wochen nur LKW, Disponentin pflegt zentral.
5. **Erweiterung:** Stapler, technische Anlagen, … nach und nach.

\textbf{Später:}

- Fahrer-App für direkte Mängelmeldung.
- Auswertungen, Kennzahlen.

# Eure Runde

**Was wir von Euch hören wollen:**

- Fehlt etwas Wichtiges?
- Felder, die wir vergessen haben?
- Begriffe, die anders heißen sollten?
- Abläufe, die so im Alltag nicht funktionieren würden?
- Hatten wir Pannen ähnlich der Ladeklappe, die das System auch nicht verhindern würde?

\vspace{0.3em}

\begin{center}
\Large\textbf{Vielen Dank.}\\[0.5em]
\includegraphics[width=2cm]{cat.png}
\end{center}
