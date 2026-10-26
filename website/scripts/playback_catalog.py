"""Keep playback data small; complete provenance stays in the original manifest."""
import json


def playback_catalog(manifest, recording_root, objectives):
    recordings = []
    for source in manifest["recordings"]:
        record = {key: source[key] for key in (
            "file", "sha256", "client", "scenario", "columns", "rows", "duration",
            "displayStart", "chapters", "still", "stillSha256", "completedStill",
            "completedStillAt", "completedStillSha256",
        ) if key in source}
        pixels = source["pixels"]
        record["pixels"] = {key: pixels[key] for key in (
            "index", "indexSha256", "width", "height", "fps",
        )}
        if source["client"] == "hermes":
            index = json.loads((recording_root / pixels["index"]).read_text(encoding="utf-8"))
            intro = index.get("reviewFrames", {}).get("nativeIntro")
            if intro:
                record["entrance"] = {
                    **intro,
                    "file": (recording_root / pixels["index"]).parent.joinpath(intro["file"]).relative_to(recording_root).as_posix(),
                }
        recordings.append(record)
    return {
        **{key: manifest[key] for key in (
            "schemaVersion", "playbackSpeed", "realTools", "scriptedToolResults",
        )},
        "assetDirectory": recording_root.name,
        "clients": {key: {"version": value["version"]} for key, value in manifest["clients"].items()},
        "cases": {key: {"title": value["title"], "objective": value.get("objective", objectives[key]["objective"])} for key, value in manifest["cases"].items()},
        "recordings": recordings,
    }
