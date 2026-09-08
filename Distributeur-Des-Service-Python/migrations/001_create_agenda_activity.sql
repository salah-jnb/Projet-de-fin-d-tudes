-- ============================================================
-- MIGRATION : Création des tables agenda et activity
-- À exécuter dans Supabase SQL Editor
-- ============================================================

-- TABLE AGENDA
CREATE TABLE IF NOT EXISTS agenda (
    id               BIGSERIAL PRIMARY KEY,
    titre            TEXT        NOT NULL,
    note             TEXT        NOT NULL DEFAULT '',
    etat             BOOLEAN     NOT NULL DEFAULT FALSE,
    contenu          TEXT        NOT NULL DEFAULT '',
    date_modification TIMESTAMPTZ DEFAULT NOW()
);

-- Mise à jour automatique de date_modification à chaque UPDATE
CREATE OR REPLACE FUNCTION update_agenda_date_modification()
RETURNS TRIGGER AS $$
BEGIN
    NEW.date_modification = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_agenda_date_modification ON agenda;
CREATE TRIGGER trg_agenda_date_modification
    BEFORE UPDATE ON agenda
    FOR EACH ROW
    EXECUTE FUNCTION update_agenda_date_modification();


-- TABLE ACTIVITY
CREATE TABLE IF NOT EXISTS activity (
    id          BIGSERIAL PRIMARY KEY,
    titre       TEXT        NOT NULL,
    description TEXT        NOT NULL DEFAULT '',
    etat        BOOLEAN     NOT NULL DEFAULT FALSE,
    date        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- VÉRIFICATION : lister les tables créées
-- ============================================================
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('agenda', 'activity');
