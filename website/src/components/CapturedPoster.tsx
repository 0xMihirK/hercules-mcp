import { useEffect, useRef, useState } from "react";
import { verifiedFetch } from "../pixel-renderer";

/** Decode the actual capture before mounting an image, including fallback. */
export default function CapturedPoster({base,opening,completed,preferCompleted,label}:{base:string;opening?:{file:string;sha256:string};completed?:{file:string;sha256:string};preferCompleted:boolean;label:string}){
  const [source,setSource]=useState<{url:string;label:string}|null>(null),urls=useRef(new Set<string>());
  useEffect(()=>()=>{for(const url of urls.current)URL.revokeObjectURL(url);urls.current.clear();},[]);
  useEffect(()=>()=>{if(source){URL.revokeObjectURL(source.url);urls.current.delete(source.url);}},[source]);
  useEffect(()=>{
    const abort=new AbortController();let objectUrl="",adopted=false;
    async function load(){
      for(const asset of preferCompleted?[completed,opening]:[opening,completed]){
        if(!asset || abort.signal.aborted)continue;
        try{
          const bytes=await verifiedFetch(new URL(base+asset.file,location.href).href,asset.sha256,abort.signal);
          objectUrl=URL.createObjectURL(new Blob([bytes],{type:"image/png"}));
          urls.current.add(objectUrl);
          const image=new Image();image.src=objectUrl;await image.decode();
          if(abort.signal.aborted){URL.revokeObjectURL(objectUrl);urls.current.delete(objectUrl);return;}
          adopted=true;setSource({url:objectUrl,label});return;
        }catch{
          if(objectUrl){URL.revokeObjectURL(objectUrl);urls.current.delete(objectUrl);objectUrl="";}
        }
      }
    }
    load();
    return()=>{abort.abort();if(objectUrl && !adopted){URL.revokeObjectURL(objectUrl);urls.current.delete(objectUrl);}};
  },[base,opening?.file,opening?.sha256,completed?.file,completed?.sha256,preferCompleted,label]);
  return source?<img className="native-still" src={source.url} alt={source.label}/>:null;
}
