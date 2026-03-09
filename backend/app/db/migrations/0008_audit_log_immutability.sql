-- Strengthen audit log queryability + immutability semantics

CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_type_actor_id ON audit_logs(actor_type, actor_id);

DO $$
BEGIN
    IF to_regclass('public.audit_logs') IS NOT NULL THEN
        CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is immutable';
        END;
        $$;

        DROP TRIGGER IF EXISTS trg_prevent_audit_logs_update ON audit_logs;
        DROP TRIGGER IF EXISTS trg_prevent_audit_logs_delete ON audit_logs;

        CREATE TRIGGER trg_prevent_audit_logs_update
            BEFORE UPDATE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_logs_mutation();

        CREATE TRIGGER trg_prevent_audit_logs_delete
            BEFORE DELETE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_logs_mutation();
    END IF;
END;
$$;
