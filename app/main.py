from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os, json, hashlib, datetime as dt, csv, io
from sqlmodel import select
from .db import engine, get_session, init_db
from .security import require_token
from .models import (
    UploadPayload, JobRoleRow, ProcessStepRow,
    ProcessFlowRow, ProcessFlowStepRow,
    skills_to_json, deps_to_json
)

app = FastAPI(title="Content API", version="1.0.0")

allowed = os.getenv("API_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    init_db()

def etag_for(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def upsert(payload: UploadPayload, session):
    # insert job roles
    if payload.job_roles:
        for jr in payload.job_roles:
            row = session.get(JobRoleRow, jr.id)
            if not row:
                row = JobRoleRow(
                    id=jr.id, title=jr.title, description=jr.description,
                    department=jr.department, skills_json=skills_to_json(jr.skills),
                    level=jr.level, updated_at=jr.updated_at
                )
                session.add(row)
            else:
                row.title = jr.title
                row.description = jr.description
                row.department = jr.department
                row.skills_json = skills_to_json(jr.skills)
                row.level = jr.level
                row.updated_at = jr.updated_at
    # insert process flows
    if payload.process_flows:
        for pf in payload.process_flows:
            flow = session.get(ProcessFlowRow, pf.id)
            if not flow:
                flow = ProcessFlowRow(
                    id=pf.id, name=pf.name, owner=pf.owner, updated_at=pf.updated_at
                )
                session.add(flow)
            else:
                flow.name = pf.name
                flow.owner = pf.owner
                flow.updated_at = pf.updated_at
            for st in pf.steps:
                s = session.get(ProcessStepRow, st.id)
                if not s:
                    s = ProcessStepRow(id=st.id, name=st.name, description=st.description)
                    session.add(s)
                else:
                    s.name = st.name
                    s.description = st.description
                m = session.get(ProcessFlowStepRow, (pf.id, st.id))
                if not m:
                    m = ProcessFlowStepRow(
                        flow_id=pf.id, step_id=st.id, depends_on_json=deps_to_json(st.depends_on)
                    )
                    session.add(m)
                else:
                    m.depends_on_json = deps_to_json(st.depends_on)
    session.commit()

# ---- CSV Upload ----
@app.post("/api/upload-csv")
async def upload_csv(
    kind: str,
    file: UploadFile = File(...),
    session=Depends(get_session),
    _auth=Depends(require_token),
):
    content = (await file.read()).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    if kind == "job_roles":
        data = []
        for r in rows:
            data.append({
                "id": r["id"].strip(),
                "title": r["title"].strip(),
                "description": (r.get("description") or "").strip(),
                "department": (r.get("department") or "").strip() or None,
                "skills": [s.strip() for s in (r.get("skills") or "").split("|") if s.strip()],
                "level": (r.get("level") or "").strip() or None,
                "updated_at": (r.get("updated_at") or "").strip() or None
            })
        payload = UploadPayload(job_roles=data)

    elif kind == "process_flows":
        from collections import defaultdict
        flows, steps_by_flow = {}, defaultdict(dict)
        for r in rows:
            fid = r["flow_id"].strip()
            flows[fid] = {
                "id": fid,
                "name": r["flow_name"].strip(),
                "owner": (r.get("owner") or "").strip() or None,
                "updated_at": (r.get("flow_updated_at") or "").strip() or None,
            }
            sid = r["step_id"].strip()
            deps = [s.strip() for s in (r.get("depends_on") or "").split("|") if s.strip()]
            steps_by_flow[fid][sid] = {
                "id": sid,
                "name": r["step_name"].strip(),
                "description": (r.get("step_description") or "").strip() or None,
                "depends_on": deps,
            }
        data = []
        for fid, meta in flows.items():
            data.append({**meta, "steps": list(steps_by_flow[fid].values())})
        payload = UploadPayload(process_flows=data)

    else:
        raise HTTPException(400, "kind must be 'job_roles' or 'process_flows'")

    upsert(payload, session)
    return {"status": "ok", "kind": kind, "rows": len(rows)}

# ---- Read endpoints ----
@app.get("/api/job-roles")
def get_job_roles(session=Depends(get_session)):
    rows: List[JobRoleRow] = session.exec(select(JobRoleRow)).all()
    return {"data": [{
        "id": r.id, "title": r.title, "description": r.description,
        "department": r.department, "skills": json.loads(r.skills_json),
        "level": r.level, "updated_at": r.updated_at
    } for r in rows], "generated_at": dt.datetime.utcnow().isoformat()}

@app.get("/api/process-flows")
def get_process_flows(session=Depends(get_session)):
    flows = session.exec(select(ProcessFlowRow)).all()
    maps = session.exec(select(ProcessFlowStepRow)).all()
    steps = {s.id: s for s in session.exec(select(ProcessStepRow)).all()}
    flow_steps = {}
    for m in maps:
        s = steps[m.step_id]
        flow_steps.setdefault(m.flow_id, []).append({
            "id": s.id, "name": s.name, "description": s.description,
            "depends_on": json.loads(m.depends_on_json)
        })
    return {"data": [{
        "id": f.id, "name": f.name, "owner": f.owner,
        "updated_at": f.updated_at, "steps": flow_steps.get(f.id, [])
    } for f in flows]}
