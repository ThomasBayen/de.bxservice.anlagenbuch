# TODO

Offene Punkte für die Veröffentlichung. Sobald das Repo öffentlich ist,
sollen diese Einträge nach GitHub Issues migrieren.

## Vor dem ersten öffentlichen Release

- [ ] **CI**: GitHub-Action, die `install.sh` gegen einen frisch
  
      hochgezogenen iDempiere-11-Docker schickt und
      `scripts/test/01_2pack_imports.sh` ausführt.

- [ ] **iDempiere 12-Kompatibilität**: Smoke-Test gegen 12 fahren,
  
      Mindest-/Maximalversion dokumentieren.

- [ ] **Sanity-Test reproduzierbar**: Skript, das nach `install.sh` 1:1
  
      die Akzeptanzkriterien durchläuft (Anlage → Fehlerbericht →
      Werkstattauftrag → Anlagenakte drucken).

- [ ] **Author-/Maintainer-Block nach Veröffentlichung finalisieren**:
  
      Sobald das Repo öffentlich liegt, in
      `2pack/source/spec/00-package.yaml` und
      `2pack/source/PackageDoc.xml` die Repo-URL und einen
      License-Verweis (AGPL-3.0-or-later) nachziehen.

## Auslieferung & Community

- [ ] **Plugin-Listing**: Eintrag im iDempiere-Plugin-Index und
  
      Community-Forum.

- [ ] **Spätere Plugin-Variante** (OSGi-Bundle): wann macht sie Sinn,
  
      wer wartet sie?

## Bewusst zurückgestellt

Punkte, die wir kennen, aber nicht aktiv verfolgen — entweder weil der
Aufwand den Nutzen nicht rechtfertigt oder weil der Bedarf bisher fehlt.
Stehen hier, damit sie nicht erneut „neu" entdeckt werden.

- **Bilinguale Werkstattmappe-Demo-PDF / englische Demo-PDFs.** Die
  Reports selbst sind zweisprachig (DE+EN-Quellen); die Demo-Ausgaben
  liefern wir nur in deutsch aus.
- **Screenshots der vier Hauptfenster im README.** Müsste bei jeder
  iDempiere-Theme-Änderung gepflegt werden.
- **Generator `emit_menu()` auf Nesting-Pattern umstellen** —
  Window/Process/Report als XML-Child unter `<AD_Menu Action="W|P|R">`
  statt flacher Siblings. Funktional gleichwertig zur jetzigen flachen
  Form (verifiziert); Mainstream-Pattern der Diego-Ruiz-Plugins, aber
  ohne Funktionsgewinn.
- **CONTRIBUTING.md.** Inhalte (Coding-Konventionen, 2Pack-Workflow,
  BeanShell-Konventionen, `uuids.csv`-Kopplung) stehen bereits in
  `CLAUDE.md` und `README.md`.
- **Release-Doku-PDF-Bundle.** Markdown reicht; GitHub rendert ohnehin.
- **Demo-Docker-Compose.** Zu viel Wartungsaufwand für ein triviales
  Plugin; iDempiere-11-Container existieren bereits in der Community.
- **Postgres-Mindestversion dokumentieren.** Hängt an iDempiere, nicht
  an uns.
