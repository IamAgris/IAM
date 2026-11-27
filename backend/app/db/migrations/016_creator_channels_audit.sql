-- OD-42: audit channel values for non-email Creator communication paths.

ALTER TABLE communication_audit DROP CONSTRAINT IF EXISTS ck_communication_channel;
ALTER TABLE communication_audit
    ADD CONSTRAINT ck_communication_channel
    CHECK (channel IN (
        'creator_email', 'creator_cli', 'creator_webhook',
        'creator_node', 'creator_file', 'operational_email', 'private_user'
    ));
