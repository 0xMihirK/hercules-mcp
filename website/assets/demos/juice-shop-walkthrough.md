# Local Juice Shop training-lab review

## Scope
- Target: `http://172.30.78.10:3000/`
- Scope: private disposable Juice Shop fixture only
- Runtime: Hercules-owned Kali container, session `4b7f0886`

## Verified observations
1. TCP port 3000 accepted connections from the owned runtime.
2. The homepage responded and was inspected in the CloakBrowser session `juice-shop-review`.
3. A normal local test login remained on the login form.
4. The fixture confirmed the **Login Admin** training challenge after the authorized local authentication exercise.
5. The fixture confirmed the **Score Board** training challenge. The live board showed **2/186 challenges solved**.

## Evidence
- `browser/juice-shop-review/juice-shop-scoreboard.png` - challenge confirmation and scoreboard capture.
- `artifacts/juice-shop-session.mp4` - native browser recording.
- Hercules call journal - startup, scan, HTTP inspection, browser actions, and this report write.

## Recommendation
Treat the observations as training-lab evidence only. Reproduce remediation and regression checks against the owned fixture before applying lessons to any separately authorized environment.
