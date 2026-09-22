# rep_asakura: ensemble-initialization and run workflow

This directory contains the input setup for an idealized SCALE-RM ensemble
experiment.  Its generated member directories (`1`–`101`), `letkfinput/`,
NetCDF files, logs, and history/restart outputs are execution products; they
are not source inputs.

## Overall relationship

```text
ensperturb/env.txt
        |
        |  python sounding_perturb.py
        v
ensperturb/env_perturb1.txt ... env_perturb101.txt
        |
        |  ensinit.sh
        |  - copies init.conf_base and init.sh_base into each member directory
        |  - inserts that member's ENV_IN_SOUNDING_file into init.conf
        |  - submits pjsub init.sh
        v
1/ ... 101/
  init.conf + init.sh
        |
        |  scale-rm_init (from ../../case_tc/scale-rm_init)
        v
member initial-condition/restart NetCDF files
        |
        |  preprocess_init.sh
        |  - copies each member to letkfinput/0001 ... letkfinput/0101
        v
letkfinput/0001 ... letkfinput/0101

run.sh + run.conf
        |
        |  scale-rm (from ../case_tc/scale-rm)
        v
history and restart output configured in run.conf
```

## Files by role

| File(s) | Role | Relationship |
| --- | --- | --- |
| `ensperturb/env.txt` | Base sounding profile. | Input read by `sounding_perturb.py`. |
| `ensperturb/sounding_perturb.py` | Creates 101 perturbed sounding profiles. | Adds independent normally distributed noise (mean 0, standard deviation 0.1) to column 3 for the first 13 rows, and writes `env_perturb1.txt`–`env_perturb101.txt`.  This is the file referred to as `sound.py` in the workflow; its actual filename is `sounding_perturb.py`. |
| `ensperturb/env_perturb*.txt` | Generated, per-member sounding inputs. | `ensinit.sh` selects one file for each member. |
| `ensinit.sh` | Ensemble initializer/submitter. | Creates member directories `1`–`101`, derives each `init.conf`, copies `init.sh`, and submits the initialization job. |
| `init.conf_base` | Template for each member's SCALE-RM initialization configuration. | The marker `!--ENV_IN_SOUNDING_file--` is replaced by an `ENV_IN_SOUNDING_file` entry that points to the corresponding perturbed sounding. |
| `init.sh_base` | Template batch script for the initialization job. | Calls `../../case_tc/scale-rm_init ./init.conf`. |
| `1/`–`101/` | Per-member working/output directories. | Contain the derived `init.conf`/`init.sh` plus generated initialization NetCDF files and logs. |
| `preprocess_init.sh` | Stages initialized members for LETKF input. | Copies members `1`–`101` to zero-padded `letkfinput/0001`–`letkfinput/0101`. |
| `init.conf`, `init.sh` | Standalone initialization configuration and job script at the directory root. | Use the unperturbed `ensperturb/env.txt`; unlike the ensemble flow, these are not generated from the templates. |
| `run.conf`, `run.sh` | Main SCALE-RM integration configuration and batch script. | `run.sh` calls `../case_tc/scale-rm run.conf`; `run.conf` specifies the restart input and history/restart output basenames. |
| `param.bucket.conf`, `PARAG.29`, `PARAPC.29`, `VARDATA.RM29`, `cira.nc`, `MIPAS/` | Static land/radiation inputs. | Referenced by `init.conf_base` (through `../...`) and by the root `init.conf`/`run.conf`. |

## Operational order

1. In `ensperturb/`, run `python sounding_perturb.py` to regenerate the 101
   sounding files when a new random ensemble is required.  The script has no
   fixed random seed, so rerunning it changes the ensemble.
2. From this directory, run `ensinit.sh`.  It submits 101 SCALE-RM initial
   condition jobs, one per sounding file.
3. After all initialization jobs complete successfully, run
   `preprocess_init.sh` to arrange the members under `letkfinput/`.
4. Submit `run.sh` when the `RESTART_IN_BASENAME` configured in `run.conf` is
   available.  The current `run.conf` points to
   `./init_per_SM_R131_0.1_1/perturbed_restart_20000131-000000.000`; that
   pathname is distinct from the direct `init` outputs made by `ensinit.sh`,
   so it must be created or updated by the appropriate downstream processing
   before the run can start.

## Version-control scope

The committed source set contains scripts, configurations, sounding inputs,
and the small static land/radiation inputs needed to understand and recreate
the setup.  Generated NetCDF files, member/output directories, logs, and
other run products are intentionally excluded: this working directory holds
about 603 GB of such products.
