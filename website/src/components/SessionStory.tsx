import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { MagnifyingGlass } from "@phosphor-icons/react/MagnifyingGlass";
import content from "../showcase-content.json";
import type { NativeRecording } from "../native-types";
type Beat={afterCall:number;action:string;finding:string;artifact?:string};
type Story={objective:string;summary:string;beats:Beat[]};
export const stories=content as Record<string,Story>;
export default function SessionStory({recording,time,base}:{recording:NativeRecording|null;time:number;base:string;title:string}){
  const story=stories[recording?.scenario || ""];
  const completed=recording?.synchronized.filter(call=>call.at<=time).length || 0;
  const beats=story?.beats.filter(beat=>completed>=beat.afterCall) || [];
  const reportReady=Boolean(recording && time>=(recording.reportAvailableAt ?? recording.chapters.report ?? recording.duration));
  const action=reportReady?"Investigation complete":beats.at(-1)?.action || "Preparing the workspace";
  const picture=recording?.scenario==="browser"?recording.artifacts.find(a=>time>=(a.availableAt ?? recording.duration) && /browser\/.*\.png$/.test(a.path)):undefined;
  return <aside className="session-story" aria-label="Investigation summary">
    <div className="story-current">{reportReady?<Check size={24}/>:<MagnifyingGlass size={24}/>}<h3>{action}</h3></div>
    {reportReady?<p className="story-conclusion">{story?.summary}</p>:beats.length?<ol className="story-observations">{beats.slice(-2).map(beat=><li key={beat.afterCall}><p>{beat.finding}</p></li>)}</ol>:<p className="story-pending">The agent connects to Hercules and starts its tool container. Findings appear as checks finish.</p>}
    {picture && <a className="story-evidence" href={base+picture.file} target="_blank" rel="noreferrer"><img src={base+picture.file} alt="Verified local dashboard" loading="lazy"/><span>View full browser capture <ArrowUpRight size={17}/></span></a>}
    {reportReady && <a className="text-link story-report-link" href={base+recording!.reportHtml} target="_blank" rel="noreferrer">View report <ArrowUpRight size={18}/></a>}
  </aside>;
}
