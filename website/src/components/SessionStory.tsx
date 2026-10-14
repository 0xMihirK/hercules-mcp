import { ArrowUpRight, Check, FileText, FolderOpen } from "@phosphor-icons/react";
import content from "../showcase-content.json";
import type { NativeRecording } from "../native-types";
type Beat={afterCall:number;action:string;finding:string;artifact?:string};
type Story={objective:string;summary:string;beats:Beat[]};
export const stories=content as Record<string,Story>;
export default function SessionStory({recording,time,base,title}:{recording:NativeRecording|null;time:number;base:string;title:string}){
  const story=stories[recording?.scenario || ""];
  const completed=recording?.synchronized.filter(call=>call.at<=time).length || 0;
  const beats=story?.beats.filter(beat=>completed>=beat.afterCall) || [];
  const reportReady=Boolean(recording && time>=(recording.reportAvailableAt ?? recording.chapters.report ?? recording.duration));
  const action=reportReady?"Report verified":beats.at(-1)?.action || (completed?"Starting the investigation":"Preparing the local workspace");
  const visible=recording?.artifacts.filter(a=>time>=(a.availableAt ?? recording.duration)) || [];
  const beatArtifact=[...beats].reverse().find(b=>b.artifact && visible.some(a=>a.path===b.artifact));
  const artifact=visible.find(a=>a.path===beatArtifact?.artifact);
  const picture=visible.find(a=>/browser\/.*\.png$/.test(a.path));
  return <aside className="session-story" aria-label="Investigation summary">
    <div className="story-objective"><span className="story-label">The investigation</span><h3>{title || "Local lab investigation"}</h3><p>{story?.objective || "Real tools in a disposable local lab. Follow the verified observations as the recording plays."}</p></div>
    <div className="story-action"><span className={reportReady?"action-mark complete":"action-mark"}>{reportReady?<Check size={17}/>:<span/>}</span><strong>{action}</strong></div>
    <ol className="story-observations">{beats.slice(-2).map(beat=><li key={beat.afterCall}><Check size={17} aria-hidden="true"/><p>{beat.finding}</p></li>)}</ol>
    {!beats.length && <div className="story-pending"><FolderOpen size={40} aria-hidden="true"/><p>The session starts its own workspace before checking the local lab.</p></div>}
    {picture && <a className="story-evidence" href={base+picture.file} target="_blank" rel="noreferrer"><img src={base+picture.file} alt={recording?.scenario==="browser"?"Verified local dashboard":recording?.scenario==="tls"?"Captured local login page":"Captured local debug page"} loading="lazy"/><span>View browser evidence <ArrowUpRight size={17}/></span></a>}
    {!picture && artifact && <div className="story-artifact"><FileText size={24} aria-hidden="true"/><span>{recording?.scenario==="forensics"?"Challenge clues checked":recording?.scenario==="reporting"?"Source material reconciled":"Supporting observations verified"}</span></div>}
    {reportReady && <div className="story-report"><h4>A report you can follow.</h4><p>{story?.summary}</p><a className="text-link" href={base+recording!.reportHtml} target="_blank" rel="noreferrer">View report <ArrowUpRight size={18}/></a></div>}
    <p className="story-provenance">Local lab. Real tools.<br/>Scripted model decisions.</p>
  </aside>;
}
