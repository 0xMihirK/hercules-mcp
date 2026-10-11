import unittest
from .clock_guard import drift,discontinuity


class CaptureClockTests(unittest.TestCase):
    def test_stable_paired_clocks_preserve_long_native_delays(self):
        anchor={"epoch":1791600000.,"monotonic":32000.}
        for seconds in (0,.016667,12,360):
            self.assertAlmostEqual(drift(anchor["epoch"]+seconds,anchor["monotonic"]+seconds,anchor),0,places=6)

    def test_forward_and_backward_wall_clock_jumps_are_detected(self):
        anchor={"epoch":1791600000.,"monotonic":32000.}
        for jump in (-1440,1440):
            self.assertEqual(drift(anchor["epoch"]+120+jump,anchor["monotonic"]+120,anchor),jump)
            self.assertGreater(discontinuity((0,0),(120+jump,120)),1/60)

    def test_clock_slew_is_distinct_from_a_presentation_discontinuity(self):
        self.assertLess(discontinuity((0,0),(.09998,.1)),1/60)
        self.assertGreater(discontinuity((0,0),(.14,.1)),1/60)


if __name__=="__main__":unittest.main()
