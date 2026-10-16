import { useEffect, useRef, useState } from "react";
export default function SessionTranscript({url}:{url?:string}){
  const [text,setText]=useState(""),[error,setError]=useState(false),request=useRef<AbortController|null>(null);
  useEffect(()=>()=>request.current?.abort(),[]);
  return <details className="session-transcript" onToggle={event=>{
    if(!event.currentTarget.open || text || request.current || !url)return;
    const abort=new AbortController();request.current=abort;setError(false);
    fetch(url,{signal:abort.signal}).then(response=>{if(!response.ok)throw Error("Transcript unavailable");return response.text();}).then(value=>{if(!abort.signal.aborted)setText(value);}).catch(()=>{if(!abort.signal.aborted){setError(true);request.current=null;}});
  }}><summary>Read the complete session transcript</summary><div>{text?<pre tabIndex={0}>{text}</pre>:<p role="status">{error?"The transcript could not load. Close and reopen this section to retry.":"Loading the recorded transcript…"}</p>}</div></details>;
}
