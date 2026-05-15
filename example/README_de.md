# Anlagenbuch — Beispiel-Deployments

Zwei vollständig getrennte Beispiel-Deployments. Beide spielen ihren
Datenbestand über `tools/import-ods.py` ein (kein psql-Seed).

## [`GardenWorld/`](GardenWorld/) — Community-Demo

GardenWorld-thematischer Demobestand (Rasenmäher, Bewässerungspumpe,
Pickup, Anhänger, Gartenhäuschen, Kettensäge) für den GardenWorld-
Mandanten der iDempiere-Standardinstallation. Login: `GardenAdmin`,
Mandant 11. Daten sind frei erfunden.

**Zweck:** Plugin schnell ausprobieren, ohne echte Daten anzulegen.

## [`JakobBayenKG/`](JakobBayenKG/) — Bayen-Init-Daten

Echte Anfangsdaten der Jakob Bayen KG (Fahrzeuge mit Kennzeichen,
Anlagenklassen, Wartungstermin-Typen). Plus operative Demo-Fehlerberichte
aus dem Steppert-Briefing 8.5.2026. Login: Datalotte (Skript-User),
Mandant 1000000.

**Zweck:** produktive Bayen-Installation und Vorlage für andere
Customer-Deployments.

## Welches Beispiel ist für mich?

| Ich will… | Beispiel |
|---|---|
| das Plugin lokal testen, mit Beispiel-Daten | GardenWorld |
| ein Customer-Deployment aufbauen | JakobBayenKG als Vorlage |
| die Jakob Bayen KG produktiv warten | JakobBayenKG |
