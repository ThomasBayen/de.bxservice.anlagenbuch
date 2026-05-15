# Anlagenbuch — Konzept

## 1. Problemstellung

Im Unternehmen werden Mängel an Fahrzeugen, Geräten und Anlagen bisher mündlich oder per Zuruf gemeldet. Meldungen verlaufen sich, werden nicht mit anstehenden Werkstattterminen verknüpft und Termine (TÜV, SP, UVV, Garantie) liegen verstreut in Köpfen, Kalendern und Papierordnern. Beispiel-Vorfall: Ein LKW kommt vom TÜV-Termin zurück; die seit Tagen bekannte defekte Ladeklappe wurde nicht miterledigt, weil niemand im Büro die Information hatte. Folge: zwei zusätzliche Fahrten à 25 km mit zwei Personen.

Ziel ist ein zentrales, elektronisches Anlagenbuch:

- Jede Fehlerbericht wird zeitnah, von beliebiger Stelle aus, zentral festgehalten.
- Zu jeder Anlage (LKW, PKW, Stapler, Rolltor, Feuerlöscher, …) ist auf einen Blick erkennbar, was offen ist und welche Termine anstehen.
- Werkstattbesuche werden als Auftrag gebündelt — wenn das Auto zum TÜV geht, kommen die offenen Fehlerberichte automatisch ins Bewusstsein.
- Eine druckbare Akte pro Asset begleitet das Gerät in die Werkstatt.

## 2. Scope

### Asset-Klassen, die abgedeckt werden

- Fahrzeuge (LKW, PKW)
- Flurförderzeuge (Stapler)
- Technische Anlagen (Rolltore, Feuerlöscher, Kehrmaschinen, Sackkarren, …)
- Immobilien (Gebäudeteile, Gewerke wie Dach, Heizung, Elektro)
- IT-Geräte (Server, Switches) — eher Inventarcharakter, sekundär

Das Datenmodell ist asset-typ-übergreifend; je nach Klasse werden in der UI bestimmte Felder ein- oder ausgeblendet.

### Funktionsumfang erste Version

- **Asset-Stamm** mit allen typübergreifenden Feldern.
- **Fehlerberichte** (Defects) erfassen, priorisieren, schließen.
- **Werkstattaufträge** (Work Orders) als Bündel mehrerer Fehlerberichte, mit Werkstatt-Geschäftspartner, Zählerstand, Kosten, Rechnungsverknüpfung.
- **Wartungstermine** (Schedules) für TÜV, SP, UVV, Garantie u.ä.; Pflicht/Kür-Kennzeichnung.
- **Druckberichte** (Asset-Akte, Werkstattmappe) per Jasper.
- **Initiales CSV-Befüllen** aus den vorhandenen `M_Resource`-Datensätzen.

### Bewusste Nicht-Ziele dieser Version

- Keine Fahrer-App (späteres Projekt).
- Keine Equipment-Hierarchie / Komponenten-Modellierung.
- Keine automatische Vor-Generierung wiederkehrender Termine.
- Keine Kennzahlen (MTBF, MTTR, Verfügbarkeit) — folgt, sobald genug Daten vorliegen.
- Kein TCO-Reporting.
- Keine Verknüpfung zur Anlagenbuchhaltung (`A_Asset`).

## 3. Festgelegte Entscheidungen

### Begriffe und Sprache

- Hauptbegriff für Mangelmeldung: **Fehlerbericht** (englisch in Tabellen: `Defect`).
- Tabellennamen, Spaltennamen und UI-Default-Labels englisch (Community-Tauglichkeit). Deutsche Labels werden als iDempiere-Übersetzung (`AD_Element_Trl` / `AD_Field_Trl` mit Sprache `de_DE`) mitgeliefert. Doku ist deutsch.
- Tabellen-Präfix: `BXS_` (BX-Service-Hauskonvention, konsistent mit anderen BXS-Plugins).
- **JasperReports-Lokalisierung:** zwei jrxml-Dateien je Report — eine mit deutschem Wortlaut (Default für JBKG), eine `_en`-Variante als Beigabe. Begründung: JasperReports-Resource-Bundles (`$R{key}` + `report_de.properties`) wären der Jasper-Standardweg, lösen aber das eigentliche Konsistenzproblem nicht — ändert ein Admin in iDempiere ein UI-Label, bleibt das Report-Property unverändert. Der Mehraufwand zahlt sich gegenüber zwei jrxml-Dateien nicht aus. Eine spätere Option wäre, Spaltenlabels per JOIN auf `AD_Element_Trl` direkt aus iDempiere zu ziehen — einzige Variante, die UI-Änderungen automatisch in den Report nachzieht. Statische Überschriften dann über `AD_Message`.

### Asset-Modell

- Eine Tabelle für alle Asset-Klassen, typabhängiges Aus-/Einblenden in der UI.
- Kein Bezug zu iDempieres `A_Asset`. Begründung: `A_Asset` ist eng an Anlagenbuchhaltung und automatische Abschreibungsbuchungen gekoppelt; das wollen wir uns nicht ans Bein binden.

### Anlagen-Kategorie und Anlagen-Klasse

Über der `BXS_AssetClass`-Ebene liegt eine **Meta-Kategorie** (`BXS_AssetCategory`, Liste mit 6 festen Werten: `Vehicle`, `Equipment`, `Stationary`, `Building`, `IT`, `Other`). Sie bestimmt UI- und Verhaltens-Logik, während die Klasse die fachliche Untergliederung ist.

Begründung: Der Anwender will eigene Klassen anlegen können (z.B. „LKW <7,5 t" mit anderem TÜV-Intervall als „LKW 12 t+"), ohne dass sich daran Code/Anzeigelogik orientieren muss. Die Trennung erlaubt beliebig viele Klassen pro Kategorie; das System weiß über die Kategorie, wie sich die Anlage „verhält" (Zählerstand sichtbar? Bringer im Werkstattauftrag nötig? Standort fest oder mobil?). `BXS_ScheduleType` hängt sich primär an die Klasse — TÜV gilt für eine bestimmte LKW-Klasse, nicht für alle Vehicles, weil das Intervall klassen-spezifisch sein kann.

### Einträge (Fehlerbericht, Wartungstermin, Statusbericht)

Datentechnisch sind diese drei Konzepte **eine Tabelle** (`BXS_AssetItem`) mit einem Diskriminator-Feld `Type`. Sammelbegriff in der Anwender-Doku: **Eintrag**. In der Programmierer-Doku und in DB-Tabellennamen bleibt `AssetItem` als technischer Term. Das vereinfacht den Werkstattauftrag (eine gemischte Detail-Liste statt zwei) und die Asset-Akte erheblich. In der UI erscheinen die drei als getrennte Detail-Tabs am Asset-Fenster, jeweils mit eigenem Filter und eigener Feldsichtbarkeit — der Anwender sieht drei klar getrennte Sichten.

- **Fehlerbericht (`Type=Defect`):** jemand hat einen Mangel festgestellt. Felder: Kurzbeschreibung (Name), Langbeschreibung, Festgestellt-Datum, Melder, Priorität (klein/mittel/hoch), Zählerstand, Kostenschätzung. Kann manuell oder über einen Werkstattauftrag geschlossen werden.
- **Wartungstermin (`Type=Schedule`):** Termin (TÜV/SP/UVV/Garantie/…) ist zu einem Datum fällig. Felder: Termin-Typ (`ScheduleType`), Fälligkeitsdatum, Zählerstand bei Erledigung, Folgetermin-Verweis. Pflicht/Kür ergibt sich aus dem Termin-Typ. Beim Schließen erzeugt ein Skript automatisch den Folgetermin: `DueDate = erster Tag des Monats des Erledigungsdatums + Standardintervall`. Begründung: TÜV/SP/UVV-Intervalle laufen vom Prüfdatum aus, nicht vom alten Soll-Datum. Kann ebenfalls in einen Werkstattauftrag eingehängt werden.
- **Statusbericht (`Type=Status`):** Zustandsmomentaufnahme ohne Mangel — z.B. bei der Erstaufnahme („Fahrzeug übergeben, km-Stand 324.850, sichtbar in Ordnung") oder bei einer regelmäßigen Sichtung. Wird direkt als erledigt angelegt, kein Werkstattauftrag. Liefert eine lückenlose Historie inklusive Zählerständen.

**Werkstattauftrag-Detail-Tab:** Eine einzige Liste, in der Fehlerberichte und Wartungstermine gemischt erscheinen — typischerweise wird beim TÜV-Besuch der TÜV-Termin selbst und ein paar offene Fehlerberichte miterledigt. Beim Schließen des Auftrags werden alle abgehakten Items auf erledigt gesetzt; bei Wartungsterminen wird zusätzlich der Folgetermin angelegt.

### Werkstattauftrag

- Eigenständiges Dokument, bündelt N Einträge (Fehlerberichte + Wartungstermine, gemischt) über Detail-Tab `BXS_WorkOrder_Item`.
- Felder vor Werkstattbesuch: Anlage, Werkstatt (`C_BPartner`), Bringer/Fahrer (`Driver_ID` → `AD_User`), Ansprechpartner intern (`InternalContact_ID` → `AD_User`; Telefon kommt aus `AD_User.Phone`).
- Felder nach Rückkehr: Rückgabedatum, finale Kosten, Belegnummer (Rechnung oder Auftragsbestätigung) bzw. Rechnungsverknüpfung (`C_Invoice`).
- **iDempiere-Eingabemaske:** Felder in zwei Bereiche per `AD_FieldGroup` trennen — *Auftragserstellung* oben (Werkstatt, Bringer, Ansprechpartner, Termine), *Nach Rückkehr* unten (Rückgabedatum, Kosten, Belegnummer, Status). Erleichtert das Ausfüllen für die Disponentin.
- Verknüpfungs-Datensatz hat Flag `IsResolved` (Default `Y`).
- **Button „Offene Einträge übernehmen":** trägt automatisch alle offenen Fehlerberichte und Wartungstermine des Assets als Werkstattpositionen ein. Der Disponent löscht oder markiert anschließend, was nicht mit zur Werkstatt soll.
- **Abschluss-Workflow** (Skript-Prozess `AD_Rule`, Beanshell/Groovy):
  - Setzt Status aller verknüpften Items mit `IsResolved=Y` auf `Done`, mit `CompletionDate=today`.
  - Items mit `IsResolved=N` bleiben offen (stehen für nächsten Auftrag bereit).
  - Für jedes erledigte Schedule-Item: legt automatisch einen neuen Schedule-Datensatz mit Default-Werten an (Asset, ScheduleType übernommen; `DueDate = ersterTagDesMonats(CompletionDate) + ScheduleType.DefaultIntervalMonths`; `ItemStatus=Open`). Setzt `NextItem_ID` der alten Zeile.
  - Setzt Werkstattauftrag-Status auf `Completed`.
- TÜV-Intervalle sind in der Realität nicht starr 12 Monate — der vorgeschlagene Folgetermin kann vor dem Speichern angepasst werden.

### Sonstiges

- **Stilllegung** = Datensatz wird inaktiv gesetzt (`IsActive=N`, iDempiere-Standard). Historie bleibt erhalten.
- **Dokumente am Asset** über iDempiere-Bordmittel (`AD_Attachment`), nicht eigens modelliert.
- **Kostenfelder:** Schätzung an der Fehlerbericht; finale Kosten und Rechnungsverknüpfung am Werkstattauftrag.

## 4. Auslieferung

### 2Pack + JRXML + Skripte

Erstinstallation läuft komplett über das Standard-2Pack-Fenster, **ohne Server- oder Plugin-Zugriff**. Enthält:

- 2Pack-XML mit Tabellen, Spalten, Fenstern, Tabs, Listen, Workflows, Prozessen.
- Skripte (`AD_Rule`) für Folgetermin-Vorschlag und Werkstattauftrag-Abschluss.
- JRXML-Berichte für Asset-Akte und Werkstattmappe.
- CSV-Import-Vorlage für Bestandsdaten aus `M_Resource`.

Alle UUIDs (Tabellen, Spalten, Fenster, Tabs, Listen, Berichte, Rules) werden einmalig fixiert und versioniert abgelegt, sodass eine spätere Migration in ein OSGi-Plugin vorhandene Datensätze aufgreift statt zu duplizieren.

### Mögliches Plugin (optional, später)

Die Auslieferung als OSGi-Bundle `de.bxservice.anlagenbuch` wird relevant, sobald

- die Logik wächst über das hinaus, was sich in `AD_Rule`-Skripten gut wartbar abbilden lässt,
- Java-Tests, IDE-Komfort oder ModelValidator-Hooks gefragt sind,
- das Modul als Community-Beitrag veröffentlicht wird.

Das Plugin würde dasselbe 2Pack als Ressource mitliefern. Wegen der stabilen UUIDs werden bestehende Datensätze beim Plugin-Import nicht dupliziert.

## 5. Glossar

| Deutsch          | Englisch / Tabelle              | Bedeutung                                                                                               |
| ---------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Anlage           | `BXS_Asset`                     | Verwaltetes Objekt: Fahrzeug, Gerät, Anlage, Gebäudeteil.                                               |
| Anlagen-Kategorie | `BXS_AssetCategory` / Liste    | Meta-Ebene: Vehicle, Equipment, Stationary, Building, IT, Other. Steuert UI-Verhalten.                  |
| Anlagenklasse    | `BXS_AssetClass`                | Fachliche Untergliederung (z.B. mehrere LKW-Klassen mit unterschiedlichen Intervallen). Verweist auf Kategorie. |
| Eintrag          | `BXS_AssetItem`                 | Sammelbegriff für Fehlerbericht, Wartungstermin oder Statusbericht (eine Tabelle, Diskriminator `Type`). |
| Fehlerbericht     | `BXS_AssetItem` (Type=Defect)   | Festgestellter Mangel an einem Asset. Hat Priorität und Status.                                         |
| Wartungstermin   | `BXS_AssetItem` (Type=Schedule) | Geplanter oder fälliger Termin (TÜV, SP, UVV, Garantie, …).                                             |
| Statusbericht    | `BXS_AssetItem` (Type=Status)   | Zustandsmomentaufnahme ohne Mangel, z.B. bei Erstaufnahme. Direkt erledigt.                             |
| Werkstattauftrag | `BXS_WorkOrder`                 | Bündelung mehrerer Items zu einem Werkstattbesuch.                                                      |
| Termin-Typ       | `BXS_ScheduleType`              | Klasse des Termins, mit Standardintervall und Pflicht/Kür-Default.                                      |
| Pflicht / Kür    | Default am Termin-Typ           | Gesetzliche Pflicht (TÜV, UVV) vs. empfohlen.                                                           |
| Werkstatt        | `C_BPartner`                    | Geschäftspartner, der den Auftrag ausführt.                                                             |

## 6. Normbezug (informativ)

Konzept orientiert sich an den einschlägigen Normen, ohne Zertifizierungsanspruch:

- **DIN 31051** — Säulen Wartung / Inspektion / Instandsetzung / Verbesserung; konzeptionelle Trennung zwischen geplanter Tätigkeit (Schedule) und reaktiver Behebung (Defect), nicht als Feld kodiert.
- **ISO 14224** — Equipment Class als `BXS_AssetClass` umgesetzt. Bewusst weggelassen: Equipment-Hierarchie, Failure Mode und Severity (für unsere Flottengröße kein Auswertungsnutzen, der den Erfassungsaufwand rechtfertigt).
- **VDI 2890** — Inspirationsquelle für Wartungsplanung.
- **ISO 55000** — strategische Ebene, nicht im Scope.
