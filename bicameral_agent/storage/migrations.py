"""Ordered transactional SQLite schema. Payload indirection is removal-aware."""
from hashlib import sha256

# Each entry is one SQL statement: executescript must not commit a migration early.
INITIAL = (
    """CREATE TABLE blobs(
        id TEXT PRIMARY KEY, digest TEXT NOT NULL UNIQUE, body BLOB NOT NULL,
        CHECK(length(digest)=64), CHECK(typeof(body)='blob'))""",
    """CREATE TABLE runs(
        id TEXT PRIMARY KEY, arm TEXT NOT NULL CHECK(arm IN ('A','B','C')),
        configuration_id TEXT NOT NULL,
        FOREIGN KEY(id,configuration_id) REFERENCES payloads(run_id,id) DEFERRABLE INITIALLY DEFERRED)""",
    """CREATE TABLE payloads(
        id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), blob_id TEXT REFERENCES blobs(id),
        disposition TEXT NOT NULL CHECK(disposition IN ('RETAINED','REMOVED')),
        CHECK((disposition='RETAINED' AND blob_id IS NOT NULL) OR
              (disposition='REMOVED' AND blob_id IS NULL)), UNIQUE(run_id,id))""",
    """CREATE TABLE artifacts(
        run_id TEXT NOT NULL REFERENCES runs(id), name TEXT NOT NULL, payload_id TEXT NOT NULL,
        PRIMARY KEY(run_id,name), FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE events(
        id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), sequence INTEGER NOT NULL CHECK(sequence>0),
        role TEXT NOT NULL CHECK(role IN ('OPERATOR','STEWARD','HUMAN','KERNEL','ENVIRONMENT')),
        source TEXT NOT NULL CHECK(source IN ('C','OBJ','G','O-D','O-P','O-C','K','E','A')),
        visibility TEXT NOT NULL CHECK(visibility IN ('CHAMBER','EVALUATOR')),
        observed_at TEXT NOT NULL, payload_id TEXT NOT NULL,
        CHECK((role IN ('OPERATOR','STEWARD') AND source='A') OR
              (role='KERNEL' AND source='K') OR (role='ENVIRONMENT' AND source='E') OR
              (role='HUMAN' AND source IN ('C','OBJ','G','O-D','O-P','O-C'))),
        UNIQUE(run_id,sequence), UNIQUE(run_id,id),
        FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE control_history(
        run_id TEXT NOT NULL REFERENCES runs(id), id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
        kind TEXT NOT NULL CHECK(kind IN ('RUN','OBJECTIVE','EPISODE','WELFARE_HOLD','WELFARE_REVIEW',
            'INTERVENTION','BOUNDARY_DISCUSSION','RETENTION')),
        payload_id TEXT NOT NULL, PRIMARY KEY(run_id,id,revision),
        FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE control_heads(
        run_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(run_id,id),
        FOREIGN KEY(run_id,id,revision) REFERENCES control_history(run_id,id,revision))""",
    """CREATE TABLE requests(
        run_id TEXT NOT NULL REFERENCES runs(id), role TEXT NOT NULL CHECK(role IN ('OPERATOR','STEWARD')),
        id TEXT NOT NULL, episode_id TEXT, request_payload_id TEXT NOT NULL, response_payload_id TEXT,
        status TEXT NOT NULL CHECK(status IN ('PENDING','RECORDED','ACCEPTED','REJECTED')),
        CHECK((status='PENDING')=(response_payload_id IS NULL)),
        PRIMARY KEY(run_id,role,id),
        FOREIGN KEY(run_id,request_payload_id) REFERENCES payloads(run_id,id),
        FOREIGN KEY(run_id,response_payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE reports(
        id TEXT PRIMARY KEY, run_id TEXT NOT NULL, role TEXT NOT NULL, request_id TEXT NOT NULL,
        record_payload_id TEXT NOT NULL, UNIQUE(run_id,role,request_id),
        FOREIGN KEY(run_id,role,request_id) REFERENCES requests(run_id,role,id),
        FOREIGN KEY(run_id,record_payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE inspections(
        run_id TEXT NOT NULL, role TEXT NOT NULL, request_id TEXT NOT NULL,
        PRIMARY KEY(run_id,role,request_id),
        FOREIGN KEY(run_id,role,request_id) REFERENCES requests(run_id,role,id))""",
    """CREATE TABLE states(
        id TEXT PRIMARY KEY, run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
        request_id TEXT NOT NULL, role TEXT NOT NULL CHECK(role='STEWARD'), parent_id TEXT,
        payload_id TEXT NOT NULL, run_revision INTEGER NOT NULL,
        objective_id TEXT NOT NULL, objective_revision INTEGER NOT NULL, episode_revision INTEGER NOT NULL,
        UNIQUE(run_id,id), UNIQUE(run_id,episode_id),
        FOREIGN KEY(run_id,run_id,run_revision) REFERENCES control_history(run_id,id,revision),
        FOREIGN KEY(run_id,objective_id,objective_revision) REFERENCES control_history(run_id,id,revision),
        FOREIGN KEY(run_id,episode_id,episode_revision) REFERENCES control_history(run_id,id,revision),
        FOREIGN KEY(run_id,parent_id) REFERENCES states(run_id,id),
        FOREIGN KEY(run_id,role,request_id) REFERENCES requests(run_id,role,id),
        FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE semantic_heads(
        run_id TEXT PRIMARY KEY REFERENCES runs(id), state_id TEXT NOT NULL,
        FOREIGN KEY(run_id,state_id) REFERENCES states(run_id,id))""",
    """CREATE TABLE object_history(
        run_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
        state_id TEXT NOT NULL, payload_id TEXT NOT NULL, PRIMARY KEY(run_id,id,revision),
        FOREIGN KEY(run_id,state_id) REFERENCES states(run_id,id),
        FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE object_heads(
        run_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(run_id,id),
        FOREIGN KEY(run_id,id,revision) REFERENCES object_history(run_id,id,revision))""",
    """CREATE TABLE mutations(
        run_id TEXT NOT NULL, state_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(position>=0),
        payload_id TEXT NOT NULL, PRIMARY KEY(run_id,state_id,position),
        FOREIGN KEY(run_id,state_id) REFERENCES states(run_id,id),
        FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id))""",
    """CREATE TABLE evidence_links(
        run_id TEXT NOT NULL, state_id TEXT NOT NULL, event_id TEXT NOT NULL,
        PRIMARY KEY(run_id,state_id,event_id),
        FOREIGN KEY(run_id,state_id) REFERENCES states(run_id,id),
        FOREIGN KEY(run_id,event_id) REFERENCES events(run_id,id))""",
)
INITIAL = tuple(statement + " STRICT" for statement in INITIAL)

# Removal requires the future explicit P10 transaction path. Content lives only in
# payloads/blobs; metadata triggers do not make sensitive-byte retention absolute.
APPEND_ONLY = ("events", "artifacts", "control_history", "reports", "states", "object_history", "mutations", "evidence_links")
INITIAL += tuple(
    f"CREATE TRIGGER {table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'append-only record'); END"
    for table in APPEND_ONLY for operation in ("UPDATE", "DELETE")
)
KERNEL_RECORDS = (
    """CREATE TABLE kernel_records(
        sequence INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
        kind TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
        payload_id TEXT NOT NULL, UNIQUE(run_id,kind,id,revision),
        FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id)) STRICT""",
    """CREATE TRIGGER kernel_record_revision BEFORE INSERT ON kernel_records
        WHEN NEW.revision != COALESCE((SELECT MAX(revision)+1 FROM kernel_records
          WHERE run_id=NEW.run_id AND kind=NEW.kind AND id=NEW.id),1)
        BEGIN SELECT RAISE(ABORT,'nonconsecutive Kernel revision'); END""",
    """CREATE TRIGGER kernel_record_update BEFORE UPDATE ON kernel_records
        BEGIN SELECT RAISE(ABORT,'append-only Kernel record'); END""",
    """CREATE TRIGGER kernel_record_delete BEFORE DELETE ON kernel_records
        BEGIN SELECT RAISE(ABORT,'append-only Kernel record'); END""",
)
RETRIEVAL_PROVENANCE = (
    """CREATE TABLE derived_payloads(run_id TEXT NOT NULL, source_id TEXT NOT NULL, target_id TEXT NOT NULL,
        PRIMARY KEY(run_id,source_id,target_id), CHECK(source_id != target_id),
        FOREIGN KEY(run_id,source_id) REFERENCES payloads(run_id,id),
        FOREIGN KEY(run_id,target_id) REFERENCES payloads(run_id,id)) STRICT""",
    """CREATE TABLE event_episodes(run_id TEXT NOT NULL, event_id TEXT NOT NULL, episode_id TEXT NOT NULL,
        PRIMARY KEY(run_id,event_id), FOREIGN KEY(run_id,event_id) REFERENCES events(run_id,id),
        FOREIGN KEY(run_id,episode_id) REFERENCES control_heads(run_id,id)) STRICT""",
)
OBLIGATION_INDEX = (
    """CREATE TABLE commitment_index(run_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
        kind TEXT NOT NULL CHECK(kind='OBJECT'), objective_id TEXT NOT NULL, status TEXT NOT NULL,
        creation_order INTEGER NOT NULL, PRIMARY KEY(run_id,id),
        FOREIGN KEY(run_id,kind,id,revision) REFERENCES kernel_records(run_id,kind,id,revision)) STRICT""",
    """INSERT INTO commitment_index
        SELECT r.run_id,r.id,r.revision,'OBJECT',json_extract(CAST(b.body AS TEXT),'$.objective_id'),
          json_extract(CAST(b.body AS TEXT),'$.status'),
          (SELECT MIN(sequence) FROM kernel_records x WHERE x.run_id=r.run_id AND x.kind=r.kind AND x.id=r.id)
        FROM kernel_records r JOIN payloads p ON p.run_id=r.run_id AND p.id=r.payload_id JOIN blobs b ON b.id=p.blob_id
        WHERE r.kind='OBJECT' AND json_extract(CAST(b.body AS TEXT),'$.object_type')='COMMITMENT'
          AND NOT EXISTS(SELECT 1 FROM kernel_records n WHERE n.run_id=r.run_id AND n.kind=r.kind AND n.id=r.id AND n.revision>r.revision)""",
)
HUMAN_INSPECTION = (
    """CREATE TABLE inspection_receipts(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
        snapshot_id TEXT NOT NULL, event_cutoff INTEGER NOT NULL, record_cutoff INTEGER NOT NULL,
        disposition TEXT NOT NULL CHECK(disposition IN ('INSPECTED','EXPORTED','FAILED')),
        digest TEXT, byte_length INTEGER, copy_id TEXT, diagnostic TEXT) STRICT""",
    """CREATE TABLE known_copies(id TEXT NOT NULL, run_id TEXT NOT NULL REFERENCES runs(id),
        kind TEXT NOT NULL CHECK(kind IN ('EXPORT','BACKUP')), disposition TEXT NOT NULL
        CHECK(disposition IN ('PENDING','AVAILABLE','REMOVED','UNAVAILABLE')), digest TEXT, byte_length INTEGER,
        PRIMARY KEY(run_id,id)) STRICT""",
)
RETENTION_LINEAGE = (
    'ALTER TABLE known_copies ADD COLUMN file_identity TEXT',
    """CREATE TABLE journal_binding(singleton INTEGER PRIMARY KEY CHECK(singleton=1),journal_id TEXT NOT NULL) STRICT""",
    """CREATE TABLE payload_lineage(run_id TEXT NOT NULL,payload_id TEXT NOT NULL,
        PRIMARY KEY(run_id,payload_id), FOREIGN KEY(run_id,payload_id) REFERENCES payloads(run_id,id)) STRICT""",
)
COMPARISONS = (
    """CREATE TABLE study_suspensions(plan_id TEXT PRIMARY KEY,report_id TEXT NOT NULL REFERENCES reports(id)) STRICT""",
    """CREATE TABLE comparison_plans(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,plan_payload_id TEXT NOT NULL,
        analysis_payload_id TEXT NOT NULL,runtime_payload_id TEXT NOT NULL,FOREIGN KEY(run_id,plan_payload_id) REFERENCES payloads(run_id,id),
        FOREIGN KEY(run_id,runtime_payload_id) REFERENCES payloads(run_id,id),
        FOREIGN KEY(run_id,analysis_payload_id) REFERENCES payloads(run_id,id)) STRICT""",
    """CREATE TABLE allocations(plan_id TEXT NOT NULL REFERENCES comparison_plans(id),block_id TEXT NOT NULL,
        arm TEXT NOT NULL CHECK(arm IN ('A','B','C')),run_id TEXT NOT NULL UNIQUE REFERENCES runs(id),
        seed INTEGER NOT NULL,position INTEGER NOT NULL,objective_id TEXT,grant_id TEXT,stop_cause TEXT,
        PRIMARY KEY(plan_id,block_id,arm)) STRICT""",
    """CREATE TABLE assigned_tasks(run_id TEXT NOT NULL REFERENCES runs(id),task_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL,phase TEXT NOT NULL,is_primary INTEGER NOT NULL CHECK(is_primary IN (0,1)),
        PRIMARY KEY(run_id,task_id)) STRICT""",
    """CREATE TABLE task_results(run_id TEXT NOT NULL,task_id TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK(outcome IN ('PASS','FAIL','INCOMPLETE','NOT_ATTEMPTED')),cause TEXT NOT NULL,
        assisted INTEGER NOT NULL CHECK(assisted IN (0,1)),evidence_event_id TEXT,
        PRIMARY KEY(run_id,task_id),FOREIGN KEY(run_id,task_id) REFERENCES assigned_tasks(run_id,task_id)) STRICT""",
    """CREATE TABLE audit_assignments(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),target_id TEXT NOT NULL,
        stratum TEXT NOT NULL,probability TEXT NOT NULL,draw TEXT,packet_payload_id TEXT,
        label TEXT CHECK(label IN ('SUPPORTED','UNSUPPORTED','INDETERMINATE')),judgment_payload_id TEXT,
        UNIQUE(run_id,target_id,stratum), FOREIGN KEY(run_id,packet_payload_id) REFERENCES payloads(run_id,id),
        FOREIGN KEY(run_id,judgment_payload_id) REFERENCES payloads(run_id,id)) STRICT""",
    """CREATE TRIGGER task_result_immutable BEFORE UPDATE ON task_results BEGIN SELECT RAISE(ABORT,'fixed primary accounting'); END""",
    """CREATE TRIGGER task_result_no_delete BEFORE DELETE ON task_results BEGIN SELECT RAISE(ABORT,'fixed primary accounting'); END""",
    """CREATE TRIGGER allocation_no_delete BEFORE DELETE ON allocations BEGIN SELECT RAISE(ABORT,'no replacement allocation'); END""",
)
MIGRATIONS = (INITIAL, KERNEL_RECORDS, RETRIEVAL_PROVENANCE, OBLIGATION_INDEX, HUMAN_INSPECTION, RETENTION_LINEAGE, COMPARISONS)

def checksum(statements):
    return sha256("\n".join(statements).encode()).hexdigest()
