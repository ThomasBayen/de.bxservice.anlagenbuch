-- =============================================================
-- install_de_reports.sql — Deutsche JRXML-Variante aktivieren
-- =============================================================
--
-- WANN AUSFÜHREN: NUR in unseren eigenen Installationen mit
-- direktem DB-Zugriff, d.h.
--   * Bayen-Dev-DB (lokales psql, Mandant Bayen)
--   * Testinstallation (~/iDempiere-development/testinstallation/)
--
-- NICHT in der Produktiv-Installation (`freibier.bayen.loc`)
-- ausführen! Dort wird die Sprach-Umstellung manuell im UI gemacht
-- (System-Mandant → Anwendung → Bericht & Prozess → Feld
-- `JasperReport` editieren, Suffix `_de` vor `.jrxml` einfügen).
-- Dieser Workflow ist bewusst getrennt, weil im Produktiv-System
-- kein direkter SQL-Zugriff erwünscht ist und die Änderung an
-- jedem AD_Process-Record manuell und nachvollziehbar im
-- Audit-Trail erscheinen soll.
--
-- Ein-Prozess-pro-Report-Konvention:
--   Im 2Pack steht je Report genau ein sprachneutraler AD_Process
--   (z.B. `BXS_Print_WorkshopDossier`) mit `JasperReport` auf der
--   englischen Default-Datei (`WorkshopDossier.jrxml`). Dieses
--   Skript hängt idempotent das Suffix `_de` vor `.jrxml`, sodass
--   stattdessen `WorkshopDossier_de.jrxml` geladen wird.
--
-- IDEMPOTENT: das Skript prüft per `NOT LIKE '%_de.jrxml'`, ob die
-- Umstellung schon geschehen ist, und macht in dem Fall nichts.
-- Daher unbedenklich mehrfach ausführbar.
-- =============================================================

BEGIN;

-- 1. JasperReport-Pfad auf _de-Variante umstellen.
UPDATE AD_Process
   SET JasperReport = REPLACE(JasperReport, '.jrxml', '_de.jrxml'),
       Updated      = now(),
       UpdatedBy    = 100
 WHERE Value IN (
         'BXS_Print_WorkshopDossier',
         'BXS_Print_AssetDossier',
         'BXS_Print_AssetStatusOverview')
   AND JasperReport NOT LIKE '%\_de.jrxml' ESCAPE '\'
   AND JasperReport LIKE '%.jrxml';

-- 2. Cleanup: alte sprach-suffixierte AD_Process-Records aus früheren
-- 2Pack-Ständen (vor der Ein-Prozess-pro-Report-Konsolidierung)
-- deaktivieren. Diese Records bleiben nach dem 2Pack-Reimport „verwaist"
-- in der DB stehen, weil 2pack keine Löschungen durchführt — wir
-- setzen sie auf IsActive='N', damit sie nicht mehr in Menüs/Toolbar
-- auftauchen.
UPDATE AD_Process
   SET IsActive  = 'N',
       Updated   = now(),
       UpdatedBy = 100
 WHERE Value IN (
         'BXS_Print_Werkstattmappe_DE',
         'BXS_Print_Werkstattmappe_EN',
         'BXS_Print_Anlagenakte_DE',
         'BXS_Print_Anlagenakte_EN',
         'BXS_Print_Anlagenuebersicht_Status_DE',
         'BXS_Print_Anlagenuebersicht_Status_EN')
   AND IsActive = 'Y';

-- 3. Cleanup: zugehörige verwaiste AD_PrintFormat-Anker deaktivieren.
UPDATE AD_PrintFormat
   SET IsActive  = 'N',
       Updated   = now(),
       UpdatedBy = 100
 WHERE Name IN (
         'BXS Werkstattmappe DE',
         'BXS Werkstattmappe EN',
         'BXS Anlagenakte DE',
         'BXS Anlagenakte EN')
   AND IsActive = 'Y';

-- 4. Cleanup: zugehörige verwaiste AD_Menu-Einträge deaktivieren.
UPDATE AD_Menu m
   SET IsActive  = 'N',
       Updated   = now(),
       UpdatedBy = 100
  FROM AD_Process p
 WHERE m.AD_Process_ID = p.AD_Process_ID
   AND p.Value IN (
         'BXS_Print_Werkstattmappe_DE',
         'BXS_Print_Werkstattmappe_EN',
         'BXS_Print_Anlagenakte_DE',
         'BXS_Print_Anlagenakte_EN',
         'BXS_Print_Anlagenuebersicht_Status_DE',
         'BXS_Print_Anlagenuebersicht_Status_EN')
   AND m.IsActive = 'Y';

-- Kontroll-Ausgabe: was steht jetzt im JasperReport-Feld?
SELECT Value, JasperReport, IsActive
  FROM AD_Process
 WHERE Value LIKE 'BXS_Print_%'
 ORDER BY Value;

COMMIT;
