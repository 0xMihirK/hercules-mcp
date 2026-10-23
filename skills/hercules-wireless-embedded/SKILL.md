---
name: hercules-wireless-embedded
description: Analyze authorized wireless, IoT, firmware, and mobile security evidence with Hercules when captures or owned devices are available; live radio and mobile tooling require separate prerequisites.
---

# Hercules wireless-embedded

Pick one topic and read only its reference. Hercules can inspect imported files and perform scoped network checks; its container does not provide a physical radio, mobile emulator, or device instrumentation by default. Never transmit, pair, commission, or test nearby third-party devices without explicit authorization and supplied hardware. Record the difference between offline analysis and a live validation.

## Select one topic

- [Bluetooth Low Energy services](references/ble-services.md)
- [Bluetooth Classic pairing and profiles](references/bluetooth-classic.md)
- [Wi-Fi management-frame resilience](references/wifi-management-frame-resilience.md)
- [Lookalike access-point detection](references/evil-twin-detection.md)
- [Wi-Fi reassembly and patch posture](references/wifi-reassembly-patches.md)
- [LoRaWAN and sub-GHz device trust](references/lorawan-subghz.md)
- [Wi-Fi asset inventory](references/wifi-asset-recon.md)
- [Wi-Fi configuration baseline](references/wifi-security-baseline.md)
- [Enterprise Wi-Fi identity validation](references/wpa-enterprise.md)
- [WPA2 personal-network hygiene](references/wpa2-psk.md)
- [WPA3 SAE transition policy](references/wpa3-sae.md)
- [WPS enrollment policy](references/wps-enrollment.md)
- [Z-Wave inclusion and command classes](references/z-wave-inclusion.md)
- [Zigbee, Thread, and Matter commissioning](references/zigbee-thread-matter.md)
- [IoT firmware and exposed services](references/iot-firmware.md)
- [Mobile application trust boundaries](references/mobile-app-boundaries.md)

The reference is guidance, not authorization. Check the current MCP schema and installed backend before executing a suggested route. If a prerequisite is absent, report the coverage gap instead of inventing a tool or widening scope.

## Finish

Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
