import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { MagnifyingGlass } from "@phosphor-icons/react/MagnifyingGlass";
import content from "../showcase-content.json";
import type { NativeRecording } from "../native-types";
type Beat={afterCall:number;action:string;finding:string;artifact?:string};
type Story={objective:string;summary:string;beats:Beat[]};
export const stories=content as Record<string,Story>;
export default function SessionStory({recording,time,base,title}:{recording:NativeRecording|null;time:number;base:string;title:string}){
  const story=stories[recording?.scenario || ""];
  const totalCalls=recording?.synchronized.length || 0;
  const completed=recording?.synchronized.filter(call=>call.at<=time).length || 0;
  const allBeats=story?.beats || [];
  const beats=allBeats.filter(beat=>completed>=beat.afterCall);
  const reportReady=Boolean(recording && time>=(recording.reportAvailableAt ?? recording.chapters.report ?? recording.duration));
  const action=reportReady?"Investigation complete":beats.at(-1)?.action || "Preparing the workspace";
  const picture=recording?.scenario==="browser"?recording.artifacts.find(a=>time>=(a.availableAt ?? recording.duration) && /browser\/.*\.png$/.test(a.path)):undefined;
  const pct=reportReady?100:totalCalls?Math.min(96,Math.round((completed/totalCalls)*100)):8;
  return <aside className="session-story" aria-label="Investigation summary">
    <div className="story-header">
      <span className="story-case-title">{title || "Local investigation"}</span>
      <span className="story-call-count">{totalCalls?`${completed}/${totalCalls} calls`:"Standby"}</span>
    </div>
    <div className="story-progress-bar" aria-hidden="true"><i style={{width:`${pct}%`}}/></div>
    <div className="story-body">
      <div className="story-current">{reportReady?<Check size={22}/>:<MagnifyingGlass size={22}/>}<h3>{action}</h3></div>
      {!beats.length && !reportReady && <p className="story-pending">The agent connects to Hercules and starts its tool container. Findings appear as checks finish.</p>}
      {allBeats.length>0 && <ol className="story-observations">
        {allBeats.map((beat,idx)=>{
          const done=completed>=beat.afterCall;
          return <li key={beat.afterCall} className={done?"is-done":"is-upcoming"}>
            <div className="story-beat-head">
              <span className="story-beat-badge">{done?<Check size={12} aria-hidden="true"/>:idx+1}</span>
              <strong>{beat.action}</strong>
            </div>
            {done && <p>{beat.finding}</p>}
          </li>;
        })}
      </ol>}
      {picture && <a className="story-evidence" href={base+picture.file} target="_blank" rel="noreferrer">
        <div className="story-evidence-chrome" aria-hidden="true"><span/><span/><span/><b>Browser capture</b></div>
        <div className="story-evidence-preview"><img src={base+picture.file} alt="Verified local dashboard" loading="lazy"/></div>
        <span>View full browser capture <ArrowUpRight size={16}/></span>
      </a>}
      {reportReady && <div className="story-conclusion-card">
        <p className="story-conclusion">{story?.summary}</p>
        <a className="button primary story-report-link" href={base+recording!.reportHtml} target="_blank" rel="noreferrer">View report <ArrowUpRight size={18}/></a>
      </div>}
    </div>
    <div className="story-footer">
      <span>{recording?`${recording.columns}×${recording.rows} terminal`:"Native terminal"}</span>
      <span>Disposable local lab</span>
    </div>
  </aside>;
}
