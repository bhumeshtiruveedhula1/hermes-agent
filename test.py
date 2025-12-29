from core.audit.audit_replay import AuditReplay

replay = AuditReplay()

events = replay.last(5)
replay.pretty_print(events)

failed = replay.filter(decision="failed")
replay.pretty_print(failed)
