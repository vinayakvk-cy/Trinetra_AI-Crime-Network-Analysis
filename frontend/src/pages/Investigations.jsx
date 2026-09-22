import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle, BriefcaseBusiness, Check, ChevronRight, Edit3,
  Eye, FileText, Plus, RefreshCw, Search, Shield, Trash2, X
} from "lucide-react";
import {
  createInvestigation, deleteInvestigation, getInvestigation,
  listInvestigations, updateInvestigation
} from "../services/investigationsApi";
import { listCases } from "../services/casesApi";
import { getApiErrorMessage } from "../services/api";
import { setActiveInvestigationId, getActiveInvestigationId, clearActiveInvestigationId } from "../services/activeInvestigation";

const REFRESH_MS = 10000;
const EMPTY_FORM = {
  caseId: "", investigationNumber: "", title: "", objective: "",
  investigator: "", investigationUnit: "", status: "in_progress", outcome: "undetermined"
};

function unwrapList(data) {
  if (Array.isArray(data)) return data;
  return data?.investigations || data?.items || data?.results || data?.data || [];
}

function unwrapItem(data) {
  return data?.investigation || data?.data || data;
}

function normalize(item = {}) {
  return {
    ...item,
    id: item.id ?? item.investigation_id,
    caseId: item.case_id ?? item.case?.id,
    caseNumber: item.case_number ?? item.case?.case_number ?? item.case_value ?? "—",
    investigationNumber: item.investigation_number ?? item.number ?? `INV-${item.id ?? "—"}`,
    title: item.title ?? "Untitled investigation",
    objective: item.objective ?? item.description ?? "",
    investigator: item.investigator ?? "",
    investigationUnit: item.investigation_unit ?? "",
    status: item.status ?? "unknown",
    outcome: item.outcome ?? "undetermined",
    createdAt: item.created_at,
    updatedAt: item.updated_at
  };
}

function statusClass(value) {
  const v = String(value || "").toLowerCase();
  if (["active", "open", "in_progress"].includes(v)) return "active";
  if (["closed", "completed", "resolved"].includes(v)) return "closed";
  if (["created", "draft", "pending"].includes(v)) return "pending";
  return "neutral";
}

export default function Investigations() {
  const [items, setItems] = useState([]);
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [mode, setMode] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadCases = useCallback(async () => {
    try {
      const data = await listCases({ skip: 0, limit: 100 });
      const rows = Array.isArray(data) ? data : data?.cases || data?.items || data?.results || data?.data || [];
      setCases(rows.map((item) => ({
        id: Number(item.id ?? item.case_id),
        caseNumber: item.case_number ?? item.caseNumber ?? `CASE-${item.id ?? "—"}`,
        title: item.title ?? "Untitled case",
      })).filter((item) => Number.isInteger(item.id) && item.id > 0));
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to load cases for investigation creation."));
    }
  }, []);

  const load = useCallback(async (manual = false) => {
    manual ? setRefreshing(true) : setLoading(true);
    try {
      const data = await listInvestigations();
      const normalized = unwrapList(data).map(normalize);
      setItems(normalized);
      const activeId = getActiveInvestigationId();
      if (!activeId && normalized[0]?.id) setActiveInvestigationId(normalized[0].id);
      if (activeId && !normalized.some((item) => item.id === activeId)) {
        if (normalized[0]?.id) setActiveInvestigationId(normalized[0].id);
        else clearActiveInvestigationId();
      }
      setError("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to load investigations."));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    loadCases();
    const timer = window.setInterval(() => load(), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [load, loadCases]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(x =>
      [x.investigationNumber, x.title, x.caseNumber, x.investigator, x.investigationUnit, x.status]
        .join(" ").toLowerCase().includes(q)
    );
  }, [items, query]);

  const openCreate = () => {
    setSelected(null); setForm(EMPTY_FORM); setMode("create");
    setError(""); setNotice("");
    loadCases();
  };

  const openEdit = (item) => {
    setSelected(item);
    setForm({
      caseId: item.caseId ?? "",
      investigationNumber: item.investigationNumber ?? "",
      title: item.title ?? "",
      objective: item.objective ?? "",
      investigator: item.investigator ?? "",
      investigationUnit: item.investigationUnit ?? "",
      status: String(item.status || "created"),
      outcome: String(item.outcome || "undetermined")
    });
    setMode("edit"); setError(""); setNotice("");
  };

  const openDetails = async (item) => {
    try {
      const data = await getInvestigation(item.id);
      setSelected(normalize(unwrapItem(data)));
      setMode("details"); setError("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to retrieve investigation."));
    }
  };

  const closePanel = () => {
    setMode(null); setSelected(null); setForm(EMPTY_FORM);
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true); setError(""); setNotice("");
    try {
      const caseId = Number(form.caseId);
      if (!Number.isInteger(caseId) || caseId < 1) {
        throw new Error("Select a valid case before creating the investigation.");
      }
      if (!form.investigationNumber.trim() || !form.title.trim()) {
        throw new Error("Investigation number and title are required.");
      }
      if (!cases.some((item) => item.id === caseId)) {
        throw new Error("The selected case no longer exists. Refresh the case list and try again.");
      }
      const saved = mode === "create"
        ? await createInvestigation(form)
        : await updateInvestigation(selected.id, form);
      const savedItem = normalize(unwrapItem(saved));
      if (savedItem.id) setActiveInvestigationId(savedItem.id);
      closePanel();
      setNotice(mode === "create" ? "Investigation created successfully." : "Investigation updated successfully.");
      await load(true);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to save investigation."));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (item) => {
    if (!window.confirm(`Delete investigation ${item.investigationNumber}?`)) return;
    try {
      await deleteInvestigation(item.id);
      if (getActiveInvestigationId() === item.id) {
        const replacement = items.find((candidate) => candidate.id !== item.id);
        if (replacement?.id) setActiveInvestigationId(replacement.id);
        else clearActiveInvestigationId();
      }
      if (selected?.id === item.id) closePanel();
      setNotice("Investigation deleted.");
      await load(true);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to delete investigation."));
    }
  };

  const active = items.filter(x => ["active","open","in_progress"].includes(String(x.status).toLowerCase())).length;
  const closed = items.filter(x => ["closed","completed","resolved"].includes(String(x.status).toLowerCase())).length;

  return (
    <div className="tn-investigations-page">
      <div className="tn-workspace-header">
        <div>
          <div className="tn-breadcrumb"><span>TRINETRA</span><ChevronRight size={13}/><span>INVESTIGATIONS</span></div>
          <h1 className="tn-display tn-page-title">Investigation Registry</h1>
          <p className="tn-page-subtitle">Create, monitor, inspect, update, and retire investigations through the live TRINETRA API.</p>
        </div>
        <div className="tn-investigations-actions">
          <button type="button" className="tn-investigations-refresh" onClick={() => load(true)} disabled={refreshing}>
            <RefreshCw size={15} className={refreshing ? "tn-spin" : ""}/> Refresh
          </button>
          <button type="button" className="tn-investigations-primary" onClick={openCreate}>
            <Plus size={16}/> New Investigation
          </button>
        </div>
      </div>

      <AnimatePresence>
        {notice && <motion.div className="tn-investigations-notice" initial={{opacity:0,y:-8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-8}}><Check size={15}/>{notice}</motion.div>}
        {error && <motion.div className="tn-investigations-error" initial={{opacity:0,y:-8}} animate={{opacity:1,y:0}}><AlertTriangle size={15}/>{error}</motion.div>}
      </AnimatePresence>

      <div className="tn-investigations-stats">
        <Stat icon={FileText} label="Total investigations" value={items.length}/>
        <Stat icon={Shield} label="Active" value={active}/>
        <Stat icon={Check} label="Closed / resolved" value={closed}/>
        <Stat icon={BriefcaseBusiness} label="Visible records" value={filtered.length}/>
      </div>

      <section className="tn-glass tn-investigations-panel">
        <div className="tn-investigations-toolbar">
          <div><span className="tn-panel-kicker">LIVE REGISTER</span><h2 className="tn-display tn-panel-title">Investigations</h2></div>
          <label className="tn-investigation-search"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search investigations..."/></label>
        </div>

        {loading ? <div className="tn-investigations-empty"><RefreshCw size={22} className="tn-spin"/><span>Synchronizing investigation registry...</span></div> :
        filtered.length === 0 ? <div className="tn-investigations-empty"><FileText size={24}/><span>No investigations match the current filter.</span><button type="button" onClick={openCreate}><Plus size={15}/> Create investigation</button></div> :
        <div className="tn-investigation-table-wrap">
          <table className="tn-investigation-table">
            <thead><tr><th>Investigation</th><th>Case</th><th>Title</th><th>Status</th><th>Outcome</th><th>Investigator</th><th/></tr></thead>
            <tbody>{filtered.map((item,index)=>
              <motion.tr key={item.id ?? index} initial={{opacity:0,y:5}} animate={{opacity:1,y:0}} transition={{delay:index*.025}}>
                <td><strong className="tn-mono">{item.investigationNumber}</strong></td>
                <td><span className="tn-investigation-case">{item.caseNumber}</span></td>
                <td><div className="tn-investigation-title-cell"><strong>{item.title}</strong>{item.objective && <span>{item.objective}</span>}</div></td>
                <td><span className={`tn-investigation-status ${statusClass(item.status)}`}>{String(item.status).replaceAll("_"," ").toUpperCase()}</span></td>
                <td><span className="tn-investigation-priority">{String(item.outcome || "undetermined").replaceAll("_", " ").toUpperCase()}</span></td>
                <td>{item.investigator || "—"}</td>
                <td><div className="tn-investigation-row-actions">
                  <button type="button" title="Use investigation" onClick={()=>{setActiveInvestigationId(item.id); setNotice(`${item.investigationNumber} is now active.`);}}><Check size={15}/></button>
                  <button type="button" title="View" onClick={()=>openDetails(item)}><Eye size={15}/></button>
                  <button type="button" title="Edit" onClick={()=>openEdit(item)}><Edit3 size={15}/></button>
                  <button type="button" className="danger" title="Delete" onClick={()=>remove(item)}><Trash2 size={15}/></button>
                </div></td>
              </motion.tr>
            )}</tbody>
          </table>
        </div>}
      </section>

      <AnimatePresence>{mode && <motion.div className="tn-investigation-drawer-backdrop" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} onMouseDown={e=>{if(e.target===e.currentTarget)closePanel();}}>
        <motion.aside className="tn-glass tn-investigation-drawer" initial={{x:35,opacity:0}} animate={{x:0,opacity:1}} exit={{x:35,opacity:0}}>
          <div className="tn-investigation-drawer-header">
            <div><span className="tn-panel-kicker">{mode==="create"?"NEW INVESTIGATION":mode==="edit"?"EDIT INVESTIGATION":"INVESTIGATION DETAIL"}</span><h2 className="tn-display">{mode==="create"?"Create Investigation":selected?.investigationNumber || "Investigation"}</h2></div>
            <button type="button" onClick={closePanel}><X size={18}/></button>
          </div>

          {mode==="details" ? <div className="tn-investigation-details">
            <Detail label="Case" value={selected?.caseNumber}/>
            <Detail label="Investigation number" value={selected?.investigationNumber}/>
            <Detail label="Title" value={selected?.title}/>
            <Detail label="Objective" value={selected?.objective || "—"} large/>
            <Detail label="Status" value={String(selected?.status||"unknown").replaceAll("_"," ").toUpperCase()}/>
            <Detail label="Outcome" value={String(selected?.outcome||"undetermined").replaceAll("_"," ").toUpperCase()}/>
            <Detail label="Investigator" value={selected?.investigator || "—"}/>
            <Detail label="Investigation unit" value={selected?.investigationUnit || "—"}/>
            <div className="tn-investigation-detail-actions">
              <button type="button" onClick={()=>openEdit(selected)}><Edit3 size={15}/> Edit investigation</button>
              <button type="button" className="danger" onClick={()=>remove(selected)}><Trash2 size={15}/> Delete</button>
            </div>
          </div> :
          <form className="tn-investigation-form" onSubmit={submit}>
            <label><span>Case <em>*</em></span><select value={form.caseId} onChange={e=>setForm({...form,caseId:e.target.value})} required><option value="">Select a case...</option>{cases.map((item)=><option key={item.id} value={item.id}>{item.caseNumber} — {item.title}</option>)}</select></label>
            <Field label="Investigation number" value={form.investigationNumber} onChange={v=>setForm({...form,investigationNumber:v})} placeholder="e.g. INV-TRI-002" required/>
            <Field label="Title" value={form.title} onChange={v=>setForm({...form,title:v})} placeholder="Investigation title" required/>
            <label><span>Objective</span><textarea value={form.objective} onChange={e=>setForm({...form,objective:e.target.value})} rows={4} placeholder="What is this investigation intended to establish?"/></label>
            <div className="tn-investigation-form-grid">
              <Field label="Investigator" value={form.investigator} onChange={v=>setForm({...form,investigator:v})} placeholder="Analyst / team"/>
              <Field label="Investigation unit" value={form.investigationUnit} onChange={v=>setForm({...form,investigationUnit:v})} placeholder="Intelligence Analysis"/>
            </div>
            <div className="tn-investigation-form-grid">
              <label><span>Status</span><select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}><option value="created">Created</option><option value="planning">Planning</option><option value="in_progress">In progress</option><option value="evidence_review">Evidence review</option><option value="suspect_verification">Suspect verification</option><option value="cross_case_analysis">Cross-case analysis</option><option value="pending_review">Pending review</option><option value="completed">Completed</option><option value="suspended">Suspended</option><option value="closed">Closed</option></select></label>
              <label><span>Outcome</span><select value={form.outcome} onChange={e=>setForm({...form,outcome:e.target.value})}><option value="undetermined">Undetermined</option><option value="lead_supported">Lead supported</option><option value="lead_not_supported">Lead not supported</option><option value="inconclusive">Inconclusive</option><option value="case_solved">Case solved</option><option value="referred">Referred</option></select></label>
            </div>
            <div className="tn-investigation-form-actions"><button type="button" onClick={closePanel}>Cancel</button><button type="submit" disabled={saving}>{saving?<RefreshCw size={15} className="tn-spin"/>:<Check size={15}/>} {mode==="create"?"Create investigation":"Save changes"}</button></div>
          </form>}
        </motion.aside>
      </motion.div>}</AnimatePresence>
    </div>
  );
}

function Stat({icon:Icon,label,value}) {
  return <div className="tn-glass tn-investigation-stat"><Icon size={17}/><div><span>{label}</span><strong>{value}</strong></div></div>;
}
function Field({label,value,onChange,placeholder,required=false}) {
  return <label><span>{label}{required&&<em> *</em>}</span><input value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} required={required}/></label>;
}
function Detail({label,value,large=false}) {
  return <div className={`tn-investigation-detail ${large?"large":""}`}><span>{label}</span><strong>{value||"—"}</strong></div>;
}
