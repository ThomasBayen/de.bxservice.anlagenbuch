# Master-Rolle „anlagenbuch"

Spielt die Anlagenbuch-Master-Rolle in eine iDempiere-Installation ein.
Konvention: Master-Rollen lowercase, halten Rechte; Login-Rollen
inkludieren sie per `AD_Role_Included`.

## Konzept

- **`anlagenbuch.csv`** — definiert die Master-Rolle und ihre Window-/
  Process-Access-Einträge. **Mandantenneutral**, mit dem Plugin
  ausgeliefert.
- **Includes-CSV (eigene Datei pro Deployment)** — listet die
  Login-Rollen, in die die Master-Rolle per `AD_Role_Included`
  eingehängt wird. **Mandantenspezifisch** und eine **bewusste
  Admin-Entscheidung** — keine vorgegebene Liste. Als Vorlage liegt
  `example/JakobBayenKG/masterrolle_includes.csv.example` bei; pro
  Deployment selbst kopieren und mit den eigenen Login-Rollen füllen.
- **`apply.py`** — REST-getriebenes Idempotent-Skript, lädt
  `anlagenbuch.csv` plus die per `--includes`-Flag angegebene
  Includes-CSV und legt Rolle + Accesses + Includes an.

## Was die Master-Rolle trägt

- **Window-Access** (R/W) auf die vier BXS-Hauptfenster:
  `BXS Asset`, `BXS Asset Class`, `BXS Schedule Type`, `BXS Work Order`.
- **Process-Access** auf die vier Workflow-Knöpfe:
  `BXS_Asset_CreateWorkOrder`, `BXS_AssetItem_CloseItem`,
  `BXS_WorkOrder_CompleteOrder`, `BXS_WorkOrder_PullOpenItems`.
- **Process-Access** auf die drei Print-Prozesse:
  `BXS_Print_WorkshopDossier`, `BXS_Print_AssetDossier`,
  `BXS_Print_AssetStatusOverview`.
- **Process-Access** auf zwei allgemeine iDempiere-Tools:
  `ImportCSVProcess`, `Cache Reset`.

Die Master-Rolle ist **kein Direkt-Login** (`IsMasterRole='Y'`) — sie
wird in eine existierende Login-Rolle per Include eingehängt.

## Anwendung

```bash
cd Anlagenbuch/import/masterrolle
cp ../../example/JakobBayenKG/masterrolle_includes.csv.example meine_includes.csv  # anpassen!
./apply.py --includes meine_includes.csv
./apply.py --no-includes    # nur die Master-Rolle, keine Login-Includes
```

Idempotent: Wiederholung markiert vorhandene Einträge mit `[skip]`.

Für ein eigenes Deployment: eine CSV mit Spalte `LoginRoleName` anlegen
(eine Zeile pro Login-Rolle, in die die Master-Rolle eingehängt werden
soll), und mit `--includes <pfad>` übergeben.

## Erweiterung

Neue Windows oder Processes für die Master-Rolle? Zeile in
`anlagenbuch.csv` ergänzen und `./apply.py` erneut laufen lassen — die
neuen Einträge werden hinzugefügt, die alten bleiben unverändert.
