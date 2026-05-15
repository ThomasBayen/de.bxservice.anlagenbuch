# Asset-Import — Spalten-Mapping

`AssetImport_Template.csv` ist die Kunden-Erstbefüllungsvorlage für `BXS_Asset`. Wird über das parallele Tool `idempiere-ods-import` (REST + `ImportCSVProcess`) eingespielt.

## Spalten

| CSV-Spalte | Ziel | Pflicht | Bemerkung |
|---|---|---|---|
| `Value` | `BXS_Asset.Value` | ja | Suchschlüssel, eindeutig |
| `Name` | `BXS_Asset.Name` | ja | Anzeigename, bei Fahrzeugen empfohlen mit Kennzeichen vorne (z.B. „KR-JB 2078 Mercedes Atego") |
| `BXS_AssetClass.Value` | FK auf `BXS_AssetClass` | ja | `100` (Fahrzeug/KfZ), `200` (Stapler/andere Fahrzeuge), `300` (Technische Anlage), `400` (IT), `500` (Immobilie) |
| `Manufacturer` | `BXS_Asset.Manufacturer` | – | Hersteller |
| `Model` | `BXS_Asset.Model` | – | Modellbezeichnung |
| `SerialNo` | `BXS_Asset.SerialNo` | – | bei Fahrzeugen die FIN |
| `YearBuilt` | `BXS_Asset.YearBuilt` | – | 4-stellig |
| `CommissionDate` | `BXS_Asset.CommissionDate` | – | Format `YYYY-MM-DD` |
| `Location` | `BXS_Asset.Location` | – | Standort, frei |
| `M_Resource.Value` | FK auf `M_Resource` | – | Verknüpft mit der dispositionsrelevanten Ressource (sofern in iDempiere als Resource geführt) |
| `AD_User.Name` | FK auf `AD_User` | – | Stammnutzer (z.B. fester Fahrer) |

`AssetStatus` wird automatisch auf `InService` gesetzt (Default-Wert).

## Wie importieren

Werkzeug: `iDempiere-development/rest/idempiere-ods-import/import-ods.py` (umbenannt von `csv-import-ods`). Nutzt iDempiere-REST + `ImportCSVProcess`.

Schritte beim Kunden:

1. Quell-Daten aus den vorhandenen `M_Resource`-Datensätzen bzw. Excel-Listen in das CSV-Format überführen.
2. Mit `import-ods.py --profile <kunde> Asset_Import.ods --dry-run` Vorschau prüfen.
3. Dann ohne `--dry-run` einspielen.

Reihenfolge bei mehreren Datasheets:
1. (Falls erforderlich) `BXS_AssetClass`-Ergänzungen (für eigene Klassen, die über das ausgelieferte Set hinausgehen)
2. `BXS_Asset` (diese CSV)
3. (optional) `BXS_AssetItem`-Initialdatensätze für Statusberichte ("Erstaufnahme")

## Beispieldaten

Ein Demo-Bestand mit Anlagen, Fehlerberichten, Wartungsterminen und Werkstattaufträgen liegt im Beispielverzeichnis `example/JakobBayenKG/` — siehe das dortige `README.md` und `build.sh`.
