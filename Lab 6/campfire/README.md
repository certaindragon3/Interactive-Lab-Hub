# Digital Campfire

Run this on the Raspberry Pi with the APDS‑9960 connected for the Story station.

```bash
git clone --filter=blob:none --sparse --branch Fall2026 https://github.com/certaindragon3/Interactive-Lab-Hub.git campfire-hub
cd campfire-hub
git sparse-checkout set 'Lab 6/campfire'
cd 'Lab 6/campfire'
bash run-story.sh
```

If you already have this fork checked out on `Fall2026`, run `git pull --ff-only` from the repository root and use the same script.

Enter the course MQTT broker password when prompted. Leave the terminal running during the demo. When the shared screen says the fire is steady, move your hand away from the sensor, then move it closer to reveal a line. Press Ctrl+C to stop the station.

[Full build instructions and station roles](../README.md#part-c-make-your-own)
