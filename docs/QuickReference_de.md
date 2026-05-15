# Anlagenbuch — Kurzanleitung

Diese Anleitung richtet sich an die tägliche Anwendung. Sie beschreibt,
**was man wo eingibt** und **wie die typischen Abläufe gehen** — nicht
jedes einzelne Feld. Selbsterklärendes wird ausgelassen; erläutert wird
nur, was Einfluss auf Sortierung, Filter, Folgeprozesse oder Reports hat.

Wer keine Lust auf den ganzen Text hat, merkt sich diese zwei
Menüpunkte unter **„Anlagenbuch"** — alles andere findet man von dort:

- **Anlage** — die Akte einer einzelnen Anlage. Hier wird gemeldet,
  gesichtet, geplant.
- **Werkstattauftrag** — was wir bei einer Werkstatt erledigen lassen.

---

## 1. Begriffe (das Wichtigste in einem Absatz)

Eine **Anlage** ist alles, was eine Akte führen soll — LKW, PKW, Stapler,
Rolltor, Feuerlöscher, Sackkarre. Jede Anlage gehört zu einer
**Anlagenklasse** (z.B. „LKW 12 t+"), und jede Klasse hat eine
**Kategorie** (Vehicle, Equipment, Stationary, Building, IT, Other) —
die Kategorie bestimmt, welche Felder die Maske anzeigt.

Zur Anlage werden drei Arten **Einträge** geführt:

| Eintrag        | Wann                                    | Belegnummer |
| -------------- | --------------------------------------- | ----------- |
| Fehlerbericht  | Mangel festgestellt                     | `FEH-...`   |
| Wartungstermin | Termin geplant oder fällig (TÜV, UVV …) | `TER-...`   |
| Statusbericht  | Sichtung ohne Mangel                    | `STA-...`   |

Mehrere Einträge werden zu einem **Werkstattauftrag** (`WAU-...`)
gebündelt, wenn die Anlage in eine Werkstatt geht.

---

## 2. Tägliche Abläufe

### 2.1 Ein Fehler wird gemeldet

Eingang: ein Fahrer oder Kollege ruft an / läuft vorbei.

1. Menü **Anlagenbuch → Anlage** öffnen, gemeldete Anlage suchen.
2. Tab **Fehlerbericht**, neuer Datensatz.
3. **Pflicht:** Kurzbeschreibung, Datum, Priorität.
4. Sinnvoll, sobald bekannt: Melder, Zählerstand, Kostenschätzung,
   Langbeschreibung.
5. Speichern. Status bleibt **Offen**, bis der Fehler erledigt oder
   in einen Werkstattauftrag gehängt wird.

**Wichtig nur für Reports und Filter:**

- **Priorität** entscheidet die Sortierung in der Anlagenakte und in der
  Werkstattmappe. Hoch = oben.
- **Festgestellt-Datum** ist die Sortierreihenfolge in der Historie.
  Wenn der Fehler älter ist als die Eingabe, das echte Datum nehmen.

### 2.2 Eine Anlage geht in die Werkstatt

1. Menü **Anlagenbuch → Werkstattauftrag**, neuer Datensatz.
2. Im oberen Block **„Auftragserstellung"** ausfüllen: Anlage,
   Werkstatt, Bringer, interner Ansprechpartner, geplantes Datum.
3. **Speichern** (sonst weiß das System noch nicht, um welche Anlage es
   geht).
4. Knopf **„Offene Einträge übernehmen"** drücken — die offenen
   Fehlerberichte und überfälligen Wartungstermine der Anlage werden
   automatisch eingetragen.
5. Im Detail-Tab **Positionen** das löschen oder per Häkchen
   `IsResolved=N` zurückstellen, was diesmal **nicht** mit zur
   Werkstatt soll.
6. Über den Druck-Knopf in der Toolbar des Auftrags die
   **Werkstattmappe** ausdrucken — die geht physisch mit zur Werkstatt.

### 2.3 Rückkehr aus der Werkstatt

1. Den richtigen Werkstattauftrag öffnen.
2. Unteren Block **„Nach Rückkehr"** ausfüllen: Rückgabedatum,
   tatsächliche Kosten, Belegnummer (Rechnung).
3. Im Tab **Positionen** prüfen, was wirklich erledigt wurde —
   Häkchen bei nicht-erledigten Punkten entfernen
   (`IsResolved=N`).
4. **Status auf „Completed"** setzen. Das löst aus:
   - alle abgehakten Fehlerberichte werden auf **Done** gesetzt;
   - für jeden erledigten Wartungstermin wird automatisch ein
     **Folgetermin** als Vorschlag angelegt;
   - nicht abgehakte Positionen bleiben offen und tauchen beim
     nächsten „Offene Einträge übernehmen" wieder auf.

### 2.4 Einen Wartungstermin einzeln erledigen

Manche Termine brauchen keinen Werkstattauftrag (z.B. interne
Sichtprüfung). In dem Fall:

1. Anlage öffnen, Tab **Wartungstermin**, den Termin auswählen.
2. **Erledigt-Datum** eintragen, Status auf **Done** setzen, speichern.
3. Das System legt automatisch den **Folgetermin** an, datiert auf den
   ersten Tag des Monats des Erledigungsdatums plus dem
   Standard-Intervall des Termin-Typs. **Datum anpassen, falls die
   Werkstatt oder die Behörde ein anderes Datum vorgibt** — TÜV ist in
   der Praxis nie exakt 12 Monate.

### 2.5 Eine Sichtung festhalten (Statusbericht)

Sinn: lückenlose Historie, auch wenn kein Mangel vorliegt.
Gebraucht wird das bei der **Erstaufnahme einer neuen Anlage**, bei
**Übergaben zwischen Fahrern** und bei **regelmäßigen Sichtungen**.

1. Anlage öffnen, Tab **Statusbericht**, neuer Datensatz.
2. Datum, Kurzbeschreibung („Sichtkontrolle Disposition"),
   km-Stand. Speichern — der Eintrag wird direkt als erledigt
   abgelegt.

### 2.6 Eine neue Anlage anlegen

1. Menü **Anlagenbuch → Anlage**, neuer Datensatz.
2. **Anlagenklasse** wählen — bestimmt UI-Verhalten, Standard-Termine
   und die Maßeinheit für Zählerstände.
3. Mindestens **Value** (Kurz-Identifikator, z.B. Kennzeichen) und
   **Name** ausfüllen. Alle anderen Stammdaten können später.
4. Im Tab **Wartungstermin** die ersten Pflicht-Termine eintragen
   (TÜV, UVV, …). Folgetermine entstehen ab dem ersten Abschluss
   automatisch.
5. Im Tab **Statusbericht** den Ist-Zustand zum Zeitpunkt der
   Aufnahme festhalten (km-Stand, allgemeiner Eindruck).

### 2.7 Eine Anlage stilllegen

Verkauft, verschrottet, ausgemustert — die Anlage soll nicht mehr in
Auswertungen erscheinen, die Akte aber erhalten bleiben.

1. Anlage öffnen.
2. Häkchen bei **Aktiv** entfernen (`IsActive=N`).
3. Speichern. Die Anlage taucht nicht mehr in den Standard-Filtern auf,
   die Historie ist über die Suche „Alle anzeigen" weiterhin erreichbar.

---

## 3. Reports — was wann

Drei Standard-Reports, alle erreichbar über das Druck-Symbol in der
Toolbar des jeweiligen Fensters oder über das Menü:

| Report                      | Aufruf von …     | Zweck                                                                       |
| --------------------------- | ---------------- | --------------------------------------------------------------------------- |
| **Werkstattmappe**          | Werkstattauftrag | Geht mit zur Werkstatt; Bestätigung bei Rückgabe.                           |
| **Anlagenakte**             | Anlage           | Stammdaten, anstehende Termine, offene Fehler, Historie.                    |
| **Anlagenübersicht Status** | Menü Anlagenbuch | Flottenweite Liste, gefiltert nach Klasse, nur Anlagen mit offenen Punkten. |

Die Übersicht ist das Werkzeug für die wöchentliche Lage in der
Disposition.

---

## 4. Kleinkram, der oft gefragt wird

- **Wer ist „Melder", wer „Erfasser"?** Melder = der, der den Mangel
  gemeldet hat. Wer die Maske ausfüllt (meist die Disponentin), wird
  von iDempiere automatisch als Anleger gespeichert — nicht extra
  eintragen.
- **Zählerstand bei jedem Eintrag?** Ja, wenn man ihn ohne Aufwand
  ablesen kann. Auch der Statusbericht profitiert davon — er liefert
  die einzigen verlässlichen km-Stände zwischen den Werkstattbesuchen.
- **Falsche Anlage erwischt?** Eintrag löschen und neu anlegen ist
  meist einfacher als auf eine andere Anlage zu verschieben.
- **„Pflicht" / „Kür"?** Steht am **Termin-Typ**, nicht am einzelnen
  Termin — TÜV ist immer Pflicht, eine Garantie-Erinnerung immer Kür.

---

## 5. Was das System (noch) nicht macht

- Keine Fahrer-App: Fehlerberichte kommen weiter mündlich / per
  Telefon, die Disponentin tippt sie ein.
- Keine automatische Vor-Generierung wiederkehrender Termine — der
  Folgetermin entsteht erst, wenn der aktuelle als erledigt gespeichert
  wird.
- Keine Kennzahlen / Statistiken in der ersten Version. Folgt, sobald
  genug Daten beisammen sind.
