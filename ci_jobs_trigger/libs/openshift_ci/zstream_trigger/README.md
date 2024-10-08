# zstream_trigger

A process which runs every 24 hours and checks for new Openshift z-stream.

If a new z-stream version is available, relevant jobs will be triggered.
Only periodic jobs can be re-triggered (openShift-ci API limitation).
Processed versions will be stored in `processed_versions_file_path`

## Supported platforms
- openshift ci

### Configuration
- Create a yaml file [example](../../../../config-examples/zstream-trigger-config.example.yaml) and update the relevant fields.
- Export `OPENSHIFT_CI_ZSTREAM_TRIGGER_CONFIG` environment variable which points to the configuration yaml file
- Z-stream supports triggering jobs for both OCP and ROSA versions. See [config file](../../../../config-examples/zstream-trigger-config.example.yaml) for examples on how to provide these versions.


```bash
export OPENSHIFT_CI_ZSTREAM_TRIGGER_CONFIG="<path to yaml file>"
```
