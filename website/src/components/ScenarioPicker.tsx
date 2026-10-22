import type { NativeManifest } from "../native-types";

export default function ScenarioPicker({cases,activeScenario,onSelect}:{cases:NativeManifest["cases"];activeScenario:string;onSelect:(id:string)=>void}){
  const entries=Object.entries(cases);
  return <aside className="scenario-picker" aria-labelledby="scenario-heading">
    <div className="scenario-header">
      <h2 id="scenario-heading">Scenarios</h2>
      <span>{entries.length} cases</span>
    </div>
    <p className="scenario-description">Choose an investigation for the selected agent.</p>
    {entries.length>0 ? <div className="scenario-options" role="group" aria-label="Investigation scenario">
      {entries.map(([id,item])=><button key={id} type="button" aria-pressed={activeScenario===id} onClick={()=>onSelect(id)}>{item.title}</button>)}
    </div> : <p role="status" className="scenario-description">Scenarios will appear when recordings are ready.</p>}
  </aside>;
}
