-- Anlagenbuch — UOM-UUID-Migration für ältere Installationen
--
-- Bis einschließlich v1.0 hatte die ausgelieferte „Kilometer"-UOM in
-- `uuids.csv` einen Lookup-Schlüssel, der an der iDempiere-internen
-- C_UOM_ID hing (`Initial,C_UOM.5000000,…` bzw. `Initial,C_UOM.1000000,…`).
-- Bei einem Rebuild der 2Pack-Quellen wurde dieser Schlüssel auf das
-- natürliche `X12DE355=KME` umgestellt — damit erhielt die Zeile eine
-- frische UUID. Bei einem zweiten install.sh-Lauf gegen eine vorher schon
-- bespielte Datenbank findet PIPO die alte Zeile nicht mehr per UUID und
-- versucht, sie neu einzufügen → `duplicate key (c_uom_id)=…`.
--
-- Diese Migration richtet die UUID der bestehenden Zeile genau auf die
-- Ziel-UUID aus der aktuellen `uuids.csv` aus. Sie ist idempotent — nach
-- dem ersten erfolgreichen Lauf greift das WHERE nicht mehr.
--
-- Wird von install.sh **vor** dem 2Pack-Drop in `migration/zip_2pack/`
-- ausgeführt. Frische Installationen ohne C_UOM-KME-Zeile sind nicht
-- betroffen — UPDATE schreibt dann 0 Zeilen.

UPDATE C_UOM
   SET C_UOM_UU = 'ad55c7f9-aa9a-418e-a4dc-f88e183e8f18'
 WHERE X12DE355 = 'KME'
   AND AD_Client_ID = 0
   AND C_UOM_UU IS DISTINCT FROM 'ad55c7f9-aa9a-418e-a4dc-f88e183e8f18';
