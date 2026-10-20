"""Observe capture-clock drift without changing the native terminal stream."""
import json
from pathlib import Path
import time


def drift(epoch, monotonic, anchor):
    return (epoch-anchor["epoch"])-(monotonic-anchor["monotonic"])


def discontinuity(previous,current):
    return abs((current[0]-previous[0])-(current[1]-previous[1]))


def main():
    out=Path('/out');anchor=None;maximum=0;jump=0;samples=0;previous=None;sample_gap=0
    while not (out/'terminal-exit.json').exists():
        if anchor is None and (out/'clock.json').exists():
            try:anchor=json.loads((out/'clock.json').read_text())
            except json.JSONDecodeError:pass
        if anchor is not None:
            before=time.monotonic();epoch=time.time();after=time.monotonic()
            # A scheduler interruption between paired reads adds uncertainty.
            measured=max(0,abs(drift(epoch,(before+after)/2,anchor))-(after-before)/2)
            maximum=max(maximum,measured);samples+=1
            current=(epoch,(before+after)/2,(after-before)/2)
            if previous is not None:
                jump=max(jump,max(0,discontinuity(previous,current)-previous[2]-current[2]))
                sample_gap=max(sample_gap,current[1]-previous[1])
            previous=current
        time.sleep(.1)
    # Original graphical PTS use UTC. Smooth OS clock slewing is retained in
    # those timestamps, rather than rewritten to PTY monotonic time. Reject
    # discontinuities that could displace native motion by a capture frame;
    # disclose cumulative drift separately for tool/milestone synchronization.
    result={"valid":anchor is not None and samples>1 and jump<=1/60,
            "maximumClockDriftSeconds":maximum,"maximumClockJumpSeconds":jump,
            "maximumSampleGapSeconds":sample_gap,"samples":samples,"toleranceSeconds":1/60,
            "method":"Independent paired UTC/monotonic samples; original graphical UTC PTS preserved; discontinuity limit is one capture frame"}
    (out/'clock-validation.json').write_text(json.dumps(result)+"\n")


if __name__=='__main__':main()
