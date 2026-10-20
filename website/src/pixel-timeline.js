/** Actual presentation timestamps: select the last captured frame at time. */
export const PLAYBACK_RATE=2.5;

export function frameAt(frames, time) {
  let lo=0, hi=frames.length;
  while(lo<hi){const mid=(lo+hi)>>>1;if(frames[mid].at<=time)lo=mid+1;else hi=mid;}
  return Math.max(0,lo-1);
}

/** Finish the report hold before native process teardown clears its screen. */
export function sessionEnd(duration, report, hold=6){
  return Number.isFinite(report)?Math.min(duration,report+hold):duration;
}

/** A wall-clock timeline. Pauses do not accrue time; slow paints do. */
export class PlaybackClock {
  constructor(time=0,rate=1){
    if(!Number.isFinite(rate) || rate<=0)throw new RangeError("Playback rate must be positive and finite");
    this.time=time;this.rate=rate;this.last=null;
  }
  tick(now, paused, duration){
    if(!paused && this.last!==null)this.time=Math.min(duration,this.time+(now-this.last)*this.rate/1000);
    this.last=paused?null:now;
    return this.time;
  }
  suspend(){this.last=null;}
}
