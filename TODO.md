# TODO

## Auslieferung & Community

- [ ] **Plugin-Listing**: Eintrag im iDempiere-Plugin-Index und Community-Forum.
- [ ] **Spätere Plugin-Variante** (OSGi-Bundle): wann macht sie Sinn?

## niedrige Priorität

- **Bilinguale Werkstattmappe-Demo-PDF / englische Demo-PDFs.** Die
  Reports selbst sind zweisprachig (DE+EN-Quellen); die Demo-Ausgaben
  liefern wir nur in deutsch aus.
- **Screenshots der vier Hauptfenster im README.** Müsste bei jeder
  iDempiere-Theme-Änderung gepflegt werden.

## Bewusst zurückgestellt

Punkte, die wir kennen, aber nicht aktiv verfolgen — entweder weil der
Aufwand den Nutzen nicht rechtfertigt oder weil der Bedarf bisher fehlt.
Stehen hier, damit sie nicht erneut „neu" entdeckt werden.

- **Generator `emit_menu()` auf Nesting-Pattern umstellen** —
  Window/Process/Report als XML-Child unter `<AD_Menu Action="W|P|R">`
  statt flacher Siblings. Funktional gleichwertig zur jetzigen flachen
  Form (verifiziert); Mainstream-Pattern der Diego-Ruiz-Plugins, aber
  ohne Funktionsgewinn.
