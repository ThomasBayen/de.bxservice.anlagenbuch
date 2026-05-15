# GardenWorld-Demo: Stammdaten-CSVs

Quelle der Wahrheit für den GardenWorld-Demo-Datenbestand. Wenn sich eine
Klasse, eine Anlage oder ein Wartungstermin-Typ ändert, hier pflegen und
dann `python3 build_ods.py` (im übergeordneten Verzeichnis) ausführen.

Das gebaute `anlagenbuch_demo.ods` ist Wegwerf-Output, wird aber
mitcommittet, damit Nutzer nicht erst bauen müssen.

## Dateien

### `classes.csv` — Anlagenklassen (GardenWorld-Universum)

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `Value` | ja | Stabiler Schlüssel (`GW-MOWER`, `GW-IRRIG`, …) |
| `Name` | ja | Deutscher Anzeigename |
| `NameEN` | – | Englischer Anzeigename (Trl-Eintrag) |
| `Kategorie` | ja | Eine von `Vehicle`/`Equipment`/`Stationary`/`Building`/`IT`/`Other` |
| `Description` | – | Lange Beschreibung |

### `assets.csv` — konkrete Anlagen

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `Value` | ja | Eindeutiger Such-Schlüssel |
| `Name` | ja | Anzeigename |
| `KlassenValue` | ja | Verweis auf `classes.csv > Value` |
| `Hersteller`/`Modell`/`Baujahr`/`SerialNo` | – | Optional, soweit bekannt |
| `Standort` | – | Frei-Text |
| `AssetStatus` | – | `InService` (Default), `OutOfService`, … |
| `Anmerkung` | – | Description in iDempiere |

### `schedules.csv` — Wartungstermin-Typen

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `Value` | ja | Kurzkennung |
| `Name` | ja | Deutscher Anzeigename |
| `NameEN` | – | Englischer Anzeigename |
| `KlassenValue` | – | Bindung an eine Klasse (leer = alle) |
| `IntervallMonate` | ja | Default-Intervall (0 = keiner) |
| `PflichtDefault` | ja | `Y`/`N` |
| `Description` | – | Erklärungstext |

`BXS_ScheduleType` hat eine 1:1-FK auf `BXS_AssetClass` — für Termine,
die für mehrere Klassen relevant sind, lassen wir `KlassenValue` leer
und filtern später im UI.

### `items.csv` — Demo-Einträge (Defects, Schedules, Status)

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `AssetValue` | ja | Verweis auf `assets.csv > Value` |
| `Type` | ja | `Defect`/`Schedule`/`Status` |
| `Name` | ja | Kurztitel des Eintrags |
| `Description` | – | Detail-Text |
| `Priority` | – | `High`/`Medium`/`Low` (nur Defect sinnvoll) |
| `ItemStatus` | ja | `Open`/`Done` |
| `ReportedDate` | ja | Erfassungsdatum (YYYY-MM-DD) |
| `DueDate` | – | Fälligkeit (nur Schedule) |
| `CompletionDate` | – | Erledigt-am (für Done) |
| `ScheduleTypeValue` | – | Verweis auf `schedules.csv > Value` (nur Schedule) |
| `MeterReading` | – | Zählerstand bei Status |
| `Reporter` | – | AD_User-Name (Default: GardenAdmin) |
