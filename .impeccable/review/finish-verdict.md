## verdict

1. Resolved — first-frame readiness: desktop-viewport.jpg visibly shows the painted native opening interface without a loading overlay; mobile.jpg, user-320.jpg and tablet-768.jpg contain populated native rows. NativePlayer now waits for xterm onRender and two animation frames before swapping, with abortable cancellation. The deferred offscreen still in full-page desktop/current-viewport captures retains real content rather than exposing an empty reconstructed frame.
2. Resolved — reduced-motion Replay: reduced-report.jpg visibly retains the completed native report by default; reduced-replay.jpg shows the same client's opening native logo, early progress and Play control after explicit pause. The post-fix observation records active Replay restarting and paused Replay retaining pause; replayCase resets the clock and allows explicitly requested playback without clearing explicitPause.
3. Resolved — failure recovery: loading-failure.jpg visibly preserves the actual captured native report and says “The native recording could not be displayed. Select Replay to retry, or read the captured transcript.” The transcript link and playback controls remain available; post-fix observations record recovery after requests were restored.
4. Resolved — FORM documentation: direction-contract.md now identifies THESIS, OWN-WORLD, STORY, FIRST VIEWPORT and FORM, and directly records seed 93af4c0e, dealt 5/3/2, with the surface-brief reference.

## remaining

Clear for the four scored fixes. No material regressions introduced by this fix batch are visible in the supplied recaptures. All original and newly required capture paths exist and show their claimed states; full-page captures retain the document top and loaded illustrations. This ship verdict covers the four scored fixes.

Accepted engine limitation, separate from the browser disposition: the React/Canvas adapter remains unsupported and the automated build phases remain open under the user's approved browser-review path. No automated completion is asserted. The provider's hidden-document transition remains untested, and 640px testing is recorded as CSS layout width rather than actual browser zoom.

disposition: ship

