# Master-Daten für den Bayen-Mandanten

Dieses Verzeichnis ist die **Single-Source-of-Truth** für alle Bayen-spezifischen
Anlagenbuch-Stammdaten. Wenn sich eine Klasse, eine konkrete Anlage oder ein
Wartungstermin-Typ ändert, **bitte hier pflegen** und dann den ODS-Builder
neu laufen lassen. Die generierte `anlagenbuch_init.ods` ist Wegwerf-Output,
nicht Quelle.

CSV-Datei-Namen (Vorgabe für den Builder):

* `classes.csv` — Bayen-Anlagenklassen
* `assets.csv` — konkrete Anlagen
* `schedules.csv` — Wartungstermin-Typen

## Verhältnis zum Community-2Pack

Das ausgelieferte 2Pack (`2pack/source/spec/20-assetclass.yaml`) enthält
**sechs sprachneutrale Standardklassen** als Fundament:

| Value | Name | Kategorie | Zweck |
|---|---|---|---|
| 1000 | Vehicle | Vehicle | Generische Fahrzeug-Klasse |
| 2000 | Equipment | Equipment | Generische Geräte-Klasse |
| 3000 | Stationary | Stationary | Fest installierte Technik |
| 4000 | IT | IT | IT-Hardware |
| 5000 | Building | Building | Gebäudeteil |
| 9000 | Other | Other | Auffangkategorie |

Die Bayen-Klassen aus `classes.csv` (1010/1020/.../3010/3020) reihen sich
numerisch dazwischen ein. Sortier-Reihenfolge in Berichten: nach `Value` →
Bayen-LKW (1010) kommt vor Bayen-Stapler (3010) usw. Die generischen
Community-Klassen sind im Bayen-Mandant praktisch ungenutzt; sie stehen für
Implementoren bereit, die nicht so tief modellieren wollen.

## Dateien

### `classes.csv` — Bayen-Anlagenklassen

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `Value` | ja | 4-stellige Nummer, in 10er-Schritten innerhalb des Kategorie-1000er-Blocks |
| `Name` | ja | Deutscher Anzeigename |
| `Kategorie` | ja | Eine von `Vehicle`/`Equipment`/`Stationary`/`Building`/`IT`/`Other` |
| `Description` | – | Lange Beschreibung für die UI |
| `Anmerkung` | – | Kommentar fürs Team (taucht nicht in iDempiere auf) |

Sortierung innerhalb einer Kategorie: groß → klein.

### `assets.csv` — konkrete Anlagen

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `Value` | ja | Eindeutiger Such-Schlüssel (z.B. Kennzeichen, „Stapler 1") |
| `Name` | ja | Anzeigename |
| `KlassenValue` | ja | Verweis auf `classes.csv > Value` |
| `Hersteller` | – | Mercedes/Iveco/MAN/Maxus/VW/… |
| `Modell` | – | Modellbezeichnung soweit bekannt |
| `Baujahr` | – | YYYY |
| `Inbetriebnahme` | – | YYYY-MM-DD |
| `Standort` | – | Frei-Text |
| `Anmerkung` | – | Originale Description aus S_Resource o.ä. |

### `schedules.csv` — Wartungstermin-Typen

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `Value` | ja | Kurzkennung (TUV/SP/UVV/INSPECTION/WARRANTY) |
| `Name` | ja | Anzeigename |
| `KlassenValue` | – | Wenn leer: gilt für alle Klassen. Sonst Verweis auf eine Klasse aus `classes.csv` |
| `IntervallMonate` | ja | Default-Intervall (0 = kein Folgetermin) |
| `PflichtDefault` | ja | `Y` oder `N` — Pflicht-Flag bei neuen Terminen |
| `Description` | – | Erklärungstext |

**Hinweis zur Klassen-Bindung**: `BXS_ScheduleType` hat eine 1:1-FK auf
`BXS_AssetClass`. Wenn ein Termin-Typ (z.B. TÜV) für mehrere Klassen relevant
ist, lassen wir die `KlassenValue` aktuell **leer** und filtern später im UI
beim Anlegen eines konkreten Termins manuell. Falls präzisere Bindungen
gewünscht: entweder pro Klasse einen eigenen ScheduleType (z.B. `TUV-LKW`,
`TUV-PKW`) oder Schema-Erweiterung um eine M:N-Tabelle `BXS_ScheduleType_AssetClass`.

## Wie wird daraus die ODS gebaut?

```bash
python3 build_ods.py
# → schreibt anlagenbuch_init.ods
```

Der Builder liest die drei CSVs, fügt die `S_Resource`-Stammdaten dazu wo
sinnvoll (z.B. um Hersteller-Felder zu vervollständigen), und erzeugt die
ODS-Sheets, die der Anwender im iDempiere-CSV-Importer einlesen kann.

## Wie wird daraus das 2Pack gebaut?

**Gar nicht.** Die Bayen-Master-Daten sind explizit **nicht** im 2Pack
enthalten — sie kommen über den ODS-Import in jeden Mandanten, der sie haben
will. Das 2Pack liefert nur die sechs sprachneutralen Community-Klassen +
das Datenmodell + die Fenster + die Reports.

## Pflege-Workflow bei Änderungen

1. CSV ändern (Klasse hinzufügen, Anlage umklassifizieren, Wartungstermin
   anpassen)
2. ODS neu bauen: `python3 build_ods.py`
3. In iDempiere im Bayen-Mandant: ODS importieren über CSV-Import oder den
   Bayen-spezifischen Workflow
4. Bei Klassen-Änderungen: prüfen, ob bestehende `BXS_Asset`-Records noch
   auf richtige `BXS_AssetClass_ID` zeigen (per UI oder SQL)

## Quellen

- Anlagen (Fahrzeuge mit Kennzeichen): `S_Resource WHERE
  ad_client_id=1000000 AND IsActive='Y'` aus der Bayen-Test-DB (Stand
  Mai 2026). 12 Fahrzeuge plus Kühlanhänger plus 3 EXTRA_ASSETS ohne
  Kennzeichen.
- Klassen + Wartungstermin-Typen: Telefonbriefing 8.5.2026 mit
  Michael Steppert plus Konsolidierung mit alter `ASSET_CLASS_ROWS` aus
  dem Build-Skript.
