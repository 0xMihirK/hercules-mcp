import unittest
import hashlib
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import numpy as np
from PIL import Image
from .pixels import pack,rectangles,interface_visible,changed_indices,selection_expression,validate_capture_times


class NativePixelsTests(unittest.TestCase):
    def test_empty_preroll_preserves_the_original_native_clock(self):
        times=[-6.706424,0,120,240.646348,240.890575]
        validate_capture_times(times,240.646348)
        self.assertEqual(times[0],-6.706424)

    def test_missing_native_interval_or_invalid_timestamps_are_rejected(self):
        for times in ([],[.04,241],[-10,239],[-1791724398,-1791724157],[-1,1,.5,241],[-1,float("nan"),241]):
            with self.subTest(times=times),self.assertRaises(ValueError):validate_capture_times(times,240)

    def test_cursor_is_not_a_native_entrance(self):
        background=np.array([16,23,31],dtype=np.uint8)
        frame=np.full((672,1320,3),background,dtype=np.uint8)
        frame[:24,:11]=[215,220,228]
        self.assertFalse(interface_visible(frame,background))
        frame[40:64,24:360]=[217,119,87]
        self.assertTrue(interface_visible(frame,background))

    def test_scattered_edits_and_partial_edge_tiles_preserve_every_pixel(self):
        height,width=67,131
        changes=np.zeros((height,width),dtype=bool)
        changes[0,0]=changes[66,130]=changes[34,65]=True
        patches=rectangles(changes)
        coverage=np.zeros_like(changes,dtype=int)
        for left,top,right,bottom in patches:
            self.assertTrue(0<=left<right<=width and 0<=top<bottom<=height)
            coverage[top:bottom,left:right]+=1
        self.assertTrue(np.all(coverage[changes]==1))
        self.assertLess(coverage.sum(),height*width//2)
        self.assertLessEqual(coverage.max(),1)

    def test_full_frame_and_unchanged_frame(self):
        self.assertEqual(rectangles(np.zeros((67,131),dtype=bool)),[])
        self.assertEqual(rectangles(np.ones((67,131),dtype=bool)),[(0,0,131,67)])

    def test_client_background_is_not_a_native_interface(self):
        frame=np.full((672,528,3),10,dtype=np.uint8)
        self.assertFalse(interface_visible(frame,np.array([0,0,0])))
        frame[40:64,24:360]=[225,225,225]
        self.assertTrue(interface_visible(frame,np.array([0,0,0])))

    def test_only_adjacent_byte_identical_frames_are_deduplicated(self):
        self.assertEqual(changed_indices(["a","a","b","b","a","c"]),[0,2,4,5])

    def test_long_decode_selection_has_bounded_parser_depth(self):
        indices=list(range(0,30000,3));expression=selection_expression(indices)
        depth=maximum=0
        for char in expression:
            if char=="(":depth+=1;maximum=max(maximum,depth)
            if char==")":depth-=1
        self.assertEqual(depth,0);self.assertLess(maximum,18)
        self.assertEqual(expression.count("eq(n,"),len(indices))

    def test_same_timestamp_uses_last_native_frame_and_reuses_exact_pixels(self):
        frames=[]
        for color in [(180,180,180),(215,119,87),(70,160,220),(215,119,87)]:
            frame=np.zeros((64,64,3),dtype=np.uint8);frame[8:48,8:48]=color;frames.append(frame)
        class Decoder:
            def __init__(self):self.stdout=io.BytesIO(b"".join(f.tobytes() for f in frames))
            def terminate(self):pass
            def wait(self):return 0
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);master=root/"fixture.mkv";master.write_bytes(b"encoder regression fixture")
            cast=root/"fixture.cast"
            cast.write_text(json.dumps({"duration":3,"chapters":{"nativeIntro":0,"investigation":1}})+"\n")
            cast.with_suffix(".json").write_text("{}")
            (root/"clock.json").write_text(json.dumps({"epoch":100}))
            probe=json.dumps({"frames":[{"best_effort_timestamp_time":str(t)} for t in [100,102,102,103]]}).encode()
            with patch("website.capture.pixels.subprocess.check_output",return_value=probe),patch("website.capture.pixels.subprocess.Popen",return_value=Decoder()):
                pack(master,cast,{"pixelWidth":64,"pixelHeight":64,"terminal":{"background":"#000000"}})
            destination=root/"fixture-pixels";index=json.loads((destination/"index.json").read_text())
            self.assertEqual(index["verification"]["capturedFrames"],4)
            self.assertGreater(index["verification"]["reusedIdenticalPatches"],0)
            self.assertEqual(index["reviewFrames"]["investigation"]["at"],2)
            for name in ["review-investigation.png","opening.png","completed.png"]:
                with Image.open(destination/name) as native:
                    self.assertEqual(native.tobytes(),frames[2].tobytes())
            latest=[f for f in index["frames"] if f["at"]==2][-1]
            self.assertEqual(latest["sha256"],hashlib.sha256(frames[2].tobytes()).hexdigest())


if __name__=="__main__":unittest.main()
