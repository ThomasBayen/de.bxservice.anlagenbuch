# Brainstorming: Wartungs- und Anlagenmanagement

## 1. Wie das Feld heißt (Standards & Begriffe)

Du erfindest hier nichts Neues — das ist ein etabliertes Feld mit klarer Terminologie:

**Disziplinen:**

- **CMMS** (Computerized Maintenance Management System) — genau das, was Du beschreibst: Asset-Stamm, Mängelmeldungen, Wartungspläne, Termine, Werkstattaufträge.
- **EAM** (Enterprise Asset Management) — der größere Bruder: deckt zusätzlich Lifecycle, Beschaffung, Stilllegung, Kosten ab. Übergang zu CMMS fließend.
- **TPM** (Total Productive Maintenance) — Kulturansatz: Bediener melden Auffälligkeiten selbst (genau Dein Fahrer-App-Gedanke).
- **RCM** (Reliability-Centered Maintenance) — Methodik zur Priorisierung: welche Wartung lohnt sich überhaupt?

**Normen, die Du nennen können solltest:**

- **DIN 31051** — definiert die vier Säulen: **Wartung, Inspektion, Instandsetzung, Verbesserung**. Hilft Dir, Begriffe sauber zu trennen.
- **ISO 55000/55001** — Asset Management Management-System (eher strategisch).
- **VDI 2890** — Wartungsplanung.
- **ISO 14224** — Datenstrukturen und Kennzahlen für Equipment, sehr nützlich für Deine Datenmodellierung (definiert Failure Modes, Equipment-Hierarchie etc.).

**Der Begriff, den Du gesucht hast:** Eine Notiz „mit dem Auto stimmt was nicht" heißt im Fachjargon je nach Kontext:

- **Mängelmeldung** / **Schadensmeldung** (am häufigsten im LKW/Fuhrpark-Kontext)
- **Beanstandung** oder **Befund** (Inspektionssprache)
- **Störmeldung** (wenn das Gerät nicht mehr läuft)
- Englisch: **Defect Report**, **Work Request**, **Notification** (SAP PM)
- Im Fuhrpark zusätzlich: **Abfahrtskontrollprotokoll** (vor jeder Fahrt; gesetzlich gefordert!) — das ist faktisch Dein „Fahrer meldet Mangel"-Workflow.

## 2. Konzepte, an die Du noch nicht gedacht hast

- **Trennung von Mängel-Ticket und Arbeitsauftrag.** Ein Fahrer meldet einen Mangel (Work Request). Daraus wird *vielleicht* ein Werkstatttermin (Work Order). Mehrere Mängel → ein Werkstattbesuch. Das ist genau Dein Schmerz aus dem TÜV-Beispiel: Hätte das System die offene Ladeklappen-Meldung beim TÜV-Termin angezeigt, wäre alles in einer Fahrt erledigt worden.
- **Equipment-Hierarchie.** LKW → Aufbau → Ladeklappe. Mängel werden an Komponenten gehängt, nicht nur am Fahrzeug. Hilft bei Wiederholtätern.
- **Meter Reading / Zählerstände.** Kilometerstand, Betriebsstunden (Stapler!), Tankvorgänge. Wartungen sind oft *zustandsbasiert* („alle 40.000 km"), nicht kalendarisch.
- **Vorlagen für Wartungspläne** je Gerätetyp. „LKW Klasse N3" hat Standard-Intervalle (TÜV 12 Monate, SP 12 Monate, UVV jährlich, Tachograph 24 Monate, Feuerlöscher 24 Monate, Verbandskasten ablaufend). Beim Anlegen eines neuen Fahrzeugs werden alle Termine automatisch erzeugt.
- **Pflicht- vs. Kür-Termine.** TÜV/SP/UVV sind gesetzlich, ein Fehlen ist ein Fahrverbot. Andere Wartungen sind Empfehlungen. Das Ranking muss das wissen.
- **Kostenerfassung pro Asset.** Werkstattrechnungen → Anlage. Ergibt nach 2 Jahren Total Cost of Ownership und damit fundierte Ersatz-Entscheidungen.
- **Dokumente am Asset.** Fahrzeugschein, TÜV-Bericht, Bedienungsanleitung, Garantieurkunde. Alles als Anhang.
- **Garantieverfolgung.** Wann läuft Herstellergarantie ab? Manche Reparatur ist noch kostenlos.
- **Stilllegung / Verkauf.** Asset bleibt im System, Status wechselt. Historie bleibt erhalten.
- **Kennzahlen:** MTBF (Mean Time Between Failures), MTTR (Mean Time To Repair), Verfügbarkeitsquote. Lohnt sich aber erst ab ~30 Assets oder mehrjähriger Datenlage.

## 3. Kategorien & deren Eigenheiten

Die Idee, das zu generalisieren, ist richtig — aber **nicht alles in eine Tabelle**. Übliches Muster:

| Kategorie                                                | Spezifika                                                                                   |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **Fahrzeuge** (LKW/PKW)                                  | TÜV/SP, Kennzeichen, Fahrer, km-Stand, ADR                                                  |
| **Flurförderzeuge** (Stapler)                            | UVV jährlich, Bediener-Schein, Betriebsstunden                                              |
| **Technische Anlagen** (Rolltore, Feuerlöscher, Kehrmaschinen) | Wiederkehrende Prüfungen nach BetrSichV, oft mit benannten Stellen                          |
| **IT-Assets**                                            | Seriennummer, Garantie, Lizenzen, kaum Wartung — eher Inventar                              |
| **Immobilien**                                           | Mängelliste pro Gewerk (Dach, Heizung, Elektro), zyklische Prüfungen (E-Check, Brandschutz) |

Empfehlung: **gemeinsamer Asset-Stamm** + **gemeinsames Mängel-/Wartungsmodul**, aber **typabhängige Pflichtfelder** und Wartungsplan-Vorlagen. In iDempiere-Sprech: ein A_Asset mit `M_Product_Category` o.ä., und je Kategorie ein eigener Satz Wartungsregeln.

## 4. iDempiere-Anbindung

Du liegst richtig: **Resources** sind für Tourenplanung/Disposition gedacht, nicht für Asset-Lifecycle. Das richtige Hausmittel ist **A_Asset**:

- A_Asset existiert bereits, hat Felder für Seriennummer, Hersteller, Inbetriebnahme, Standort, Lifecycle-Status, Garantie.
- Eine **Resource** sollte dann auf ein Asset *verweisen* (M_Resource → A_Asset_ID), nicht umgekehrt. Ein Asset kann existieren, ohne aktuell als Resource disponierbar zu sein (z.B. ausgemustert oder in der Werkstatt). Mehrere Resources könnten theoretisch dasselbe Asset abbilden (Tag/Nacht-Schicht).
- Für Mängel/Wartungen bietet sich ein **eigenes Modul** an. Es gab/gibt iDempiere-Erweiterungen wie *iDempiere CMMS* (community) — würde ich anschauen, vermutlich aber zu schwergewichtig. Ein schlankes Eigenmodul mit zwei Tabellen (`X_Asset_Issue`, `X_Asset_Maintenance`) und Workflows ist wahrscheinlich passender.
- **Berichte/Druckansicht** via Jasper Reports — das ist iDempiere-Standard und löst Deine „mit in die Werkstatt geben"-Anforderung sauber.

## 5. Konkrete Empfehlungen für die erste Version

1. **MVP eng schneiden:** Asset-Stamm + Mängelmeldungen + Termine (TÜV/SP/UVV) + Werkstattauftrag + Druckbericht. Nur LKW. Kein Fahrer-App, kein Kostenmodul, keine Hierarchie.
2. **Rückwirkende Datenpflege:** Vorhandene LKW einmalig erfassen mit aktuellen Mängeln. Ohne diese Investition bleibt das System leer.
3. **Eine zentrale Eingabestelle.** Solange die Fahrer-App fehlt, **eine** Person im Büro, an die alle Meldungen gehen, mit der Anweisung: *sofort* eintragen. Ohne diese Disziplin scheitert das System unabhängig von der Software.
4. **Generalisierung als Schema, nicht als Feature.** Plane das Datenmodell heute schon kategorienfähig (Asset-Typ, Wartungsplan-Vorlage), aber baue UI/Reports erstmal nur für Fahrzeuge.

## 6. Namensvorschläge

Reine Wartungs-Begriffe sind zu eng, „Asset Management" zu generisch und englisch. Ein paar Richtungen:

**Sachlich-deutsch:**

- **Betriebsmittelakte** — präzise, nüchtern, deckt Fahrzeuge bis Rolltor.
- **Anlagenbuch** — klassischer Begriff, klingt nach Buchhaltung.
- **Geräteakte** — kurz, aber „Geräte" passt nicht recht zu Immobilien.
- **Instandhaltungsmanagement** — fachlich exakt, sperrig.

**Bildhaft:**

- **Werkbuch** — schön kurz, hat Werkstatt-Klang.
- **Pflegebuch** — warm, fast freundlich; betont das „Kümmern".
- **Lebenslauf** (intern: „LKW-Lebenslauf") — beschreibt gut, was es ist: die Akte des Geräts von Wiege bis Bahre.
- **Logbuch** — passt zu Fahrzeugen, weniger zum Dach.

**Mein Favorit:** **Betriebsmittelakte**. Begründung:

- „Betriebsmittel" ist der saubere Oberbegriff (BGB/Steuerrecht/Versicherung kennen ihn), umfasst LKW, Stapler, Rolltor, Server, Gebäudeteile.
- „Akte" trifft Deine ursprüngliche Formulierung („ich möchte eine Akte haben") und ist haptisch — jeder versteht sofort, dass da alles reinkommt.
- Im Alltag verkürzbar zu „die Akte vom MB-2078".

Falls Du etwas Knackigeres willst: **Werkbuch**.

---

**Offene Punkte für die nächste Session:**

- Vertiefungsrichtung wählen: Datenmodell, iDempiere-Integration, MVP-Scope, oder weitere Standards/Beispiele?
- Namensentscheidung treffen.
