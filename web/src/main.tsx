import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

interface Session {id:string;course:string;title:string;code:string;active:number;recording:number;interval:number;created:number}
interface Student {id:string;name:string;student_id:string;status:string;frame_at:number;capture_at:number;mode:string}
interface Sample {id:string;student:string;captured:number;name:string;student_id:string}
interface Drive {configured:boolean;connected:boolean;pending:number;last_error:string|null;retention_days:number}
const clock=(timestamp:number)=>timestamp?new Date(timestamp*1000).toLocaleTimeString():'No frame yet';
async function api<T>(path:string,method='GET',body?:unknown):Promise<T> {
  const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});
  if(!response.ok){const text=await response.json().catch(()=>({detail:'Request failed'}));throw Error(typeof text.detail==='string'?text.detail:'Check the submitted values');}
  return response.json();
}

function App(){
  const [authenticated,setAuthenticated]=useState(false),[checking,setChecking]=useState(true),[password,setPassword]=useState('');
  const [sessions,setSessions]=useState<Session[]>([]),[selected,setSelected]=useState(''),[students,setStudents]=useState<Student[]>([]);
  const [frames,setFrames]=useState<Record<string,string>>({}),[focus,setFocus]=useState<string|null>(null),[search,setSearch]=useState('');
  const [error,setError]=useState(''),[connection,setConnection]=useState('Offline'),[interval,setIntervalValue]=useState(20),[drive,setDrive]=useState<Drive>();
  const [samples,setSamples]=useState<Sample[]|null>(null),[playStudent,setPlayStudent]=useState(''),[playIndex,setPlayIndex]=useState(0),[playing,setPlaying]=useState(false);
  const socket=useRef<WebSocket|null>(null),currentFocus=useRef<string|null>(null);
  const current=sessions.find(session=>session.id===selected);
  useEffect(()=>{api('/me').then(()=>setAuthenticated(true)).catch(()=>{}).finally(()=>setChecking(false));},[]);
  async function refresh(){const list=await api<Session[]>('/sessions');setSessions(list);setSelected(id=>id&&list.some(s=>s.id===id)?id:list[0]?.id||'');setDrive(await api<Drive>('/drive'));}
  useEffect(()=>{if(authenticated)void refresh().catch(err=>setError(err.message));},[authenticated]);
  useEffect(()=>{if(current)setIntervalValue(current.interval);},[selected]);
  useEffect(()=>{
    if(!authenticated||!selected)return;
    let cancelled=false,retry:ReturnType<typeof setTimeout>,heartbeat:ReturnType<typeof setInterval>,ws:WebSocket;
    setFrames({});setStudents([]);setFocus(null);currentFocus.current=null;setSamples(null);
    async function connect(){
      try{
        const {token}=await api<{token:string}>('/ws-ticket','POST');if(cancelled)return;
        ws=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/api/ws/teacher/${selected}`);socket.current=ws;
        ws.onopen=()=>{ws.send(JSON.stringify({token}));ws.send(JSON.stringify({type:'focus',student:currentFocus.current}));setConnection('Connected');};
        ws.onmessage=event=>{
          const body=JSON.parse(event.data);
          if(body.type==='frame')setFrames(old=>({...old,[body.student]:'data:image/webp;base64,'+body.data}));
          if(body.type==='roster'){
            setStudents(body.students);
            setSessions(old=>old.map(session=>session.id===selected?{...session,active:Number(body.active),recording:Number(body.recording),interval:body.interval}:session));
            // Clear stopped/disconnected images so old screens cannot look live.
            setFrames(old=>{const next={...old};for(const student of body.students)if(student.status==='disconnected')delete next[student.id];return next;});
          }
          if(body.type==='error')setError(body.message);
        };
        ws.onclose=event=>{if(cancelled)return;setConnection('Reconnecting');setStudents(old=>old.map(student=>({...student,status:'disconnected'})));setFrames({});if(event.code===4401){setAuthenticated(false);return;}retry=setTimeout(()=>void connect(),2000);};
        ws.onerror=()=>ws.close();
      }catch(err){if(!cancelled){setError((err as Error).message);retry=setTimeout(()=>void connect(),3000);}}
    }
    void connect();
    heartbeat=setInterval(()=>{if(ws?.readyState===WebSocket.OPEN)ws.send(JSON.stringify({type:'heartbeat'}));},5000);
    return()=>{cancelled=true;clearTimeout(retry);clearInterval(heartbeat);ws?.close();socket.current=null;};
  },[authenticated,selected]);
  useEffect(()=>{currentFocus.current=focus;if(socket.current?.readyState===WebSocket.OPEN)socket.current.send(JSON.stringify({type:'focus',student:focus}));},[focus]);
  useEffect(()=>{const handler=(event:KeyboardEvent)=>{if(event.key==='Escape')setFocus(null);};window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);},[]);
  const playback=(samples||[]).filter(sample=>sample.student===playStudent);
  useEffect(()=>{if(!playing)return;const timer=setInterval(()=>setPlayIndex(index=>{if(index>=playback.length-1){setPlaying(false);return index;}return index+1;}),1000);return()=>clearInterval(timer);},[playing,playback.length]);
  async function run(action:()=>Promise<unknown>){setError('');try{await action();}catch(err){setError((err as Error).message);}}
  async function create(event:React.FormEvent<HTMLFormElement>){event.preventDefault();const data=new FormData(event.currentTarget);await run(async()=>{const session=await api<Session>('/sessions','POST',{course:data.get('course'),title:data.get('title'),recording:false,interval:20});await refresh();setSelected(session.id);});}
  async function configure(recording:boolean){if(current)await run(async()=>{await api(`/sessions/${current.id}/recording`,'PATCH',{recording,interval});await refresh();});}
  async function openPlayback(){if(current)await run(async()=>{const rows=await api<Sample[]>(`/sessions/${current.id}/samples`);setSamples(rows);setPlayStudent(rows[0]?.student||'');setPlayIndex(0);setPlaying(false);setFocus(null);});}
  if(checking)return <main className="login">Opening classroom…</main>;
  if(!authenticated)return <main className="login"><div className="logo">▦</div><div className="eyebrow">CLASSROOM / TEACHER ACCESS</div><h1>A window into<br/>your classroom.</h1><p>See progress, offer help, and keep your class moving.</p><form onSubmit={event=>{event.preventDefault();void run(async()=>{await api('/login','POST',{password});setPassword('');setAuthenticated(true);});}}><label>Teacher password<input type="password" required value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"/></label><button>Open dashboard →</button></form>{error&&<p role="alert" className="error">{error}</p>}<small>Students join using the Classroom Screen Sharing extension.</small></main>;
  const visible=students.filter(student=>(student.name+' '+student.student_id).toLowerCase().includes(search.toLowerCase()));
  const focused=students.find(student=>student.id===focus);
  return <div className="app"><aside><div className="brand"><span className="logo">▦</span> Classroom<span className="brand-dot">●</span></div><div className="eyebrow">WORKSPACE</div><div className="nav active">▦ &nbsp; Screen overview</div><button className="nav" onClick={()=>void openPlayback()}>◷ &nbsp; Session recordings</button><div className="sidebar-bottom"><span className="avatar">T</span><div>Teacher workspace<small>Private classroom access</small></div><button className="icon-button" aria-label="Sign out" onClick={()=>void run(async()=>{await api('/logout','POST');setAuthenticated(false);})}>↪</button></div></aside>
  <div className="workspace"><header><span>Workspace <span className="muted">/</span> Screen overview</span><span className={`connection ${connection==='Connected'?'good':''}`}>● {connection}</span></header>
  <main><div className="title-row"><div className="page-title"><div className="eyebrow">TEACHER DASHBOARD</div><h1>Your classroom, live<span>.</span></h1><p>A little visibility. More room to help.</p></div><div className="session-select"><label>Classroom session<select value={selected} onChange={e=>setSelected(e.target.value)}><option value="" disabled>Select a session</option>{sessions.map(session=><option key={session.id} value={session.id}>{session.course} · {session.title}{session.active?' · Live':''}</option>)}</select></label></div></div>
  {error&&<div className="error" role="alert">{error}<button className="icon-button" onClick={()=>setError('')}>×</button></div>}
  {!sessions.some(session=>session.active)?<form className="new-session" onSubmit={event=>void create(event)}><div><strong>Start a classroom</strong><small>Students will use its joining code in their extension.</small></div><input name="course" placeholder="Course name" required maxLength={100} aria-label="Course name"/><input name="title" placeholder="Session title" required maxLength={100} aria-label="Session title"/><button>Start session +</button></form>:null}
  {current&&<><section className="session-bar"><div><span className={current.active?'pill live':'pill'}>● {current.active?'SESSION LIVE':'SESSION ENDED'}</span><strong>{current.course} <span className="muted">/ {current.title}</span></strong></div><div className="join-code"><span>JOIN CODE</span><b>{current.active?current.code:'Closed'}</b></div>{!!current.active&&<button className="outline danger" onClick={()=>{if(window.confirm('End this classroom? All student captures will stop.'))void run(async()=>{await api(`/sessions/${current.id}/end`,'POST');setFocus(null);await refresh();});}}>End session</button>}</section>
  <section className="stats"><div><span>In the classroom</span><strong>{students.length.toString().padStart(2,'0')} <small>students</small></strong></div><div><span>Sharing now</span><strong className="green">{students.filter(s=>s.status==='sharing').length.toString().padStart(2,'0')} <small>live screens</small></strong></div><div><span>Need a check-in</span><strong>{students.filter(s=>s.status!=='sharing').length.toString().padStart(2,'0')} <small>frozen / offline</small></strong></div><div><span>Screenshot recording</span><strong className="record-state">{current.recording?'On':'Off'} <small>{current.recording?`every ${current.interval}s`:'live viewing only'}</small></strong></div></section>
  <section className="record-controls"><div><b>◉ &nbsp; Periodic screenshots</b><small>Only changed screens are saved. Live viewing is independent.</small></div><label>Interval <input aria-label="Recording interval in seconds" type="number" min="5" max="3600" value={interval} onChange={e=>setIntervalValue(Number(e.target.value))}/> s</label><button className="outline" disabled={!current.active} onClick={()=>void configure(Boolean(current.recording))}>Apply interval</button><button disabled={!current.active} className="outline" onClick={()=>void configure(!current.recording)}>{current.recording?'Pause recording':'Enable recording'}</button><button className="text-button" onClick={()=>void openPlayback()}>Playback ↗</button></section>
  <div className="grid-toolbar"><div><h2>Student screens <span>{visible.length}</span></h2><p>Click a screen for a closer look. Unchanged screens send a health heartbeat.</p></div><input className="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search name or student ID…" aria-label="Search students"/></div>
  <section className="screen-grid">{visible.map(student=><button key={student.id} className="student-card" onClick={()=>setFocus(student.id)}><div className="screen">{frames[student.id]?<img src={frames[student.id]} alt={`${student.name}'s shared screen`}/>:<div className="no-frame"><span>▧</span>{student.status==='disconnected'?'Sharing stopped':'Waiting for screen'}</div>}<span className={'screen-status '+student.status}>● {student.status}</span></div><div className="student-info"><span className="initial">{student.name.slice(0,1).toUpperCase()}</span><div><strong>{student.name}</strong><small>{student.student_id}</small></div><span className="frame-time">Last frame<small>{clock(student.frame_at)}</small></span></div></button>)}</section>
  {!students.length&&<div className="empty"><span>▦</span><h2>Ready when your students are.</h2><p>Ask students to open the extension, join with <b>{current.active?current.code:'an active session code'}</b>,<br/>and click Start Sharing. Their real screens appear here.</p></div>}
  </>}
  <footer><span>● Private by design. Students choose what to share.</span><div>Drive: {drive?.connected?'Connected':drive?.configured?'Ready to connect':'Not configured'} {drive?.connected&&`· ${drive.pending} archive batches pending`}{drive?.last_error&&` · Upload retry pending (${drive.last_error})`}{drive?.configured&&!drive.connected&&<a href="/api/drive/connect">Connect Google Drive ↗</a>}<small>{drive?.retention_days||30}-day retention</small></div></footer>
  </main></div>
  {focused&&<div className="modal-backdrop" onClick={()=>setFocus(null)}><section className="focus-modal" role="dialog" aria-modal="true" aria-label="Focused student screen" onClick={event=>event.stopPropagation()}><div className="modal-title"><div><h2>{focused.name} <span>{focused.student_id}</span></h2><p>{focused.status} · {focused.mode==='focused'?'High quality · up to 3 fps':'Overview'} · Last frame {clock(focused.frame_at)}</p></div><button className="outline" onClick={()=>setFocus(null)}>Close ×</button></div>{frames[focused.id]?<img className="focused-screen" src={frames[focused.id]} alt={`${focused.name}'s enlarged shared screen`}/>:<div className="empty">No live frame. The student must start sharing.</div>}</section></div>}
  {samples&&<div className="modal-backdrop"><section className="playback-modal" role="dialog" aria-modal="true" aria-label="Recorded session playback"><div className="modal-title"><div><h2>Session playback</h2><p>Periodic screenshots · original timestamps · unchanged frames skipped</p></div><button className="outline" onClick={()=>{setSamples(null);setPlaying(false);}}>Close ×</button></div>{samples.length?<><div className="playback-controls"><select aria-label="Playback student" value={playStudent} onChange={e=>{setPlayStudent(e.target.value);setPlayIndex(0);setPlaying(false);}}>{[...new Map(samples.map(sample=>[sample.student,sample])).values()].map(sample=><option key={sample.student} value={sample.student}>{sample.name} · {sample.student_id}</option>)}</select><button onClick={()=>{if(playIndex===playback.length-1)setPlayIndex(0);setPlaying(!playing);}}>{playing?'Pause':'Play'}</button><span>{playback[playIndex]?new Date(playback[playIndex].captured*1000).toLocaleString():''}</span></div>{playback[playIndex]&&<img className="focused-screen" src={`/api/samples/${playback[playIndex].id}`} alt="Recorded classroom screenshot"/>}<input className="timeline" aria-label="Recording timeline" type="range" min="0" max={Math.max(0,playback.length-1)} value={playIndex} onChange={e=>{setPlayIndex(Number(e.target.value));setPlaying(false);}}/><small>{playIndex+1} of {playback.length} changed screenshots · preview advances one sample per second</small></>:<div className="empty">No saved screenshots. Enable recording in an active classroom, or check retention settings.</div>}</section></div>}
  </div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
